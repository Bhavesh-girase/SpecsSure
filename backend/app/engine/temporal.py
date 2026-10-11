"""
Temporal Standards Engine — "which edition, amendments and QCOs applied ON a given date?"

Standards are modelled with valid-time intervals [effective_from, effective_to). Amendments and
regulations carry their own effective dates. Resolving a citation "as of" the tender's publication
(or bid-due, or delivery) date lets us answer questions a keyword search cannot:

  * Was IS 8112:1989 still valid when this tender was published?        (no — withdrawn, merged in IS 269:2015)
  * Which amendments to IS 1786:2008 were in force on 01-10-2026?        (Amd 1, Amd 2 ...)
  * Will a QCO come into force before the delivery date?                  (upcoming-enforcement warning)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Optional

from app.engine.kb import KnowledgeBase, StdRecord, _d
from app.engine.std_refs import family_of, year_of, base_number


@dataclass
class Resolution:
    citation: str
    family: str
    cited_year: Optional[int]
    as_of: str
    cited: Optional[dict]
    in_force: Optional[dict]
    status: str                      # current | outdated_edition | withdrawn | superseded | unknown | not_yet_effective | undated_current
    replacement: Optional[str]
    amendments_in_force: List[dict] = field(default_factory=list)
    amendments_pending: List[dict] = field(default_factory=list)
    regulations_in_force: List[dict] = field(default_factory=list)
    regulations_upcoming: List[dict] = field(default_factory=list)
    timeline: List[dict] = field(default_factory=list)
    explanation: str = ""

    def to_dict(self):
        return self.__dict__.copy()


def _valid_on(s: StdRecord, on: date) -> bool:
    start = s.effective_from or s.publication_date
    if start and start > on:
        return False
    if s.effective_to and s.effective_to < on:
        return False
    if s.status in ("withdrawn", "superseded") and not s.effective_to:
        return False
    return True


def _follow_supersession(kb: KnowledgeBase, s: StdRecord, on: date, depth: int = 0) -> Optional[StdRecord]:
    if depth > 6 or not s.superseded_by:
        return s if _valid_on(s, on) else None
    nxt = kb.lookup(s.superseded_by)
    if nxt is None:
        return None
    if _valid_on(nxt, on):
        return nxt
    return _follow_supersession(kb, nxt, on, depth + 1)


def resolve(kb: KnowledgeBase, citation: str, as_of: Optional[date] = None, horizon_days: int = 365) -> Resolution:
    on = as_of or date.today()
    fam = family_of(citation)
    yr = year_of(citation)
    editions = kb.by_family.get(fam, [])
    if not editions and fam != base_number(fam):
        editions = kb.by_family.get(base_number(fam), [])
    timeline = [{"is_number": e.is_number, "status": e.status,
                 "from": (e.effective_from or e.publication_date).isoformat() if (e.effective_from or e.publication_date) else None,
                 "to": e.effective_to.isoformat() if e.effective_to else None, "superseded_by": e.superseded_by} for e in editions]
    cited = None
    if yr:
        cited = next((e for e in editions if e.year == yr), None)
    in_force = next((e for e in reversed(editions) if _valid_on(e, on)), None)
    replacement = None
    status = "unknown"
    explanation = ""

    if not editions:
        status = "unknown"
        explanation = f"{citation} is not in the curated registry — verify the designation on standards.bis.gov.in."
    elif cited is None and yr is None:
        # undated reference -> refers to latest edition in force
        if in_force:
            status = "undated_current"
            explanation = (f"Undated reference: as of {on.isoformat()} it resolves to {in_force.is_number}. "
                           f"Citing the year avoids ambiguity if the standard is revised during the tender.")
        else:
            latest = editions[-1]
            succ = _follow_supersession(kb, latest, on)
            status = "withdrawn" if latest.status == "withdrawn" else "superseded"
            replacement = succ.is_number if succ else latest.superseded_by
            explanation = f"{fam} has no edition in force on {on.isoformat()}; it was {latest.status} and replaced by {replacement or 'an unspecified standard'}."
    elif cited is None:
        status = "unknown"
        explanation = f"Edition {yr} of {fam} is not in the registry. Editions known: {', '.join(e.is_number for e in editions)}."
        if in_force:
            replacement = in_force.is_number
    else:
        if _valid_on(cited, on):
            status = "current"
            explanation = f"{cited.is_number} is the edition in force on {on.isoformat()}."
        elif (cited.effective_from or cited.publication_date or date.min) > on:
            status = "not_yet_effective"
            explanation = f"{cited.is_number} only takes effect on {cited.effective_from}."
        else:
            succ = _follow_supersession(kb, cited, on)
            replacement = succ.is_number if succ else cited.superseded_by
            status = "withdrawn" if cited.status == "withdrawn" or (succ and succ.family != cited.family) else "outdated_edition"
            when = cited.effective_to.isoformat() if cited.effective_to else "an earlier date"
            explanation = (f"{cited.is_number} ceased to be valid on {when}. "
                           f"As of {on.isoformat()} the applicable standard is {replacement or 'not identifiable'}"
                           + (" (the family was withdrawn and merged into another standard)." if status == "withdrawn" else "."))

    target = in_force if status in ("current", "undated_current") else (kb.lookup(replacement) if replacement else None)
    if status == "current" and cited:
        target = cited
    amends_in, amends_pending = [], []
    if target:
        for a in kb.amendments_of(target.id):
            eff = a.effective_from or a.published_at
            (amends_in if (eff is None or eff <= on) else amends_pending).append(a.to_dict())
    regs_in, regs_up = [], []
    fam_for_reg = (target.family if target else fam)
    for r in kb.regulations_for_family(fam_for_reg) + ([] if fam_for_reg == fam else kb.regulations_for_family(fam)):
        if r.in_force(on):
            if r.to_dict() not in regs_in:
                regs_in.append(r.to_dict())
        elif r.effective_from and on < r.effective_from <= on + timedelta(days=horizon_days):
            regs_up.append(r.to_dict())
    return Resolution(citation=citation, family=fam, cited_year=yr, as_of=on.isoformat(),
                      cited=cited.to_dict() if cited else None, in_force=(target.to_dict() if target else None),
                      status=status, replacement=replacement, amendments_in_force=amends_in, amendments_pending=amends_pending,
                      regulations_in_force=regs_in, regulations_upcoming=regs_up, timeline=timeline, explanation=explanation)
