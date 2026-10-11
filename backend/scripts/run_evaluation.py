import os
import json
import time
import asyncio
import logging
from app.db.session import async_session_maker
from app.orchestrator.graph import run_analysis_pipeline
from scripts.seed_standards_database import seed_all_if_needed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("evaluation")

async def run_benchmark():
    eval_file = os.path.join(os.path.dirname(__file__), "..", "data", "evaluation", "test_queries.json")
    with open(eval_file, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    logger.info(f"Loaded {len(test_cases)} evaluation test cases. Ensuring database is ready...")
    await seed_all_if_needed()

    top1_correct = 0
    top3_correct = 0
    total = len(test_cases)
    results_log = []

    print("\n" + "="*80)
    print(" SPECSURE INDIAN STANDARDS AI BENCHMARK EVALUATION")
    print("="*80)

    async with async_session_maker() as session:
        for tc in test_cases:
            tc_id = tc["id"]
            query = tc["query"]
            expected = tc["expected_is_number"]
            expected_sec = tc.get("expected_secondary")

            start = time.time()
            state = await run_analysis_pipeline(
                input_text=query,
                input_language="auto",
                max_depth=2,
                db=session
            )
            elapsed = time.time() - start

            rec_list = state.get("recommended_standards", [])
            rec_is_numbers = [r.get("is_number") if isinstance(r, dict) else r.is_number for r in rec_list]

            is_top1 = len(rec_is_numbers) > 0 and (expected in rec_is_numbers[0] or (expected_sec and expected_sec in rec_is_numbers[0]))
            is_top3 = any(expected in is_num or (expected_sec and expected_sec in is_num) for is_num in rec_is_numbers[:3])

            if is_top1:
                top1_correct += 1
            if is_top3:
                top3_correct += 1

            status = "PASS (Top-1)" if is_top1 else ("PASS (Top-3)" if is_top3 else "FAIL")
            print(f"[{tc_id}] {tc['category']} ({tc['difficulty']}): {status} | Time: {elapsed:.2f}s")
            print(f"     Expected: {expected} | Retrieved: {rec_is_numbers[:3]}")

            results_log.append({
                "test_id": tc_id,
                "category": tc["category"],
                "query": query,
                "expected": expected,
                "retrieved": rec_is_numbers,
                "top1_match": is_top1,
                "top3_match": is_top3,
                "latency_seconds": round(elapsed, 2)
            })

    top1_acc = (top1_correct / total) * 100
    top3_acc = (top3_correct / total) * 100

    print("\n" + "="*80)
    print(f"BENCHMARK RESULTS SUMMARY:")
    print(f"  Total Test Cases : {total}")
    print(f"  Top-1 Accuracy   : {top1_acc:.1f}% ({top1_correct}/{total})")
    print(f"  Top-3 Accuracy   : {top3_acc:.1f}% ({top3_correct}/{total})")
    print("="*80 + "\n")

    output_path = os.path.join(os.path.dirname(__file__), "..", "data", "evaluation", "evaluation_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_test_cases": total,
            "top1_accuracy": top1_acc,
            "top3_accuracy": top3_acc,
            "details": results_log
        }, f, indent=2)

if __name__ == "__main__":
    asyncio.run(run_benchmark())
