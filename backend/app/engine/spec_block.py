"""
Exportable specification block — the clause text an officer pastes into a tender (GeM "additional specification",
CPPP technical bid), generated from the corpus with every citation traceable.

For one recommended standard (optionally for a named item) it assembles:
  standard & edition (with amendments in force), normative references that apply through it, type / acceptance tests and
  sampling, mandatory certification (ISI mark / CRS registration / hallmarking with the Quality Control Order), marking
  and packing, terminology — plus a provenance footnote per sentence. Wording follows common Indian public-procurement
  drafting; it is a draft for the competent authority, not a legal text.
"""
from __future__ import annotations

from typing import Dict, List, Optional


def _names(items: List[dict], n: int = 8) -> str:
    out = []
    for x in items[:n]:
        t = (x.get("title") or "").strip()
        out.append(f"{x['base']}" + (f" ({t[:70]})" if t else ""))
    more = len(items) - n
    return "; ".join(out) + (f"; and {more} more" if more > 0 else "")


def build(card: dict, allied: dict, certification: List[dict], status: Optional[dict] = None, item: Optional[str] = None,
          labs: Optional[dict] = None) -> Dict:
    base = card["base"]
    edition = (status or {}).get("in_force") or (f"{base}:{card['latest_archived_year']}" if card.get("latest_archived_year") else base)
    import re
    clean = re.sub(r"\s*\((?:[A-Za-z]+ )?Revision\s*\)|\(\s*(?:First|Second|Third|Fourth|Fifth|Sixth|Seventh)[^)]*\)", "", card["title"])
    clean = re.split(r"\s*[—–-]+\s*(?:Specification|Code of Practice)\b|\s*,?\s*Specification for\b", clean, flags=re.I)[0].strip(" -—,")
    subject = item.strip() if item else (clean or card["title"])
    groups = {g["kind"]: g for g in allied.get("groups", [])}
    clauses: List[dict] = []

    def add(key: str, heading: str, text: str, source: str):
        clauses.append({"key": key, "heading": heading, "text": text, "source": source})

    amds = (status or {}).get("amendments") or []
    amd_txt = ""
    if amds:
        amd_txt = (f" with Amendment No. {amds[0]['no']} ({amds[0]['year']})" if len(amds) == 1 else
                   f" with Amendments No. {amds[0]['no']} ({amds[0]['year']}) to No. {amds[-1]['no']} ({amds[-1]['year']})")
    src1 = f"Scope clause of {base} — {card.get('source')}"
    if (status or {}).get("fetched") and (status or {}).get("source", "").startswith("BIS e-Sale"):
        src1 += f"; edition and amendments: BIS e-Sale portal, checked {status['fetched']}"
    add("1", "Standard", f"The {subject} shall conform to {edition} “{card['title']}”{amd_txt}, and any amendment issued up to the "
        f"last date of bid submission.", src1)
    norm = groups.get("normative", {}).get("items", [])
    if norm:
        add("2", "Referred standards", "The standards referred to in the normative-references clause of " + base +
            " shall apply to the extent specified therein: " + _names(norm) + ".", f"Clause 2 (References) of {base}")
    tests = groups.get("test_method", {}).get("items", [])
    samp = groups.get("sampling", {}).get("items", [])
    t = f"Type tests shall be carried out as per {base}"
    if tests:
        t += " using the test methods of " + _names(tests, 6)
    t += ". Type-test reports from a NABL-accredited laboratory (or BIS-recognised laboratory), not older than the period specified " \
         "in the tender, shall be submitted with the bid. Acceptance tests shall be conducted on samples drawn from each lot"
    t += (" as per the sampling plan of " + _names(samp, 2)) if samp else f" as per the sampling plan of {base}"
    t += "; a lot failing any acceptance test on re-test shall be rejected."
    add("3", "Tests and acceptance", t, f"Test-method citations in {base}")
    certs = [c for c in certification if c.get("scheme")]
    if certs:
        c0 = certs[0]
        scheme = c0["scheme"]
        order = c0.get("title") or c0.get("order") or "the applicable Quality Control Order"
        if "CRS" in scheme or "Scheme-II" in scheme:
            txt = (f"The product is notified under the Compulsory Registration Scheme ({order}). The bidder shall furnish a valid BIS "
                   f"registration (R-number) for the offered model against {base}, valid on the last date of bid submission; the product "
                   f"shall carry the Standard Mark with the registration number.")
        elif "Hallmark" in scheme:
            txt = f"Articles shall be hallmarked as required by the {order}."
        else:
            txt = (f"The product is under compulsory BIS certification ({order}). It shall bear the Standard Mark (ISI mark) under a valid BIS "
                   f"licence (CM/L number) covering the offered product and {base}; a copy of the licence valid on the last date of bid "
                   f"submission shall be submitted.")
        add("4", "Mandatory certification", txt, f"BIS ‘Products under Compulsory Certification’ list — {c0.get('source_url') or 'bis.gov.in'}")
    else:
        add("4", "Certification", f"Products bearing the BIS Standard Mark for {base} are preferred. (No compulsory certification order was found "
            f"for {base} in the BIS list at the time of drafting — verify before publication.)", "BIS compulsory-certification list (no match)")
    pack = groups.get("packaging_marking", {}).get("items", [])
    add("5", "Marking and packing", f"Marking and packing shall be as per {base}" + ((" and " + _names(pack, 2)) if pack else "") + ".",
        f"Marking / packing citations in {base}")
    term = groups.get("terminology", {}).get("items", [])
    if term:
        add("6", "Terminology", "Terms used shall have the meanings given in " + _names(term, 3) + ".", f"Terminology clause of {base}")
    safety = groups.get("safety", {}).get("items", []) + groups.get("installation", {}).get("items", [])
    if safety:
        add("7", "Safety and installation", "Safety and installation requirements shall comply with " + _names(safety, 4) + " where applicable.",
            f"Safety / installation citations in {base}")
    notes = []
    if labs and labs.get("count"):
        notes.append(f"Testing: {labs['count']} BIS / BIS-recognised laboratories list test facilities for {base} on BIS LIMS"
                     + (f" (full-test charges from ₹{labs['min_charges']:,} excl. taxes)" if labs.get("min_charges") else "")
                     + (f", in {len(labs['cities'])} cities" if labs.get("cities") else "") + ".")
    if not card.get("parsed"):
        notes.append(f"The full text of {base} is not in the SpecSure corpus (published after the archive or not digitised): "
                     "referred standards and test methods could not be read from it — add them from the standard.")
    if status and status.get("level") in ("warn", "bad"):
        notes.append(status["text"])
    notes.append("Draft generated by SpecSure from the text of archived Indian Standards and the BIS compulsory-certification list. "
                 "Confirm the edition in force, amendments and certification scheme on standards.bis.gov.in before publication.")
    text = "\n".join(f"{c['key']}. {c['heading']}: {c['text']}" for c in clauses)
    return {"base": base, "edition": edition, "item": subject, "clauses": clauses, "notes": notes, "text": text,
            "tests_seen": (labs or {}).get("tests_seen") or []}


def to_docx(blocks: List[Dict], title: str = "Technical specification — Indian Standards") -> bytes:
    import io
    import docx
    from docx.shared import Pt, RGBColor

    d = docx.Document()
    st = d.styles["Normal"]
    st.font.name = "Calibri"
    st.font.size = Pt(10.5)
    d.add_heading(title, level=1)
    for i, b in enumerate(blocks, 1):
        d.add_heading(f"{i}. {b['item']} — {b['edition']}", level=2)
        for c in b["clauses"]:
            p = d.add_paragraph()
            r = p.add_run(f"{i}.{c['key']} {c['heading']}: ")
            r.bold = True
            p.add_run(c["text"])
            s = d.add_paragraph(f"Source: {c['source']}")
            s.runs[0].italic = True
            s.runs[0].font.size = Pt(8)
            s.runs[0].font.color.rgb = RGBColor(0x66, 0x66, 0x66)
        for n in b["notes"]:
            q = d.add_paragraph(n)
            q.runs[0].italic = True
            q.runs[0].font.size = Pt(8.5)
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()
