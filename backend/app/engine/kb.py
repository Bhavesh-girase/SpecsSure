"""
Knowledge-base snapshot used by the Tender Compiler.

The compiler never queries the database mid-analysis: it takes an immutable snapshot of the
standards registry, amendments, relations and regulations. That makes every compile
reproducible (the snapshot hash is written to the audit ledger) and lets the engine run
fully offline in tests.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional

from app.engine.std_refs import family_of, year_of

SEED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "seed"))


def _d(v) -> Optional[date]:
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    try:
        return datetime.strptime(str(v)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


@dataclass
class StdRecord:
    id: int
    is_number: str
    title: str
    status: str
    family: str
    year: Optional[int]
    scope: str = ""
    edition: Optional[str] = None
    division: Optional[str] = None
    publication_date: Optional[date] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    superseded_by: Optional[str] = None
    iso_equivalent: Optional[str] = None
    source_url: Optional[str] = None

    def to_dict(self) -> dict:
        return {"id": self.id, "is_number": self.is_number, "title": self.title, "status": self.status,
                "family": self.family, "year": self.year, "edition": self.edition, "division": self.division,
                "publication_date": self.publication_date.isoformat() if self.publication_date else None,
                "effective_from": self.effective_from.isoformat() if self.effective_from else None,
                "effective_to": self.effective_to.isoformat() if self.effective_to else None,
                "superseded_by": self.superseded_by, "iso_equivalent": self.iso_equivalent,
                "source_url": self.source_url or f"https://standards.bis.gov.in/"}


@dataclass
class AmendRecord:
    standard_id: int
    number: int
    title: str
    published_at: Optional[date]
    effective_from: Optional[date]
    changed_clauses: str = ""
    summary: str = ""
    source_url: Optional[str] = None

    def to_dict(self):
        return {"number": self.number, "title": self.title,
                "published_at": self.published_at.isoformat() if self.published_at else None,
                "effective_from": self.effective_from.isoformat() if self.effective_from else None,
                "changed_clauses": self.changed_clauses, "summary": self.summary, "source_url": self.source_url}


@dataclass
class RelRecord:
    from_id: int
    to_id: int
    type: str
    clause_reference: Optional[str] = None


@dataclass
class RegRecord:
    id: int
    key: str
    regulation_type: str
    scheme: str
    title: str
    authority: str
    notification: Optional[str]
    families: List[str]
    product_scope: str
    effective_from: Optional[date]
    effective_to: Optional[date]
    mandatory: str
    source_url: Optional[str]
    verification_state: str

    def in_force(self, on: date) -> bool:
        if self.effective_from and self.effective_from > on:
            return False
        if self.effective_to and self.effective_to < on:
            return False
        return True

    def to_dict(self):
        return {"id": self.id, "key": self.key, "regulation_type": self.regulation_type, "scheme": self.scheme,
                "title": self.title, "issuing_authority": self.authority, "notification_number": self.notification,
                "standards": self.families, "product_scope": self.product_scope,
                "effective_from": self.effective_from.isoformat() if self.effective_from else None,
                "effective_to": self.effective_to.isoformat() if self.effective_to else None,
                "is_mandatory": self.mandatory, "source_url": self.source_url,
                "verification_state": self.verification_state}


@dataclass
class KnowledgeBase:
    standards: List[StdRecord]
    amendments: List[AmendRecord]
    relations: List[RelRecord]
    regulations: List[RegRecord]
    by_id: Dict[int, StdRecord] = field(default_factory=dict)
    by_family: Dict[str, List[StdRecord]] = field(default_factory=dict)
    by_number: Dict[str, StdRecord] = field(default_factory=dict)

    def __post_init__(self):
        self.reindex()

    def reindex(self):
        self.by_id = {s.id: s for s in self.standards}
        self.by_number = {s.is_number.upper(): s for s in self.standards}
        self.by_family = {}
        for s in self.standards:
            self.by_family.setdefault(s.family, []).append(s)
        for fam in self.by_family.values():
            fam.sort(key=lambda s: (s.year or 0, s.publication_date or date.min))

    # -------------------------------------------------------------------------------------
    def amendments_of(self, std_id: int) -> List[AmendRecord]:
        return sorted([a for a in self.amendments if a.standard_id == std_id], key=lambda a: a.number)

    def outgoing(self, std_id: int, types: Optional[List[str]] = None) -> List[RelRecord]:
        return [r for r in self.relations if r.from_id == std_id and (types is None or r.type in types)]

    def incoming(self, std_id: int, types: Optional[List[str]] = None) -> List[RelRecord]:
        return [r for r in self.relations if r.to_id == std_id and (types is None or r.type in types)]

    def regulations_for_family(self, family: str) -> List[RegRecord]:
        from app.engine.std_refs import base_number
        out = []
        for r in self.regulations:
            for f in r.families:
                if f == family or base_number(f) == family or f == base_number(family):
                    out.append(r)
                    break
        return out

    def lookup(self, text: str) -> Optional[StdRecord]:
        s = self.by_number.get(text.strip().upper())
        if s:
            return s
        fam = family_of(text)
        yr = year_of(text)
        eds = self.by_family.get(fam, [])
        if yr:
            for e in eds:
                if e.year == yr:
                    return e
        return eds[-1] if eds else None

    def snapshot_hash(self) -> str:
        payload = json.dumps({
            "s": [(s.is_number, s.status, str(s.effective_to)) for s in self.standards],
            "a": [(a.standard_id, a.number, str(a.published_at)) for a in self.amendments],
            "r": [(r.key, str(r.effective_from), str(r.effective_to)) for r in self.regulations],
        }, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

    # -------------------------------------------------------------------------------------
    @classmethod
    def from_seed(cls) -> "KnowledgeBase":
        """Build directly from the seed JSON (no database) — used by tests & the MCP server."""
        with open(os.path.join(SEED_DIR, "standards_sample.json"), encoding="utf-8") as f:
            sample = json.load(f)
        with open(os.path.join(SEED_DIR, "standards_extended.json"), encoding="utf-8") as f:
            ext = json.load(f)
        with open(os.path.join(SEED_DIR, "regulations.json"), encoding="utf-8") as f:
            regs = json.load(f)["regulations"]
        stds: List[StdRecord] = []
        amends: List[AmendRecord] = []
        rels: List[RelRecord] = []
        num_to_id: Dict[str, int] = {}

        def add_std(d: dict):
            if d["is_number"].upper() in num_to_id:
                return num_to_id[d["is_number"].upper()]
            sid = len(stds) + 1
            pub = _d(d.get("publication_date"))
            stds.append(StdRecord(
                id=sid, is_number=d["is_number"], title=d.get("title", d["is_number"]), status=d.get("status", "current"),
                family=family_of(d["is_number"]), year=year_of(d["is_number"]), scope=d.get("scope") or "",
                edition=d.get("edition"), division=d.get("division_code"), publication_date=pub,
                effective_from=_d(d.get("effective_from")) or pub, effective_to=_d(d.get("effective_to")),
                superseded_by=d.get("superseded_by"), iso_equivalent=d.get("iso_equivalent"), source_url=d.get("source_url")))
            num_to_id[d["is_number"].upper()] = sid
            return sid

        for d in sample:
            add_std(d)
        for d in ext["standards"]:
            add_std(d)

        def resolve_or_stub(num: str) -> int:
            if num.upper() in num_to_id:
                return num_to_id[num.upper()]
            fam = family_of(num)
            for s in stds:
                if s.family == fam:
                    return s.id
            return add_std({"is_number": num, "title": f"Allied Standard {num}", "status": "current"})

        for d in sample:
            fid = num_to_id[d["is_number"].upper()]
            for a in d.get("amendments", []):
                amends.append(AmendRecord(fid, a["amendment_number"], a.get("title", ""), _d(a.get("published_at")),
                                          _d(a.get("effective_from")) or _d(a.get("published_at")),
                                          a.get("changed_clauses", ""), a.get("summary", ""), a.get("source_url")))
            for r in d.get("relations", []):
                rels.append(RelRecord(fid, resolve_or_stub(r["to_is_number"]), r["relationship_type"], r.get("clause_reference")))
        for r in ext["relations"]:
            rels.append(RelRecord(resolve_or_stub(r["from"]), resolve_or_stub(r["to"]), r["relationship_type"], r.get("clause_reference")))
        reg_records = [RegRecord(i + 1, r["key"], r["regulation_type"], r.get("scheme", ""), r["title"], r.get("issuing_authority", ""),
                                 r.get("notification_number"), r["standards"], r.get("product_scope", ""),
                                 _d(r.get("effective_from")), _d(r.get("effective_to")), r.get("is_mandatory", "yes"),
                                 r.get("source_url"), r.get("verification_state", "curated_unverified"))
                       for i, r in enumerate(regs)]
        return cls(stds, amends, rels, reg_records)

    @classmethod
    async def from_db(cls, db) -> "KnowledgeBase":
        from sqlalchemy import select
        from app.models import Standard, Amendment, StandardRelation, Regulation

        stds = []
        for s in (await db.execute(select(Standard))).scalars().all():
            status = s.status.value if hasattr(s.status, "value") else str(s.status)
            pub = _d(s.publication_date)
            stds.append(StdRecord(s.id, s.is_number, s.title, status, family_of(s.is_number), year_of(s.is_number),
                                  s.scope or "", s.edition, s.division_code, pub, _d(s.effective_from) or pub,
                                  _d(s.effective_to), s.superseded_by, s.iso_equivalent, s.source_url))
        amends = [AmendRecord(a.standard_id, a.amendment_number, a.title or "", _d(a.published_at),
                              _d(a.effective_from) or _d(a.published_at), a.changed_clauses or "", a.summary or "", a.source_url)
                  for a in (await db.execute(select(Amendment))).scalars().all()]
        rels = [RelRecord(r.from_standard_id, r.to_standard_id, r.relationship_type, r.clause_reference)
                for r in (await db.execute(select(StandardRelation))).scalars().all()]
        regs = []
        for r in (await db.execute(select(Regulation))).scalars().all():
            fams = [family_of(x) for x in (r.standard_ids or [])]
            regs.append(RegRecord(r.id, getattr(r, "key", None) or f"REG-{r.id}", r.regulation_type,
                                  getattr(r, "scheme", None) or r.regulation_type, r.title, r.issuing_authority or "",
                                  r.notification_number, fams, r.product_scope or "", _d(r.effective_from), _d(r.effective_to),
                                  r.is_mandatory or "yes", r.source_url, getattr(r, "verification_state", None) or "curated_unverified"))
        return cls(stds, amends, rels, regs)


_SEED_KB: Optional[KnowledgeBase] = None


def seed_kb() -> KnowledgeBase:
    global _SEED_KB
    if _SEED_KB is None:
        _SEED_KB = KnowledgeBase.from_seed()
    return _SEED_KB
