"""
Smart Bid Form + Tender Match Index — the contractor side of the Tender Digital Twin.

1. derive_form(twin)      Every requirement of the *canonical* tender (after corrigenda) becomes a typed field:
                          numbers with the tender's unit and bound, size lists, certificate numbers with validity,
                          test-report particulars, and declarations. The form is generated, never hand-built, so it
                          always matches the latest effective version of every clause.
2. autofill(form, docs)   Uploaded datasheets / BIS licences / NABL reports (PDF, DOCX, scans via OCR) pre-fill the
                          form; every value keeps document → page → snippet and an evidence strength
                          (3 lab report · 2 licence/certificate · 1 datasheet · 0.5 self-declared).
3. score(form, answers)   Deterministic evaluation of every field and a transparent *Tender Match Index*:
                              knock-outs  a mandatory technical/legal requirement that is not met (substantive)
                              coverage    share of requirements met, weighted (certification 3 · technical 2 · declaration 1)
                              confidence  how strongly the claims are evidenced
                              headroom    how far the offer exceeds the requirement — shown for information only;
                                          under L1 evaluation exceeding a requirement earns no marks
                          plus a *path to compliance*: what to attach (curable) vs what to change (substantive).

AI does not score bids: every status is a comparison of numbers/dates against the clause, and the result is
labelled decision support for the tender committee.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List, Optional

import re

from app.engine import ontology


def _test_method_families() -> set:
    from functools import lru_cache  # noqa: F401
    fams = set()
    try:
        from app.engine.kg import items
        from app.engine.std_refs import family_of
        for it in items():
            for x in it["standards"]:
                if x["role"] == "test method":
                    fams.add(family_of(x["family"]))
    except Exception:
        pass
    for p in ontology.parameters().values():
        t = p.get("test") or {}
        if t.get("standard") and not ontology.standards_parameters().get(t["standard"]):
            from app.engine.std_refs import family_of
            fams.add(family_of(t["standard"]))
    return fams


def _edition_mismatch(on_cert: str, required: str) -> bool:
    from app.engine.std_refs import family_of, year_of
    return family_of(on_cert) == family_of(required) and year_of(on_cert) is not None and year_of(required) is not None \
        and year_of(on_cert) != year_of(required)


def _item_domain(family: str) -> Optional[str]:
    try:
        from app.engine.kg import items
        from app.engine.std_refs import family_of
        for it in items():
            if any(family_of(x["family"]) == family or x["family"] == family for x in it["standards"]):
                return it["domain"]
    except Exception:
        return None
    return None

DECLARATION_KINDS = {"delivery", "warranty", "packaging", "documentation", "inspection", "acceptance", "general", "eligibility", "brand"}
WEIGHT = {"certificate": 3, "number": 2, "sizes": 2, "standard": 2, "test_report": 2, "declaration": 1}
STRENGTH_LABEL = {0: "none", 0.5: "self-declared", 1: "manufacturer datasheet", 2: "licence / certificate", 3: "accredited lab report"}


def _unit_display(u: Optional[str]) -> str:
    if not u or u == "dimensionless":
        return ""
    return u.replace("**2", "²").replace("**3", "³").replace("percent", "%")


def _req_text(norm: dict) -> str:
    lo, hi, u = norm.get("min"), norm.get("max"), _unit_display(norm.get("unit"))
    if norm.get("values"):
        return "all of " + ", ".join(f"{v:g}" for v in norm["values"]) + f" {u}"
    if lo is not None and hi is not None and lo == hi:
        return f"= {lo:g} {u}".strip()
    if lo is not None and hi is not None:
        return f"{lo:g} – {hi:g} {u}".strip()
    if lo is not None:
        return f"≥ {lo:g} {u}".strip()
    if hi is not None:
        return f"≤ {hi:g} {u}".strip()
    return ""


def derive_form(twin: dict) -> dict:
    clauses = {c["key"]: c for c in twin.get("clauses", [])}
    groups: Dict[str, dict] = {}
    fields: List[dict] = []
    bid_due = (twin.get("tender") or {}).get("dates", {}).get("bid_due")
    contradictory = {rid for f in twin.get("findings", []) if f["rule_id"] in ("SS-CON-001", "SS-CON-002") for rid in f.get("requirement_ids", [])}

    def group_for(req) -> str:
        dom = req.get("domain") if req.get("domain") not in (None, "general") else None
        c = clauses.get(req["clause_key"]) or {}
        dom = dom or (ontology.detect_domains((c.get("heading") or "") + " " + (c.get("text") or "")) or c.get("domain_hint") or [None])[0]
        key = dom or "general"
        if key not in groups:
            ds = (twin.get("domain_standards") or {}).get(key, {})
            groups[key] = {"id": key, "title": (f"{key.title()} — {ds.get('resolved')}" if ds.get("resolved") else ("General & commercial conditions" if key == "general" else key.title())),
                           "standard": ds.get("resolved")}
        return key

    # mandatory certification per product domain (from the regulation registry, as of the tender date)
    for dom, ds in (twin.get("domain_standards") or {}).items():
        mand = [g for g in ds.get("regulations_in_force", []) if (g.get("is_mandatory") or "yes") == "yes"]
        if not mand:
            continue
        g = mand[0]
        crs = g.get("regulation_type") == "CRS"
        group_for({"domain": dom, "clause_key": ds.get("clause_key") or ""})
        fields.append({"id": f"CERT-{dom}", "group": dom, "type": "certificate", "clause_key": ds.get("clause_key"), "mandatory": True,
                       "label": "BIS registration (R-number)" if crs else "BIS licence (CM/L number)",
                       "requirement": f"{'Registration' if crs else 'Licence'} for {ds.get('resolved')} valid on the bid due date {bid_due or ''}".strip(),
                       "regulation": g.get("title"), "scheme": g.get("scheme"), "evidence_hint": "BIS licence / registration certificate",
                       "resolved": ds.get("resolved"),
                       "bid_due": bid_due, "knockout": True})

    for r in twin.get("requirements", []):
        kind = r["kind"]
        if kind == "schedule":
            continue
        c = clauses.get(r["clause_key"]) or {}
        base = {"id": r["id"], "clause_key": r["clause_key"], "page": r.get("page"), "text": r["text"], "clause_heading": c.get("heading"),
                "modality": r.get("modality"), "mandatory": (r.get("modality") or "shall") in ("shall", "must", "is required to", "are required to"),
                "contradictory": r["id"] in contradictory}
        if kind == "parameter" and r.get("parameter"):
            p = ontology.parameters().get(r["parameter"], {})
            cat = p.get("category")
            g = group_for(r)
            if r.get("op") == "enum" and r["norm"].get("values"):
                fields.append({**base, "group": g, "type": "sizes", "label": r.get("parameter_label"), "parameter": r["parameter"],
                               "unit": _unit_display(r["norm"].get("unit")), "required_values": r["norm"]["values"],
                               "requirement": _req_text(r["norm"]), "knockout": base["mandatory"], "evidence_hint": "datasheet / licence schedule"})
                continue
            if r["norm"].get("min") is None and r["norm"].get("max") is None:
                continue
            test = (p.get("test") or {}).get("standard")
            fields.append({**base, "group": g, "type": "number", "label": r.get("parameter_label"), "parameter": r["parameter"],
                           "unit": _unit_display(r["norm"].get("unit")), "norm": r["norm"], "requirement": _req_text(r["norm"]),
                           "commercial": cat in ("delivery", "warranty"), "knockout": base["mandatory"] and cat not in ("delivery", "warranty"),
                           "evidence_hint": f"NABL test report ({test})" if test else "declaration"})
            continue
        if kind in ("standard_compliance",) and r.get("standards"):
            if re.search(r"referenced standards|normative|^acceptance", c.get("heading") or "", re.I):
                continue      # dependency closure / lot-acceptance clauses are not bid-time conformity declarations
            by_dom: Dict[str, List[str]] = {}
            for s_ in r.get("standards", []):
                if s_.get("body") != "BIS":
                    continue
                fam = s_.get("family") or ""
                if fam in _test_method_families():
                    continue  # "conformity to a test method" is meaningless; it is covered by the test report
                dom = (ontology.standards_parameters().get(fam) or {}).get("domain") or _item_domain(fam) or None
                by_dom.setdefault(dom or group_for(r), []).append(s_.get("display") or fam)
            is_type_test = bool(re.search(r"type test", (c.get("heading") or "") + " " + r["text"], re.I))
            for dom, fams in by_dom.items():
                groups.setdefault(dom, {"id": dom, "title": dom.title(), "standard": None}) if dom not in groups else None
                if is_type_test:
                    fields.append({**base, "id": f"{r['id']}:{dom}:report", "group": dom, "type": "test_report",
                                   "label": "Type test report (" + ", ".join(fams[:2]) + ")", "requirement": "NABL-accredited type test report, not older than three years",
                                   "knockout": base["mandatory"], "evidence_hint": "NABL-accredited laboratory report (lab name, NABL certificate no., report no., date)"})
                    continue
                fields.append({**base, "id": r["id"] if len(by_dom) == 1 else f"{r['id']}:{dom}", "group": dom, "type": "standard",
                               "label": "Conformity to " + ", ".join(fams[:3]), "standards": fams,
                               "requirement": "Offered product conforms (incl. amendments in force)", "knockout": base["mandatory"],
                               "evidence_hint": "type test report / licence"})
            continue
        if kind == "testing" and not re.search(r"type test|test report|with the bid|report", r["text"], re.I):
            kind = "acceptance"      # lot acceptance / re-test rules are obligations at supply stage, not bid documents
        if kind == "testing":
            g = group_for(r)
            fields.append({**base, "group": g, "type": "test_report", "label": "Type test report", "requirement": r["text"][:160],
                           "knockout": base["mandatory"], "evidence_hint": "NABL-accredited laboratory report (lab name, NABL certificate no., report no., date)"})
            continue
        if kind in DECLARATION_KINDS or kind == "certification":
            if kind == "certification" and any(f["type"] == "certificate" for f in fields):
                continue      # covered by the licence field
            fields.append({**base, "group": "general" if kind not in ("certification",) else group_for(r), "type": "declaration",
                           "label": (c.get("heading") or kind.title())[:60], "requirement": r["text"][:200], "knockout": False,
                           "evidence_hint": "signed undertaking"})
            groups.setdefault("general", {"id": "general", "title": "General & commercial conditions", "standard": None})
    # de-duplicate declarations of the same clause
    seen, out = set(), []
    for f in fields:
        k = (f["type"], f.get("clause_key"), f.get("parameter"), f["label"]) if f["type"] == "declaration" else f["id"]
        if k in seen:
            continue
        seen.add(k)
        out.append(f)
    order = {g: i for i, g in enumerate(list(groups.keys()))}
    out.sort(key=lambda f: (f["group"] == "general", order.get(f["group"], 99), {"certificate": 0, "standard": 1, "number": 2, "sizes": 3, "test_report": 4, "declaration": 5}[f["type"]]))
    return {"tender": {"id": (twin.get("tender") or {}).get("id"), "title": (twin.get("tender") or {}).get("title"), "bid_due": bid_due,
                       "reference_no": (twin.get("tender") or {}).get("reference_no")},
            "groups": [groups[g] for g in groups], "fields": out, "field_count": len(out),
            "kb_snapshot": (twin.get("provenance") or {}).get("kb_snapshot"), "content_hash": (twin.get("provenance") or {}).get("content_hash")}


# ------------------------------------------------------------------------------------------ autofill
def autofill(form: dict, evidence_docs: List[dict]) -> Dict[str, dict]:
    items = [i for d in evidence_docs for i in d["items"]]
    metas = [d["meta"] for d in evidence_docs]
    answers: Dict[str, dict] = {}
    for f in form["fields"]:
        if f["type"] == "number":
            evs = [i for i in items if i["kind"] == "parameter" and i.get("parameter") == f["parameter"] and i.get("value") is not None]
            if evs:
                e = max(evs, key=lambda i: i["strength"])
                answers[f["id"]] = {"value": e["value"], "doc_value": e["value"], "source": _src(e)}
        elif f["type"] == "sizes":
            evs = [i for i in items if i["kind"] == "sizes" and i.get("parameter") == f["parameter"]]
            if evs:
                e = max(evs, key=lambda i: i["strength"])
                answers[f["id"]] = {"values": e["values"], "source": _src(e)}
        elif f["type"] == "certificate":
            lic = next((m for m in metas if m.get("licence_no") and (not m.get("domains") or f["group"] in m["domains"])), None)
            if lic:
                std_on_cert = next((i["raw_value"] for i in items if i["kind"] == "standard" and i["doc_name"] == lic["doc_name"]), None)
                answers[f["id"]] = {"number": lic["licence_no"], "valid_to": lic.get("valid_to"), "grade": lic.get("grade"), "standard": std_on_cert,
                                    "source": {"doc_name": lic["doc_name"], "doc_type": lic["doc_type"], "page": 1, "strength": 2,
                                               "snippet": f"Licence {lic['licence_no']} valid to {lic.get('valid_to')}"}}
        elif f["type"] == "standard":
            evs = [i for i in items if i["kind"] == "standard"]
            fams = [s.split(":")[0] for s in f["standards"]]
            hit = [e for e in evs if any(e["extra"].get("family", "").split(":")[0] in s or s in e["extra"].get("family", "") for s in fams)]
            if hit:
                e = max(hit, key=lambda i: i["strength"])
                answers[f["id"]] = {"conforms": True, "source": _src(e)}
        elif f["type"] == "test_report":
            rep = next((m for m in metas if m.get("doc_type") == "test_report" and (not m.get("domains") or f["group"] in (m["domains"] + ["general"]))), None)
            if rep:
                answers[f["id"]] = {"lab": rep.get("lab"), "nabl_certificate": rep.get("nabl_certificate"), "report_no": rep.get("report_no"),
                                    "report_date": rep.get("report_date"), "accredited": bool(rep.get("accredited")),
                                    "source": {"doc_name": rep["doc_name"], "doc_type": "test_report", "page": 1, "strength": 3,
                                               "snippet": f"{rep.get('lab')} · {rep.get('nabl_certificate') or 'NABL no. not found'} · {rep.get('report_date')}"}}
    return answers


def _src(e: dict) -> dict:
    return {"doc_name": e["doc_name"], "doc_type": e["doc_type"], "page": e["page"], "snippet": e["snippet"][:200],
            "strength": e["strength"], "raw_value": e.get("raw_value"), "qualifier": e.get("qualifier")}


# ------------------------------------------------------------------------------------------ scoring
def _cmp_number(norm: dict, v: float) -> (str, Optional[float], str):
    lo, hi = norm.get("min"), norm.get("max")
    if lo is not None and hi is not None and lo == hi:
        tol = max(abs(lo) * 1e-6, 1e-9)
        return ("MEETS" if abs(v - lo) <= tol else "FAILS"), 0.0, f"required {lo:g}, offered {v:g}"
    if lo is not None and v < lo - 1e-9:
        return "FAILS", (v - lo) / abs(lo) if lo else None, f"offered {v:g} is below the minimum {lo:g}"
    if hi is not None and v > hi + 1e-9:
        return "FAILS", (hi - v) / abs(hi) if hi else None, f"offered {v:g} exceeds the maximum {hi:g}"
    margins = []
    if lo is not None and lo:
        margins.append((v - lo) / abs(lo))
    if hi is not None and hi:
        margins.append((hi - v) / abs(hi))
    m = min(margins) if margins else None
    if m is not None and m > 0.02:
        return "EXCEEDS", m, f"offered {v:g} — {m * 100:.0f}% headroom over the limit"
    return "MEETS", m, f"offered {v:g} — meets the requirement"


def infer_scope(form: dict, evidence_docs: List[dict]) -> Optional[List[str]]:
    doms = {d for doc in evidence_docs for d in (doc["meta"].get("domains") or [])}
    groups = {g["id"] for g in form["groups"]}
    hit = sorted(doms & groups)
    return hit or None


def score(form: dict, answers: Dict[str, dict], today: Optional[date] = None, scope: Optional[List[str]] = None) -> dict:
    """scope: product groups the bidder is quoting for (item-wise bids); None = all."""
    today = today or date.today()
    bid_due = form["tender"].get("bid_due")
    results = []
    for f in form["fields"]:
        if scope and f["group"] not in scope and f["group"] != "general":
            continue
        a = answers.get(f["id"]) or {}
        src = a.get("source")
        strength = (src or {}).get("strength", 0.5 if a else 0)
        st, detail, margin, action, curable = "MISSING", "", None, None, True
        t = f["type"]
        if f.get("contradictory"):
            st, detail = "CLARIFY", "The tender clause itself is contradictory (formally proven) — raise a pre-bid query."
            action = f"Ask the buyer to resolve Clause {f['clause_key']} before quoting."
        elif t == "number":
            v = a.get("value")
            if v is None or v == "":
                detail = f"No value offered for {f['label']}."
                action = f"State {f['label']} ({f['requirement']}) and attach {f['evidence_hint']}."
            else:
                st, margin, detail = _cmp_number(f["norm"], float(v))
                if st == "FAILS":
                    curable = False
                    action = f"Offer a product with {f['label']} {f['requirement']} (yours: {float(v):g} {f.get('unit') or ''})."
                ev = a.get("doc_value")
                if ev is not None and abs(float(ev) - float(v)) > max(abs(float(v)) * 0.005, 1e-9):
                    st, detail, curable = "CONFLICT", f"Declared {float(v):g} but {src.get('doc_name')} p.{src.get('page')} shows {float(ev):g}.", False
                    action = f"Reconcile the declared {f['label']} with {src.get('doc_name')}."
                elif st in ("MEETS", "EXCEEDS") and strength < 2 and not f.get("commercial"):
                    action = f"Attach {f['evidence_hint']} to prove {f['label']}."
        elif t == "sizes":
            vals = a.get("values") or []
            if not vals:
                detail = "No sizes offered."
                action = f"List the offered sizes ({f['requirement']})."
            else:
                missing = sorted(set(f["required_values"]) - set(float(x) for x in vals))
                st = "FAILS" if missing else "MEETS"
                detail = f"missing {', '.join(f'{m:g}' for m in missing)}" if missing else "all required sizes offered"
                if missing:
                    curable = False
                    action = f"Offer the missing sizes {', '.join(f'{m:g}' for m in missing)} {f.get('unit') or ''}."
        elif t == "certificate":
            num, vt = (a.get("number") or "").strip(), a.get("valid_to")
            if not num:
                detail = f"No {f['label']} provided — mandatory under {f.get('regulation') or 'the applicable order'}."
                action = f"Provide a valid {f['label']} ({f.get('scheme') or 'BIS'})."
                curable = False
            elif vt and bid_due and vt < bid_due:
                st, detail, curable = "FAILS", f"{num} expires on {vt}, before the bid due date {bid_due}.", False
                action = f"Renew {num} before {bid_due} and upload the renewed licence."
                if a.get("standard") and f.get("resolved") and _edition_mismatch(a["standard"], f["resolved"]):
                    detail += f" It is also issued against {a['standard']}, not the edition in force {f['resolved']}."
                    action = f"Renew {num} before {bid_due} against {f['resolved']} (the edition in force) and upload it."
            elif a.get("standard") and f.get("resolved") and _edition_mismatch(a["standard"], f["resolved"]):
                st, curable = "FAILS", True
                detail = (f"{num} is issued against {a['standard']}, but the edition in force (required by the tender) is {f['resolved']} — "
                          "the licence/registration must cover the current edition.")
                action = f"Get {num} updated to {f['resolved']} (BIS inclusion / re-registration) and upload the revised certificate."
            elif not vt:
                st, detail = "UNVERIFIED", f"{num} given without validity date."
                action = f"Enter the validity date of {num} and attach the licence copy."
            else:
                st, detail = "MEETS", f"{num} valid to {vt}; verify on the BIS portal."
                strength = max(strength, 2 if src else 1)
        elif t == "standard":
            if a.get("conforms"):
                st, detail = "MEETS", "Conformity declared" + (f" ({src['doc_name']})" if src else " (self-declared)")
                if strength < 2:
                    action = f"Attach a type test report / licence showing conformity to {', '.join(f['standards'][:2])}."
            else:
                detail = "Conformity not declared."
                action = f"Declare conformity to {', '.join(f['standards'][:2])}."
                curable = False
        elif t == "test_report":
            if a.get("lab") and (a.get("nabl_certificate") or a.get("accredited")):
                rd = a.get("report_date")
                stale = False
                if rd:
                    try:
                        stale = date.fromisoformat(rd) < today - timedelta(days=3 * 365)
                    except ValueError:
                        stale = False
                st = "FAILS" if stale else "MEETS"
                detail = f"{a.get('lab')} ({a.get('nabl_certificate') or 'accredited'}), report {a.get('report_no') or ''} dated {rd or '—'}" + (" — older than 3 years" if stale else "")
                strength = max(strength, 3 if src else 1)
                if stale:
                    action = "Obtain a fresh type test report (not older than three years)."
            elif a.get("lab"):
                st, detail = "UNVERIFIED", "Laboratory named without NABL accreditation details."
                action = "Add the NABL certificate number of the laboratory (scope must cover the tests)."
            else:
                detail = "No test report particulars."
                action = "Attach a NABL-accredited type test report."
        elif t == "declaration":
            if a.get("accepted"):
                st, detail, strength = "MEETS", "Accepted by the bidder", max(strength, 1)
            else:
                detail = "Not yet accepted."
                action = f"Accept Clause {f['clause_key']} ({f['label']})."
        results.append({"field_id": f["id"], "group": f["group"], "type": t, "label": f["label"], "clause_key": f.get("clause_key"),
                        "requirement": f.get("requirement"), "status": st, "detail": detail, "margin": round(margin, 4) if margin is not None else None,
                        "evidence_strength": strength, "evidence_label": STRENGTH_LABEL.get(strength, str(strength)), "source": src,
                        "knockout": bool(f.get("knockout")) and st in ("FAILS", "CONFLICT") or (t == "certificate" and st in ("FAILS",) ) or (t == "certificate" and st == "MISSING"),
                        "action": action, "curable": curable if st not in ("MEETS", "EXCEEDS") else None, "weight": WEIGHT[t]})

    tot_w = sum(r["weight"] for r in results) or 1
    met_w = sum(r["weight"] * (1.0 if r["status"] in ("MEETS", "EXCEEDS") else 0.5 if r["status"] == "UNVERIFIED" else 0.0) for r in results)
    tech = [r for r in results if r["type"] in ("number", "sizes", "certificate", "standard", "test_report")]
    conf = (sum(min(r["evidence_strength"], 3) / 3 for r in tech if r["status"] in ("MEETS", "EXCEEDS", "UNVERIFIED")) / len(tech)) if tech else 0.0
    coverage = met_w / tot_w
    knockouts = [r for r in results if r["knockout"]]
    index = round(100 * (0.75 * coverage + 0.25 * conf), 1)
    if knockouts:
        index = min(index, 49.0)
    missing = [r for r in results if r["status"] in ("MISSING", "UNVERIFIED")]
    if knockouts:
        tier, verdict = "NON_RESPONSIVE", f"Knock-out on {len(knockouts)} mandatory requirement(s) — the bid would be rejected at technical evaluation."
    elif missing:
        tier, verdict = "RESPONSIVE_WITH_GAPS", f"No knock-outs; {len(missing)} item(s) need documents or entries before submission."
    elif any(r["status"] == "CLARIFY" for r in results):
        tier, verdict = "SUBJECT_TO_CLARIFICATION", "Depends on the buyer's clarification of contradictory clauses."
    else:
        tier, verdict = "FULLY_RESPONSIVE", "Every requirement is met and evidenced."
    margins = [r["margin"] for r in results if r["margin"] is not None and r["status"] in ("MEETS", "EXCEEDS")]
    by_group: Dict[str, dict] = {}
    for r in results:
        g = by_group.setdefault(r["group"], {"group": r["group"], "total": 0, "met": 0, "knockouts": 0})
        g["total"] += 1
        g["met"] += 1 if r["status"] in ("MEETS", "EXCEEDS") else 0
        g["knockouts"] += 1 if r["knockout"] else 0
    path = [{"field_id": r["field_id"], "clause_key": r["clause_key"], "action": r["action"], "kind": "substantive" if r["curable"] is False else "documentary",
             "status": r["status"]} for r in results if r["action"]]
    path.sort(key=lambda p: (p["kind"] != "substantive", p["clause_key"] or ""))
    counts: Dict[str, int] = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return {"scope": scope or [g["id"] for g in form["groups"]], "match_index": index, "tier": tier, "verdict": verdict, "coverage": round(coverage, 3), "evidence_confidence": round(conf, 3),
            "knockouts": len(knockouts), "counts": counts, "headroom": round(sum(margins) / len(margins), 4) if margins else None,
            "headroom_note": "Informational only — under L1 evaluation, exceeding a requirement earns no extra marks.",
            "groups": list(by_group.values()), "results": results, "path_to_compliance": path,
            "formula": "Match Index = 100 × (0.75 × weighted coverage + 0.25 × evidence confidence); capped at 49 if any knock-out. "
                       "Weights: certificate 3, technical 2, declaration 1. Evidence: lab 3, licence 2, datasheet 1, self-declared 0.5.",
            "disclaimer": "Decision support — the tender committee decides technical responsiveness."}


def declared_evidence_doc(form: dict, answers: Dict[str, dict], bidder: str) -> dict:
    """Turn typed form answers into an evidence document (strength 0.5–1) so the Bid Mirror can combine them with files."""
    items, meta = [], {"doc_type": "declaration", "doc_name": f"Technical compliance sheet — {bidder}", "sha256": "", "domains": []}
    for f in form["fields"]:
        a = answers.get(f["id"]) or {}
        if a.get("source"):
            continue          # already backed by a document
        if f["type"] == "number" and a.get("value") not in (None, ""):
            items.append({"doc_name": meta["doc_name"], "doc_type": "datasheet", "page": 1, "kind": "parameter", "snippet": f"Declared {f['label']}: {a['value']} {f.get('unit') or ''}",
                          "strength": 1, "parameter": f["parameter"], "parameter_label": f["label"], "value": float(a["value"]), "values": [],
                          "unit": f.get("unit"), "raw_value": f"{a['value']} {f.get('unit') or ''}".strip(), "qualifier": None, "method": None, "extra": {}})
        if f["type"] == "sizes" and a.get("values"):
            items.append({"doc_name": meta["doc_name"], "doc_type": "datasheet", "page": 1, "kind": "sizes", "snippet": f"Declared sizes {a['values']}",
                          "strength": 1, "parameter": f["parameter"], "parameter_label": f["label"], "value": None, "values": [float(x) for x in a["values"]],
                          "unit": f.get("unit"), "raw_value": str(a["values"]), "qualifier": None, "method": None, "extra": {}})
        if f["type"] == "certificate" and a.get("number"):
            meta.update({"licence_no": a["number"], "valid_to": a.get("valid_to"), "grade": a.get("grade")})
    return {"meta": meta, "items": items}
