"""Simple test to verify evaluation setup."""
import json
from pathlib import Path

print("=" * 60)
print("PSUR Multi-Agent System - Simple Test")
print("=" * 60)

# Test 1: Load test queries
print("\n1. Loading queries from evaluation/test_queries.json...")
try:
    with open("evaluation/test_queries.json", "r") as f:
        data = json.load(f)
    queries = data.get("queries", [])
    print(f"   Found {len(queries)} queries")
    for i, q in enumerate(queries[:3], 1):
        print(f"\n[{i}] Query: {q['query'][:70]}...")
        print(f"    Context: {q.get('context', 'N/A')[:60]}...")
except Exception as e:
    print(f"   ERROR: {e}")

# Test 2: Check evaluators
print("\n2. Testing evaluators...")
try:
    from evaluate import PlaceholderDetectorEvaluator, DataConsistencyEvaluator, ContentQualityEvaluator
    
    test_response = """
    The ZyMot Multi Sperm Separation Device has demonstrated excellent safety performance.
    Total devices sold: 621,217 units (cumulative 2021-2024).
    Total complaints received: 73 complaints.
    Complaint rate: 0.012% (73/621,217).
    No serious adverse events reported.
    """
    
    placeholder_eval = PlaceholderDetectorEvaluator()
    consistency_eval = DataConsistencyEvaluator()
    quality_eval = ContentQualityEvaluator()
    
    p_result = placeholder_eval(response=test_response)
    c_result = consistency_eval(response=test_response, key_data_points=["621,217 units", "73 complaints", "0.012%"])
    q_result = quality_eval(response=test_response)
    
    print(f"   Placeholder Score: {p_result['placeholder_score']:.2f}")
    print(f"   Consistency Score: {c_result['consistency_score']:.2f}")
    print(f"   Quality Score:     {q_result['quality_score']:.2f}")
    print("   Evaluators working!")
except Exception as e:
    print(f"   ERROR: {e}")

print("\n" + "=" * 60)
print("Test queries loaded successfully!")
print("\nTo run full evaluation, you need to:")
print("1. Start the backend: python -m uvicorn backend.main:app --reload")
print("2. Run: python evaluation/agent_runner.py --limit 3")
print("3. Run: python evaluation/evaluate.py")
print("=" * 60)
