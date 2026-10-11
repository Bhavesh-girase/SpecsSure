"""
GeM category → Indian Standard mapping, mined from live GeM bids (bidplus.gem.gov.in "all bids" listing).

GeM names many product categories after the standard they must meet — "Portable Fire Extinguishers (V3) ISI Marked to
IS 15683", "LED Luminaire For Road And Street Lights Conforming To IS 10322 (Part 5/Section 3) (V3) (Under BIS Scheme - II)".
These are written by GeM / the ministries, independently of our corpus, so they serve two purposes:

  1. an independent benchmark: category name with the standard stripped → does SpecSure recommend that standard?
  2. a procurement layer in the knowledge graph: GeM category —specifies→ IS, with the number of live bids and buyers.

Input: var/gem/bids.jsonl (harvested from a machine in India; bidplus refuses some cloud IP ranges).
Output: data/corpus/gem_categories.json
"""
import collections
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

IS_RE = re.compile(r"\bIS\s*[:/]?\s*(\d{2,5})(?:\s*\(\s*(Part|Pt\.?)\s*([0-9A-Za-z]+)(?:\s*/\s*(?:Sec(?:tion)?\.?)\s*([0-9A-Za-z]+))?\s*\))?", re.I)
TAIL = re.compile(r"\s*(?:\((?:V\d+|Q\d+)\)|\(\s*Under BIS Scheme[^)]*\)|\((?:\?|≤|<=)?[^)]{0,3}\))", re.I)
LEAD_IN = re.compile(r"\s*(?:,?\s*(?:ISI\s+Marked\s+)?(?:to|as per|conforming\s+to|confirming\s+to|conform\s+to|according\s+to|marked\s+to|compliant\s+to|as\s+per\s+latest)\s*)$", re.I)


def base_of(m) -> str:
    b = f"IS {int(m.group(1))}"
    if m.group(3):
        b += f" (Part {m.group(3)}" + (f"/Sec {m.group(4)}" if m.group(4) else "") + ")"
    return b


def segments(cat: str):
    """Split a (possibly multi-item) category string after each IS designation."""
    pos = 0
    for m in IS_RE.finditer(cat):
        seg = cat[pos:m.start()]
        pos = m.end()
        tail = re.match(r"(\s*\([^)]{0,40}\))*", cat[pos:])
        pos += tail.end() if tail else 0
        seg = seg.lstrip(" ,;")
        seg = re.sub(r"^.*?,(?=[A-Z][a-z])", lambda x: x.group(0) if len(x.group(0)) > 60 else "", seg) if seg.count(",") > 3 else seg
        name = seg
        for _ in range(3):
            name = TAIL.sub("", name).strip()
            name = LEAD_IN.sub("", name).strip(" ,;-")
        name = re.sub(r"\b(ISI|BIS)\s+Marked\b", "", name, flags=re.I).strip(" ,;-")
        yield name, base_of(m)


def main():
    from app.services.corpus_service import Corpus
    c = Corpus().load()
    src = os.path.join(ROOT, "var", "gem", "bids.jsonl")
    cats = {}
    for line in open(src, encoding="utf-8"):
        r = json.loads(line)
        for name, base in segments(r["cat"]):
            if len(name) < 4 or not re.search(r"[A-Za-z]{3,}", name):
                continue
            key = (re.sub(r"\s+", " ", name.lower()).strip(), base)
            e = cats.setdefault(key, {"category": re.sub(r"\s+", " ", name).strip(), "standard": base, "bids": 0, "buyers": collections.Counter(), "examples": []})
            e["bids"] += 1
            e["buyers"][r.get("min") or r.get("dept") or "?"] += 1
            if len(e["examples"]) < 3:
                e["examples"].append(r["bid"])
    out = []
    for e in cats.values():
        b = e["standard"]
        known = b in c.catalogue or re.sub(r" \(Part [^)]*\)$", "", b) in c.catalogue
        out.append({"category": e["category"], "standard": b, "in_corpus": known, "bids": e["bids"],
                    "buyers": [k for k, _ in e["buyers"].most_common(5)], "example_bids": e["examples"]})
    out.sort(key=lambda x: -x["bids"])
    meta = {"source": "GeM bidplus public bid listing (bidplus.gem.gov.in/all-bids), category names of live bids",
            "harvested_bids": sum(1 for _ in open(src, encoding="utf-8")), "categories": len(out),
            "in_corpus": sum(x["in_corpus"] for x in out),
            "note": "Category names are written by GeM; the IS in each name is the label. Used as an independent benchmark "
                    "(with the GeM alias field switched off) and as a procurement layer of the knowledge graph."}
    dst = os.path.join(ROOT, "data", "corpus", "gem_categories.json")
    json.dump({"meta": meta, "categories": out}, open(dst, "w"), indent=1, ensure_ascii=False)
    print(json.dumps(meta, indent=1))
    for x in out[:25]:
        print(x["bids"], "|", x["category"], "→", x["standard"], "" if x["in_corpus"] else "(not in corpus)")


if __name__ == "__main__":
    main()
