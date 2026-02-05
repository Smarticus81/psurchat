import pandas as pd  # type: ignore[reportMissingImports]
import io
import re
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import docx  # type: ignore[reportMissingImports]

class DataProcessor:
    """
    Robust Data Processing Engine
    Handles CSV, Excel, and DOCX files.
    Extracts raw data samples and statistical summaries for AI reasoning.
    """
    
    @staticmethod
    def process_file(content: bytes, filename: str, file_type: str) -> Dict[str, Any]:
        """Process file content (bytes) and return analysis."""
        try:
            name_lower = (filename or "").lower()
            
            if name_lower.endswith('.docx') or file_type == 'cer':
                return DataProcessor._process_docx_bytes(content, filename)
            
            buf = io.BytesIO(content)
            if name_lower.endswith('.csv'):
                try:
                    df = pd.read_csv(buf, encoding='utf-8', on_bad_lines='skip')
                except UnicodeDecodeError:
                    buf.seek(0)
                    df = pd.read_csv(buf, encoding='latin-1', on_bad_lines='skip')
            elif name_lower.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(buf, engine='openpyxl' if name_lower.endswith('.xlsx') else None)
            else:
                return {"summary": "Unsupported file format.", "metadata": {}}

            return DataProcessor._analyze_dataframe(df, file_type)
            
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            return {"summary": f"Error processing file: {str(e)}", "metadata": {}}

    @staticmethod
    def _process_docx_bytes(content: bytes, filename: str) -> Dict[str, Any]:
        """Extract text from DOCX from bytes"""
        try:
            doc = docx.Document(io.BytesIO(content))
            full_text = []
            for para in doc.paragraphs:
                if para.text.strip():
                    full_text.append(para.text)
            
            text_content = "\n".join(full_text)
            # Limit context size to prevent overflow
            summary = f"### CONTENT FROM {os.path.basename(filename)}\n\n"
            summary += text_content[:15000] 
            
            if len(text_content) > 15000:
                summary += "\n...[Content Truncated]..."
                
            return {
                "summary": summary,
                "metadata": {"source": "docx", "chars": len(text_content)}
            }
        except Exception as e:
             return {"summary": f"Error reading DOCX: {str(e)}", "metadata": {}}

    @staticmethod
    def _analyze_dataframe(df: pd.DataFrame, file_type: str) -> Dict[str, Any]:
        """Generate statistical summary of dataframe"""
        summary = ""
        metadata = {
            "columns_detected": {},
            "all_columns": list(df.columns),
            "record_count": len(df),
        }
        
        try:
            # Basic info
            summary += f"### ANALYSIS OF {file_type.upper()} DATA\n"
            summary += f"Total Records: {len(df)}\n"
            summary += f"Columns: {', '.join(df.columns)}\n\n"
            
            # Detect key columns based on file type and add to summary
            summary += "**Column Detection Results:**\n"
            if file_type == "sales":
                units_col = next((c for c in df.columns if any(x in c.lower() for x in ['units', 'quantity', 'qty', 'sold', 'distributed', 'shipped', 'volume', 'amount', 'count'])), None)
                year_col = next((c for c in df.columns if any(x in c.lower() for x in ['year', 'date', 'period', 'fiscal'])), None)
                metadata["columns_detected"]["units"] = units_col
                metadata["columns_detected"]["year"] = year_col
                summary += f"- Units Column: {units_col or 'NOT DETECTED - check column names'}\n"
                summary += f"- Year/Date Column: {year_col or 'NOT DETECTED'}\n"
            elif file_type == "complaints":
                severity_col = next((c for c in df.columns if any(x in c.lower() for x in ['severity', 'priority', 'level', 'criticality', 'grade', 'impact', 'harm', 'classification'])), None)
                closure_col = next((c for c in df.columns if any(x in c.lower() for x in ['closed', 'closure', 'status', 'investigation', 'state', 'resolved', 'outcome', 'disposition'])), None)
                type_col = next((c for c in df.columns if any(x in c.lower() for x in ['type', 'category', 'classification', 'kind'])), None)
                root_cause_col = next((c for c in df.columns if any(x in c.lower() for x in ['root', 'cause', 'determination', 'finding', 'reason', 'failure'])), None)
                metadata["columns_detected"]["severity"] = severity_col
                metadata["columns_detected"]["closure"] = closure_col
                metadata["columns_detected"]["type"] = type_col
                metadata["columns_detected"]["root_cause"] = root_cause_col
                summary += f"- Severity Column: {severity_col or 'NOT DETECTED - check column names'}\n"
                summary += f"- Closure/Status Column: {closure_col or 'NOT DETECTED'}\n"
                summary += f"- Type/Category Column: {type_col or 'NOT DETECTED'}\n"
                summary += f"- Root Cause Column: {root_cause_col or 'NOT DETECTED'}\n"
            elif file_type in ("vigilance", "maude"):
                type_col = next((c for c in df.columns if any(x in c.lower() for x in ['type', 'category', 'outcome', 'event', 'incident', 'harm'])), None)
                metadata["columns_detected"]["type"] = type_col
                summary += f"- Event Type Column: {type_col or 'NOT DETECTED'}\n"
            summary += "\n"
            
            # 1. Metadata Detection (Deep Scan)
            metadata['udi_di'] = "Pending Extraction"
            
            # Check Column Headers
            udi_col = next((c for c in df.columns if re.search(r'(udi|gtin|device.?id|material|sku)', str(c), re.IGNORECASE)), None)
            
            if udi_col:
                top_udi = df[udi_col].mode()
                if not top_udi.empty:
                    metadata['udi_di'] = str(top_udi[0])
                    summary += f"**Detected UDI-DI (from column '{udi_col}')**: {top_udi[0]}\n"
            else:
                try:
                    head_str = df.head(20).to_string()
                    match = re.search(r'(?:UDI|GTIN|Global Trade Item Number)[\s:._-]*([0-9A-Za-z]{10,20})', head_str, re.IGNORECASE)
                    if match:
                         metadata['udi_di'] = match.group(1)
                         summary += f"**Detected UDI-DI (from header search)**: {match.group(1)}\n"
                except:
                    pass

            # 2. Key Statistics (Safe Numeric Summation)
            summary += "#### KEY STATISTICS:\n"
            numeric_cols = df.select_dtypes(include=['number']).columns
            
            # Coerce potential numeric columns if none found
            if len(numeric_cols) == 0:
                 potential_nums = [c for c in df.columns if re.search(r'(qty|quantity|amount|price|sales|revenue|count)', str(c), re.IGNORECASE)]
                 for c in potential_nums:
                     df[c] = pd.to_numeric(df[c], errors='coerce')
                 numeric_cols = df.select_dtypes(include=['number']).columns

            if len(numeric_cols) > 0:
                # Group by if applicable
                cat_cols = df.select_dtypes(include=['object']).columns
                region_col = next((c for c in cat_cols if 'country' in c.lower() or 'region' in c.lower() or 'state' in c.lower()), None)
                
                if region_col:
                     summary += f"**Breakdown by {region_col}**:\n"
                     grp = df.groupby(region_col)[numeric_cols].sum(numeric_only=True).sort_values(by=numeric_cols[0], ascending=False).head(5)
                     summary += grp.to_markdown() + "\n\n"
                else:
                    sums = df[numeric_cols].sum(numeric_only=True)
                    summary += "**Total Sums**:\n"
                    summary += sums.to_markdown() + "\n\n"

            # 3. Categorical Counts
            summary += "#### CATEGORICAL DISTRIBUTION:\n"
            cat_cols = df.select_dtypes(include=['object']).columns
            for col in cat_cols:
                if df[col].nunique() > 50 or df[col].nunique() < 2:
                    continue
                if re.search(r'(description|comment|narrative|text)', col, re.IGNORECASE):
                    continue
                    
                top_n = df[col].value_counts().head(5)
                summary += f"**Top 5 {col}**:\n"
                summary += top_n.to_markdown() + "\n\n"

            # 4. Raw Data Samples
            summary += "#### RAW DATA SAMPLE (First 20 rows):\n"
            df_preview = df.head(20).copy()
            for c in df_preview.columns:
                if df_preview[c].dtype == 'object':
                    df_preview[c] = df_preview[c].astype(str).str.slice(0, 50) 
            
            summary += df_preview.to_markdown(index=False)
            
            return {"summary": summary, "metadata": metadata}
            
        except Exception as e:
            return {"summary": f"Error analyzing data: {str(e)}", "metadata": metadata}


# =============================================================================
# MASTER CONTEXT EXTRACTOR - Single golden source for all agents
# =============================================================================

def _safe_int(v: Any) -> int:
    try:
        return int(v) if v is not None else 0
    except (ValueError, TypeError):
        return 0


def _in_reporting_period(
    row_ts: Any,
    period_start: Optional[datetime],
    period_end: Optional[datetime],
    date_cols: List[str],
) -> bool:
    if not period_start or not period_end:
        return True
    for col in date_cols:
        val = row_ts.get(col) if isinstance(row_ts, dict) else getattr(row_ts, col, None)
        if val is None:
            continue
        if isinstance(val, datetime):
            dt = val
        else:
            try:
                dt = pd.to_datetime(val)
            except Exception:
                continue
        if period_start <= dt <= period_end:
            return True
    return False


class MasterContextExtractor:
    """
    Extracts a single canonical master context from session data files and intake.
    All section agents must use these numbers and flags only (no per-agent re-interpretation).
    """

    DEFAULT_CLOSURE_DEFINITION = (
        "Closed = investigation completed with root cause documented and recorded."
    )
    DEFAULT_INFERENCE_POLICY = "strictly_factual"
    DEFAULT_DENOMINATOR_SCOPE = "reporting_period_only"

    # Comprehensive column keyword lists for robust detection
    UNITS_KEYWORDS = [
        'units', 'quantity', 'qty', 'sold', 'distributed', 'shipped',
        'volume', 'amount', 'count', 'total', 'devices', 'pieces',
        'inventory', 'stock', 'dispatched', 'delivered', 'sales_qty',
        'unit_count', 'num_units', 'number'
    ]

    YEAR_KEYWORDS = [
        'year', 'date', 'period', 'fiscal', 'quarter', 'month',
        'time', 'calendar', 'reporting', 'ship_date', 'sale_date',
        'transaction_date', 'order_date'
    ]

    SEVERITY_KEYWORDS = [
        'severity', 'priority', 'level', 'criticality', 'grade',
        'impact', 'harm', 'seriousness', 'classification', 'risk_level',
        'risk', 'class', 'category', 'importance', 'urgency', 'tier'
    ]

    CLOSURE_KEYWORDS = [
        'closed', 'closure', 'status', 'investigation', 'state',
        'resolved', 'complete', 'outcome', 'disposition', 'final',
        'investigation_status', 'case_status', 'resolution', 'result'
    ]

    ROOT_CAUSE_KEYWORDS = [
        'root', 'cause', 'determination', 'finding', 'reason',
        'root_cause', 'failure', 'failure_mode', 'defect', 'issue',
        'problem', 'analysis', 'conclusion', 'attribution'
    ]

    TYPE_KEYWORDS = [
        'type', 'category', 'classification', 'complaint_type',
        'issue_type', 'event_type', 'incident_type', 'kind'
    ]

    # Patterns for matching closed status values
    CLOSED_PATTERNS = r'closed|complete|resolved|done|finalized|investigated|concluded|finished|verified|confirmed'

    @staticmethod
    def extract(
        data_files: List[Any],
        period_start: Optional[datetime],
        period_end: Optional[datetime],
        intake: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Build master context from list of DataFile-like objects (with file_type, filename, file_data)
        and optional intake (denominator_scope, inference_policy, closure_definition,
        external_vigilance_searched, complaint_closures_complete, rmf_hazard_list_available, intended_use_provided).
        """
        intake = intake or {}
        denominator_scope = intake.get("denominator_scope") or MasterContextExtractor.DEFAULT_DENOMINATOR_SCOPE
        inference_policy = intake.get("inference_policy") or MasterContextExtractor.DEFAULT_INFERENCE_POLICY
        closure_definition = intake.get("closure_definition") or MasterContextExtractor.DEFAULT_CLOSURE_DEFINITION
        baseline_year = intake.get("baseline_year")

        annual_units: Dict[int, int] = {}
        reporting_period_units = 0
        cumulative_units = 0
        total_complaints = 0
        complaints_closed_canonical = 0
        closure_col_found = False
        has_sales = False
        has_complaints = False
        has_vigilance = False
        has_risk_rmf = False

        # Column mapping tracking for diagnostics
        column_mapping: Dict[str, Any] = {
            "sales": {"units_column": None, "year_column": None, "all_columns": []},
            "complaints": {"severity_column": None, "closure_column": None, "type_column": None, "root_cause_column": None, "all_columns": []},
            "vigilance": {"type_column": None, "all_columns": []},
        }
        parsing_warnings: List[str] = []

        for data_file in data_files:
            file_type = getattr(data_file, "file_type", None) or ""
            filename = getattr(data_file, "filename", "") or ""
            file_data = getattr(data_file, "file_data", b"")
            name_lower = (filename or "").lower()
            if name_lower.endswith(".docx") or file_type == "cer":
                if file_type in ("risk", "rmf", "risk_rmf"):
                    has_risk_rmf = True
                continue
            try:
                content = file_data.decode("utf-8", errors="replace") if isinstance(file_data, bytes) else str(file_data)
            except Exception:
                content = ""
            if not content and isinstance(file_data, bytes):
                continue
            if name_lower.endswith(".csv"):
                try:
                    df = pd.read_csv(io.StringIO(content), encoding="utf-8", on_bad_lines="skip")
                except Exception:
                    try:
                        df = pd.read_csv(io.StringIO(content), encoding="latin-1", on_bad_lines="skip")
                    except Exception:
                        continue
            elif name_lower.endswith((".xls", ".xlsx")):
                try:
                    df = pd.read_excel(io.BytesIO(file_data) if isinstance(file_data, bytes) else io.BytesIO(content.encode() if isinstance(content, str) else content), engine="openpyxl" if name_lower.endswith(".xlsx") else None)
                except Exception:
                    continue
            else:
                continue

            if file_type == "sales":
                has_sales = True
                column_mapping["sales"]["all_columns"] = list(df.columns)
                units_col = None
                year_col = None
                for c in df.columns:
                    cl = str(c).lower()
                    if units_col is None and any(x in cl for x in MasterContextExtractor.UNITS_KEYWORDS):
                        units_col = c
                    if year_col is None and any(x in cl for x in MasterContextExtractor.YEAR_KEYWORDS):
                        year_col = c
                # Fallback: use first numeric column if no units column found
                if units_col is None:
                    for c in df.columns:
                        if pd.api.types.is_numeric_dtype(df[c]):
                            units_col = c
                            parsing_warnings.append(f"Sales: No units column found by keyword; using first numeric column '{c}'")
                            break
                # Track mapping
                column_mapping["sales"]["units_column"] = units_col
                column_mapping["sales"]["year_column"] = year_col
                if units_col is None:
                    parsing_warnings.append(f"Sales ({filename}): Could not detect units/quantity column. Available columns: {list(df.columns)}")
                if units_col is not None:
                    total_sum = _safe_int(df[units_col].sum())
                    cumulative_units += total_sum
                    if year_col is not None:
                        try:
                            for y, g in df.groupby(year_col):
                                try:
                                    yr = int(y) if isinstance(y, (int, float)) else int(pd.to_datetime(y).year)
                                except Exception:
                                    yr = datetime.now().year
                                annual_units[yr] = annual_units.get(yr, 0) + _safe_int(g[units_col].sum())
                        except Exception:
                            annual_units[datetime.now().year] = total_sum
                    else:
                        annual_units[period_start.year if period_start else datetime.now().year] = annual_units.get(period_start.year if period_start else datetime.now().year, 0) + total_sum
                    if period_start is not None and period_end is not None and year_col is not None:
                        try:
                            df_date = df.copy()
                            df_date["_parsed_year"] = pd.to_numeric(df_date[year_col], errors="coerce").fillna(0).astype(int)
                            start_y, end_y = period_start.year, period_end.year
                            mask = (df_date["_parsed_year"] >= start_y) & (df_date["_parsed_year"] <= end_y)
                            reporting_period_units += _safe_int(df_date.loc[mask, units_col].sum())
                        except Exception:
                            if reporting_period_units == 0:
                                reporting_period_units = total_sum
                    elif reporting_period_units == 0:
                        reporting_period_units = total_sum
            elif file_type == "complaints":
                has_complaints = True
                column_mapping["complaints"]["all_columns"] = list(df.columns)
                total_complaints += len(df)
                
                # Look for closure column
                for c in df.columns:
                    cl = str(c).lower()
                    if any(x in cl for x in MasterContextExtractor.CLOSURE_KEYWORDS):
                        closure_col_found = True
                        column_mapping["complaints"]["closure_column"] = c
                        try:
                            closed_vals = df[c].astype(str).str.lower()
                            complaints_closed_canonical = int((closed_vals.str.contains(MasterContextExtractor.CLOSED_PATTERNS, case=False, na=False)).sum())
                        except Exception:
                            pass
                        break
                
                # Look for severity column
                for c in df.columns:
                    cl = str(c).lower()
                    if any(x in cl for x in MasterContextExtractor.SEVERITY_KEYWORDS):
                        column_mapping["complaints"]["severity_column"] = c
                        break
                
                # Look for type column
                for c in df.columns:
                    cl = str(c).lower()
                    if any(x in cl for x in MasterContextExtractor.TYPE_KEYWORDS):
                        column_mapping["complaints"]["type_column"] = c
                        break
                
                # Look for root cause column
                for c in df.columns:
                    cl = str(c).lower()
                    if any(x in cl for x in MasterContextExtractor.ROOT_CAUSE_KEYWORDS):
                        column_mapping["complaints"]["root_cause_column"] = c
                        break
                
                # Add warnings for missing columns
                if not column_mapping["complaints"]["closure_column"]:
                    parsing_warnings.append(f"Complaints ({filename}): No closure/status column detected. Available columns: {list(df.columns)}")
                if not column_mapping["complaints"]["severity_column"]:
                    parsing_warnings.append(f"Complaints ({filename}): No severity column detected. Available columns: {list(df.columns)}")
            elif file_type in ("vigilance", "maude"):
                has_vigilance = True
                column_mapping["vigilance"]["all_columns"] = list(df.columns)
                # Look for type column
                for c in df.columns:
                    cl = str(c).lower()
                    if any(x in cl for x in MasterContextExtractor.TYPE_KEYWORDS + ['outcome', 'event', 'incident', 'harm']):
                        column_mapping["vigilance"]["type_column"] = c
                        break
            elif file_type in ("risk", "rmf", "risk_rmf"):
                has_risk_rmf = True

        if reporting_period_units == 0 and period_start is not None and period_end is not None and annual_units:
            start_y, end_y = period_start.year, period_end.year
            reporting_period_units = sum(annual_units.get(y, 0) for y in range(start_y, end_y + 1))

        if denominator_scope == "cumulative_with_baseline" and baseline_year is not None:
            try:
                baseline_year_int = int(baseline_year)
                exposure_denominator_value = sum(v for y, v in annual_units.items() if y >= baseline_year_int)
            except (ValueError, TypeError):
                exposure_denominator_value = cumulative_units or reporting_period_units
        elif denominator_scope == "reporting_period_only":
            exposure_denominator_value = reporting_period_units if reporting_period_units > 0 else cumulative_units
        else:
            exposure_denominator_value = cumulative_units if cumulative_units > 0 else reporting_period_units

        if exposure_denominator_value <= 0 and annual_units:
            exposure_denominator_value = sum(annual_units.values())

        data_availability = {
            "external_vigilance_searched": bool(intake.get("external_vigilance_searched", False)),
            "complaint_closures_complete": bool(intake.get("complaint_closures_complete", False)),
            "rmf_hazard_list_available": bool(intake.get("rmf_hazard_list_available", has_risk_rmf)),
            "intended_use_provided": bool(intake.get("intended_use_provided", False)),
        }

        return {
            "exposure_denominator_scope": denominator_scope,
            "exposure_denominator_value": int(exposure_denominator_value),
            "annual_units_canonical": {int(k): int(v) for k, v in annual_units.items()},
            "baseline_year": int(baseline_year) if baseline_year is not None else None,
            "closure_definition_text": str(closure_definition),
            "complaints_closed_canonical": int(complaints_closed_canonical),
            "total_complaints_canonical": int(total_complaints),
            "inference_policy": str(inference_policy),
            "data_availability": data_availability,
            "has_sales": has_sales,
            "has_complaints": has_complaints,
            "has_vigilance": has_vigilance,
            "has_risk_rmf": has_risk_rmf,
            # Column mapping diagnostics
            "column_mapping": column_mapping,
            "parsing_warnings": parsing_warnings,
        }
