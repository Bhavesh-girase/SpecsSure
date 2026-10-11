"""
Recommender benchmark with labels authored by BIS itself: every row of the "Products under Compulsory Certification"
pages pairs a product name with the Indian Standard it must conform to (e.g. "Sulphate Resisting Portland Cement" →
IS 12330). The product name is the query; we check whether that standard (or its parent part) is ranked in the top k.

Output: data/evaluation/corpus_benchmark.json
"""
import json
import os
import re
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def main():
    # benchmark numbers are reported WITHOUT the product-name alias field: the BIS list is itself one of its sources
    os.environ.setdefault("CORPUS_ALIASES", "0")
    if os.environ["CORPUS_ALIASES"] != "0":
        os.environ.setdefault("CORPUS_GEM_ALIAS_SPLIT", "train")      # with aliases, GeM names of the test half stay unseen
    from app.services.corpus_service import Corpus
    c = Corpus().load()
    rows = json.load(open(os.path.join(ROOT, "data", "corpus", "compulsory_certification.json"), encoding="utf-8"))["rows"]
    seen, cases = set(), []
    for r in rows:
        q = re.sub(r"\s+", " ", (r.get("product") or "")).strip(" -–—")
        q = re.split(r" — ", q)[0] if r["scheme"].startswith("Scheme-II") else q
        if len(q) < 6 or r["base"] not in c.catalogue or (q.lower(), r["base"]) in seen:
            continue
        seen.add((q.lower(), r["base"]))
        cases.append({"query": q, "expected": r["base"], "scheme": r["scheme"]})
    hits = {1: 0, 3: 0, 5: 0, 10: 0}
    misses = []
    t0 = time.time()
    for cs in cases:
        res = [x["base"] for x in c.search(cs["query"], 10)]
        exp = cs["expected"]
        parent = re.sub(r" \(Part [^)]*\)$", "", exp)
        rank = next((i + 1 for i, b in enumerate(res) if b == exp or b == parent or re.sub(r" \(Part [^)]*\)$", "", b) == exp), None)
        for k in hits:
            if rank and rank <= k:
                hits[k] += 1
        if not rank or rank > 3:
            misses.append({**cs, "rank": rank, "top3": res[:3]})
    n = len(cases)
    out = {"benchmark": "BIS compulsory-certification product list → IS number", "cases": n,
           "top1": round(100 * hits[1] / n, 1), "top3": round(100 * hits[3] / n, 1), "top5": round(100 * hits[5] / n, 1),
           "top10": round(100 * hits[10] / n, 1), "dense_index": c.emb is not None, "parsed_texts": len(c.graph),
           "mean_ms": round(1000 * (time.time() - t0) / max(1, n), 1), "aliases": os.environ.get("CORPUS_ALIASES"), "run": time.strftime("%Y-%m-%d %H:%M"), "sample_misses": misses[:40]}
    # --- procurement-language queries (team-written, not copied from titles)
    pq = json.load(open(os.path.join(ROOT, "data", "evaluation", "procurement_queries.json"), encoding="utf-8"))["cases"]
    ph = {1: 0, 3: 0, 5: 0, 10: 0}
    pmiss = []
    for cs in pq:
        res = [x["base"] for x in c.search(cs["query"], 10)]
        def ok(b):
            return any(b == e or (" (Part" not in e and re.sub(r" \(Part [^)]*\)$", "", b) == e) for e in cs["expected"])
        rank = next((i + 1 for i, b in enumerate(res) if ok(b)), None)
        for k in ph:
            if rank and rank <= k:
                ph[k] += 1
        if not rank or rank > 1:
            pmiss.append({**cs, "rank": rank, "top3": res[:3]})
    m = len(pq)
    out["procurement_language"] = {"cases": m, "top1": round(100 * ph[1] / m, 1), "top3": round(100 * ph[3] / m, 1),
                                   "top5": round(100 * ph[5] / m, 1), "top10": round(100 * ph[10] / m, 1), "misses": pmiss}
    # --- multilingual (same path as the API: detect → translate / lexicon → search with dense on the original)
    import asyncio
    from app.services.multilingual import detect_language, translate_to_english
    ml = json.load(open(os.path.join(ROOT, "data", "evaluation", "procurement_queries.json"), encoding="utf-8")).get("multilingual", [])
    mh = {1: 0, 3: 0}
    mres = []
    for cs in ml:
        lang = detect_language(cs["query"])
        t, tr = asyncio.run(translate_to_english(cs["query"], lang)) if lang != "en" else (cs["query"], False)
        terms = re.findall(r"\(([^)]+)\)", t) if tr else []
        q = " ".join(terms + re.findall(r"[A-Za-z0-9./]+", re.sub(r"\([^)]*\)", " ", t))) if terms else t
        res = [x["base"] for x in c.search(q, 5, dense_query=cs["query"])]
        rank = next((i + 1 for i, b in enumerate(res) if any(b == e or (" (Part" not in e and re.sub(r" \(Part [^)]*\)$", "", b) == e) for e in cs["expected"])), None)
        mh[1] += bool(rank and rank <= 1)
        mh[3] += bool(rank and rank <= 3)
        mres.append({**cs, "detected": lang, "searched_as": q, "rank": rank, "top3": res[:3]})
    held = json.load(open(os.path.join(ROOT, "data", "evaluation", "procurement_queries.json"), encoding="utf-8")).get("multilingual_heldout", [])
    if held:
        hh = {1: 0, 3: 0}
        hres = []
        for cs in held:
            lang = detect_language(cs["query"])
            t, tr = asyncio.run(translate_to_english(cs["query"], lang)) if lang != "en" else (cs["query"], False)
            terms = re.findall(r"\(([^)]+)\)", t) if tr else []
            q = " ".join(terms + re.findall(r"[A-Za-z0-9./]+", re.sub(r"\([^)]*\)", " ", t))) if terms else t
            res = [x["base"] for x in c.search(q, 5, dense_query=cs["query"])]
            rank = next((i + 1 for i, b in enumerate(res) if any(b == e or (" (Part" not in e and re.sub(r" \(Part [^)]*\)$", "", b) == e) for e in cs["expected"])), None)
            hh[1] += bool(rank and rank <= 1)
            hh[3] += bool(rank and rank <= 3)
            hres.append({**cs, "searched_as": q, "rank": rank, "top3": res[:3]})
        out["multilingual_heldout"] = {"cases": len(held), "top1": round(100 * hh[1] / len(held), 1), "top3": round(100 * hh[3] / len(held), 1),
                                       "results": hres, "note": held[0].get("set")}
        print("multilingual held-out:", {k: v for k, v in out["multilingual_heldout"].items() if k in ("cases", "top1", "top3")})
    if ml:
        out["multilingual"] = {"cases": len(ml), "top1": round(100 * mh[1] / len(ml), 1), "top3": round(100 * mh[3] / len(ml), 1), "results": mres,
                               "note": "No LLM translator configured: Hindi/Tamil/Telugu/Bengali/Kannada handled by a procurement lexicon + multilingual embeddings."}
        print("multilingual:", {k: v for k, v in out["multilingual"].items() if k in ("cases", "top1", "top3")})
    # --- abstention: vague requests and services/software must not get a "Recommended" standard; and how often a
    #     "Recommended" (high-confidence) answer is wrong on the answerable sets
    qd = json.load(open(os.path.join(ROOT, "data", "evaluation", "procurement_queries.json"), encoding="utf-8"))
    ab = qd.get("should_abstain", [])
    if ab:
        rows_ab = []
        for cs in ab:
            res = c.search(cs["query"], 3)
            top = res[0] if res else None
            rows_ab.append({**cs, "top": top["base"] if top else None, "title": (top or {}).get("title"), "confidence": top["confidence"] if top else "none"})
        n_ab = len(rows_ab)
        out["abstention"] = {"cases": n_ab, "no_recommendation": round(100 * sum(r["confidence"] != "high" for r in rows_ab) / n_ab, 1),
                             "abstained_fully": round(100 * sum(r["confidence"] in ("low", "none") for r in rows_ab) / n_ab, 1),
                             "by_kind": {k: round(100 * sum(r["confidence"] != "high" for r in rows_ab if r["kind"] == k) / max(1, sum(r["kind"] == k for r in rows_ab)), 1)
                                         for k in ("vague", "out_of_scope")},
                             "results": rows_ab, "note": qd.get("should_abstain_note")}
        print("abstention:", {k: v for k, v in out["abstention"].items() if k not in ("results", "note")})
    # --- GeM category names (independent: written by GeM / ministries; the IS in each name is the label)
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    from eval_sets import gem_cases, score
    split = "test" if os.environ.get("CORPUS_GEM_ALIAS_SPLIT") == "train" else None
    g_all = score(c, gem_cases(c, split=split))
    g_new = score(c, gem_cases(c, exclude_bis_names=True, split=split))
    out["gem_categories"] = {**{k: v for k, v in g_all.items() if k != "misses"}, "misses": g_all["misses"][:60],
                             "excluding_bis_list_names": {k: v for k, v in g_new.items() if k != "misses"},
                             "note": ("GeM category names from live bids (bidplus.gem.gov.in, 27 Sep 2026) with the IS stripped; label = the IS GeM names. "
                                      + ("Aliases on, but only GeM names of the train half are used; scored on the unseen test half." if split else
                                         "Aliases (BIS list, GeM names, trade names) switched off."))}
    print("gem:", {k: v for k, v in g_all.items() if k != "misses"}, "excl-BIS-names:", {k: v for k, v in g_new.items() if k != "misses"})
    json.dump(out, open(os.getenv("BENCH_OUT") or os.path.join(ROOT, "data", "evaluation", "corpus_benchmark.json"), "w"), indent=1, ensure_ascii=False)
    print("procurement-language:", {k: v for k, v in out["procurement_language"].items() if k != "misses"})
    for x in pmiss:
        print("  PMISS", x["query"][:55], "| exp", x["expected"], "| got", x["top3"], x["rank"])
    print({k: v for k, v in out.items() if k != "sample_misses"})
    for m in misses[:12]:
        print("  MISS", m["query"][:60], "| exp", m["expected"], "| got", m["top3"], m["rank"])


if __name__ == "__main__":
    main()
