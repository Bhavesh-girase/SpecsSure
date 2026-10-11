"""
Step 2: normalise the harvested archive metadata into a catalogue of Indian Standards.

Input : var/corpus/archive_metadata.jsonl
Output: data/corpus/is_catalogue.jsonl.gz — one record per archived document with
        designation, base (number/part/section), year, title, division, committee, amendments, equivalence, status note
"""
import gzip
import json
import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..")
SRC = os.path.join(ROOT, "var", "corpus", "archive_metadata.jsonl")
OUT = os.path.join(ROOT, "data", "corpus", "is_catalogue.jsonl.gz")

LABELS = ["Name of Standards Organization", "Division Name", "Section Name", "Designator of Legally Binding Document",
          "Title of Legally Binding Document", "Number of Amendments", "Equivalence", "Superceding", "Superceded by",
          "LEGALLY BINDING DOCUMENT"]
LAB_RE = re.compile("(" + "|".join(re.escape(l) for l in LABELS) + "):?")
DIV_ALIASES = {"Textile": "Textiles"}


def fields(desc: str) -> dict:
    parts = LAB_RE.split(desc or "")
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}


def norm_division(d):
    if not d:
        return None
    d = re.sub(r"\s*Division.*$", "", d).strip()
    d = d.replace("Petroleum, Coal and", "Petroleum, Coal, and")
    return DIV_ALIASES.get(d, d)


def parse_identifier(ident: str):
    """gov.in.is.<prefix?>.<number>.<part?>.<sec?>.<year>  →  (prefix, number, part, sec, year, variant)"""
    toks = ident.split(".")[3:]
    prefix = None
    if toks and toks[0] in ("iso", "iec", "qc", "sp"):
        prefix = toks.pop(0).upper()
    year = toks.pop() if toks and re.fullmatch(r"\d{4}", toks[-1]) else None
    variant = None
    toks2 = []
    for t in toks:
        if t in ("b", "od"):
            variant = {"b": "hindi", "od": "other"}[t]
        else:
            toks2.append(t)
    number = toks2[0] if toks2 else None
    part = toks2[1] if len(toks2) > 1 else None
    sec = toks2[2] if len(toks2) > 2 else None
    return prefix, number, part, sec, year, variant


def base_designation(prefix, number, part, sec):
    p = {"ISO": "IS/ISO ", "IEC": "IS/IEC ", "QC": "IS/QC ", "SP": "SP "}.get(prefix, "IS ")
    s = f"{p}{number}"
    if part:
        s += f" (Part {part}" + (f"/Sec {sec}" if sec else "") + ")"
    return s


def clean_title(title: str) -> str:
    t = re.sub(r"^(IS|SP|IS/ISO|IS/IEC|IS/QC)\s*[\w\-/ ().]*?(:\s*\d{4})?\s*:\s*", "", title or "").strip()
    t = re.sub(r"\s+-\s*$", "", t)
    return t


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    n = 0
    with gzip.open(OUT, "wt", encoding="utf-8") as out:
        for line in open(SRC, encoding="utf-8"):
            r = json.loads(line)
            f = fields(r.get("description") if isinstance(r.get("description"), str) else " ".join(r.get("description") or []))
            prefix, number, part, sec, year, variant = parse_identifier(r["identifier"])
            if not number:
                continue
            base = base_designation(prefix, number, part, sec)
            committee = f.get("Section Name") or None
            code = None
            if committee:
                m = re.search(r"\(([A-Z]{2,4}\s*\d+[A-Z]?)\)\s*$", committee)
                code = m.group(1).replace("  ", " ") if m else None
            amend = f.get("Number of Amendments")
            rec = {
                "id": r["identifier"], "base": base, "designation": f"{base}:{year}" if year else base, "year": int(year) if year else None,
                "variant": variant, "title": clean_title(f.get("Title of Legally Binding Document") or r.get("title") or ""),
                "division": norm_division(f.get("Division Name")), "committee": committee, "committee_code": code,
                "amendments": int(amend) if amend and amend.isdigit() else None,
                "equivalence": (f.get("Equivalence") or "").strip(" .") or None,
                "supersedes_raw": (f.get("Superceding") or "").strip() or None,
                "superseded_by_raw": (f.get("Superceded by") or "").strip() or None,
                "source": f"https://archive.org/details/{r['identifier']}",
            }
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    print("catalogue records:", n, "→", OUT)


if __name__ == "__main__":
    main()
