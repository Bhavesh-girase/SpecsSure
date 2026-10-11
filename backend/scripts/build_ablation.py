"""Collect the benchmark runs of each configuration into data/evaluation/retrieval_ablation.json (Evidence page)."""
import json, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
E = os.path.join(ROOT, "var", "exp")
runs = [("Archive only (19.7k texts) · e5-small", "official_e5_noportal.json", False),
        ("+ BIS portal catalogue & current titles (29.9k) · e5-small", "official_e5.json", False),
        ("+ bge-m3 multilingual embeddings", "official_clean_prev.json", False),
        ("+ BIS catalogue status & document type for all standards (default)", "official_clean.json", True),
        ("+ product-name aliases & GeM prior (product mode; GeM scored on unseen half)", os.path.join("..", "..", "data", "evaluation", "corpus_benchmark_with_aliases.json"), False)]
cols = ["BIS list top-1", "BIS list top-3", "GeM names top-1", "GeM names top-3", "Procurement top-1", "Procurement top-3", "Indian-language held-out top-1", "held-out top-3", "ms / query"]
rows = []
for name, f, chosen in runs:
    p = os.path.join(E, f)
    if not os.path.exists(p):
        continue
    d = json.load(open(p, encoding="utf-8"))
    g, pl, mh = d.get("gem_categories", {}), d.get("procurement_language", {}), d.get("multilingual_heldout", {})
    cs = {"bis": d.get("cases"), "gem": d.get("gem_categories", {}).get("cases")}
    rows.append({"name": f"{name} — BIS n={cs['bis']}, GeM n={cs['gem']}", "chosen": chosen, "values": [d.get("top1"), d.get("top3"), g.get("top1"), g.get("top3"), pl.get("top1"), pl.get("top3"),
                                                           mh.get("top1"), mh.get("top3"), d.get("mean_ms")],
                 "cases": {"bis": d.get("cases"), "gem": g.get("cases"), "procurement": pl.get("cases"), "heldout": mh.get("cases")}})
out = {"columns": cols, "rows": rows,
       "note": "Same scripts; BIS-list and GeM case counts grow when the BIS-portal layer adds standards the archive lacks (the added cases are "
               "title-only, hence harder). Clean rows have all product-name aliases off. Before the multilingual work (glossary of ~100 words, no "
               "transliteration, e5-small) the held-out Indian-language set scored 7.1 % top-1 / 10.7 % top-3. Engineering measurements, not an official BIS methodology."}
json.dump(out, open(os.path.join(ROOT, "data", "evaluation", "retrieval_ablation.json"), "w"), indent=1)
print(json.dumps(rows, indent=1))
