"""
Tender Compiler benchmark — measured, not claimed.

  recall      = planted issues detected (rule + clause) / planted issues
  false alarm = critical findings on tenders labelled clean
  latency     = compile time per tender (ms)

    python -m scripts.evaluate_compiler
Writes data/evaluation/compiler_results.json
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.engine.compiler import compile_ir  # noqa: E402
from app.engine.docparse import parse_document, parse_text  # noqa: E402
from app.engine.kb import KnowledgeBase  # noqa: E402
from app.engine.tender_ir import build_ir  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def main():
    gold = json.load(open(os.path.join(ROOT, "data", "evaluation", "compiler_gold.json"), encoding="utf-8"))["cases"]
    kb = KnowledgeBase.from_seed()
    tot, hit, fa_cases, fa = 0, 0, 0, 0
    rows = []
    for case in gold:
        if "file" in case:
            with open(os.path.join(ROOT, case["file"]), "rb") as f:
                doc = parse_document(f.read(), os.path.basename(case["file"]))
        else:
            doc = parse_text(case["text"], f"{case['id']}.txt")
        t0 = time.time()
        tw = compile_ir(build_ir(doc, doc_type="tender"), kb)
        ms = (time.time() - t0) * 1000
        got = {(f["rule_id"], f.get("clause_key")) for f in tw["findings"]}
        got_rules = {f["rule_id"] for f in tw["findings"]}
        missed = []
        for rule, clause in case["expected"]:
            ok = (rule, clause) in got if clause else rule in got_rules
            tot += 1
            hit += ok
            if not ok:
                missed.append([rule, clause])
        crit = [f for f in tw["findings"] if f["severity"] == "critical"]
        if case.get("no_critical"):
            fa_cases += 1
            fa += len(crit)
        rows.append({"case": case["id"], "expected": len(case["expected"]), "missed": missed, "findings": len(tw["findings"]),
                     "critical": len(crit), "readiness": tw["readiness"]["score"], "compile_ms": round(ms, 1)})
        print(f"{case['id']:<16} expected {len(case['expected']):>2}  missed {len(missed)}  findings {len(tw['findings']):>2}  critical {len(crit)}  {ms:6.1f} ms  {missed or ''}")
    res = {"planted_issue_recall": round(hit / tot, 4) if tot else None, "planted_issues": tot,
           "critical_false_alarms_on_clean_tenders": fa, "clean_tenders": fa_cases,
           "mean_compile_ms": round(sum(r["compile_ms"] for r in rows) / len(rows), 1), "cases": rows}
    print(f"\nPlanted-issue recall: {hit}/{tot} = {res['planted_issue_recall']:.1%} · critical false alarms on clean tenders: {fa} · mean compile {res['mean_compile_ms']} ms")
    json.dump(res, open(os.path.join(ROOT, "data", "evaluation", "compiler_results.json"), "w"), indent=2)


if __name__ == "__main__":
    main()
