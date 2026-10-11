"""
Bid evaluation & award engine — closes the tender lifecycle.

    technical evaluation (Tender Match Index knock-outs, per line item)
        → financial opening (sealed-bid commitments verified: SHA-256 of each price bid was ledgered at submission)
        → L1 among technically responsive bids, per line item
        → Public Procurement (Preference to Make in India) Order 2017 (revised): Class-I local supplier within the 20 %
          margin of purchase preference is invited to match L1 — full quantity for non-divisible items, 50 % for divisible
          items; procurement below ₹5 lakh is exempt
        → Public Procurement Policy for MSEs Order 2012: MSEs quoting within L1 + 15 % may supply up to 25 % of the
          requirement by matching L1, shared proportionately
        → price reasonableness vs estimate, abnormally-low and single-bid flags
        → award recommendation with every step cited

Everything is deterministic and explained step by step. The committee decides; this module only proposes.
"""
from __future__ import annotations

import hashlib
import json
from statistics import median
from typing import Dict, List, Optional

MII_MARGIN = 0.20
MII_EXEMPT_BELOW = 500000
MSE_BAND = 0.15
MSE_SHARE = 0.25
RULES = {
    "MII": {"title": "Public Procurement (Preference to Make in India) Order, 2017 (revised 16-09-2020)",
            "source_url": "https://www.dpiit.gov.in/static/uploads/2025/07/cd246ee6c3329c60400df59c0debda42.pdf", "verification_state": "secondary_source"},
    "MSE": {"title": "Public Procurement Policy for Micro and Small Enterprises Order, 2012 (as amended)",
            "source_url": "https://www.dcmsme.gov.in/FAQs-PPP_25032022.pdf", "verification_state": "secondary_source"},
}


def commitment(bid_id: str, financial: dict, salt: str) -> str:
    """Sealed-bid commitment: SHA-256 over the canonical financial bid + bid id + salt."""
    payload = json.dumps({"bid": bid_id, "financial": financial, "salt": salt}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _fmt(v: float) -> str:
    return f"₹{v:,.2f}"


def _line_price(fin: dict, line_index: int) -> Optional[float]:
    lines = (fin or {}).get("lines") or {}
    x = lines.get(str(line_index)) or lines.get(line_index)
    if isinstance(x, dict):
        x = x.get("unit_price")
    try:
        return float(x) if x not in (None, "") else None
    except (TypeError, ValueError):
        return None


def tender_lines(tender_twin: dict, generation: Optional[dict]) -> List[dict]:
    if generation and generation.get("lines"):
        from app.engine.kg import item_by_id
        out = []
        for l in generation["lines"]:
            it = item_by_id(l["item_id"]) or {}
            lo, hi = it.get("estimate_inr") or [None, None]
            out.append({"index": l["index"], "label": l["item_label"], "item_id": l["item_id"], "domain": it.get("domain"),
                        "quantity": float(l["quantity"]), "unit": l.get("unit") or it.get("default_unit"),
                        "estimate_unit": (lo + hi) / 2 if lo is not None else None, "divisible": float(l["quantity"]) > 1})
        return out
    doms = (tender_twin.get("tender") or {}).get("domains") or [None]
    return [{"index": 1, "label": "Entire tender (lump sum)", "item_id": None, "domain": doms[0], "quantity": 1.0, "unit": "lot",
             "estimate_unit": None, "divisible": False}]


def _responsive_for_line(score: dict, domain: Optional[str]) -> (bool, List[str]):
    reasons = []
    for r in score.get("results", []):
        if r.get("knockout") and (domain is None or r["group"] in (domain, "general")):
            reasons.append(f"{r['label']} (Cl. {r.get('clause_key')}): {r['detail']}")
    return (not reasons), reasons


def evaluate(tender_twin: dict, generation: Optional[dict], bids: List[dict], estimated_value: Optional[float] = None,
             financial_open: bool = True) -> dict:
    """bids: [{bid_id, bidder, score, scope, financial, declarations, commitment, salt}]"""
    lines = tender_lines(tender_twin, generation)
    est_total = estimated_value or sum((l["estimate_unit"] or 0) * l["quantity"] for l in lines) or None
    mii_applicable = bool(est_total and est_total >= MII_EXEMPT_BELOW)
    integrity = []
    for b in bids:
        if b.get("commitment") and b.get("salt") is not None:
            ok = commitment(b["bid_id"], b.get("financial") or {}, b["salt"]) == b["commitment"]
            integrity.append({"bid_id": b["bid_id"], "bidder": b["bidder"], "sealed": True, "verified": ok})
        else:
            integrity.append({"bid_id": b["bid_id"], "bidder": b["bidder"], "sealed": False, "verified": None})
    out_lines = []
    for ln in lines:
        entries = []
        for b in bids:
            scope = b.get("scope") or []
            quoting = (not scope) or ln["domain"] in scope or ln["domain"] is None
            price = _line_price(b.get("financial"), ln["index"])
            if not quoting or price is None:
                continue
            responsive, reasons = _responsive_for_line(b.get("score") or {}, ln["domain"])
            d = b.get("declarations") or {}
            entries.append({"bid_id": b["bid_id"], "bidder": b["bidder"], "unit_price": price if financial_open else None,
                            "_price": price, "responsive": responsive, "reasons": reasons, "match_index": (b.get("score") or {}).get("match_index"),
                            "mse": bool(d.get("mse")), "mii_class": d.get("mii_class") or "non-local", "local_content": d.get("local_content")})
        steps: List[dict] = []
        resp = sorted([e for e in entries if e["responsive"]], key=lambda e: e["_price"])
        rejected = [e for e in entries if not e["responsive"]]
        for e in rejected:
            steps.append({"step": "technical", "text": f"{e['bidder']} is technically non-responsive and its financial bid is not considered: {'; '.join(e['reasons'][:2])}"})
        line_out = {**{k: ln[k] for k in ("index", "label", "item_id", "domain", "quantity", "unit", "divisible")},
                    "estimate_unit": ln["estimate_unit"], "bids": [], "steps": steps, "allocation": [], "flags": []}
        if not entries:
            line_out["flags"].append({"level": "warn", "text": "No bid received for this item — consider re-tendering or a limited tender enquiry for it."})
            out_lines.append(line_out)
            continue
        if not resp:
            line_out["flags"].append({"level": "warn", "text": "No technically responsive bid — re-tender after reviewing restrictive clauses (see Market restriction)."})
            line_out["bids"] = [{k: v for k, v in e.items() if k != "_price"} for e in entries]
            out_lines.append(line_out)
            continue
        if not financial_open:
            line_out["bids"] = [{k: v for k, v in e.items() if k != "_price"} for e in entries]
            line_out["sealed"] = True
            out_lines.append(line_out)
            continue
        for i, e in enumerate(resp):
            e["rank"] = f"L{i + 1}"
        l1 = resp[0]
        p1 = l1["_price"]
        steps.append({"step": "L1", "text": f"L1 among {len(resp)} technically responsive bid(s): {l1['bidder']} at {_fmt(p1)} per {ln['unit']}."})
        q = ln["quantity"]
        alloc: Dict[str, float] = {l1["bid_id"]: q}
        price_of: Dict[str, float] = {l1["bid_id"]: p1}
        # ---- Make in India
        if not mii_applicable:
            steps.append({"step": "MII", "rule": "MII", "text": f"Make in India purchase preference not applied: estimated value {_fmt(est_total or 0)} is below ₹5 lakh (exempt)."})
        elif l1["mii_class"] == "I":
            steps.append({"step": "MII", "rule": "MII", "text": f"L1 is a Class-I local supplier — no purchase-preference adjustment needed."})
        else:
            cands = [e for e in resp[1:] if e["mii_class"] == "I" and e["_price"] <= p1 * (1 + MII_MARGIN) + 1e-9]
            if not cands:
                steps.append({"step": "MII", "rule": "MII", "text": "No Class-I local supplier within the 20 % margin of purchase preference — L1 stands."})
            else:
                c = cands[0]
                share = q * 0.5 if ln["divisible"] else q
                if ln["unit"] == "nos":
                    share = float(int(share))
                alloc[l1["bid_id"]] = q - share
                alloc[c["bid_id"]] = alloc.get(c["bid_id"], 0) + share
                price_of[c["bid_id"]] = p1
                steps.append({"step": "MII", "rule": "MII",
                              "text": (f"L1 is not Class-I. {c['bidder']} (Class-I, {_fmt(c['_price'])}, within 20 % of L1) is invited to match L1 at {_fmt(p1)} for "
                                       + ("50 % of the quantity (divisible item)." if ln["divisible"] else "the full quantity (non-divisible item).")
                                       + " Subject to its written acceptance; if it declines, the next Class-I bidder within the margin is invited.")})
        # ---- MSE
        if l1["mse"]:
            steps.append({"step": "MSE", "rule": "MSE", "text": "L1 is a Micro/Small Enterprise — MSE purchase preference not triggered."})
        else:
            mses = [e for e in resp[1:] if e["mse"] and e["_price"] <= p1 * (1 + MSE_BAND) + 1e-9]
            if not mses:
                steps.append({"step": "MSE", "rule": "MSE", "text": "No MSE within the L1 + 15 % price band."})
            else:
                target = q * MSE_SHARE
                already = sum(alloc.get(e["bid_id"], 0) for e in mses)
                if already + 1e-9 >= target:
                    steps.append({"step": "MSE", "rule": "MSE", "text": f"MSE(s) within L1 + 15 % already receive {already:g} {ln['unit']} (≥ 25 % reserved share) through the Make in India step — no further change."})
                else:
                    need = target - already
                    per = need / len(mses)
                    if ln["unit"] == "nos":
                        per = float(int(per))
                    for e in mses:
                        take = min(per, alloc.get(l1["bid_id"], 0))
                        alloc[l1["bid_id"]] -= take
                        alloc[e["bid_id"]] = alloc.get(e["bid_id"], 0) + take
                        price_of[e["bid_id"]] = p1
                    steps.append({"step": "MSE", "rule": "MSE",
                                  "text": f"{', '.join(e['bidder'] for e in mses)} (MSE, within L1 + 15 %) may supply up to 25 % of the requirement ({target:g} {ln['unit']}) by matching L1 at {_fmt(p1)}, shared proportionately; subject to acceptance."})
        # ---- reasonableness / flags
        if ln["estimate_unit"]:
            dev = (p1 - ln["estimate_unit"]) / ln["estimate_unit"]
            line_out["price_vs_estimate"] = round(dev, 3)
            if dev < -0.4:
                line_out["flags"].append({"level": "warn", "text": f"L1 is {abs(dev) * 100:.0f} % below the estimate — possibly abnormally low; seek price justification before award."})
            elif dev > 0.25:
                line_out["flags"].append({"level": "warn", "text": f"L1 is {dev * 100:.0f} % above the estimate — check reasonableness (market survey / last purchase price)."})
        if len(resp) == 1:
            line_out["flags"].append({"level": "info", "text": "Single technically responsive bid — record reasons and assess reasonableness before award."})
        if len(resp) >= 3:
            prices = [e["_price"] for e in resp]
            if p1 < 0.7 * median(prices):
                line_out["flags"].append({"level": "warn", "text": "L1 is more than 30 % below the median responsive price — seek justification."})
        by_id = {e["bid_id"]: e for e in entries}
        for bid_id, qty in alloc.items():
            if qty <= 0:
                continue
            e = by_id[bid_id]
            line_out["allocation"].append({"bid_id": bid_id, "bidder": e["bidder"], "quantity": qty, "unit_price": price_of[bid_id],
                                           "value": round(qty * price_of[bid_id], 2), "basis": "L1" if bid_id == l1["bid_id"] else "preference (match L1)"})
        line_out["bids"] = sorted([{k: v for k, v in e.items() if k != "_price"} | {"unit_price": e["_price"]} for e in entries],
                                  key=lambda x: (not x["responsive"], x["unit_price"]))
        line_out["l1"] = {"bid_id": l1["bid_id"], "bidder": l1["bidder"], "unit_price": p1}
        line_out["contract_value"] = round(sum(a["value"] for a in line_out["allocation"]), 2)
        out_lines.append(line_out)
    total = round(sum(l.get("contract_value") or 0 for l in out_lines), 2)
    return {"financial_open": financial_open, "estimated_value": est_total, "mii_applicable": mii_applicable, "lines": out_lines,
            "recommended_contract_value": total if financial_open else None, "integrity": integrity, "rules": RULES,
            "note": ("Proposal for the Tender Evaluation Committee. Purchase-preference steps assume the invited bidders accept to match L1; "
                     "where both Make in India and MSE preferences apply, the allocation must be confirmed against the latest DoE / DPIIT / MSME instructions.")}
