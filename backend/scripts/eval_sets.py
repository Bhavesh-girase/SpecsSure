"""Shared evaluation sets and scoring for the recommender (used by corpus_benchmark.py and quick experiments)."""
import json
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PART = re.compile(r" \(Part [^)]*\)$")


def family(b: str) -> str:
    return PART.sub("", b)


def match(pred: str, labels) -> bool:
    """Exact designation, or same family when the label names no part (GeM "IS 550" ↔ corpus "IS 550 (Part 1)")."""
    for e in labels:
        if pred == e or (" (Part" not in e and family(pred) == e):
            return True
    return False


def gem_cases(c=None, exclude_bis_names: bool = False, split: str = None):
    g = json.load(open(os.path.join(ROOT, "data", "corpus", "gem_categories.json"), encoding="utf-8"))["categories"]
    fams = {family(b) for b in c.catalogue} if c is not None else set()
    by = {}
    for x in g:
        name = x["category"]
        if re.search(r"\bservice\b", name, re.I) or len(re.findall(r"[A-Za-z]{4,}", name)) < 1 or len(name) > 160 \
                or re.match(r"^[:;,.\d\s-]", name) or re.search(r",\S", name):
            continue                      # parsing artefacts (":2003 and") and joined multi-item strings ("A,B") are not clean queries
        if c is not None and not (x["standard"] in c.catalogue or family(x["standard"]) in fams):
            continue
        k = re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()
        e = by.setdefault(k, {"query": name, "expected": [], "bids": 0})
        if x["standard"] not in e["expected"]:
            e["expected"].append(x["standard"])
        e["bids"] += x["bids"]
    cases = list(by.values())
    if split:
        from app.services.corpus_service import gem_split
        cases = [cs for cs in cases if gem_split(cs["query"]) == split]
    if exclude_bis_names:
        rows = json.load(open(os.path.join(ROOT, "data", "corpus", "compulsory_certification.json"), encoding="utf-8"))["rows"]
        bis = {re.sub(r"[^a-z0-9]+", " ", (r.get("product") or "").lower()).strip() for r in rows}
        cases = [cs for cs in cases if re.sub(r"[^a-z0-9]+", " ", cs["query"].lower()).strip() not in bis]
    return cases


def score(c, cases, k=10, **kw):
    hits = {1: 0, 3: 0, 5: 0, 10: 0}
    misses = []
    high = high_ok = 0
    for cs in cases:
        cards = c.search(cs["query"], k, **kw)
        res = [x["base"] for x in cards]
        rank = next((i + 1 for i, b in enumerate(res) if match(b, cs["expected"])), None)
        if cards and cards[0].get("confidence") == "high":
            high += 1
            high_ok += rank == 1
        for kk in hits:
            hits[kk] += bool(rank and rank <= kk)
        if not rank or rank > 1:
            misses.append({**cs, "rank": rank, "top3": res[:3]})
    n = max(1, len(cases))
    return {"cases": len(cases), **{f"top{kk}": round(100 * v / n, 1) for kk, v in hits.items()},
            "recommended_share": round(100 * high / n, 1), "recommended_precision": round(100 * high_ok / max(1, high), 1),
            "confident_but_wrong": round(100 * (high - high_ok) / n, 1), "misses": misses}
