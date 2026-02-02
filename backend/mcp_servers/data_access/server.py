"""
MCP Data Access Server
Exposes tools for querying sales data, complaints, and device metadata
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json
from mcp.server import Server, Tool
from mcp.types import TextContent
from sqlalchemy.orm import Session
import io
from backend.database.session import get_db_context
from backend.database.models import DataFile
import pandas as pd


class DataAccessServer:
    """MCP Server for data access operations"""
    
    def __init__(self):
        self.server = Server("data-access")
        self.register_tools()
    
    def register_tools(self):
        """Register all data access tools"""
        
        @self.server.tool()
        async def get_sales_data(
            session_id: int,
            region: Optional[str] = None,
            date_range: Optional[Dict[str, str]] = None,
            product_filter: Optional[str] = None
        ) -> Dict[str, Any]:
            """
            Retrieve sales data from uploaded files
            
            Args:
                session_id: PSUR session ID
                region: Optional region filter (e.g., 'EU', 'US', 'Global')
                date_range: Optional date range {'start': 'YYYY-MM-DD', 'end': 'YYYY-MM-DD'}
                product_filter: Optional product/catalog number filter
            
            Returns:
                Dict containing sales data, totals, and regional breakdown
            """
            with get_db_context() as db:
                sales_file = db.query(DataFile).filter(
                    DataFile.session_id == session_id,
                    DataFile.file_type.in_(["sales_data", "sales"]),
                    DataFile.file_data.isnot(None)
                ).first()
                
                if not sales_file or not sales_file.file_data:
                    return {
                        "error": "No valid sales data file found",
                        "status": "error"
                    }
                
                try:
                    df = pd.read_excel(io.BytesIO(sales_file.file_data), engine="openpyxl")
                    cols = [c for c in df.columns]
                    
                    if region and region != "Global":
                        region_col = next((c for c in cols if "region" in str(c).lower()), None)
                        if region_col:
                            df = df[df[region_col] == region]
                    
                    if date_range:
                        date_col = next((c for c in cols if "date" in str(c).lower()), None)
                        if date_col:
                            start = pd.to_datetime(date_range.get("start"))
                            end = pd.to_datetime(date_range.get("end"))
                            df = df[(pd.to_datetime(df[date_col], errors="coerce") >= start) &
                                   (pd.to_datetime(df[date_col], errors="coerce") <= end)]
                    
                    if product_filter:
                        product_col = next((c for c in cols if "product" in str(c).lower() or "catalog" in str(c).lower()), None)
                        if product_col and df[product_col].dtype == object:
                            df = df[df[product_col].astype(str).str.contains(product_filter, case=False, na=False)]
                    
                    units_col = next((c for c in cols if "unit" in str(c).lower() or "qty" in str(c).lower() or "quantity" in str(c).lower()), None)
                    total_units = int(df[units_col].sum()) if units_col else len(df)
                    region_col = next((c for c in cols if "region" in str(c).lower()), None)
                    regional_breakdown = df.groupby(region_col)[units_col].sum().to_dict() if region_col and units_col else {"total": total_units}
                    
                    return {
                        "status": "success",
                        "total_units_sold": total_units,
                        "regional_breakdown": regional_breakdown,
                        "records": len(df),
                        "data": df.head(100).to_dict("records"),
                        "filters_applied": {"region": region, "date_range": date_range, "product_filter": product_filter}
                    }
                except Exception as e:
                    return {
                        "error": f"Failed to process sales data: {str(e)}",
                        "status": "error"
                    }
        
        @self.server.tool()
        async def query_complaints(
            session_id: int,
            filters: Optional[Dict[str, Any]] = None,
            aggregation: Optional[str] = None
        ) -> Dict[str, Any]:
            """
            Query complaint data with filters and aggregation
            
            Args:
                session_id: PSUR session ID
                filters: Optional filters {'severity': ['serious', 'non-serious'], 'category': [...]}
                aggregation: Optional aggregation method ('by_category', 'by_month', 'by_severity')
            
            Returns:
                Dict containing complaint data and statistics
            """
            with get_db_context() as db:
                complaints_file = db.query(DataFile).filter(
                    DataFile.session_id == session_id,
                    DataFile.file_type == "complaints",
                    DataFile.file_data.isnot(None)
                ).first()
                
                if not complaints_file or not complaints_file.file_data:
                    return {
                        "error": "No valid complaints file found",
                        "status": "error"
                    }
                
                try:
                    df = pd.read_excel(io.BytesIO(complaints_file.file_data), engine="openpyxl")
                    cols = {str(c).lower(): c for c in df.columns}
                    
                    if filters:
                        severity_col = next((cols[k] for k in cols if "severity" in k), None)
                        if severity_col and "severity" in (filters or {}):
                            df = df[df[severity_col].isin(filters["severity"])]
                        cat_col = next((cols[k] for k in cols if "imdrf" in k or "category" in k), None)
                        if cat_col and "category" in (filters or {}):
                            df = df[df[cat_col].isin(filters["category"])]
                        date_col = next((cols[k] for k in cols if "date" in k), None)
                        if date_col and filters.get("date_range"):
                            start = pd.to_datetime(filters["date_range"].get("start"))
                            end = pd.to_datetime(filters["date_range"].get("end"))
                            df = df[(pd.to_datetime(df[date_col], errors="coerce") >= start) &
                                   (pd.to_datetime(df[date_col], errors="coerce") <= end)]
                    
                    total_complaints = len(df)
                    aggregated_data = {}
                    cat_col = next((cols[k] for k in cols if "imdrf" in k or "category" in k), None)
                    severity_col = next((cols[k] for k in cols if "severity" in k), None)
                    date_col = next((cols[k] for k in cols if "date" in k), None)
                    
                    if aggregation == "by_category" and cat_col:
                        aggregated_data = df.groupby(cat_col).size().to_dict()
                        aggregated_data = {str(k): int(v) for k, v in aggregated_data.items()}
                    elif aggregation == "by_month" and date_col:
                        df = df.copy()
                        df["_month"] = pd.to_datetime(df[date_col], errors="coerce").dt.to_period("M")
                        aggregated_data = df.groupby("_month").size().to_dict()
                        aggregated_data = {str(k): int(v) for k, v in aggregated_data.items()}
                    elif aggregation == "by_severity" and severity_col:
                        aggregated_data = df.groupby(severity_col).size().to_dict()
                        aggregated_data = {str(k): int(v) for k, v in aggregated_data.items()}
                    elif not aggregated_data and cat_col:
                        aggregated_data = df.groupby(cat_col).size().to_dict()
                        aggregated_data = {str(k): int(v) for k, v in aggregated_data.items()}
                    
                    return {
                        "status": "success",
                        "total_complaints": total_complaints,
                        "aggregated_data": aggregated_data,
                        "records": len(df),
                        "data": df.head(100).to_dict("records"),
                        "filters_applied": filters
                    }
                except Exception as e:
                    return {
                        "error": f"Failed to process complaints: {str(e)}",
                        "status": "error"
                    }
        
        @self.server.tool()
        async def get_device_metadata(
            session_id: int,
            udi_di: Optional[str] = None
        ) -> Dict[str, Any]:
            """
            Retrieve device metadata and UDI information
            
            Args:
                session_id: PSUR session ID
                udi_di: Optional UDI-DI identifier
            
            Returns:
                Dict containing device information
            """
            with get_db_context() as db:
                from backend.database.models import PSURSession
                
                session = db.query(PSURSession).filter(
                    PSURSession.id == session_id
                ).first()
                
                if not session:
                    return {
                        "error": "Session not found",
                        "status": "error"
                    }
                
                return {
                    "status": "success",
                    "device_name": session.device_name,
                    "udi_di": session.udi_di or udi_di,
                    "period_start": session.period_start.isoformat(),
                    "period_end": session.period_end.isoformat(),
                    "surveillance_months": (session.period_end - session.period_start).days // 30
                }
    
    async def start(self, host: str = "localhost", port: int = 8001):
        """Start the MCP server"""
        await self.server.run(host=host, port=port)


# Server instance
data_access_server = DataAccessServer()


if __name__ == "__main__":
    import asyncio
    asyncio.run(data_access_server.start())
