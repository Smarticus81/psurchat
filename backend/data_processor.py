import pandas as pd
import io
import re
import os
from typing import Dict, Any
import docx  # python-docx

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
                df = pd.read_csv(buf, encoding='utf-8', on_bad_lines='skip')
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
        metadata = {}
        
        try:
            # Basic info
            summary += f"### ANALYSIS OF {file_type.upper()} DATA\n"
            summary += f"Total Records: {len(df)}\n"
            summary += f"Columns: {', '.join(df.columns)}\n\n"
            
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
