from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.bidmirror import mirror
from app.engine.docparse import parse_document
from app.engine.evidence import extract_evidence
from app.engine.guardrails import scan_injection
from app.engine import passport as vc
from app.models import Bid, BidDocument, Passport, Tender
from app.services import ledger_service
from app.services.tender_service import compile_tender


async def create_bid(db: AsyncSession, tender_id: str, bidder: str, product_name: Optional[str],
                     files: List[Tuple[str, bytes]], doc_types: Optional[Dict[str, str]] = None) -> Bid:
    tender = await db.get(Tender, tender_id)
    if tender is None:
        raise ValueError("tender not found")
    twin = tender.twin or await compile_tender(db, tender_id, reason="bid-mirror")
    evidence_docs = []
    bid = Bid(tender_id=tender_id, bidder=bidder, product_name=product_name)
    db.add(bid)
    await db.flush()
    security = []
    for name, data in files:
        parsed = parse_document(data, name)
        ev = extract_evidence(parsed, (doc_types or {}).get(name))
        hits = scan_injection(parsed.text)
        if hits:
            security.append({"file": name, "hits": hits[:3]})
        evidence_docs.append(ev)
        db.add(BidDocument(bid_id=bid.id, filename=name, doc_type=ev["meta"]["doc_type"], sha256=parsed.sha256, content=data, text=parsed.text))
    result = mirror(twin, evidence_docs, bidder=bidder)
    result["product_name"] = product_name
    result["security_flags"] = security
    bid.result, bid.evidence = result, evidence_docs
    bid.compliance_score, bid.verdict = result["compliance_score"], result["verdict"]
    await db.commit()
    await db.refresh(bid)
    await ledger_service.append(db, bidder, "bid.mirrored", "bid", bid.id, {
        "tender_id": tender_id, "files": [{"f": d["meta"]["doc_name"], "sha256": d["meta"]["sha256"]} for d in evidence_docs],
        "verdict": result["verdict"], "score": result["compliance_score"], "tender_kb": twin["provenance"]["kb_snapshot"]})
    return bid


async def issue_passport(db: AsyncSession, bid_id: str, base_url: str = "") -> Passport:
    bid = await db.get(Bid, bid_id)
    if bid is None:
        raise ValueError("bid not found")
    tender = await db.get(Tender, bid.tender_id)
    subject = vc.build_subject({**bid.result, "bidder": bid.bidder, "product_name": bid.product_name}, tender.twin, bid.evidence or [])
    valid_until = subject["certification"].get("validUntil")
    cred = vc.issue(subject, valid_until)
    p = Passport(bid_id=bid.id, product_name=bid.product_name, credential=cred)
    db.add(p)
    await db.commit()
    await db.refresh(p)
    await ledger_service.append(db, "system", "passport.issued", "passport", p.id,
                                {"bid_id": bid.id, "credential_id": cred["id"], "issuer": cred["issuer"]["id"],
                                 "proof": cred["proof"]["proofValue"][:24]})
    return p


async def bid_files(db: AsyncSession, bid_id: str):
    return (await db.execute(select(BidDocument).where(BidDocument.bid_id == bid_id))).scalars().all()
