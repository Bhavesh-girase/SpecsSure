"""Tender Digital Twin, bidder, regulatory-radar and governance tables."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, JSON, LargeBinary, String, Text

from app.db.session import Base


def short_id() -> str:
    return uuid.uuid4().hex[:12]


class Tender(Base):
    __tablename__ = "tenders"

    id = Column(String(32), primary_key=True, default=short_id)
    title = Column(Text, nullable=False)
    reference_no = Column(String(200), nullable=True)
    organisation = Column(String(300), nullable=True)
    status = Column(String(30), default="draft", index=True)       # draft | published | closed | template | archived
    as_of_date = Column(Date, nullable=True)
    twin = Column(JSON, nullable=True)
    compiled_at = Column(DateTime, nullable=True)
    readiness_score = Column(Float, nullable=True)
    gate = Column(String(30), nullable=True)
    generation = Column(JSON, nullable=True)     # Tender Studio: intent, clause provenance, verification passes
    award = Column(JSON, nullable=True)          # evaluation committee decision
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TenderDocument(Base):
    __tablename__ = "tender_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tender_id = Column(String(32), ForeignKey("tenders.id", ondelete="CASCADE"), index=True, nullable=False)
    doc_type = Column(String(30), nullable=False)                  # tender | annexure | corrigendum | prebid
    filename = Column(String(300), nullable=False)
    sha256 = Column(String(64), nullable=False)
    sequence_no = Column(Integer, nullable=True)
    issued_on = Column(String(10), nullable=True)
    text = Column(Text, nullable=False)
    parse_meta = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class FindingState(Base):
    """Human review state of a finding, keyed by its stable fingerprint (survives re-compilation)."""
    __tablename__ = "finding_states"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tender_id = Column(String(32), ForeignKey("tenders.id", ondelete="CASCADE"), index=True, nullable=False)
    fingerprint = Column(String(32), index=True, nullable=False)
    rule_id = Column(String(30), nullable=True)
    review_status = Column(String(20), default="open")             # open | accepted | dismissed | fixed
    reviewer = Column(String(120), nullable=True)
    comment = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PrebidItem(Base):
    __tablename__ = "prebid_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tender_id = Column(String(32), ForeignKey("tenders.id", ondelete="CASCADE"), index=True, nullable=False)
    qid = Column(String(40), index=True)
    source = Column(String(20), default="predicted")                # predicted | received
    clause_key = Column(String(40), nullable=True)
    question = Column(Text, nullable=False)
    likelihood = Column(Float, nullable=True)
    draft_response = Column(Text, nullable=True)
    final_response = Column(Text, nullable=True)
    status = Column(String(20), default="predicted")               # predicted | received | approved | published | rejected
    finding_fingerprint = Column(String(32), nullable=True)
    data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Bid(Base):
    __tablename__ = "bids"

    id = Column(String(32), primary_key=True, default=short_id)
    tender_id = Column(String(32), ForeignKey("tenders.id", ondelete="CASCADE"), index=True, nullable=False)
    bidder = Column(String(300), nullable=False)
    product_name = Column(String(300), nullable=True)
    result = Column(JSON, nullable=True)
    evidence = Column(JSON, nullable=True)
    compliance_score = Column(Float, nullable=True)
    verdict = Column(String(60), nullable=True)
    form = Column(JSON, nullable=True)           # Smart Bid Form: answers + Tender Match Index
    match_index = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class BidDocument(Base):
    __tablename__ = "bid_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bid_id = Column(String(32), ForeignKey("bids.id", ondelete="CASCADE"), index=True, nullable=False)
    filename = Column(String(300), nullable=False)
    doc_type = Column(String(30), nullable=True)
    sha256 = Column(String(64), nullable=False)
    content = Column(LargeBinary, nullable=True)
    text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class RegulatoryEvent(Base):
    __tablename__ = "regulatory_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(30), nullable=False)                # amendment | revision | withdrawal | qco_new | qco_amend | source_changed
    subject = Column(String(200), nullable=True)
    title = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    effective_from = Column(String(10), nullable=True)
    source_url = Column(Text, nullable=True)
    simulated = Column(Boolean, default=False)
    status = Column(String(20), default="applied")                 # applied | pending_triage | dismissed
    impact = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tender_id = Column(String(32), nullable=True, index=True)
    event_id = Column(Integer, nullable=True)
    severity = Column(String(20), default="info")
    title = Column(Text, nullable=False)
    message = Column(Text, nullable=True)
    delta = Column(JSON, nullable=True)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class LedgerEntry(Base):
    __tablename__ = "audit_ledger"

    seq = Column(Integer, primary_key=True, autoincrement=False)
    ts = Column(String(40), nullable=False)
    actor = Column(String(120), nullable=False)
    action = Column(String(80), nullable=False)
    subject_type = Column(String(40), nullable=False)
    subject_id = Column(String(80), nullable=False)
    payload = Column(JSON, nullable=False)
    payload_hash = Column(String(64), nullable=False)
    prev_hash = Column(String(64), nullable=False)
    entry_hash = Column(String(64), nullable=False, index=True)


class Passport(Base):
    __tablename__ = "passports"

    id = Column(String(32), primary_key=True, default=short_id)
    bid_id = Column(String(32), nullable=True, index=True)
    product_name = Column(String(300), nullable=True)
    credential = Column(JSON, nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Review(Base):
    """Generic human-in-the-loop decision (equivalence approval, clarification approval, restriction justification ...)."""
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_type = Column(String(40), nullable=False)
    subject_id = Column(String(120), nullable=False)
    decision = Column(String(30), nullable=False)                  # approved | rejected | needs_info | justified
    reviewer = Column(String(120), nullable=True)
    comment = Column(Text, nullable=True)
    data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SourceSnapshot(Base):
    __tablename__ = "source_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(80), index=True, nullable=False)
    url = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=True)
    status = Column(String(30), nullable=True)
    fetched_at = Column(DateTime, default=datetime.utcnow)
