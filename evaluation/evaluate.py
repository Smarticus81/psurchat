"""PSUR Evaluation - Local Evaluators"""
import json
import argparse
import re
from pathlib import Path
from datetime import datetime


class PlaceholderDetectorEvaluator:
    """Detects placeholder/mock data in responses."""
    
    PATTERNS = [
        r"\[.*?\]",  # [placeholder]
        r"\{.*?\}",  # {placeholder}
        r"XX+",      # XXX
        r"TBD",
        r"TODO",
        r"PLACEHOLDER",
        r"lorem ipsum",
    ]
    
    def __call__(self, response: str, **kwargs) -> dict:
        """Evaluate response for placeholder content."""
        if not response:
            return {"placeholder_score": 0, "placeholders_found": ["Empty response"]}
        
        found = []
        text = str(response).lower()
        
        for pattern in self.PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                found.extend(matches[:3])
        
        score = max(0, 1.0 - (len(found) * 0.1))
        
        return {
            "placeholder_score": score,
            "placeholders_found": found[:10]
        }


class DataConsistencyEvaluator:
    """Checks if numbers and data are consistent."""
    
    def __call__(self, response: str, key_data_points: list = None, **kwargs) -> dict:
        """Evaluate data consistency."""
        if not response:
            return {"consistency_score": 0, "data_coverage": 0}
        
        text = str(response)
        
        if key_data_points:
            found = sum(
                1 for p in key_data_points 
                if any(k.lower() in text.lower() for k in p.split()[:3])
            )
            coverage = found / len(key_data_points) if key_data_points else 1.0
        else:
            coverage = 0.5
        
        return {
            "consistency_score": coverage,
            "data_coverage": coverage
        }


class ContentQualityEvaluator:
    """Evaluates overall content quality."""
    
    def __call__(self, response: str, expected_sections: list = None, **kwargs) -> dict:
        """Evaluate content quality."""
        if not response:
            return {"quality_score": 0, "word_count": 0, "section_coverage": 0}
        
        text = str(response)
        word_count = len(text.split())
        length_score = min(1.0, word_count / 500)
        
        section_score = 1.0
        if expected_sections:
            found = sum(1 for s in expected_sections if s.lower() in text.lower())
            section_score = found / len(expected_sections)
        
        overall_score = (length_score * 0.5 + section_score * 0.5)
        
        return {
            "quality_score": overall_score,
            "word_count": word_count,
            "section_coverage": section_score
        }


def run_local_evaluation(responses_file: str, output_file: str):
    """Run evaluation using local evaluators."""
    
    with open(responses_file, "r") as f:
        data = json.load(f)
    
    results_list = data.get("results", [])
    
    placeholder_eval = PlaceholderDetectorEvaluator()
    consistency_eval = DataConsistencyEvaluator()
    quality_eval = ContentQualityEvaluator()
    
    evaluation_results = []
    
    for result in results_list:
        if "error" in result:
            evaluation_results.append({
                "query_id": result["query_id"],
                "error": result["error"]
            })
            continue
        
        response_text = ""
        if isinstance(result.get("response"), dict):
            response_text = result["response"].get("content", str(result["response"]))
        else:
            response_text = str(result.get("response", ""))
        
        p_result = placeholder_eval(response=response_text)
        c_result = consistency_eval(
            response=response_text,
            key_data_points=result.get("key_data_points", [])
        )
        q_result = quality_eval(
            response=response_text,
            expected_sections=result.get("expected_sections", [])
        )
        
        overall = (
            p_result["placeholder_score"] * 0.3 +
            c_result["consistency_score"] * 0.3 +
            q_result["quality_score"] * 0.4
        )
        
        evaluation_results.append({
            "query_id": result["query_id"],
            "scores": {
                "placeholder": p_result["placeholder_score"],
                "consistency": c_result["consistency_score"],
                "quality": q_result["quality_score"],
                "overall": overall
            },
            "details": {
                "placeholder": p_result,
                "consistency": c_result,
                "quality": q_result
            }
        })
    
    valid = [r for r in evaluation_results if "error" not in r]
    
    if valid:
        avg = {
            "placeholder": sum(r["scores"]["placeholder"] for r in valid) / len(valid),
            "consistency": sum(r["scores"]["consistency"] for r in valid) / len(valid),
            "quality": sum(r["scores"]["quality"] for r in valid) / len(valid),
            "overall": sum(r["scores"]["overall"] for r in valid) / len(valid)
        }
    else:
        avg = {}
    
    output = {
        "timestamp": datetime.now().isoformat(),
        "total": len(evaluation_results),
        "successful": len(valid),
        "aggregate_scores": avg,
        "results": evaluation_results
    }
    
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)
    
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    print(f"Total: {len(evaluation_results)}, Successful: {len(valid)}")
    
    if avg:
        print(f"\nAggregate Scores:")
        print(f"  Placeholder Detection: {avg['placeholder']:.2f}")
        print(f"  Data Consistency:      {avg['consistency']:.2f}")
        print(f"  Content Quality:       {avg['quality']:.2f}")
        print(f"  Overall Score:         {avg['overall']:.2f}")
    
    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--responses", default="evaluation/results/responses.json")
    parser.add_argument("--output", default="evaluation/results/evaluation_report.json")
    args = parser.parse_args()
    run_local_evaluation(args.responses, args.output)
