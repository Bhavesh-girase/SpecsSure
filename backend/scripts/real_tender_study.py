"""
Real-tender study: run SpecSure over public Indian tender documents and measure what it finds.

Input : data/evaluation/real_tenders.json (URLs)   Output: data/evaluation/real_tender_study.json
Per tender: items found, per-item status (recommended / possible / none / service), Indian Standards cited, cited standards
that are unknown / have a newer archived edition / are withdrawn per the registry, and items under compulsory BIS
certification for which the tender never mentions ISI / BIS licence / CRS registration.
"""
import hashlib
import json
import os
import re
import sys
import time
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
CACHE = os.path.join(ROOT, "var", "tenders")
CERT_WORDS = re.compile(r"\b(ISI|BIS licen[cs]e|Standard Mark|CM/L|R-?\s?\d{8}|Compulsory Registration|BIS registration|CRS)\b", re.I)


def fetch(url):
    os.makedirs(CACHE, exist_ok=True)
    name = hashlib.sha1(url.encode()).hexdigest()[:12] + ".pdf"
    path = os.path.join(CACHE, name)
    if not os.path.exists(path):
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (SpecSure research; SIH 2026)"})
        with urllib.request.urlopen(req, timeout=120) as r:
            open(path, "wb").write(r.read())
        time.sleep(1)
    return path


def main():
    from app.engine.docparse import parse_document
    from app.services.corpus_service import check_citations, get_corpus, recommend_items
    c = get_corpus()
    src = [{**t, "source": "institutional"} for t in json.load(open(os.path.join(ROOT, "data", "evaluation", "real_tenders.json")))["tenders"]]
    gem_idx = os.path.join(CACHE, "gem", "index.json")
    if os.path.exists(gem_idx):                 # GeM bid documents downloaded from India (bidplus refuses some cloud ranges)
        for g in json.load(open(gem_idx)):
            src.append({"org": (g.get("dept") or g.get("min") or "GeM buyer").strip(), "url": g["url"], "bid": g["bid"],
                        "category": g["cat"][:160], "source": "gem", "local": os.path.join(CACHE, "gem", g["file"])})
    rows = []
    for t in src:
        try:
            path = t.get("local") or fetch(t["url"])
            data = open(path, "rb").read()
            if not data.startswith(b"%PDF"):
                rows.append({**t, "error": "not a PDF (blocked or HTML page)"})
                continue
            doc = parse_document(data, os.path.basename(path))
        except Exception as e:  # noqa: BLE001
            rows.append({**t, "error": str(e)[:160]})
            continue
        pages = [{"page": p.page_no, "text": p.text, "tables": p.tables} for p in doc.pages]
        r = recommend_items(pages)
        cc = check_citations([{"family": x["base"], "citation": f"{x['base']}:{x['year']}" if x["year"] else x["base"], "body": "BIS"}
                              for x in r["cited_in_document"]])
        text = "\n".join(p["text"] for p in pages)
        mentions_cert = bool(CERT_WORDS.search(text))
        cert_items = []
        for it in r["items"]:
            if it["status"] in ("recommended", "named") and it["candidates"] and it["candidates"][0]["certification"]:
                cert_items.append({"item": it["text"][:80], "standard": it["candidates"][0]["base"],
                                   "scheme": it["candidates"][0]["certification"][0]["scheme"]})
        t = {k: v for k, v in t.items() if k != "local"}
        named_withdrawn = [c["base"] for it in r["items"] for c in it["candidates"][:1] if it["status"] == "named" and (c.get("edition") or {}).get("status") == "Withdrawn"]
        named_newer = []                         # an item names an edition year older than the edition in force (GeM names carry no year)
        for it in r["items"]:
            m = re.search(r"\bIS\s*[:/]?\s*\d{2,5}(?:\s*\([^)]*\))?\s*[:\-]\s*((?:19|20)\d{2})", it["text"])
            ed = (it["candidates"][0].get("edition") or {}) if it["status"] == "named" and it["candidates"] else {}
            if m and ed.get("year_in_force") and int(m.group(1)) < ed["year_in_force"]:
                named_newer.append(f"{it['candidates'][0]['base']}:{m.group(1)} → {ed['edition_in_force']}")
        rows.append({**t, "pages": doc.page_count, "named_withdrawn": named_withdrawn, "named_newer_edition": named_newer,
                     "cited_withdrawn": cc.get("withdrawn", []), "ocr_pages": len(doc.ocr_pages), "items": len(r["items"]), "counts": r["counts"],
                     "is_cited": [x["citation"] for x in cc.get("citations", [])],
                     "cited_unknown": cc.get("unknown", []), "cited_older_edition": cc.get("newer_editions", []),
                     "items_needing_compulsory_certification": cert_items, "mentions_certification": mentions_cert,
                     "sample_items": [{"text": it["text"][:90], "status": it["status"],
                                       "top": (it["candidates"][0]["base"] + " " + (it["candidates"][0]["title"] or "")[:60]) if it["candidates"] else None}
                                      for it in r["items"][:12]]})
        print(f"{t['org'][:40]:40} pages={doc.page_count:4} items={len(r['items']):3} {r['counts']} cited={len(cc.get('citations', []))} older={len(cc.get('newer_editions', []))}", flush=True)
    def summarise(ok, failed):
      return {
        "tenders_analysed": len(ok), "tenders_failed": failed,
        "pages": sum(x["pages"] for x in ok),
        "items_found": sum(x["items"] for x in ok),
        "items_named": sum(x["counts"].get("named", 0) for x in ok),
        "items_recommended": sum(x["counts"]["recommended"] for x in ok),
        "items_possible": sum(x["counts"]["possible"] for x in ok),
        "items_abstained": sum(x["counts"]["none"] for x in ok),
        "items_service": sum(x["counts"]["service"] for x in ok),
        "tenders_citing_no_IS": sum(1 for x in ok if not x["is_cited"]),
        "tenders_citing_older_edition": sum(1 for x in ok if x["cited_older_edition"]),
        "distinct_IS_cited": len({s for x in ok for s in x["is_cited"]}),
        "tenders_with_compulsory_items_but_no_certification_clause": sum(1 for x in ok if x["items_needing_compulsory_certification"] and not x["mentions_certification"]),
        "tenders_citing_withdrawn": sum(1 for x in ok if x.get("cited_withdrawn") or x.get("named_withdrawn")),
        "tenders_naming_superseded_edition": sum(1 for x in ok if x.get("named_newer_edition")),
      }
    ok = [x for x in rows if "error" not in x]
    agg = summarise(ok, len(rows) - len(ok))
    by_source = {}
    for srcname in ("institutional", "gem"):
        sub = [x for x in rows if x.get("source") == srcname]
        oks = [x for x in sub if "error" not in x]
        if sub:
            by_source[srcname] = summarise(oks, len(sub) - len(oks))
    agg["by_source"] = by_source
    json.dump({"run": time.strftime("%Y-%m-%d %H:%M"), "summary": agg, "tenders": rows,
               "method": "Automatic run; per-item statuses and cited-edition flags must be spot-checked by a person before being quoted."},
              open(os.path.join(ROOT, "data", "evaluation", "real_tender_study.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(agg, indent=1))


if __name__ == "__main__":
    main()
