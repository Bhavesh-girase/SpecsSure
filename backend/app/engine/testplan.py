"""
Testing & Laboratory Route Planner.

requirements -> required tests (deduplicated: one tensile test yields YS, UTS, elongation, Agt)
             -> accredited labs with the test in scope
             -> parallel schedule (critical path) + duplicate / conflicting test-method detection
"""
from __future__ import annotations

from typing import Dict, List, Optional

from app.engine import ontology
from app.engine.extractor import Requirement
from app.engine.std_refs import base_number

SAMPLE_PREP_DAYS = 2


def labs() -> List[dict]:
    try:
        return ontology.load_json("labs.json")["labs"]
    except FileNotFoundError:
        return []


def _in_scope(lab: dict, std: str) -> bool:
    return any(std == s or base_number(std) == s or std.startswith(s) for s in lab["scope"])


def plan(reqs: List[Requirement], cited_families: List[str], delivery_days: Optional[float] = None) -> dict:
    groups: Dict[str, dict] = {}
    method_by_param: Dict[str, set] = {}
    for q in reqs:
        if q.kind != "parameter" or not q.parameter:
            continue
        t = ontology.param_test(q.parameter)
        if not t:
            continue
        key = f"{q.domain}:{t['group']}"
        g = groups.setdefault(key, {"test_id": key, "standard": t["standard"], "name": t["name"], "discipline": t["discipline"],
                                    "days": t["days"], "sample": q.domain, "parameters": [], "requirement_ids": [], "clause_keys": []})
        if q.parameter_label not in g["parameters"]:
            g["parameters"].append(q.parameter_label)
        g["days"] = max(g["days"], t["days"])
        g["requirement_ids"].append(q.id)
        if q.clause_key not in g["clause_keys"]:
            g["clause_keys"].append(q.clause_key)
        # explicitly cited alternative methods in the same sentence -> potential duplicate testing
        for s in q.standards:
            fam = s.get("family", "")
            if fam and base_number(fam) != base_number(t["standard"]) and ontology.standards_parameters().get(fam) is None:
                method_by_param.setdefault(q.parameter_label, set()).add(fam)
    tests = list(groups.values())
    for t in tests:
        t["cited_in_tender"] = any(t["standard"] == f or base_number(t["standard"]) == base_number(f) for f in cited_families)
        candidates = [l for l in labs() if _in_scope(l, t["standard"])]
        candidates.sort(key=lambda l: (l["turnaround_factor"], l["cost_index"]))
        t["labs"] = [{"id": l["id"], "name": l["name"], "accreditation": l["accreditation"],
                      "est_days": round(t["days"] * l["turnaround_factor"] + SAMPLE_PREP_DAYS, 1)} for l in candidates]
        t["covers"] = len(t["parameters"])

    # route: assign each test to the fastest lab, run labs in parallel, tests inside a lab in parallel too
    tracks: Dict[str, dict] = {}
    for t in tests:
        if not t["labs"]:
            continue
        lab = t["labs"][0]
        tr = tracks.setdefault(lab["id"], {"lab": lab["name"], "tests": [], "days": 0})
        tr["tests"].append(t["name"])
        tr["days"] = max(tr["days"], lab["est_days"])
    gantt = []
    for lid, tr in tracks.items():
        gantt.append({"lab_id": lid, "lab": tr["lab"], "start_day": 0, "end_day": tr["days"], "tests": tr["tests"]})
    critical = max((g["end_day"] for g in gantt), default=0)
    duplicates = [{"parameter": p, "methods": sorted(m), "note": "Parameter is also tied to another test method — confirm which one governs to avoid double testing."}
                  for p, m in method_by_param.items() if m]
    merged_note = [f"One {t['name'].lower()} covers {', '.join(t['parameters'])}" for t in tests if len(t["parameters"]) > 1]
    warnings = []
    if delivery_days is not None and critical > delivery_days:
        warnings.append(f"Critical-path testing time (~{critical:g} days) exceeds the delivery period ({delivery_days:g} days).")
    untested = [t for t in tests if not t["labs"]]
    for t in untested:
        warnings.append(f"No laboratory in the directory lists {t['standard']} in scope.")
    return {"tests": tests, "gantt": gantt, "critical_path_days": critical, "duplicates": duplicates,
            "consolidation": merged_note, "warnings": warnings,
            "lab_directory_note": "Synthetic demo lab directory — replace with NABL scope data."}
