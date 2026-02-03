"""Agent Runner for PSUR Evaluation"""
import asyncio
import json
import argparse
import aiohttp
from pathlib import Path
from datetime import datetime

BASE_URL = "http://localhost:8080"


async def create_session(client, query_data):
    """Create a new PSUR session with device info from query context."""
    context = query_data.get("context", "")
    
    # Parse device name from context
    device_name = "ZyMot Multi Sperm Separation Device"
    if "ZyMot" in context or "ZyMōt" in context:
        device_name = "ZyMot Multi Sperm Separation Device"
    elif "LifeGlobal" in context:
        device_name = "LifeGlobal Culture Media"
    
    params = {
        "device_name": device_name,
        "udi_di": "00850003864105",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31"
    }
    
    async with client.post(f"{BASE_URL}/api/sessions", params=params) as resp:
        if resp.status == 200:
            data = await resp.json()
            return data.get("session_id")
        raise Exception(f"Failed to create session: {await resp.text()}")


async def start_generation(client, session_id):
    """Start the PSUR generation process."""
    async with client.post(f"{BASE_URL}/api/sessions/{session_id}/start") as resp:
        if resp.status == 200:
            return await resp.json()
        raise Exception(f"Failed to start generation: {await resp.text()}")


async def get_messages(client, session_id):
    """Get all messages from the session."""
    async with client.get(f"{BASE_URL}/api/sessions/{session_id}/messages") as resp:
        if resp.status == 200:
            return await resp.json()
        return []


async def get_sections(client, session_id):
    """Get all generated sections."""
    async with client.get(f"{BASE_URL}/api/sessions/{session_id}/sections") as resp:
        if resp.status == 200:
            return await resp.json()
        return []


async def wait_for_completion(client, session_id, timeout=120):
    """Wait for generation to complete or timeout."""
    start_time = datetime.now()
    last_message_count = 0
    idle_count = 0
    
    while (datetime.now() - start_time).seconds < timeout:
        messages = await get_messages(client, session_id)
        
        if len(messages) > last_message_count:
            last_message_count = len(messages)
            idle_count = 0
            print(f"    Messages: {len(messages)}")
        else:
            idle_count += 1
        
        # If no new messages for 10 checks, consider done
        if idle_count > 10:
            break
            
        await asyncio.sleep(2)
    
    return await get_messages(client, session_id)


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
                # Create session
                session_id = await create_session(client, query_data)
                print(f"  Created session: {session_id}")
                
                # Start PSUR generation
                print("  Starting generation...")
                await start_generation(client, session_id)
                
                # Wait for completion and collect messages
                print("  Waiting for completion...")
                messages = await wait_for_completion(client, session_id, timeout=120)
                
                # Get generated sections
                sections = await get_sections(client, session_id)
                
                result = {
                    "query_id": query_data["id"],
                    "query": query_data["query"],
                    "context": query_data.get("context"),
                    "key_data_points": query_data.get("key_data_points", []),
                    "response": {
                        "messages": messages,
                        "sections": sections,
                        "message_count": len(messages),
                        "section_count": len(sections)
                    },
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                }
                results.append(result)
                print(f"  Completed: {len(messages)} messages, {len(sections)} sections")
                
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
