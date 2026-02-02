"""
MCP External Search Server
Interfaces with external databases and search APIs
Includes Perplexity AI, FDA MAUDE database (OpenFDA API), and general web search
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from mcp.server import Server
import httpx
from backend.config import settings

# AI fallback imports
try:
    from openai import AsyncOpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    from anthropic import AsyncAnthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


class ExternalSearchServer:
    """MCP Server for external database and web searches"""
    
    def __init__(self):
        self.server = Server("external-search")
        
        # Perplexity client (if API key available)
        self.perplexity_client = None
        if settings.perplexity_api_key:
            self.perplexity_client = httpx.AsyncClient(
                base_url="https://api.perplexity.ai",
                headers={"Authorization": f"Bearer {settings.perplexity_api_key}"},
                timeout=60.0
            )
        
        # FDA OpenFDA API client (no auth required)
        self.fda_client = httpx.AsyncClient(
            base_url="https://api.fda.gov",
            timeout=30.0
        )
        
        # Fallback AI clients
        self.openai_client = None
        self.anthropic_client = None
        
        if HAS_OPENAI and settings.openai_api_key:
            self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        
        if HAS_ANTHROPIC and settings.anthropic_api_key:
            self.anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        
        self.register_tools()
    
    def register_tools(self):
        """Register all external search tools"""
        
        @self.server.tool()
        async def search_perplexity(
            query: str,
            search_type: str = "general",
            max_results: int = 5,
            agent_name: str = "Unknown"
        ) -> Dict[str, Any]:
            """
            Search using Perplexity AI for web-based information
            Falls back to OpenAI/Anthropic if Perplexity unavailable
            """
            try:
                # Try Perplexity first
                if self.perplexity_client:
                    if search_type == "medical":
                        enhanced_query = f"Medical device safety: {query}"
                    elif search_type == "regulatory":
                        enhanced_query = f"EU MDR regulatory: {query}"
                    else:
                        enhanced_query = query
                    
                    response = await self.perplexity_client.post(
                        "/chat/completions",
                        json={
                            "model": "sonar",
                            "messages": [
                                {
                                    "role": "system",
                                    "content": "You are a regulatory affairs expert searching for medical device safety information."
                                },
                                {"role": "user", "content": enhanced_query}
                            ],
                            "max_tokens": 1000,
                            "return_citations": True
                        }
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        return {
                            "status": "success",
                            "query": query,
                            "answer": result.get("choices", [{}])[0].get("message", {}).get("content", ""),
                            "citations": result.get("citations", []),
                            "search_type": search_type,
                            "provider": "perplexity"
                        }
                
                # Fallback to Anthropic
                if self.anthropic_client:
                    response = await self.anthropic_client.messages.create(
                        model=settings.anthropic_model_orchestrator,
                        system="You are a regulatory affairs expert. Provide accurate, well-researched information about medical device safety and regulations.",
                        messages=[{"role": "user", "content": query}],
                        max_tokens=1000
                    )
                    return {
                        "status": "success",
                        "query": query,
                        "answer": response.content[0].text,
                        "citations": [],
                        "search_type": search_type,
                        "provider": "anthropic_fallback"
                    }
                
                # Fallback to OpenAI
                if self.openai_client:
                    response = await self.openai_client.chat.completions.create(
                        model=settings.openai_model_default,
                        messages=[
                            {"role": "system", "content": "You are a regulatory affairs expert."},
                            {"role": "user", "content": query}
                        ],
                        max_tokens=1000
                    )
                    return {
                        "status": "success",
                        "query": query,
                        "answer": response.choices[0].message.content,
                        "citations": [],
                        "search_type": search_type,
                        "provider": "openai_fallback"
                    }
                
                return {"error": "No search providers available", "status": "error"}
                
            except Exception as e:
                return {"error": f"Search failed: {str(e)}", "status": "error"}
        
        @self.server.tool()
        async def search_maude_database(
            device_name: str,
            event_type: Optional[str] = None,
            date_range: Optional[Dict[str, str]] = None,
            limit: int = 100,
            agent_name: str = "Unknown"
        ) -> Dict[str, Any]:
            """
            Search FDA MAUDE database for device-related adverse events
            Uses the real OpenFDA API - https://open.fda.gov/apis/device/event/
            
            Args:
                device_name: Device name to search
                event_type: Type of event (Malfunction, Injury, Death)
                date_range: Optional date range {'start': 'YYYY-MM-DD', 'end': 'YYYY-MM-DD'}
                limit: Maximum results (max 1000)
                agent_name: Name of requesting agent
            
            Returns:
                Dict with MAUDE search results including adverse event reports
            """
            try:
                # Build search query
                search_parts = []
                
                # Device name search (in brand_name or generic_name)
                device_query = device_name.replace(" ", "+")
                search_parts.append(f'(device.brand_name:"{device_query}"+OR+device.generic_name:"{device_query}")')
                
                # Event type filter
                if event_type:
                    event_map = {
                        "malfunction": "Malfunction",
                        "injury": "Injury",
                        "death": "Death"
                    }
                    mapped_type = event_map.get(event_type.lower(), event_type)
                    search_parts.append(f'event_type:"{mapped_type}"')
                
                # Date range filter
                if date_range:
                    start = date_range.get("start", "2020-01-01").replace("-", "")
                    end = date_range.get("end", datetime.now().strftime("%Y%m%d"))
                    search_parts.append(f'date_received:[{start}+TO+{end}]')
                
                search_query = "+AND+".join(search_parts)
                
                # Call OpenFDA API
                response = await self.fda_client.get(
                    f"/device/event.json?search={search_query}&limit={min(limit, 100)}"
                )
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    total = data.get("meta", {}).get("results", {}).get("total", 0)
                    
                    # Process results into structured format
                    processed_events = []
                    event_summary = {"Malfunction": 0, "Injury": 0, "Death": 0, "Other": 0}
                    
                    for event in results[:50]:  # Limit processing to 50
                        event_type_val = event.get("event_type", "Unknown")
                        if event_type_val in event_summary:
                            event_summary[event_type_val] += 1
                        else:
                            event_summary["Other"] += 1
                        
                        processed_events.append({
                            "report_number": event.get("mdr_report_key", "N/A"),
                            "event_type": event_type_val,
                            "date_received": event.get("date_received", "N/A"),
                            "device_brand": event.get("device", [{}])[0].get("brand_name", "N/A") if event.get("device") else "N/A",
                            "manufacturer": event.get("device", [{}])[0].get("manufacturer_d_name", "N/A") if event.get("device") else "N/A",
                            "event_description": (event.get("mdr_text", [{}])[0].get("text", "")[:500] if event.get("mdr_text") else "")
                        })
                    
                    return {
                        "status": "success",
                        "database": "FDA MAUDE (OpenFDA)",
                        "device_searched": device_name,
                        "event_type_filter": event_type,
                        "date_range": date_range,
                        "total_results": total,
                        "results_returned": len(processed_events),
                        "event_summary": event_summary,
                        "events": processed_events,
                        "api_url": f"https://api.fda.gov/device/event.json?search={search_query}"
                    }
                
                elif response.status_code == 404:
                    return {
                        "status": "success",
                        "database": "FDA MAUDE (OpenFDA)",
                        "device_searched": device_name,
                        "total_results": 0,
                        "results_returned": 0,
                        "event_summary": {"Malfunction": 0, "Injury": 0, "Death": 0},
                        "events": [],
                        "note": "No adverse events found for this device in MAUDE database"
                    }
                
                else:
                    return {
                        "error": f"FDA API error: {response.status_code}",
                        "status": "error",
                        "response_text": response.text[:500]
                    }
                
            except Exception as e:
                return {
                    "error": f"MAUDE search failed: {str(e)}",
                    "status": "error"
                }
        
        @self.server.tool()
        async def search_fda_recalls(
            device_name: str,
            status: Optional[str] = None,
            date_range: Optional[Dict[str, str]] = None,
            agent_name: str = "Unknown"
        ) -> Dict[str, Any]:
            """
            Search FDA device recall database
            
            Args:
                device_name: Device name to search
                status: Recall status (Ongoing, Completed, Terminated)
                date_range: Optional date range
                agent_name: Name of requesting agent
            
            Returns:
                Dict with recall information
            """
            try:
                device_query = device_name.replace(" ", "+")
                search_query = f'product_description:"{device_query}"'
                
                if status:
                    search_query += f'+AND+status:"{status}"'
                
                response = await self.fda_client.get(
                    f"/device/recall.json?search={search_query}&limit=50"
                )
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    total = data.get("meta", {}).get("results", {}).get("total", 0)
                    
                    recalls = []
                    for recall in results[:25]:
                        recalls.append({
                            "recall_number": recall.get("res_event_number", "N/A"),
                            "product_description": recall.get("product_description", "N/A")[:200],
                            "reason": recall.get("reason_for_recall", "N/A")[:300],
                            "classification": recall.get("event_date_terminated", "N/A"),
                            "status": recall.get("status", "N/A"),
                            "firm_name": recall.get("recalling_firm", "N/A")
                        })
                    
                    return {
                        "status": "success",
                        "database": "FDA Device Recalls",
                        "device_searched": device_name,
                        "total_recalls": total,
                        "recalls": recalls
                    }
                
                elif response.status_code == 404:
                    return {
                        "status": "success",
                        "database": "FDA Device Recalls",
                        "device_searched": device_name,
                        "total_recalls": 0,
                        "recalls": [],
                        "note": "No recalls found for this device"
                    }
                
                else:
                    return {"error": f"FDA Recall API error: {response.status_code}", "status": "error"}
                
            except Exception as e:
                return {"error": f"Recall search failed: {str(e)}", "status": "error"}
        
        @self.server.tool()
        async def search_literature(
            topic: str,
            keywords: List[str],
            max_results: int = 10,
            agent_name: str = "Unknown"
        ) -> Dict[str, Any]:
            """
            Search scientific literature and regulatory guidance
            Uses Perplexity with academic focus, falls back to OpenAI/Anthropic
            """
            try:
                query = f"{topic}. Keywords: {', '.join(keywords)}. Focus on peer-reviewed publications and regulatory guidance."
                
                # Try Perplexity first
                if self.perplexity_client:
                    response = await self.perplexity_client.post(
                        "/chat/completions",
                        json={
                            "model": "sonar",
                            "messages": [
                                {
                                    "role": "system",
                                    "content": "You are a medical device regulatory researcher. Provide evidence-based information with proper citations from peer-reviewed sources and regulatory guidance documents."
                                },
                                {"role": "user", "content": query}
                            ],
                            "max_tokens": 1500,
                            "return_citations": True
                        }
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        return {
                            "status": "success",
                            "topic": topic,
                            "keywords": keywords,
                            "summary": result.get("choices", [{}])[0].get("message", {}).get("content", ""),
                            "citations": result.get("citations", []),
                            "search_type": "literature",
                            "provider": "perplexity"
                        }
                
                # Fallback to Anthropic for literature synthesis
                if self.anthropic_client:
                    response = await self.anthropic_client.messages.create(
                        model=settings.anthropic_model_orchestrator,
                        system="You are a medical device regulatory researcher. Synthesize current knowledge about the topic, referencing relevant standards (ISO, IEC), regulations (MDR, FDA), and scientific literature.",
                        messages=[{"role": "user", "content": query}],
                        max_tokens=1500
                    )
                    return {
                        "status": "success",
                        "topic": topic,
                        "keywords": keywords,
                        "summary": response.content[0].text,
                        "citations": [],
                        "search_type": "literature",
                        "provider": "anthropic_fallback"
                    }
                
                # Fallback to OpenAI
                if self.openai_client:
                    response = await self.openai_client.chat.completions.create(
                        model=settings.openai_model_default,
                        messages=[
                            {"role": "system", "content": "You are a medical device regulatory researcher."},
                            {"role": "user", "content": query}
                        ],
                        max_tokens=1500
                    )
                    return {
                        "status": "success",
                        "topic": topic,
                        "keywords": keywords,
                        "summary": response.choices[0].message.content,
                        "citations": [],
                        "search_type": "literature",
                        "provider": "openai_fallback"
                    }
                
                return {"error": "No literature search providers available", "status": "error"}
                
            except Exception as e:
                return {"error": f"Literature search failed: {str(e)}", "status": "error"}
    
    async def close(self):
        """Close HTTP clients"""
        if self.perplexity_client:
            await self.perplexity_client.aclose()
        await self.fda_client.aclose()
    
    async def start(self, host: str = "localhost", port: int = 8004):
        """Start the MCP server"""
        await self.server.run(host=host, port=port)


# Server instance
external_search_server = ExternalSearchServer()


if __name__ == "__main__":
    import asyncio
    asyncio.run(external_search_server.start())
