"""
Data Extraction Engine - SOTA parsing for all document types.

Handles CSV, Excel (.xls/.xlsx), DOCX, PDF, and plain text files.
Uses scored keyword matching with LLM-assisted fallback for column detection.
Populates PSURContext fields from raw uploaded data.
Accumulates across multiple files of the same type instead of overwriting.
"""

import io
import json
import re
import traceback
from typing import Dict, List, Any, Optional

import pandas as pd

from backend.psur.context import PSURContext

# ---------------------------------------------------------------------------
# Column detection keyword maps (scored; higher = more confident match)
# Broadened with variations from data_processor.py and real-world naming
# ---------------------------------------------------------------------------

UNITS_KEYWORDS = {
    "units": 5, "quantity": 5, "qty": 5, "sold": 4, "distributed": 5,
    "shipped": 4, "volume": 3, "devices": 3, "amount": 3, "count": 3,
    "dispatched": 4, "delivered": 4, "sales_qty": 5, "unit_count": 5,
    "num_units": 5, "number_of_units": 5, "total_units": 5,
    "units_sold": 5, "units_shipped": 5, "units_distributed": 5,
    "number": 2, "total": 2, "pieces": 3, "items": 3,
}

YEAR_KEYWORDS = {
    "year": 5, "date": 4, "period": 3, "fiscal": 3, "quarter": 3,
    "month": 3, "calendar": 3, "reporting": 2, "ship_date": 4,
    "sale_date": 4, "transaction_date": 4, "order_date": 4,
    "report_date": 4, "event_date": 4, "complaint_date": 4,
    "received_date": 4, "created": 3, "opened": 3, "time": 2,
}

REGION_KEYWORDS = {
    "region": 5, "country": 5, "market": 4, "territory": 4,
    "geography": 3, "location": 3, "area": 2, "state": 2,
    "site": 2, "facility": 2, "distribution_region": 5,
}

SEVERITY_KEYWORDS = {
    "severity": 5, "priority": 4, "criticality": 5, "grade": 3,
    "impact": 3, "harm": 4, "seriousness": 5, "risk_level": 4,
    "risk_class": 4, "level": 3, "classification": 3,
    "patient_impact": 5, "injury_level": 5,
}

TYPE_KEYWORDS = {
    "type": 4, "category": 4, "classification": 3, "complaint_type": 5,
    "issue_type": 5, "event_type": 5, "incident_type": 5,
    "kind": 3, "class": 2, "code": 2, "problem_code": 4,
    "complaint_category": 5, "issue_category": 5,
}

ROOT_CAUSE_KEYWORDS = {
    "root": 4, "cause": 4, "determination": 3, "finding": 2,
    "reason": 3, "root_cause": 5, "failure_mode": 5,
    "defect": 3, "attribution": 4, "analysis": 2,
    "investigation_result": 5, "conclusion": 3, "outcome": 3,
}

CLOSURE_KEYWORDS = {
    "closed": 5, "closure": 5, "status": 3, "investigation": 4,
    "resolved": 4, "complete": 3, "outcome": 3, "state": 3,
    "disposition": 4, "investigation_status": 5, "case_status": 5,
    "resolution": 4, "open_closed": 5, "case_state": 5,
}

DESCRIPTION_KEYWORDS = {
    "description": 5, "narrative": 4, "detail": 3, "summary": 3,
    "complaint_description": 5, "event_description": 5, "text": 2,
    "notes": 2, "comment": 2, "remarks": 2, "report": 2,
}


def _score_column(col_name: str, keyword_map: Dict[str, int]) -> int:
    """Score a column name against a keyword map. Higher = better match."""
    col_lower = col_name.lower().strip().replace(" ", "_").replace("-", "_")
    total = 0
    for kw, weight in keyword_map.items():
        if kw == col_lower:
            return weight * 3  # Exact match bonus
        if kw in col_lower:
            total += weight
    return total


def _best_column(df: pd.DataFrame, keyword_map: Dict[str, int],
                 exclude: Optional[List[str]] = None) -> Optional[str]:
    """Find best matching column in a DataFrame using scored keyword matching."""
    best_col = None
    best_score = 0
    exclude = exclude or []
    for col in df.columns:
        if col in exclude:
            continue
        score = _score_column(col, keyword_map)
        if score > best_score:
            best_score = score
            best_col = col
    return best_col if best_score >= 3 else None


def _extract_year(val: Any) -> Optional[int]:
    """Robustly extract a 4-digit year from any value using regex."""
    s = str(val).strip()
    m = re.search(r"((?:19|20)\d{2})", s)
    if m:
        return int(m.group(1))
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# LLM-assisted column mapping fallback
# ---------------------------------------------------------------------------

def _llm_column_mapping(df: pd.DataFrame, file_type: str,
                        missing_roles: List[str]) -> Dict[str, Optional[str]]:
    """
    Use a fast LLM call to identify column mappings when heuristic detection
    fails for critical columns. Returns a dict of role -> column_name.
    """
    from backend.psur.ai_client import call_ai_sync

    columns = list(df.columns)
    # Build a sample of first 5 rows
    sample_rows = df.head(5).to_dict(orient="records")
    sample_str = json.dumps(sample_rows, default=str, indent=2)[:2000]

    role_descriptions = {
        "units": "the column containing the NUMBER of units/devices sold/distributed/shipped (numeric count)",
        "year": "the column containing the year or date of the transaction/event",
        "region": "the column containing the geographic region/country/market",
        "severity": "the column containing complaint/event severity level or priority",
        "type": "the column containing the complaint/event type or category",
        "root_cause": "the column containing the root cause or failure mode determination",
        "closure": "the column containing the investigation status (open/closed/resolved)",
    }

    roles_needed = {r: role_descriptions.get(r, r) for r in missing_roles}

    prompt = f"""You are a data column mapper for medical device post-market surveillance files.

Given these columns: {columns}

And this sample data:
{sample_str}

This is a {file_type} data file. Identify which column matches each role below.
Return ONLY a JSON object mapping role to column name. Use null if no match exists.

Roles needed:
{json.dumps(roles_needed, indent=2)}

Return ONLY valid JSON, nothing else. Example: {{"units": "Qty Shipped", "year": "Order Date"}}"""

    try:
        result = call_ai_sync("Quincy", "You are a data column identification assistant. Return only valid JSON.", prompt)
        if result:
            # Extract JSON from response
            json_match = re.search(r'\{[^}]+\}', result, re.DOTALL)
            if json_match:
                mapping = json.loads(json_match.group())
                # Validate that mapped columns actually exist
                validated = {}
                for role, col in mapping.items():
                    if col and col in df.columns:
                        validated[role] = col
                    else:
                        validated[role] = None
                print(f"[extraction] LLM column mapping result: {validated}")
                return validated
    except Exception as e:
        print(f"[extraction] LLM column mapping failed: {e}")

    return {r: None for r in missing_roles}


# ---------------------------------------------------------------------------
# File reading helpers
# ---------------------------------------------------------------------------

def read_dataframe(file_data: bytes, filename: str) -> Optional[pd.DataFrame]:
    """Read a file into a pandas DataFrame. Supports CSV, Excel, TSV."""
    fname_lower = filename.lower()
    try:
        if fname_lower.endswith(".csv"):
            return pd.read_csv(io.BytesIO(file_data), encoding_errors="replace")
        if fname_lower.endswith(".tsv"):
            return pd.read_csv(io.BytesIO(file_data), sep="\t", encoding_errors="replace")
        if fname_lower.endswith((".xls", ".xlsx")):
            engine = "openpyxl" if fname_lower.endswith(".xlsx") else "xlrd"
            return pd.read_excel(io.BytesIO(file_data), engine=engine)
        # Try CSV as fallback for unknown extensions
        text = file_data.decode("utf-8", errors="replace")
        if "," in text[:500] or "\t" in text[:500]:
            sep = "\t" if text[:500].count("\t") > text[:500].count(",") else ","
            return pd.read_csv(io.StringIO(text), sep=sep)
    except Exception as e:
        print(f"[extraction] ERROR reading {filename}: {e}")
        traceback.print_exc()
    return None


def read_docx_text(file_data: bytes) -> str:
    """Extract text from a DOCX file."""
    try:
        import docx
        doc = docx.Document(io.BytesIO(file_data))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as e:
        print(f"[extraction] DOCX read failed: {e}")
        return ""


def read_pdf_text(file_data: bytes) -> str:
    """Extract text from a PDF file."""
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(io.BytesIO(file_data)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
        return "\n".join(text_parts)
    except ImportError:
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(io.BytesIO(file_data))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            pass
    except Exception as e:
        print(f"[extraction] PDF read failed: {e}")
    return ""


# ---------------------------------------------------------------------------
# Raw sample builder
# ---------------------------------------------------------------------------

def _raw_sample(df: pd.DataFrame, n: int = 15) -> str:
    """Create a markdown table of the first n rows with truncated strings,
    followed by summary statistics for numeric and categorical columns."""
    sample = df.head(n).copy()
    for col in sample.columns:
        if sample[col].dtype == "object":
            sample[col] = sample[col].astype(str).str.slice(0, 60)
    try:
        table = sample.to_markdown(index=False) or ""
    except Exception:
        table = sample.to_string(index=False)

    stats_parts = [f"\n\n### Summary ({len(df)} total records)"]

    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            desc = df[col].describe()
            stats_parts.append(
                f"- {col}: min={desc.get('min', 'N/A')}, "
                f"max={desc.get('max', 'N/A')}, "
                f"mean={desc.get('mean', 'N/A'):.1f}, "
                f"sum={df[col].sum():,.0f}"
            )
        elif df[col].dtype == "object":
            vc = df[col].value_counts()
            if len(vc) <= 10:
                top_vals = ", ".join(f"{k}: {v}" for k, v in vc.items())
            else:
                top_vals = ", ".join(f"{k}: {v}" for k, v in vc.head(8).items())
                top_vals += f", ... ({len(vc)} unique)"
            stats_parts.append(f"- {col}: [{top_vals}]")

    return table + "\n".join(stats_parts)


# ---------------------------------------------------------------------------
# Extraction functions per file type
# ---------------------------------------------------------------------------

def extract_sales(df: pd.DataFrame, ctx: PSURContext, filename: str = "") -> Dict[str, Any]:
    """Extract sales / distribution metrics from a DataFrame into ctx.
    Accumulates across multiple sales files. Uses LLM fallback for column mapping."""
    diag: Dict[str, Any] = {"columns_detected": {}, "warnings": []}

    units_col = _best_column(df, UNITS_KEYWORDS)
    year_col = _best_column(df, YEAR_KEYWORDS, exclude=[units_col] if units_col else [])
    region_col = _best_column(df, REGION_KEYWORDS, exclude=[c for c in [units_col, year_col] if c])

    # LLM fallback for critical missing columns
    missing_roles = []
    if units_col is None:
        missing_roles.append("units")
    if year_col is None:
        missing_roles.append("year")
    if region_col is None:
        missing_roles.append("region")

    if missing_roles:
        print(f"[extraction] Sales file '{filename}': heuristic missed {missing_roles}. Trying LLM fallback...")
        llm_map = _llm_column_mapping(df, "sales/distribution", missing_roles)
        if units_col is None and llm_map.get("units"):
            units_col = llm_map["units"]
            diag["warnings"].append(f"Units column '{units_col}' identified by LLM fallback.")
        if year_col is None and llm_map.get("year"):
            year_col = llm_map["year"]
            diag["warnings"].append(f"Year column '{year_col}' identified by LLM fallback.")
        if region_col is None and llm_map.get("region"):
            region_col = llm_map["region"]
            diag["warnings"].append(f"Region column '{region_col}' identified by LLM fallback.")

    # Final fallback: first numeric column for units
    if units_col is None:
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]) and df[col].sum() > 0:
                units_col = col
                diag["warnings"].append(f"No units column matched; fell back to first numeric column '{col}'.")
                break

    diag["columns_detected"]["units"] = units_col
    diag["columns_detected"]["year"] = year_col
    diag["columns_detected"]["region"] = region_col

    print(f"[extraction] Sales '{filename}': units={units_col}, year={year_col}, region={region_col}")

    extracted_units = 0
    if units_col:
        try:
            numeric_series = pd.to_numeric(df[units_col], errors="coerce").fillna(0)
            file_total = int(numeric_series.sum())
            extracted_units = file_total
            ctx.total_units_sold += file_total
            ctx.cumulative_units_all_time += file_total
        except Exception as e:
            diag["warnings"].append(f"Error summing units column '{units_col}': {e}")
            print(f"[extraction] ERROR summing units: {e}")

    if units_col and year_col:
        try:
            df_copy = df[[year_col, units_col]].copy()
            df_copy[units_col] = pd.to_numeric(df_copy[units_col], errors="coerce").fillna(0)
            yearly = df_copy.groupby(year_col)[units_col].sum()
            for k, v in yearly.items():
                yr = _extract_year(k)
                if yr is not None:
                    ctx.total_units_by_year[yr] = ctx.total_units_by_year.get(yr, 0) + int(v)
        except Exception as e:
            diag["warnings"].append(f"Error in yearly aggregation: {e}")

    if units_col and region_col:
        try:
            df_copy = df[[region_col, units_col]].copy()
            df_copy[units_col] = pd.to_numeric(df_copy[units_col], errors="coerce").fillna(0)
            regional = df_copy.groupby(region_col)[units_col].sum()
            for k, v in regional.items():
                rk = str(k)
                ctx.total_units_by_region[rk] = ctx.total_units_by_region.get(rk, 0) + int(v)
            ctx.regions = list(set(ctx.regions) | set(ctx.total_units_by_region.keys()))
        except Exception as e:
            diag["warnings"].append(f"Error in regional aggregation: {e}")

    if units_col and extracted_units > 0:
        ctx.sales_data_available = True
    elif units_col:
        diag["warnings"].append(f"Units column '{units_col}' found but sum is 0. Check data.")
    else:
        diag["warnings"].append("CRITICAL: No units column could be identified in this sales file.")

    # Append raw sample
    header = f"\n#### Source: {filename}\n" if filename else ""
    new_sample = header + _raw_sample(df)
    ctx.sales_raw_sample = (ctx.sales_raw_sample + "\n\n" + new_sample).strip() if ctx.sales_raw_sample else new_sample
    ctx.sales_columns_detected = list(set(ctx.sales_columns_detected + list(df.columns)))

    print(f"[extraction] Sales result: {extracted_units:,} units extracted from '{filename}'")
    return diag


def extract_complaints(df: pd.DataFrame, ctx: PSURContext, filename: str = "") -> Dict[str, Any]:
    """Extract complaint metrics from a DataFrame into ctx.
    Accumulates across multiple complaint files. Uses LLM fallback."""
    diag: Dict[str, Any] = {"columns_detected": {}, "warnings": []}
    ctx.total_complaints += len(df)

    type_col = _best_column(df, TYPE_KEYWORDS)
    severity_col = _best_column(df, SEVERITY_KEYWORDS, exclude=[type_col] if type_col else [])
    root_col = _best_column(df, ROOT_CAUSE_KEYWORDS, exclude=[c for c in [type_col, severity_col] if c])
    closure_col = _best_column(df, CLOSURE_KEYWORDS, exclude=[c for c in [type_col, severity_col, root_col] if c])
    desc_col = _best_column(df, DESCRIPTION_KEYWORDS)
    year_col = _best_column(df, YEAR_KEYWORDS, exclude=[c for c in [type_col, severity_col, root_col, closure_col] if c])

    # LLM fallback for critical missing columns
    missing_roles = []
    if severity_col is None:
        missing_roles.append("severity")
    if type_col is None:
        missing_roles.append("type")
    if closure_col is None:
        missing_roles.append("closure")
    if root_col is None:
        missing_roles.append("root_cause")
    if year_col is None:
        missing_roles.append("year")

    if missing_roles:
        print(f"[extraction] Complaints file '{filename}': heuristic missed {missing_roles}. Trying LLM fallback...")
        llm_map = _llm_column_mapping(df, "complaints", missing_roles)
        if severity_col is None and llm_map.get("severity"):
            severity_col = llm_map["severity"]
        if type_col is None and llm_map.get("type"):
            type_col = llm_map["type"]
        if closure_col is None and llm_map.get("closure"):
            closure_col = llm_map["closure"]
        if root_col is None and llm_map.get("root_cause"):
            root_col = llm_map["root_cause"]
        if year_col is None and llm_map.get("year"):
            year_col = llm_map["year"]

    diag["columns_detected"] = {
        "type": type_col, "severity": severity_col, "root_cause": root_col,
        "closure": closure_col, "description": desc_col, "year": year_col,
    }

    print(f"[extraction] Complaints '{filename}': type={type_col}, severity={severity_col}, "
          f"root_cause={root_col}, closure={closure_col}, year={year_col}")

    # Complaint types
    if type_col:
        for k, v in df[type_col].value_counts().items():
            key = str(k)
            ctx.complaints_by_type[key] = ctx.complaints_by_type.get(key, 0) + int(v)

    # Severity breakdown
    if severity_col:
        for k, v in df[severity_col].value_counts().items():
            key = str(k)
            ctx.complaints_by_severity[key] = ctx.complaints_by_severity.get(key, 0) + int(v)
    else:
        diag["warnings"].append("No severity column detected; severity breakdown unavailable.")

    # Root cause categorization
    if root_col:
        cause_counts = df[root_col].value_counts().to_dict()
        has_root_cause = 0
        for cause, count in cause_counts.items():
            cl = str(cause).lower()
            c = int(count)
            if any(t in cl for t in [
                "defect", "product", "manufacturing", "design", "quality",
                "malfunction", "failure", "breakage", "fault", "component",
                "material", "electrical", "mechanical", "software", "wear",
            ]):
                ctx.complaints_product_defect += c
                has_root_cause += c
            elif any(t in cl for t in [
                "user", "error", "misuse", "operator", "training",
                "improper", "incorrect", "wrong",
            ]):
                ctx.complaints_user_error += c
                has_root_cause += c
            elif any(t in cl for t in [
                "unrelated", "environmental", "patient", "external",
                "no_fault", "not_device", "coincidental",
            ]):
                ctx.complaints_unrelated += c
                has_root_cause += c
            elif cl in ("", "nan", "none", "n/a", "unknown", "pending", "tbd"):
                ctx.complaints_unconfirmed += c
            else:
                ctx.complaints_unconfirmed += c
                has_root_cause += c
        ctx.complaints_with_root_cause_identified += has_root_cause
    else:
        diag["warnings"].append("No root cause column detected; root cause breakdown unavailable.")

    # Closure status
    if closure_col:
        closed_vals = df[closure_col].astype(str).str.lower()
        closed_pattern = r"closed|complete|resolved|done|finalized|investigated|concluded|finished"
        ctx.complaints_closed_count += int(closed_vals.str.contains(closed_pattern, case=False, na=False).sum())
    else:
        diag["warnings"].append("No closure/status column detected; investigation closure rate unknown.")

    # Complaints by year
    if year_col:
        for _, row in df.iterrows():
            yr = _extract_year(row[year_col])
            if yr is not None:
                ctx.total_complaints_by_year[yr] = ctx.total_complaints_by_year.get(yr, 0) + 1

    ctx.complaint_data_available = True
    header = f"\n#### Source: {filename}\n" if filename else ""
    new_sample = header + _raw_sample(df)
    ctx.complaints_raw_sample = (ctx.complaints_raw_sample + "\n\n" + new_sample).strip() if ctx.complaints_raw_sample else new_sample
    ctx.complaints_columns_detected = list(set(ctx.complaints_columns_detected + list(df.columns)))

    print(f"[extraction] Complaints result: {len(df)} complaints from '{filename}', "
          f"severity_col={severity_col is not None}, closure_col={closure_col is not None}")
    return diag


def extract_vigilance(df: pd.DataFrame, ctx: PSURContext, filename: str = "") -> Dict[str, Any]:
    """Extract vigilance / incident metrics from a DataFrame into ctx."""
    diag: Dict[str, Any] = {"columns_detected": {}, "warnings": []}
    ctx.total_vigilance_events += len(df)

    type_col = _best_column(df, TYPE_KEYWORDS)
    severity_col = _best_column(df, SEVERITY_KEYWORDS, exclude=[type_col] if type_col else [])

    diag["columns_detected"]["type"] = type_col
    diag["columns_detected"]["severity"] = severity_col

    SERIOUS_PATTERNS = r"serious|death|fatal|life.?threaten|hospitali|permanent|critical|severe"

    if severity_col:
        sev_vals = df[severity_col].astype(str).str.lower()
        serious_mask = sev_vals.str.contains(SERIOUS_PATTERNS, case=False, na=False)
        serious_df = df[serious_mask]
        ctx.serious_incidents += len(serious_df)

        effective_col = type_col or severity_col
        if effective_col:
            type_counts = serious_df[effective_col].value_counts().to_dict()
            for k, v in type_counts.items():
                key = str(k)
                ctx.serious_incidents_by_type[key] = ctx.serious_incidents_by_type.get(key, 0) + int(v)

        for _, row in serious_df.iterrows():
            tl = str(row[severity_col]).lower()
            if any(t in tl for t in ["death", "fatal", "deceased", "mortality"]):
                ctx.deaths += 1
            elif any(t in tl for t in ["injur", "harm", "hospitali", "permanent"]):
                ctx.serious_injuries += 1
    elif type_col:
        type_counts = df[type_col].value_counts().to_dict()
        for incident_type, count in type_counts.items():
            tl = str(incident_type).lower()
            key = str(incident_type)
            c = int(count)
            if any(t in tl for t in SERIOUS_PATTERNS.replace("|", " ").split()):
                ctx.serious_incidents += c
                ctx.serious_incidents_by_type[key] = ctx.serious_incidents_by_type.get(key, 0) + c
                if any(t in tl for t in ["death", "fatal", "deceased", "mortality"]):
                    ctx.deaths += c
                elif any(t in tl for t in ["injur", "harm", "hospitali", "permanent"]):
                    ctx.serious_injuries += c
            else:
                ctx.serious_incidents_by_type[key] = ctx.serious_incidents_by_type.get(key, 0) + c
        diag["warnings"].append("No severity column; serious incidents filtered by type keywords.")
    else:
        diag["warnings"].append(f"No severity or type column; cannot distinguish serious incidents. Records: {len(df)}.")

    ctx.vigilance_data_available = True
    header = f"\n#### Source: {filename}\n" if filename else ""
    new_sample = header + _raw_sample(df)
    ctx.vigilance_raw_sample = (ctx.vigilance_raw_sample + "\n\n" + new_sample).strip() if ctx.vigilance_raw_sample else new_sample
    ctx.vigilance_columns_detected = list(set(ctx.vigilance_columns_detected + list(df.columns)))

    print(f"[extraction] Vigilance result: {len(df)} events, {ctx.serious_incidents} serious from '{filename}'")
    return diag


def extract_text_context(text: str, ctx: PSURContext,
                         source_type: str = "general",
                         filename: str = "") -> Dict[str, Any]:
    """Extract contextual information from free-text documents."""
    diag: Dict[str, Any] = {"type": source_type, "length": len(text), "warnings": [], "columns_detected": {}}

    iu_match = re.search(r"intended\s+(?:use|purpose)[:\s]+(.+?)(?:\.\s|\n)", text, re.IGNORECASE)
    if iu_match and not ctx.intended_use:
        ctx.intended_use = iu_match.group(1).strip()

    dn_match = re.search(r"device\s+name[:\s]+(.+?)(?:\.\s|\n)", text, re.IGNORECASE)
    if dn_match and not ctx.device_name:
        ctx.device_name = dn_match.group(1).strip()

    mfr_match = re.search(r"(?:manufacturer|mfg|mfr)[:\s]+(.+?)(?:\.\s|\n)", text, re.IGNORECASE)
    if mfr_match and not ctx.manufacturer:
        ctx.manufacturer = mfr_match.group(1).strip()

    excerpt = text[:5000].replace("\n", " ").strip()
    if len(text) > 5000:
        dot = excerpt.rfind(".")
        if dot > 3000:
            excerpt = excerpt[:dot + 1]
        excerpt += " [...]"

    ctx.text_documents.append({
        "filename": filename or "unknown",
        "file_type": source_type,
        "length": len(text),
        "excerpt": excerpt,
    })

    return diag


def extract_supplementary(df: pd.DataFrame, ctx: PSURContext,
                          file_type: str, filename: str = "") -> Dict[str, Any]:
    """Extract data from supplementary file types (risk, cer, pmcf)."""
    diag: Dict[str, Any] = {"columns_detected": {}, "warnings": [], "records": len(df)}

    sample = _raw_sample(df)
    key = f"{file_type}:{filename}" if filename else file_type
    ctx.supplementary_raw_samples[key] = sample
    ctx.supplementary_columns[key] = list(df.columns)

    diag["warnings"].append(
        f"File '{filename}' ({file_type}): {len(df)} records. Stored for agent reference."
    )
    return diag


# ---------------------------------------------------------------------------
# Extraction summary (for debugging)
# ---------------------------------------------------------------------------

def generate_extraction_summary(ctx: PSURContext) -> Dict[str, Any]:
    """Generate a structured summary of what was extracted, for debugging."""
    return {
        "sales": {
            "available": ctx.sales_data_available,
            "total_units": ctx.total_units_sold,
            "cumulative": ctx.cumulative_units_all_time,
            "by_year": ctx.total_units_by_year,
            "by_region": ctx.total_units_by_region,
            "columns": ctx.sales_columns_detected,
        },
        "complaints": {
            "available": ctx.complaint_data_available,
            "total": ctx.total_complaints,
            "by_year": ctx.total_complaints_by_year,
            "by_type": ctx.complaints_by_type,
            "by_severity": ctx.complaints_by_severity,
            "closed": ctx.complaints_closed_count,
            "root_cause_identified": ctx.complaints_with_root_cause_identified,
            "columns": ctx.complaints_columns_detected,
        },
        "vigilance": {
            "available": ctx.vigilance_data_available,
            "total_events": ctx.total_vigilance_events,
            "serious": ctx.serious_incidents,
            "deaths": ctx.deaths,
            "serious_injuries": ctx.serious_injuries,
            "columns": ctx.vigilance_columns_detected,
        },
        "text_documents": len(ctx.text_documents),
        "supplementary_files": list(ctx.supplementary_raw_samples.keys()),
        "warnings": ctx.data_quality_warnings,
        "column_mappings": ctx.column_mappings,
    }


# ---------------------------------------------------------------------------
# Upload analysis (for immediate file preview in chat)
# ---------------------------------------------------------------------------

def analyze_upload(file_data: bytes, filename: str, file_type: str) -> Dict[str, Any]:
    """
    Quick analysis of an uploaded file for the upload endpoint.
    Returns {summary: str, metadata: dict} with column detection and statistics.
    This is separate from extract_from_file() which populates the PSURContext.
    """
    fname_lower = filename.lower()
    metadata: Dict[str, Any] = {"columns_detected": {}, "all_columns": [], "record_count": 0}

    if fname_lower.endswith(".docx"):
        text = read_docx_text(file_data)
        if text:
            preview = text[:5000]
            if len(text) > 5000:
                preview += "\n...[Truncated]..."
            return {
                "summary": f"DOCX content from {filename} ({len(text)} chars): {preview[:500]}...",
                "metadata": {"source": "docx", "chars": len(text)},
            }
        return {"summary": f"Could not read DOCX: {filename}", "metadata": metadata}

    if fname_lower.endswith(".pdf"):
        text = read_pdf_text(file_data)
        if text:
            return {
                "summary": f"PDF content from {filename} ({len(text)} chars): {text[:500]}...",
                "metadata": {"source": "pdf", "chars": len(text)},
            }
        return {"summary": f"Could not read PDF: {filename}", "metadata": metadata}

    df = read_dataframe(file_data, filename)
    if df is None or df.empty:
        return {"summary": f"Could not parse data from {filename}", "metadata": metadata}

    metadata["all_columns"] = list(df.columns)
    metadata["record_count"] = len(df)

    # Detect key columns using the same scoring engine
    if file_type == "sales":
        metadata["columns_detected"]["units"] = _best_column(df, UNITS_KEYWORDS)
        metadata["columns_detected"]["year"] = _best_column(df, YEAR_KEYWORDS)
        metadata["columns_detected"]["region"] = _best_column(df, REGION_KEYWORDS)
    elif file_type == "complaints":
        metadata["columns_detected"]["severity"] = _best_column(df, SEVERITY_KEYWORDS)
        metadata["columns_detected"]["closure"] = _best_column(df, CLOSURE_KEYWORDS)
        metadata["columns_detected"]["type"] = _best_column(df, TYPE_KEYWORDS)
        metadata["columns_detected"]["root_cause"] = _best_column(df, ROOT_CAUSE_KEYWORDS)
    elif file_type in ("vigilance", "maude"):
        metadata["columns_detected"]["type"] = _best_column(df, TYPE_KEYWORDS)
        metadata["columns_detected"]["severity"] = _best_column(df, SEVERITY_KEYWORDS)

    # Build summary
    parts = [
        f"### ANALYSIS OF {file_type.upper()} DATA ({filename})",
        f"Records: {len(df)}",
        f"Columns: {', '.join(df.columns)}",
    ]

    for role, col in metadata["columns_detected"].items():
        parts.append(f"{role.title()} Column: {col if col else 'NOT DETECTED'}")

    # Numeric summaries
    numeric_cols = df.select_dtypes(include=["number"]).columns
    if len(numeric_cols) > 0:
        sums = df[numeric_cols].sum()
        parts.append("\nNumeric Totals:")
        for c in numeric_cols:
            parts.append(f"  {c}: {sums[c]:,.0f}")

    # Sample rows
    sample = df.head(10).to_string(index=False, max_colwidth=40)
    parts.append(f"\nSample (first 10 rows):\n{sample}")

    return {"summary": "\n".join(parts), "metadata": metadata}


# ---------------------------------------------------------------------------
# Main extraction orchestrator
# ---------------------------------------------------------------------------

def extract_from_file(file_data: bytes, filename: str, file_type: str,
                      ctx: PSURContext) -> Dict[str, Any]:
    """
    Top-level extraction: given raw bytes and user-selected file_type,
    parse and populate the relevant PSURContext fields.
    Returns diagnostics dict with columns_detected, warnings, etc.
    """
    fname_lower = filename.lower()
    print(f"[extraction] Processing '{filename}' as '{file_type}'...")

    # For document types, extract text
    if fname_lower.endswith(".docx"):
        text = read_docx_text(file_data)
        if text:
            return extract_text_context(text, ctx, source_type=file_type, filename=filename)
        return {"warnings": [f"DOCX file '{filename}' could not be read."], "columns_detected": {}}

    if fname_lower.endswith(".pdf"):
        text = read_pdf_text(file_data)
        if text:
            return extract_text_context(text, ctx, source_type=file_type, filename=filename)
        return {"warnings": [f"PDF file '{filename}' could not be read."], "columns_detected": {}}

    if fname_lower.endswith(".txt"):
        text = file_data.decode("utf-8", errors="replace")
        return extract_text_context(text, ctx, source_type=file_type, filename=filename)

    # For tabular files, read as DataFrame
    df = read_dataframe(file_data, filename)
    if df is None or df.empty:
        msg = f"Could not parse tabular data from '{filename}'."
        print(f"[extraction] ERROR: {msg}")
        return {"warnings": [msg], "columns_detected": {}}

    print(f"[extraction] Loaded {len(df)} rows, {len(df.columns)} columns from '{filename}': {list(df.columns)}")

    # Route to the correct extractor based on user-selected file_type
    if file_type == "sales":
        return extract_sales(df, ctx, filename=filename)
    elif file_type == "complaints":
        return extract_complaints(df, ctx, filename=filename)
    elif file_type == "vigilance":
        return extract_vigilance(df, ctx, filename=filename)
    else:
        return extract_supplementary(df, ctx, file_type=file_type, filename=filename)
