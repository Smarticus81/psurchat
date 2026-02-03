"""Agent Runner for PSUR Evaluation"""
import asyncio
import json
import argparse
import aiohttp
from pathlib import Path
from datetime import datetime

BASE_URL = "http://localhost:8080"


async def create_session(client, name="Evaluation Session"):
    """Create a new PSUR session."""
    async with client.post(
        f"{BASE_URL}/api/sessions",
        json={"name": name, "description": "Automated evaluation test"}
    ) as resp:
        if resp.status == 200:
            data = await resp.json()
            return data.get("id")
        raise Exception(f"Failed to create session: {await resp.text()}")


async def send_message(client, session_id, message, context=None):
    """Send a message to the PSUR system and get response."""
    payload = {"message": message}
    if context:
        payload["context"] = context
    async with client.post(
        f"{BASE_URL}/api/sessions/{session_id}/messages",
        json=payload
    ) as resp:
        if resp.status == 200:
            return await resp.json()
        raise Exception(f"Failed to send message: {await resp.text()}")


async def run_evaluation_queries(queries_file, output_file, limit=None):
    """Run test queries and collect responses."""
    with open(queries_file, "r") as f:
        data = json.load(f)
    
    queries = data.get("queries", [])
    if limit:
        queries = queries[:limit]
    
    results = []
    
    async with aiohttp.ClientSession() as client:
        for i, query_data in enumerate(queries, 1):
            print(f"\n[{i}/{len(queries)}] Processing: {query_data['id']}")
            
            try:
                session_id = await create_session(client, f"Eval - {query_data['id']}")
                print(f"  Created session: {session_id}")
                
                response = await send_message(
                    client, 
                    session_id, 
                    query_data["query"], 
                    query_data.get("context")
                )
                
                result = {
                    "query_id": query_data["id"],
                    "query": query_data["query"],
                    "context": query_data.get("context"),
                    "key_data_points": query_data.get("key_data_points", []),
                    "response": response,
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                }
                results.append(result)
                print(f"  Response received: {len(str(response))} chars")
                
            except Exception as e:
                print(f"  ERROR: {e}")
                results.append({
                    "query_id": query_data["id"],
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
    
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump({
            "run_timestamp": datetime.now().isoformat(),
            "total_queries": len(queries),
            "results": results
        }, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run PSUR evaluation queries")
    parser.add_argument("--queries", default="evaluation/test_queries.json")
    parser.add_argument("--output", default="evaluation/results/responses.json")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    asyncio.run(run_evaluation_queries(args.queries, args.output, args.limit))
