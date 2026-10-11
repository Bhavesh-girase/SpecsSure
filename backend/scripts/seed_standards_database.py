"""
Seeds the standards registry, amendments, relations and the regulatory (QCO/CRS) registry.

Sources (curated, see data/seed/*.json):
  standards_sample.json    — primary product standards with relations & amendments
  standards_extended.json  — historical editions, withdrawn standards, test-method standards, foreign standards
  regulations.json         — QCO / CRS / mandatory certification registry with verification state
"""
import os
import json
import asyncio
import logging
from datetime import datetime
from sqlalchemy import select, func
from app.db.session import async_session_maker
from app.models.standard import Standard, StandardStatus
from app.models.amendment import Amendment
from app.models.regulation import Regulation
from app.models.requirement import StandardRelation
from app.services.embedding_service import embedding_service
from app.engine.std_refs import family_of
from scripts.seed_product_ontology import seed_product_ontology

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_standards")
SEED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "seed")


def _date(v):
    return datetime.strptime(v, "%Y-%m-%d") if v else None


def _load(name):
    with open(os.path.join(SEED_DIR, name), "r", encoding="utf-8") as f:
        return json.load(f)


# designations that earlier seeds got wrong -> corrected designation (renamed in place so relations survive)
RETIRED_DESIGNATIONS = {"IS 694:2020": "IS 694:2010"}


def registry_fingerprint() -> str:
    """Hash of the seed files — lets an existing database pick up registry updates automatically."""
    import hashlib
    h = hashlib.sha256()
    for name in ("standards_sample.json", "standards_extended.json", "regulations.json"):
        with open(os.path.join(SEED_DIR, name), "rb") as f:
            h.update(f.read())
    return h.hexdigest()[:16]


async def _retire_designations(session):
    from sqlalchemy import delete, or_
    for old, new in RETIRED_DESIGNATIONS.items():
        o = (await session.execute(select(Standard).where(Standard.is_number == old))).scalars().first()
        if not o:
            continue
        n = (await session.execute(select(Standard).where(Standard.is_number == new))).scalars().first()
        if n is None:
            o.is_number = new
        else:
            await session.execute(delete(StandardRelation).where(or_(StandardRelation.from_standard_id == o.id,
                                                                     StandardRelation.to_standard_id == o.id)))
            await session.execute(delete(Amendment).where(Amendment.standard_id == o.id))
            await session.delete(o)
    await session.commit()


async def seed_standards():
    sample = _load("standards_sample.json")
    ext = _load("standards_extended.json")
    regs = _load("regulations.json")["regulations"]
    all_std = sample + ext["standards"]
    logger.info(f"Seeding {len(all_std)} standards records...")

    async with async_session_maker() as session:
        await _retire_designations(session)
        num_to_id = {}
        texts = [f"{s['is_number']} — {s['title']} — {(s.get('scope') or '')[:500]}" for s in all_std]
        embs = embedding_service.embed_batch(texts, is_query=False)
        for s_data, emb in zip(all_std, embs):
            is_num = s_data["is_number"]
            res = await session.execute(select(Standard).where(Standard.is_number == is_num))
            std = res.scalars().first()
            status_enum = getattr(StandardStatus, s_data.get("status", "current").upper(), StandardStatus.CURRENT)
            pub = _date(s_data.get("publication_date"))
            fields = dict(
                title=s_data["title"], scope=s_data.get("scope"), status=status_enum, edition=s_data.get("edition"),
                division_code=s_data.get("division_code"), section_committee=s_data.get("section_committee"),
                publication_date=pub, effective_from=_date(s_data.get("effective_from")) or pub,
                effective_to=_date(s_data.get("effective_to")), superseded_by=s_data.get("superseded_by"),
                iso_equivalent=s_data.get("iso_equivalent"), source_url=s_data.get("source_url") or "https://standards.bis.gov.in/",
                embedding=emb, search_text=f"{is_num} {s_data['title']} {s_data.get('scope', '') or ''} {s_data.get('division_code', '') or ''}",
            )
            if std:
                for k, v in fields.items():
                    setattr(std, k, v)
            else:
                std = Standard(is_number=is_num, **fields)
                session.add(std)
                await session.flush()
            num_to_id[is_num.upper()] = std.id
        await session.commit()

        async def resolve(num: str) -> int:
            if num.upper() in num_to_id:
                return num_to_id[num.upper()]
            fam = family_of(num)
            res = await session.execute(select(Standard))
            for s in res.scalars().all():
                if family_of(s.is_number) == fam:
                    num_to_id[num.upper()] = s.id
                    return s.id
            stub = Standard(is_number=num, title=f"Allied Standard {num}", scope=f"Normatively linked reference {num}",
                            status=StandardStatus.CURRENT, division_code="BIS Technical Standard",
                            embedding=embedding_service.embed_document(num))
            session.add(stub)
            await session.flush()
            num_to_id[num.upper()] = stub.id
            return stub.id

        # amendments
        for s_data in sample:
            sid = num_to_id[s_data["is_number"].upper()]
            for a in s_data.get("amendments", []):
                res = await session.execute(select(Amendment).where(Amendment.standard_id == sid, Amendment.amendment_number == a["amendment_number"]))
                if not res.scalars().first():
                    session.add(Amendment(standard_id=sid, amendment_number=a["amendment_number"], title=a.get("title"),
                                          published_at=_date(a.get("published_at")), effective_from=_date(a.get("effective_from")) or _date(a.get("published_at")),
                                          changed_clauses=a.get("changed_clauses"), summary=a.get("summary")))
        # relations
        rel_specs = [(s["is_number"], r["to_is_number"], r["relationship_type"], r.get("clause_reference")) for s in sample for r in s.get("relations", [])]
        rel_specs += [(r["from"], r["to"], r["relationship_type"], r.get("clause_reference")) for r in ext["relations"]]
        for frm, to, rtype, clause in rel_specs:
            fid, tid = await resolve(frm), await resolve(to)
            res = await session.execute(select(StandardRelation).where(StandardRelation.from_standard_id == fid,
                                                                       StandardRelation.to_standard_id == tid,
                                                                       StandardRelation.relationship_type == rtype))
            if not res.scalars().first():
                session.add(StandardRelation(from_standard_id=fid, to_standard_id=tid, relationship_type=rtype, clause_reference=clause))
        # regulations (registry file is authoritative; drop legacy un-keyed rows from v1 seeds)
        from sqlalchemy import delete
        await session.execute(delete(Regulation).where(Regulation.key.is_(None)))
        for r in regs:
            res = await session.execute(select(Regulation).where(Regulation.key == r["key"]))
            reg = res.scalars().first()
            fields = dict(regulation_type=r["regulation_type"], scheme=r.get("scheme"), title=r["title"],
                          issuing_authority=r.get("issuing_authority"), notification_number=r.get("notification_number"),
                          product_scope=r.get("product_scope"), standard_ids=r["standards"], effective_from=_date(r.get("effective_from")),
                          effective_to=_date(r.get("effective_to")), is_mandatory=r.get("is_mandatory", "yes"),
                          source_url=r.get("source_url"), verification_state=r.get("verification_state"))
            if reg:
                for k, v in fields.items():
                    setattr(reg, k, v)
            else:
                session.add(Regulation(key=r["key"], **fields))
        await session.commit()
        logger.info("Seeded standards, amendments, relations and regulatory registry.")


def _write_marker(fp: str):
    marker = os.path.join(os.path.dirname(__file__), "..", "var", "registry_fingerprint")
    os.makedirs(os.path.dirname(marker), exist_ok=True)
    with open(marker, "w") as f:
        f.write(fp)


async def seed_all_if_needed():
    """Auto-seeds the database if the standards table is empty."""
    async with async_session_maker() as session:
        try:
            count = (await session.execute(select(func.count(Standard.id)))).scalar() or 0
            if count == 0:
                logger.info("Database is empty. Seeding ontologies and standards registry...")
                await seed_product_ontology()
                await seed_standards()
                _write_marker(registry_fingerprint())
            else:
                marker = os.path.join(os.path.dirname(__file__), "..", "var", "registry_fingerprint")
                fp = registry_fingerprint()
                old = open(marker).read().strip() if os.path.exists(marker) else None
                reg_keys = (await session.execute(select(func.count(Regulation.id)).where(Regulation.key.isnot(None)))).scalar() or 0
                if reg_keys == 0 or old != fp:
                    logger.info("Registry seed files changed — upserting standards, editions and QCO registry...")
                    await seed_standards()
                else:
                    logger.info(f"Database already populated ({count} standards registered).")
                _write_marker(fp)
        except Exception as e:
            logger.warning(f"Seeding check notice: {e}")


if __name__ == "__main__":
    async def main():
        from app.db.init_db import init_db
        await init_db()
        await seed_product_ontology()
        await seed_standards()
    asyncio.run(main())
