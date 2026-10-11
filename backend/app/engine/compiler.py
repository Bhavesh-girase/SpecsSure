"""
The Tender Compiler — builds the Tender Digital Twin.

    documents ──parse──▶ Tender IR (clause AST, page-anchored)
              ──extract─▶ typed requirements (units normalised, spans kept)
              ──resolve─▶ standards as-of the tender date (temporal engine) + QCO / CRS in force
              ──verify──▶ Z3 formal verification (contradictions = minimal unsat cores)
              ──market──▶ product-space feasibility & restriction evidence
              ──lint────▶ ~35 rule findings with autofixes (SARIF-exportable)
              ──link────▶ Digital Twin graph  Tender→Clause→Requirement→Standard→Amendment→QCO→
                          Certification→Test→Lab (→ Evidence when a bid is mirrored)
              ──gate────▶ readiness score + pre-publication checklist

Pure function of (documents, knowledge-base snapshot, as-of date) → reproducible and auditable.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import date, timedelta
from typing import Dict, List, Optional

from app.engine import ontology
from app.engine.constraints import atoms_from_requirements, standard_atoms, verify
from app.engine.context import CompileContext, DOMAIN_DEFAULT_STANDARD
from app.engine.extractor import extract
from app.engine.kb import KnowledgeBase
from app.engine.linter import run_all, SEVERITY_ORDER
from app.engine.market import analyse as market_analyse
from app.engine.std_refs import base_number, family_of
from app.engine.temporal import resolve
from app.engine.tender_ir import TenderIR, assign_domain_hints
from app.engine.testplan import plan as test_plan

ENGINE_VERSION = "tender-compiler/2.0"
SEVERITY_WEIGHT = {"critical": 12, "major": 5, "minor": 2, "info": 0.5}
CATEGORY_GROUP = {
    "ambiguity": "clarity", "drafting": "clarity", "measurability": "clarity",
    "standards": "currency", "certification": "compliance", "contradiction": "consistency",
    "restriction": "competition", "completeness": "completeness", "testing": "completeness", "security": "clarity",
}


def _as_of(ex, explicit: Optional[date]) -> date:
    if explicit:
        return explicit
    for role in ("publication", "bid_due"):
        if ex.dates.get(role):
            return date.fromisoformat(ex.dates[role])
    return date.today()


def _domain_standards(ctx: CompileContext) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    for dom in ctx.ex.domains:
        default = DOMAIN_DEFAULT_STANDARD.get(dom)
        if not default:
            continue
        dom_clauses = [c for c in ctx.clauses if dom in (ontology.detect_domains(c.heading + " " + c.text) or c.domain_hint or [])]
        cited = None
        for res in ctx.resolutions:
            if res["clause_key"] in {c.key for c in dom_clauses} and res.get("body") == "BIS":
                fam = res["family"]
                target_fam = family_of(res["replacement"]) if res.get("replacement") else fam
                if fam == default or base_number(fam) == base_number(default) or target_fam == default \
                        or ontology.standards_parameters().get(fam, {}).get("domain") == dom:
                    cited = res
                    break
        if cited:
            resolved = (cited.get("in_force") or {}).get("is_number") or cited.get("replacement") or cited["citation"]
            fam = family_of(resolved)
            info = {"family": fam, "cited": cited["citation"], "resolved": resolved, "status": cited["status"],
                    "clause_key": cited["clause_key"], "regulations_in_force": cited["regulations_in_force"],
                    "regulations_upcoming": cited["regulations_upcoming"], "source": "cited"}
        else:
            r = resolve(ctx.kb, default, ctx.as_of, horizon_days=int((ctx.delivery_days() or 90) + 60))
            info = {"family": default, "cited": None, "resolved": (r.in_force or {}).get("is_number") or default, "status": "not_cited",
                    "clause_key": dom_clauses[0].key if dom_clauses else None,
                    "regulations_in_force": r.regulations_in_force, "regulations_upcoming": r.regulations_upcoming, "source": "inferred"}
        info["grade"] = ctx.ex.grades.get(dom)
        info["licence_mandatory"] = any((g.get("is_mandatory") or "yes") == "yes" for g in info["regulations_in_force"])
        out[dom] = info
    return out


def _missing_dependencies(ctx: CompileContext) -> List[dict]:
    cited_fams = {c["family"] for c in ctx.ex.citations}
    cited_base = {base_number(f) for f in cited_fams}
    text = ctx.full_text().lower()
    gaps = []
    for dom, ds in ctx.domain_standards.items():
        rec = ctx.kb.lookup(ds["resolved"]) if ds.get("resolved") else None
        if not rec:
            continue
        missing = []
        for rel in ctx.kb.outgoing(rec.id, ["test_method", "normative_reference", "safety_requirement"]):
            tgt = ctx.kb.by_id.get(rel.to_id)
            if not tgt:
                continue
            if tgt.family in cited_fams or base_number(tgt.family) in cited_base:
                continue
            if rel.type == "safety_requirement" and "13920" in tgt.family and not re.search(r"seismic|zone\s*(?:iii|iv|v|3|4|5)", text):
                continue
            missing.append((rel, tgt))
        if not missing:
            continue
        names = "; ".join(f"{t.is_number} ({r.type.replace('_', ' ')}{': ' + r.clause_reference if r.clause_reference else ''})" for r, t in missing)
        gaps.append({"relationship_type": missing[0][0].type if len({r.type for r, _ in missing}) == 1 else "test_method",
                     "affected_standard": rec.is_number, "mandated_standard": ", ".join(t.is_number for _, t in missing),
                     "clause_key": ds.get("clause_key"), "graph_clause": None,
                     "description": f"{rec.is_number} depends on {len(missing)} standard(s) the tender never cites: {names}.",
                     "suggestion": f"Cite them explicitly where they govern testing/safety (e.g. 'tested as per {missing[0][1].is_number}').",
                     "items": [{"is_number": t.is_number, "title": t.title, "type": r.type, "clause_reference": r.clause_reference} for r, t in missing]})
    return gaps


def compile_ir(ir: TenderIR, kb: KnowledgeBase, as_of: Optional[date] = None, market: bool = True,
               tender_meta: Optional[dict] = None) -> dict:
    t0 = time.time()
    assign_domain_hints(ir.clauses)
    ex = extract(ir)
    ctx = CompileContext(ir=ir, ex=ex, kb=kb, as_of=_as_of(ex, as_of))
    horizon = int((ctx.delivery_days() or 90) + 60)

    # 1. temporal resolution of every citation occurrence
    for c in ex.citations:
        if c["body"] != "BIS":
            ctx.resolutions.append({**c, "citation": c["display"], "status": "foreign", "explanation": "Foreign / international standard — not a substitute where a QCO mandates the IS.",
                                    "as_of": ctx.as_of.isoformat(), "regulations_in_force": [], "regulations_upcoming": [], "in_force": None, "replacement": None})
            continue
        r = resolve(kb, c["display"], ctx.as_of, horizon_days=max(horizon, 365))
        ctx.resolutions.append({**r.to_dict(), "raw": c["raw"], "clause_key": c["clause_key"], "page": c["page"], "body": c["body"], "family": c["family"]})

    # 2. product standard + regulations per domain
    ctx.domain_standards = _domain_standards(ctx)

    # 3. formal verification
    atoms = atoms_from_requirements(ex.requirements)
    std_atoms = []
    for dom, ds in ctx.domain_standards.items():
        std_atoms += standard_atoms(dom, ds["family"], ds.get("grade"))
    ctx.verification = verify(atoms, std_atoms)
    conflicting = {a.label for cf in ctx.verification.conflicts for a in cf.atoms if a.kind == "requirement"}

    # 4. market feasibility (on the contradiction-free part of the spec)
    if market:
        ctx.market = market_analyse(ex.requirements, {d: {"family": v["family"], "grade": v.get("grade"), "licence_mandatory": v["licence_mandatory"]}
                                                      for d, v in ctx.domain_standards.items()}, conflicting)

    # 5. graph dependencies + test plan
    ctx.missing_dependencies = _missing_dependencies(ctx)
    ctx.test_plan = test_plan(ex.requirements, [c["family"] for c in ex.citations], ctx.delivery_days())

    # 6. lint
    findings = [f.to_dict() for f in run_all(ctx)]

    # 7. twin graph + readiness
    graph = build_graph(ctx, findings)
    readiness = readiness_report(ctx, findings)
    reqs = [r.to_dict() for r in ex.requirements]
    for r in reqs:
        _link_requirement(r, ctx)
    clause_findings: Dict[str, int] = {}
    for f in findings:
        if f.get("clause_key"):
            clause_findings[f["clause_key"]] = clause_findings.get(f["clause_key"], 0) + 1
    clauses = []
    for c in ir.clauses:
        d = c.to_dict()
        d["finding_count"] = clause_findings.get(c.key, 0)
        d["requirement_ids"] = [r["id"] for r in reqs if r["clause_key"] == c.key]
        clauses.append(d)
    doc_hash = hashlib.sha256(json.dumps([c.text for c in ir.clauses]).encode()).hexdigest()
    return {
        "tender": {**(tender_meta or {}), "title": (tender_meta or {}).get("title") or ir.title, "as_of": ctx.as_of.isoformat(),
                   "dates": ex.dates, "domains": ex.domains, "grades": ex.grades, "doc_type": ir.doc_type},
        "clauses": clauses,
        "requirements": reqs,
        "citations": ctx.resolutions,
        "domain_standards": ctx.domain_standards,
        "verification": ctx.verification.to_dict(),
        "market": ctx.market,
        "missing_dependencies": ctx.missing_dependencies,
        "test_plan": ctx.test_plan,
        "findings": findings,
        "readiness": readiness,
        "graph": graph,
        "provenance": {"engine": ENGINE_VERSION, "kb_snapshot": kb.snapshot_hash(), "content_hash": doc_hash,
                       "compiled_in_ms": round((time.time() - t0) * 1000, 1), "solver": ctx.verification.engine,
                       "deterministic": True, "llm_used": False},
    }


def _link_requirement(r: dict, ctx: CompileContext):
    """Requirement -> governing standard, test method, certification (Digital Twin edges)."""
    ds = ctx.domain_standards.get(r.get("domain") or "", {})
    governing = None
    for s in r.get("standards") or []:
        if s.get("body") == "BIS":
            res = next((x for x in ctx.resolutions if x["clause_key"] == r["clause_key"] and x["family"] == s["family"]), None)
            governing = (res or {}).get("in_force", {}) and res["in_force"]["is_number"] if res and res.get("in_force") else s["display"]
            break
    if not governing and r.get("kind") == "parameter":
        governing = ds.get("resolved")
    t = ontology.param_test(r["parameter"]) if r.get("parameter") else None
    r["links"] = {
        "governing_standard": governing,
        "test_method": t["standard"] if t else None,
        "certification": ([g["title"] for g in ds.get("regulations_in_force", [])] if ds else []),
    }
    unresolved = []
    if r.get("kind") == "parameter":
        if not governing:
            unresolved.append("no governing standard")
        if not t:
            unresolved.append("no test method")
        if r.get("flags"):
            unresolved += r["flags"]
    r["unresolved"] = unresolved


def readiness_report(ctx: CompileContext, findings: List[dict]) -> dict:
    param_reqs = [r for r in ctx.reqs if r.kind == "parameter"]
    with_test = [r for r in param_reqs if ontology.param_test(r.parameter)]
    coverage = {
        "requirements": len(ctx.reqs), "quantitative": len(param_reqs),
        "measurable_share": round(len([r for r in param_reqs if "no_unit" not in r.flags]) / len(param_reqs), 3) if param_reqs else None,
        "test_method_share": round(len(with_test) / len(param_reqs), 3) if param_reqs else None,
    }
    unresolved = [{"id": r.id, "clause_key": r.clause_key, "label": r.parameter_label, "flags": r.flags} for r in param_reqs if r.flags]
    return {**score_findings(findings), "coverage": coverage, "unresolved": unresolved}


def rescore(twin: dict) -> dict:
    """Re-score after human review (dismissed/accepted findings no longer block)."""
    twin["readiness"].update(score_findings(twin["findings"]))
    return twin


def score_findings(findings: List[dict]) -> dict:
    open_f = [f for f in findings if f.get("review_status", "open") in ("open", "accepted")]
    groups = {g: 100.0 for g in ["clarity", "currency", "compliance", "consistency", "competition", "completeness"]}
    for f in open_f:
        g = CATEGORY_GROUP.get(f["category"], "clarity")
        groups[g] = max(0.0, groups[g] - SEVERITY_WEIGHT.get(f["severity"], 1) * 1.6)
    penalty = sum(SEVERITY_WEIGHT.get(f["severity"], 1) for f in open_f)
    overall = 100.0 * 40.0 / (40.0 + penalty)   # smooth, never hits 0; ~95 for 2 minor issues
    crit = sum(1 for f in open_f if f["severity"] == "critical")
    major = sum(1 for f in open_f if f["severity"] == "major")
    gate = "BLOCKED" if crit else ("NEEDS_REVIEW" if major else "READY")

    def has(rule_prefix):
        return any(f["rule_id"].startswith(rule_prefix) for f in open_f)

    checklist = [
        {"item": "All cited standards valid on the tender date", "ok": not has("SS-STD-003") and not has("SS-STD-004"), "rules": ["SS-STD-003", "SS-STD-004"]},
        {"item": "Mandatory BIS certification (QCO/CRS) required where applicable", "ok": not has("SS-CERT-001"), "rules": ["SS-CERT-001"]},
        {"item": "No formally contradictory requirements", "ok": not has("SS-CON-001") and not has("SS-CON-002"), "rules": ["SS-CON-001", "SS-CON-002"]},
        {"item": "Requirements not weaker than the cited standard", "ok": not has("SS-CON-003"), "rules": ["SS-CON-003"]},
        {"item": "Test method defined for every acceptance parameter", "ok": not has("SS-TEST-001"), "rules": ["SS-TEST-001"]},
        {"item": "Sampling & acceptance criteria defined", "ok": not has("SS-ACC-001"), "rules": ["SS-ACC-001"]},
        {"item": "No brand / proprietary wording (GFR 144)", "ok": not has("SS-RES-001") and not has("SS-RES-002"), "rules": ["SS-RES-001", "SS-RES-002"]},
        {"item": "At least 3 manufacturers can comply", "ok": not has("SS-RES-004"), "rules": ["SS-RES-004"]},
        {"item": "Delivery schedule compatible with mandatory testing", "ok": not has("SS-CON-005"), "rules": ["SS-CON-005"]},
        {"item": "Tender dates consistent (pre-bid before bid due)", "ok": not has("SS-CON-004"), "rules": ["SS-CON-004"]},
        {"item": "All values carry units", "ok": not has("SS-UNIT-001"), "rules": ["SS-UNIT-001"]},
    ]
    return {"score": round(overall, 1), "gate": gate, "subscores": {k: round(v, 1) for k, v in groups.items()},
            "counts": {s: sum(1 for f in open_f if f["severity"] == s) for s in SEVERITY_ORDER},
            "reviewed": sum(1 for f in findings if f.get("review_status", "open") not in ("open",)),
            "checklist": checklist}


def build_graph(ctx: CompileContext, findings: List[dict]) -> dict:
    nodes: Dict[str, dict] = {}
    edges: List[dict] = []

    def node(nid, ntype, label, **kw):
        if nid not in nodes:
            nodes[nid] = {"id": nid, "type": ntype, "label": label, **kw}
        return nid

    def edge(a, b, rel):
        eid = f"{a}->{b}:{rel}"
        if not any(e["id"] == eid for e in edges):
            edges.append({"id": eid, "source": a, "target": b, "relation": rel})

    t = node("tender", "tender", ctx.ir.title[:60])
    for c in ctx.clauses:
        crs = [r for r in ctx.reqs if r.clause_key == c.key]
        cf = [f for f in findings if f.get("clause_key") == c.key]
        if not crs and not cf:
            continue
        cid = node(f"clause:{c.key}", "clause", f"Cl. {c.key} {c.heading[:28]}", page=c.page_start,
                   findings=len(cf), worst=min((f["severity"] for f in cf), key=lambda s: SEVERITY_ORDER.get(s, 9)) if cf else None)
        edge(t, cid, "contains")
        for r in crs:
            if r.kind not in ("parameter", "standard_compliance", "certification", "testing"):
                continue
            rid = node(f"req:{r.id}", "requirement", (r.parameter_label or r.kind)[:34], kind=r.kind,
                       bounds=r.norm, text=r.text[:140])
            edge(cid, rid, "states")
            if r.parameter:
                tst = ontology.param_test(r.parameter)
                if tst:
                    tid = node(f"test:{tst['standard']}", "test", f"{tst['standard']} — {tst['name'][:26]}", days=tst["days"])
                    edge(rid, tid, "verified_by")
            ds = ctx.domain_standards.get(r.domain or "", {})
            if ds.get("resolved"):
                sid = node(f"std:{ds['resolved']}", "standard", ds["resolved"], status="current")
                edge(rid, sid, "governed_by")
    for res in ctx.resolutions:
        if res.get("body") != "BIS":
            node(f"std:{res['citation']}", "standard", res["citation"], status="foreign")
            edge(f"clause:{res['clause_key']}", f"std:{res['citation']}", "cites")
            continue
        cited_id = node(f"std:{res['citation']}", "standard", res["citation"], status=res["status"])
        cid = f"clause:{res['clause_key']}"
        node(cid, "clause", f"Cl. {res['clause_key']}")
        edge(t, cid, "contains")
        edge(cid, cited_id, "cites")
        if res.get("replacement"):
            rid = node(f"std:{res['replacement']}", "standard", res["replacement"], status="current")
            edge(cited_id, rid, "superseded_by")
    for dom, ds in ctx.domain_standards.items():
        if not ds.get("resolved"):
            continue
        sid = node(f"std:{ds['resolved']}", "standard", ds["resolved"], status="current", domain=dom)
        rec = ctx.kb.lookup(ds["resolved"])
        if rec:
            for a in ctx.kb.amendments_of(rec.id):
                aid = node(f"amd:{rec.is_number}:{a.number}", "amendment", f"Amd {a.number} ({a.published_at.year if a.published_at else '?'})",
                           summary=a.summary)
                edge(sid, aid, "amended_by")
            for rel in ctx.kb.outgoing(rec.id, ["test_method", "normative_reference", "safety_requirement", "installation_code"]):
                tgt = ctx.kb.by_id.get(rel.to_id)
                if tgt:
                    tid = node(f"std:{tgt.is_number}", "standard", tgt.is_number, status=tgt.status, title=tgt.title[:80])
                    edge(sid, tid, rel.type)
        for g in ds.get("regulations_in_force", []) + ds.get("regulations_upcoming", []):
            gid = node(f"reg:{g['key']}", "regulation", g["title"][:40], verification=g.get("verification_state"), effective=g.get("effective_from"))
            edge(sid, gid, "mandated_by")
            cert = node(f"cert:{g.get('scheme') or g['regulation_type']}", "certification", (g.get("scheme") or g["regulation_type"])[:40])
            edge(gid, cert, "requires")
    for f in findings:
        if f["severity"] in ("critical", "major") and f.get("clause_key") and f"clause:{f['clause_key']}" in nodes:
            fid = node(f"finding:{f['fingerprint']}", "finding", f"{f['rule_id']}", severity=f["severity"], message=f["message"][:140])
            edge(fid, f"clause:{f['clause_key']}", "flags")
    return {"nodes": list(nodes.values()), "edges": edges,
            "legend": ["tender", "clause", "requirement", "standard", "amendment", "regulation", "certification", "test", "finding", "evidence"]}
