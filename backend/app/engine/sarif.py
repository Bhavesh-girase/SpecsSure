"""
SARIF 2.1.0 export (OASIS Static Analysis Results Interchange Format).

Treating a tender like source code means its lint results can flow into the same tooling
ecosystem as software static analysis: SARIF viewers (VS Code SARIF Viewer, GitHub code scanning,
Azure DevOps) can display SpecSure findings with rule metadata, locations and suggested fixes.
"""
from __future__ import annotations

from typing import Dict, List

from app.engine.linter import rules_catalog

LEVEL = {"critical": "error", "major": "warning", "minor": "note", "info": "note"}


def to_sarif(twin: Dict, artifact_uri: str = "tender.txt", version: str = "2.0.0") -> Dict:
    rules = rules_catalog()
    rule_index = {r["id"]: i for i, r in enumerate(rules)}
    results: List[Dict] = []
    for f in twin.get("findings", []):
        loc = {
            "physicalLocation": {"artifactLocation": {"uri": f.get("doc_name") or artifact_uri},
                                 "region": {"snippet": {"text": (f.get("quote") or "")[:500]}}},
            "logicalLocations": [{"name": f"Clause {f.get('clause_key')}" if f.get("clause_key") else "Tender", "kind": "clause",
                                  "fullyQualifiedName": f"{twin['tender'].get('title', 'tender')}/clause/{f.get('clause_key')}"}],
        }
        if f.get("page"):
            loc["physicalLocation"]["region"]["properties"] = {"page": f["page"]}
        res = {
            "ruleId": f["rule_id"], "ruleIndex": rule_index.get(f["rule_id"], -1), "level": LEVEL.get(f["severity"], "note"),
            "message": {"text": f["message"] + (f"\nSuggestion: {f['suggestion']}" if f.get("suggestion") else "")},
            "locations": [loc],
            "partialFingerprints": {"specsure/v1": f["fingerprint"]},
            "properties": {"severity": f["severity"], "category": f["category"], "source": f.get("source"),
                           "confidence": f.get("confidence"), "basis": f.get("basis"), "review_status": f.get("review_status", "open")},
        }
        fx = f.get("fix")
        if fx and fx.get("op") == "replace" and fx.get("find"):
            res["fixes"] = [{"description": {"text": f.get("suggestion") or "Apply suggested wording"},
                             "artifactChanges": [{"artifactLocation": {"uri": f.get("doc_name") or artifact_uri},
                                                  "replacements": [{"deletedRegion": {"snippet": {"text": fx["find"]}},
                                                                    "insertedContent": {"text": fx["replace"]}}]}]}]
        results.append(res)
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {"name": "SpecSure Tender Linter", "version": version, "informationUri": "https://github.com/",
                                "rules": [{"id": r["id"], "name": r["name"].replace(" ", ""), "shortDescription": {"text": r["name"]},
                                           "fullDescription": {"text": r["description"]},
                                           "help": {"text": r["basis"] or r["description"]},
                                           "defaultConfiguration": {"level": LEVEL.get(r["default_severity"], "note")},
                                           "properties": {"category": r["category"]}} for r in rules]}},
            "artifacts": [{"location": {"uri": artifact_uri}}],
            "results": results,
            "properties": {"readiness": twin.get("readiness", {}).get("score"), "gate": twin.get("readiness", {}).get("gate"),
                           "kbSnapshot": twin.get("provenance", {}).get("kb_snapshot")},
        }],
    }
