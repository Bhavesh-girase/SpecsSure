"""
Step 5: mandatory certification layer — parse BIS "Products under Compulsory Certification" pages (Scheme-I ISI mark,
Scheme-II CRS registration, Scheme-X) into data/corpus/compulsory_certification.json, keyed by IS designation.

Pages are saved first to var/corpus/bis/*.html (see README of the pipeline); rows inherit the notification of the
row above when the table uses merged cells.
"""
import html
import json
import os
import re
import sys
import time
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from app.engine.corpus_parse import CITE_RE, base_of, cite_parts  # noqa: E402

PAGES = {
    "Scheme-I (ISI mark)": "https://www.bis.gov.in/product-certification/products-under-compulsory-certification/scheme-1/?lang=en",
    "Scheme-II (CRS registration)": "https://www.bis.gov.in/product-certification/products-under-compulsory-certification/scheme-ii-registration-scheme/?lang=en",
    "Scheme-X": "https://www.bis.gov.in/products-under-compulsory-certification-scheme-x/?lang=en",
}
CACHE = os.path.join(ROOT, "var", "corpus", "bis")
OUT = os.path.join(ROOT, "data", "corpus", "compulsory_certification.json")
ORDER_RE = re.compile(r"([A-Z][A-Za-z ,&()\-–/]+?\(Quality Control\)\s*(?:[A-Za-z]+ )?Order,? ?\d{4}|[A-Z][A-Za-z ,&()\-–/]+?\(Requirements? for Compulsory Registration\)(?: [A-Za-z]+)? Order,? ?\d{4}|Gas Cylinder Rules,? ?\d{4}|Food Safety and Standards[^.]{0,120}?Regulations,? ?\d{4})")


def cells(row):
    return [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", c))).strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)]


def get(url, name):
    path = os.path.join(CACHE, name + ".html")
    if not os.path.exists(path):
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 SpecSure-research"})
        with urllib.request.urlopen(req, timeout=90) as r:
            open(path, "wb").write(r.read())
        time.sleep(1)
    return open(path, encoding="utf-8", errors="ignore").read()


def main():
    os.makedirs(CACHE, exist_ok=True)
    out = []
    for scheme, url in PAGES.items():
        s = get(url, re.sub(r"[^a-z0-9]+", "-", scheme.lower()))
        last_order = None
        for row in re.findall(r"<tr[^>]*>(.*?)</tr>", s, re.S):
            c = cells(row)
            if len(c) < 2:
                continue
            joined = " | ".join(c)
            m_order = ORDER_RE.search(joined)
            if m_order:
                last_order = re.sub(r"^\d+\.\s*", "", m_order.group(1)).strip()
            cites = list(CITE_RE.finditer(joined))
            if not cites:
                continue
            m = cites[0]
            pre, num, part, sec, _ = cite_parts(m)
            base = base_of(pre, num, part, sec)
            # product column = first non-number, non-IS cell after the IS cell
            texts = [x for x in c if x and not CITE_RE.search(x) and not re.fullmatch(r"[\d.()a-z ]{0,8}", x)
                     and "Quality Control" not in x and "Compulsory Registration" not in x and not x.lower().startswith(("all test", "electromagnetic"))]
            product = " — ".join(reversed(texts[:2])) if scheme.startswith("Scheme-II") else (texts[0] if texts else None)
            out.append({"scheme": scheme, "base": base, "is_number": m.group(0).strip(), "product": (product or "")[:160],
                        "order": last_order, "source_url": url})
    # hallmarking (not in the scheme tables)
    out.append({"scheme": "Hallmarking", "base": "IS 1417", "is_number": "IS 1417", "product": "Gold jewellery and gold artefacts",
                "order": "Hallmarking of Gold Jewellery and Gold Artefacts Order, 2020", "source_url": "https://www.bis.gov.in/hallmarking-overview/",
                "verification_state": "secondary_source"})
    seen, dedup = set(), []
    for r in out:
        k = (r["scheme"], r["base"], r["product"][:60])
        if k not in seen:
            seen.add(k)
            dedup.append(r)
    json.dump({"_comment": "Parsed from BIS 'Products under Compulsory Certification' pages (bis.gov.in). Verify on the page before relying on it.",
               "fetched": time.strftime("%Y-%m-%d"), "rows": dedup}, open(OUT, "w"), indent=1, ensure_ascii=False)
    from collections import Counter
    print(len(dedup), Counter(r["scheme"] for r in dedup), len({r["base"] for r in dedup}), "distinct standards")


if __name__ == "__main__":
    main()
