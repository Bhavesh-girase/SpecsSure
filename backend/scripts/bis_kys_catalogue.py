"""
Status of EVERY Indian Standard from BIS "Know Your Standards" (services.bis.gov.in) — the catalogue behind the BIS
portal's standard search. Its DataTables endpoint takes base64-encoded parameters; seeding the IS-number substring search
with the digits 0–9 covers the whole catalogue (every number contains a digit). Fetched from a machine in India.

Per standard: edition (number:year), status (Active / Withdrawn / …), title, amendments count, technical committee,
aspect (BIS's own document type: Product Specification, Method of Test, Code of Practice, Terminology …) and the ISO/IEC
equivalence degree.

Input : var/bis_kys/<seed>_<start>.json   Output: data/corpus/bis_kys.json.gz
"""
import collections
import glob
import gzip
import html
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

NUM = re.compile(r"^\s*((?:IS|SP)(?:/[A-Z]+)*)\s*([A-Z]?\d[\w.-]*)\s*(\(([^)]*)\))?\s*:\s*(\d{4})", re.I)


def parse_is_no(raw: str):
    parts = [html.unescape(re.sub(r"<[^>]+>", "", p)).strip() for p in re.split(r"<br\s*/?>", raw or "", flags=re.I)]
    head = parts[0] if parts else ""
    status = None
    equiv = None
    for p in parts[1:]:
        m = re.match(r"^\(?\s*([A-Za-z ,]+?)\s*\)?$", p)
        if p.startswith("(") and m:
            status = m.group(1).strip()
        elif p:
            equiv = p
    m = NUM.match(head)
    if not m:
        return None
    pre, num, _, part, year = m.groups()
    base = f"{pre.upper()} {num}"
    if part:
        segs = [s.strip() for s in re.split(r"/", part) if s.strip()]
        norm = []
        for s in segs:
            s = re.sub(r"^(Part|Pt\.?)\s*", "Part ", s, flags=re.I)
            s = re.sub(r"^(Sec(?:tion)?\.?)\s*", "Sec ", s, flags=re.I)
            norm.append(s)
        base += " (" + "/".join(norm) + ")"
    return {"base": base, "year": int(year), "status": status, "equivalent": equiv}


def main():
    rows = {}
    raw_n = 0
    for f in sorted(glob.glob(os.path.join(ROOT, "var", "bis_kys", "*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        for r in d.get("aaData") or []:
            raw_n += 1
            p = parse_is_no(r.get("is_no"))
            if not p:
                continue
            rec = {"edition": f"{p['base']}:{p['year']}", "year": p["year"], "status": p["status"] or ("Withdrawn" if r.get("withdrawn_status") else None),
                   "title": html.unescape(re.sub(r"\s+", " ", r.get("is_title") or "")).strip(),
                   "amendments": int(r["amendments"]) if str(r.get("amendments") or "").isdigit() else None,
                   "committee": re.sub(r"\s+", " ", r.get("technical_committee") or "").strip() or None,
                   "aspect": (r.get("aspect") or "").strip() or None, "iso_degree": (r.get("referirmatin_year") or "").strip() or None,
                   "equivalent": p["equivalent"], "withdrawn_note": r.get("withdrawn_status"), "bis_id": r.get("id") if False else None}
            m = re.search(r"choosenIS\((\d+)\)", r.get("Action") or "")
            rec["bis_id"] = int(m.group(1)) if m else None
            rows.setdefault(p["base"], []).append(rec)
    out = {}
    for base, eds in rows.items():
        uniq = {(e["year"], e["status"]): e for e in eds}
        eds = sorted(uniq.values(), key=lambda e: (e["year"], (e["status"] or "").lower() == "active"))
        active = [e for e in eds if (e["status"] or "").lower().startswith("active")]
        cur = active[-1] if active else eds[-1]
        out[base] = {**cur, "editions": [[e["year"], e["status"]] for e in eds]}
    st = collections.Counter((v["status"] or "?") for v in out.values())
    asp = collections.Counter((v["aspect"] or "?") for v in out.values())
    meta = {"source": "BIS 'Know Your Standards' catalogue (services.bis.gov.in), IS-number search seeded 0–9", "fetched": "2026-09-27",
            "raw_rows": raw_n, "designations": len(out), "status": dict(st), "aspect": dict(asp.most_common(20))}
    with gzip.open(os.path.join(ROOT, "data", "corpus", "bis_kys.json.gz"), "wt", encoding="utf-8") as g:
        json.dump({"meta": meta, "standards": out}, g, ensure_ascii=False)
    print(json.dumps(meta, indent=1))


if __name__ == "__main__":
    main()
