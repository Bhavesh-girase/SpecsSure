"""
Indian Standard full-text parser — turns the text of a standard into the facts the recommender needs:

  * SCOPE clause            → what products / subjects the standard covers (the retrieval target)
  * REFERENCES clause       → normative references (the standard's own list of standards it depends on)
  * TERMINOLOGY clause      → terminology standards
  * citations in the body   → test methods, sampling, packing, safety … (typed by the cited standard's title)
  * FOREWORD                → revision number, what it supersedes, ISO / IEC equivalence and its degree
  * "Reaffirmed YYYY"       → last reaffirmation

Every extracted relation keeps the clause it came from and a short snippet, so the UI can show *why* two standards
are linked. Citations are validated against the catalogue of known designations to suppress OCR noise.
"""
from __future__ import annotations

import re
from typing import Dict, Iterable, List, Optional, Set

# ---------------------------------------------------------------------------------------------- text normalisation
_OCR_FIXES = [
    (re.compile(r"\b(?:1S|lS|I\.S\.|I S)\s*[:\-]?\s*(?=\d)"), "IS "),
    (re.compile(r"\b18\s*:\s*(?=\d{2,5}\b)"), "IS "),          # "18:1885" is an OCR'd "IS:1885"
    (re.compile(r"\bIS\s*:\s*"), "IS "),
    (re.compile(r"[ \t]+"), " "),
]


def normalise(text: str) -> str:
    t = text.replace("\r", "")
    for rx, rep in _OCR_FIXES:
        t = rx.sub(rep, t)
    return t


def strip_front_matter(text: str) -> str:
    """Drop the Public.Resource.Org cover page and BIS committee-membership lists before the standard proper."""
    m = re.search(r"Indian\s+Standard\s*\n", text)
    if m and m.start() < len(text) * 0.6:
        return text[max(0, m.start() - 400):]
    return text


# ---------------------------------------------------------------------------------------------- citations
_PART = r"(?:\s*\(\s*Part\s*([0-9]{1,3}[A-Z]?)(?:\s*[/,]\s*Sec(?:tion)?\s*([0-9]{1,3}))?\s*\))?"
_YEAR = r"(?:\s*[:\-–]\s*((?:19|20)\d{2}))?"
CITE_RE = re.compile(r"\b(?P<pre>IS/ISO|IS/IEC|IS)\s*(?P<num>\d{2,5})"
                     r"(?:\s*\(\s*Part\s*(?P<p1>[0-9]{1,3}[A-Z]?)(?:\s*[/,]\s*Sec(?:tion)?\s*(?P<s1>[0-9]{1,3}))?\s*\)"
                     r"|\s*[:\-]\s*\(?Part\s*(?P<p2>[0-9]{1,3}[A-Z]?)\)?(?:\s*[:/,]\s*\(?Sec(?:tion)?\s*(?P<s2>[0-9]{1,3})\)?)?)?"
                     r"(?:\s*[:\-–]\s*(?P<y>(?:19|20)\d{2}))?")
BARE_RE = re.compile(r"(?<![\d.])(\d{3,5})" + _PART + r"\s*[:\-–]\s*((?:19|20)\d{2})\b")   # table rows in REFERENCES


def cite_parts(m):
    """(prefix, number, part, section, year) from a CITE_RE match."""
    return (m.group("pre"), m.group("num"), m.group("p1") or m.group("p2"), m.group("s1") or m.group("s2"),
            int(m.group("y")) if m.group("y") else None)
FOREIGN_RE = re.compile(r"\b(ISO|IEC|CISPR|EN|BS|ASTM)\s*(?:/IEC\s*)?(\d{2,6}(?:-\d{1,3}){0,3})")


def base_of(prefix: str, number: str, part: Optional[str], sec: Optional[str]) -> str:
    p = {"IS/ISO": "IS/ISO ", "IS/IEC": "IS/IEC "}.get(prefix, "IS ")
    s = f"{p}{number}"
    if part:
        s += f" (Part {part}" + (f"/Sec {sec}" if sec else "") + ")"
    return s


def citations(text: str, known: Optional[Set[str]] = None, bare: bool = False) -> List[dict]:
    out, seen = [], set()
    it: Iterable = CITE_RE.finditer(text)
    for m in it:
        pre, num, part, sec, yr = cite_parts(m)
        b = base_of(pre, num, part, sec)
        cand = [b, base_of(pre, num, part, None), base_of(pre, num, None, None)]
        hit = next((c for c in cand if known is None or c in known), None)
        if hit and hit not in seen:
            seen.add(hit)
            out.append({"base": hit, "year": yr, "at": m.start()})
    if bare:
        for m in BARE_RE.finditer(text):
            b = base_of("IS", m.group(1), m.group(2), m.group(3))
            cand = [b, base_of("IS", m.group(1), None, None)]
            hit = next((c for c in cand if known is None or c in known), None)
            if hit and hit not in seen:
                seen.add(hit)
                out.append({"base": hit, "year": int(m.group(4)) if m.group(4) else None, "at": m.start()})
    return out


PART_ONLY_RE = re.compile(r"\(\s*Part\s*([0-9]{1,3}[A-Z]?)(?:\s*/\s*Sec\s*([0-9]{1,3}))?\s*\)\s*[:\-–]\s*((?:19|20)\d{2})")
NUM_RE = re.compile(r"(?<![\d.(])(?:IS\s*)?(\d{3,5})(?=\s*(?:\(|[A-Z]|:))")


def part_continuations(refs: str, known: Optional[Set[str]]) -> List[dict]:
    """Reference tables list "10810 Methods of test for cables: (Part 0) : 1984 … (Part 64) : 2003" — attach bare parts
    to the last standard number seen before them."""
    out, last = [], None
    events = sorted([(m.start(), "num", m) for m in NUM_RE.finditer(refs)] + [(m.start(), "part", m) for m in PART_ONLY_RE.finditer(refs)],
                    key=lambda e: e[0])
    for pos, kind, m in events:
        if kind == "num":
            prev = refs[max(0, pos - 3): pos].strip()
            if prev.endswith((":", "-", "–", "/")):      # a year or an edition suffix, not a standard number
                continue
            last = m.group(1)
        elif last:
            b = base_of("IS", last, m.group(1), m.group(2))
            if known is None or b in known:
                out.append({"base": b, "year": int(m.group(3)), "at": pos})
    return out


# ---------------------------------------------------------------------------------------------- clauses
_HEAD = r"(?:^|\n)\s*(?:0?{n}(?:\.0)?\.?\s*)"
SCOPE_RE = re.compile(_HEAD.format(n=1) + r"(SCOPE|Scope)\b\s*[—\-–:.]*\s*", re.M)
REFS_RE = re.compile(_HEAD.format(n=2) + r"((?:NORMATIVE\s+)?REFERENCES?|(?:Normative\s+)?[Rr]eferences?)\b\s*[—\-–:.]*\s*", re.M)
TERM_RE = re.compile(_HEAD.format(n=r"[2-4]") + r"(TERMINOLOGY|DEFINITIONS|TERMS AND DEFINITIONS|Terminology|Definitions)\b\s*[—\-–:.]*\s*", re.M)
NEXT_HEAD_RE = re.compile(r"\n\s*(?:0?[2-9]|1[0-9])(?:\.0)?\.?\s+(?:[A-Z][A-Z ,&\-]{3,}|[A-Z][a-z]+(?:\s+[a-z]+)?\s*[—\-–:])")
FOREWORD_RE = re.compile(r"\bF\s?O\s?R\s?E\s?W\s?O\s?R\s?D\b|\bForeword\b")


def _clause(text: str, rx: re.Pattern, max_len: int) -> Optional[str]:
    m = rx.search(text)
    if not m:
        return None
    rest = text[m.end(): m.end() + max_len * 3]
    n = NEXT_HEAD_RE.search(rest)
    body = rest[: n.start()] if n else rest[:max_len]
    body = re.sub(r"\s+", " ", body).strip()
    return body[:max_len] if body else None


SCOPE_ANY_RE = re.compile(r"(?:(?<=\n)|(?<=\s))(?:0?1(?:\.1)?\.?\s*(?:GENERAL\s+1\.1\s*)?)?(SCOPE|Scope)\b\s*[—\-–:.]*\s*")
SCOPE_END_RE = re.compile(r"\s(?:1\.[2-9]|0?2)(?:\.0)?\.?\s+(?:[A-Z]{3,}|[A-Z][a-z]{2,})|\sNOTES?\b\s*[—\-–:]?\s*1?\s|\s(?:NORMATIVE\s+)?REFERENCES\b")
COVERS_RE = re.compile(r"This (?:Indian )?[Ss]tandard (?:covers|specifies|prescribes|lays down|deals with|gives|applies)[^.]{10,600}\.")


def scope_clause(text: str) -> Optional[str]:
    for m in SCOPE_ANY_RE.finditer(text[:60000]):
        before = text[max(0, m.start() - 6): m.start()].lower()
        after = text[m.end(): m.end() + 1200]
        headed = bool(re.match(r"\s*(?:0?1(?:\.1)?)", text[m.start(): m.start() + 6])) or text[max(0, m.start() - 1): m.start()] == "\n"
        if not headed and (before.endswith("the ") or before.endswith("of ") or not re.match(r"\s*(?:This|These|The|It|Covers|covers|[A-Z])", after)):
            continue
        end = SCOPE_END_RE.search(after, 40)
        body = re.sub(r"\s+", " ", after[: end.start()] if end else after[:900]).strip()
        if len(body) >= 25:
            return body[:900]
    m = COVERS_RE.search(text[:40000])
    return re.sub(r"\s+", " ", m.group(0))[:900] if m else None


def references_clause(text: str) -> Optional[str]:
    return _clause(text, REFS_RE, 4000)


ANNEX_REF_RE = re.compile(r"\bAnnex\s+([A-Z])\b", re.I)


def referenced_annex(text: str, refs: Optional[str]) -> Optional[str]:
    """Newer standards put the list of normative references in an annex ("The standards listed in Annex A …")."""
    if not refs:
        return None
    m = ANNEX_REF_RE.search(refs[:600])
    if not m:
        return None
    letter = m.group(1).upper()
    best = None
    for h in re.finditer(r"\bANNEX\s+" + letter + r"\b", text):
        after = text[h.end(): h.end() + 250]
        if re.search(r"Clause\s+2|REFERRED|NORMATIVE|STANDARDS", after, re.I):
            best = h
    if not best:
        return None
    rest = text[best.end(): best.end() + 6000]
    nxt = re.search(r"\bANNEX\s+[A-Z]\b", rest[50:])
    return rest[: 50 + nxt.start()] if nxt else rest


def terminology_clause(text: str) -> Optional[str]:
    return _clause(text, TERM_RE, 700)


def foreword(text: str) -> Optional[str]:
    m = FOREWORD_RE.search(text)
    if not m:
        return None
    body = text[m.end(): m.end() + 3500]
    return re.sub(r"\s+", " ", body)


REVISION_RE = re.compile(r"\(\s*(First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth)\s+Revision\s*\)", re.I)
REAFFIRMED_RE = re.compile(r"Reaffirmed\s*[:\-]?\s*((?:19|20)\d{2})", re.I)


def equivalents(fw: Optional[str]) -> List[dict]:
    """ISO / IEC documents named in the foreword, with the degree of correspondence stated around them."""
    if not fw:
        return []
    out, seen = [], set()
    for m in FOREIGN_RE.finditer(fw):
        std = f"{m.group(1)} {m.group(2)}"
        if std in seen:
            continue
        ctx = fw[max(0, m.start() - 220): m.end() + 80].lower()
        if "identical" in ctx:
            degree = "identical"
        elif "technically equivalent" in ctx or "technical equivalen" in ctx:
            degree = "technically equivalent"
        elif any(k in ctx for k in ("assistance", "based on", "derived", "aligned", "in line with", "harmoni")):
            degree = "derived from"
        else:
            degree = "mentioned"
        seen.add(std)
        out.append({"standard": std, "degree": degree})
    return out[:12]


SUPERSEDES_RE = re.compile(r"(?:supersedes?|superseding|in\s+place\s+of|replaces?|merged)\b[^.]{0,160}", re.I)


# ---------------------------------------------------------------------------------------------- relation typing
TITLE_KIND = [
    ("terminology", re.compile(r"\b(vocabulary|glossary|terminology|definitions?|terms)\b", re.I)),
    ("test_method", re.compile(r"\b(methods?\s+(?:of|for)\s+(?:test|testing|determination|analysis|measurement|sampling and test)|test(?:ing)?\s+methods?|determination\s+of|measurement\s+of)\b", re.I)),
    ("sampling", re.compile(r"\bsampling\b", re.I)),
    ("installation", re.compile(r"\b(installation|laying|erection|code of practice for (?:electrical )?wiring|fixing)\b", re.I)),
    ("safety", re.compile(r"\b(safety|hazard|protection against|fire|flammab)\b", re.I)),
    ("packaging_marking", re.compile(r"\b(packing|packaging|drums?|marking|labelling|containers?)\b", re.I)),
    ("material", re.compile(r"\b(compound|raw material|conductors?|wires? for|powder|resin|pigment|alloy)\b", re.I)),
    ("allied_product", re.compile(r"\bspecification\b", re.I)),
]


REL_TEST = re.compile(r"\b(tests?|testing|methods?\s+(?:of|for)\b|determination|measurement|chemical analysis|analysis of|evaluation procedure|"
                      r"assessment of|calibration|verification of)\b", re.I)
REL_DIM = re.compile(r"\b(dimensions?|tolerances?|preferred sizes|rolling and cutting)\b", re.I)


def relation_kind(title: str) -> str:
    """Kind of a *cited* standard, read from its title — broader than kind_from_title: 'Metallic materials — Bend test',
    'Mechanical testing of metals — Tensile testing' are test methods; 'Rolling and cutting tolerances …' are dimensions."""
    k = kind_from_title(title)
    if k in ("terminology", "test_method", "sampling"):
        return k
    if REL_TEST.search(title or "") and not re.search(r"\b(machines?|apparatus|sieves?|equipment|kits?)\b", title or "", re.I):
        return "test_method"
    if REL_DIM.search(title or ""):
        return "dimensions"
    return k


def kind_from_title(title: str) -> str:
    for k, rx in TITLE_KIND:
        if rx.search(title or ""):
            return k
    return "allied_product"


def parse(text: str, known: Set[str], self_base: Optional[str] = None) -> Dict:
    t = strip_front_matter(normalise(text))
    sc = scope_clause(t)
    refs = references_clause(t)
    term = terminology_clause(t)
    fw = foreword(t)
    rel: Dict[str, dict] = {}

    def add(c, clause, snippet_src):
        if c["base"] == self_base:
            return
        cur = rel.get(c["base"])
        snippet = re.sub(r"\s+", " ", snippet_src[max(0, c["at"] - 90): c["at"] + 110]).strip() if snippet_src else None
        if cur is None:
            rel[c["base"]] = {"base": c["base"], "year": c["year"], "clauses": [clause], "snippet": snippet}
        elif clause not in cur["clauses"]:
            cur["clauses"].append(clause)
            cur["year"] = cur["year"] or c["year"]

    annex = referenced_annex(t, refs)
    for block in [x for x in (refs, annex) if x]:
        for c in citations(block, known, bare=True):
            add(c, "references", block)
        for c in part_continuations(block, known):
            add(c, "references", block)
    if term:
        for c in citations(term, known):
            add(c, "terminology", term)
    body = t[:120000]
    for c in citations(body, known):
        add(c, "body", body)
    rev = REVISION_RE.search(t[:6000])
    reaff = [int(y) for y in REAFFIRMED_RE.findall(t[:8000])]
    sup = SUPERSEDES_RE.search(fw or "")
    return {
        "scope": sc, "has_references_clause": bool(refs), "revision": rev.group(1).title() if rev else None,
        "reaffirmed": max(reaff) if reaff else None, "equivalents": equivalents(fw),
        "supersedes_text": re.sub(r"\s+", " ", sup.group(0)).strip()[:200] if sup else None,
        "relations": list(rel.values()),
    }
