"""
Standard-citation parsing & normalisation.

Tenders cite standards in wildly inconsistent ways: "IS:1786-2008", "IS 1786 : 2008",
"IS-1786", "IS 4031 (Pt 6)", "IS 10322 (Part 5/Sec 1):2012", "IS/IEC 60529", "BS EN 197-1".
Everything is normalised to a *family key* (number + part/section, no year) plus an
optional *edition year*, so the temporal engine can resolve which edition applies.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

_PART = r"(?:\s*\(\s*(?:Part|Pt\.?|P)\s*(?P<part>\d+[A-Z]?)(?:\s*/\s*(?:Sec(?:tion)?\.?|S)\s*(?P<sec>\d+))?\s*\))"
_PART_BARE = r"(?:\s*(?:Part|Pt\.?)\s*(?P<part2>\d+[A-Z]?)(?:\s*/?\s*(?:Sec(?:tion)?\.?)\s*(?P<sec2>\d+))?)"
_YEAR = r"(?:\s*[:\-–]\s*(?P<year>(?:19|20)\d{2}))"

IS_CITATION = re.compile(
    r"\bIS\s*(?:/\s*(?P<co>IEC|ISO))?\s*[:\-]?\s*(?P<num>\d{2,5})(?:" + _PART + "|" + _PART_BARE + r")?" + _YEAR + "?",
    re.IGNORECASE,
)
FOREIGN_CITATION = re.compile(
    r"\b(?P<body>BS\s+EN|BS|EN|ASTM|ISO|IEC|IEEE|DIN|JIS)\s*[:\-]?\s*(?P<num>[A-Z]?\d{2,6}(?:[\-/][A-Z0-9]+)?(?:\s*/\s*[A-Z]\d+M?)?)"
    r"(?:\s*[:\-]\s*(?P<year>(?:19|20)\d{2}))?",
)
GENERIC_REFERENCE = re.compile(
    r"\b(?:as per|conforming to|confirming to|complying with|in accordance with)\s+(?:the\s+)?(?:relevant\s+|latest\s+|applicable\s+)?"
    r"(?:BIS|IS|Indian Standards?|standards?|IS codes?|codes?)(?:\s+(?:specifications?|norms|codes?))?\b(?!\s*[:\-/]?\s*(?:\d|IEC|ISO|\())",
    re.IGNORECASE,
)


@dataclass
class StdRef:
    raw: str
    family: str             # e.g. "IS 1786", "IS 4031 (Part 6)", "IS/IEC 60529", "BS 4449"
    year: Optional[int]
    body: str = "BIS"       # BIS | BS | EN | ASTM | ISO | IEC ...
    start: int = 0
    end: int = 0

    @property
    def display(self) -> str:
        return f"{self.family}:{self.year}" if self.year else self.family

    def to_dict(self):
        return {"raw": self.raw, "family": self.family, "year": self.year, "body": self.body,
                "display": self.display, "span": [self.start, self.end]}


def _family(num: str, part: Optional[str], sec: Optional[str], co: Optional[str]) -> str:
    base = f"IS/{co.upper()} {num}" if co else f"IS {num}"
    if part:
        base += f" (Part {part.upper()}" + (f"/Sec {sec})" if sec else ")")
    return base


def parse_citations(text: str) -> List[StdRef]:
    refs: List[StdRef] = []
    seen = set()
    for m in IS_CITATION.finditer(text or ""):
        part = m.group("part") or m.group("part2")
        sec = m.group("sec") or m.group("sec2")
        fam = _family(m.group("num"), part, sec, m.group("co"))
        year = int(m.group("year")) if m.group("year") else None
        key = (fam, year, m.start())
        if key in seen:
            continue
        seen.add(key)
        refs.append(StdRef(raw=m.group(0).strip(), family=fam, year=year, body="BIS", start=m.start(), end=m.end()))
    for m in FOREIGN_CITATION.finditer(text or ""):
        body = re.sub(r"\s+", " ", m.group("body").upper())
        num = m.group("num").replace(" ", "")
        fam = f"{body} {num}"
        year = int(m.group("year")) if m.group("year") else None
        # skip "IS/IEC" already captured above
        prefix = (text[max(0, m.start() - 3):m.start()] or "").upper()
        if prefix.endswith("IS/"):
            continue
        refs.append(StdRef(raw=m.group(0).strip(), family=fam, year=year, body=body.split()[0], start=m.start(), end=m.end()))
    refs.sort(key=lambda r: r.start)
    return refs


def family_of(is_number: str) -> str:
    """Normalise a registry IS number ("IS 1786:2008", "IS 10322 (Part 5/Sec 1):2012") to its family key."""
    refs = parse_citations(is_number)
    if refs:
        return refs[0].family
    return re.sub(r"\s*[:\-]\s*(?:19|20)\d{2}\s*$", "", is_number.strip())


def year_of(is_number: str) -> Optional[int]:
    refs = parse_citations(is_number)
    if refs and refs[0].year:
        return refs[0].year
    m = re.search(r"[:\-]\s*((?:19|20)\d{2})\s*$", is_number or "")
    return int(m.group(1)) if m else None


def base_number(family: str) -> str:
    """'IS 4031 (Part 6)' -> 'IS 4031'"""
    return re.sub(r"\s*\(.*\)\s*$", "", family).strip()


def find_generic_references(text: str):
    return [(m.group(0), m.start(), m.end()) for m in GENERIC_REFERENCE.finditer(text or "")]
