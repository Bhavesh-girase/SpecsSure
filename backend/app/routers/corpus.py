"""Standards Recommender over the full Indian Standards corpus (PS SIH26108 core)."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.engine.kb import KnowledgeBase
from app.services.corpus_service import get_corpus

router = APIRouter()

DISCLAIMER = ("Recommendations are computed from the text of archived Indian Standards (Public.Resource.Org on the Internet Archive) "
              "and the curated regulation registry. Archived editions can be older than the edition in force — confirm the current "
              "edition, amendments and certification scheme on the BIS portal (standards.bis.gov.in / bis.gov.in) before use.")


def _status(card: dict, kb: KnowledgeBase) -> dict:
    """Edition status. Order of authority: BIS e-Sale portal (fetched on a stated date) → curated registry → archive notes."""
    c = get_corpus()
    es = c.edition_status(card["base"])
    rec = kb.lookup(card["base"])
    yr = card.get("latest_archived_year")
    common = {"portal": es, "amendments": es.get("amendments") or [], "source": es.get("source"), "fetched": es.get("fetched")}
    amd_txt = ""
    if es.get("amendments"):
        amd_txt = " with Amendment " + ", ".join(f"No. {a['no']} ({a['year']})" for a in es["amendments"][-4:])
        if len(es["amendments"]) > 4:
            amd_txt = f" with {len(es['amendments'])} amendments (latest " + ", ".join(f"No. {a['no']} ({a['year']})" for a in es["amendments"][-2:]) + ")"
    elif es.get("amendments_count"):
        amd_txt = f" with {es['amendments_count']} amendment(s)"
    if es.get("status") == "Withdrawn":
        rep = es.get("replacement")
        return {**common, "level": "bad", "in_force": rep, "replacement": rep,
                "text": f"{card['base']} is withdrawn on the BIS portal" + (f" — superseded by {es['superseded_by']}." if es.get("superseded_by") else ".")
                        + f" (checked {es.get('fetched')})"}
    if es.get("status") == "Active":
        txt = f"In force: {es['edition_in_force']}{amd_txt}" + (f", reaffirmed {es['reaffirmed']}" if es.get("reaffirmed") else "")
        if es.get("newer_than_archive"):
            txt += f". The archived text analysed here is the {yr} edition — check clause numbers against the {es['year_in_force']} edition"
        return {**common, "level": "warn" if es.get("newer_than_archive") else "ok", "in_force": es["edition_in_force"],
                "title_in_force": es.get("title_in_force"), "text": txt + f". Source: {es.get('source')}, checked {es.get('fetched')}."}
    if rec and rec.status and rec.status.lower() in ("withdrawn", "superseded"):
        return {**common, "level": "bad", "in_force": rec.superseded_by, "replacement": rec.superseded_by,
                "text": f"{rec.is_number} is {rec.status.lower()}" + (f"; use {rec.superseded_by}." if rec.superseded_by else ".")}
    if es.get("status") == "Listed":
        txt = f"BIS catalogue lists {es['edition_in_force']} as the latest edition"
        if es.get("newer_than_archive"):
            txt += f" (archived text: {yr} edition)"
        return {**common, "level": "warn" if es.get("newer_than_archive") else "info", "in_force": es["edition_in_force"],
                "title_in_force": es.get("title_in_force"), "text": txt + f". Status not yet verified on the standard's portal page (catalogue checked {es.get('fetched')})."}
    if rec and rec.year and yr and rec.year > yr:
        return {**common, "level": "warn", "in_force": rec.is_number, "title_in_force": rec.title,
                "text": f"A newer edition, {rec.is_number}, is in force per the registry; the archived text analysed is the {yr} edition."}
    if card.get("superseded_by_raw"):
        return {**common, "level": "warn", "in_force": None, "text": f"Catalogue note: superseded by {card['superseded_by_raw']}."}
    if es.get("status") == "Not listed":
        return {**common, "level": "warn", "in_force": None,
                "text": f"{card['base']} is not listed in the BIS e-Sale catalogue ({es.get('fetched')}) — it may be withdrawn or renumbered; verify before citing."}
    txt = f"Latest edition found: {card['base']}:{yr}" if yr else "Edition year not found"
    return {**common, "level": "info", "in_force": None, "text": txt + ". Confirm the current edition on the BIS portal."}


def _certification(card: dict, kb: KnowledgeBase, today: date) -> list:
    out = []
    for r in get_corpus().certification(card["base"]):
        out.append({"key": None, "type": r["scheme"], "scheme": r["scheme"], "title": r.get("order"), "product": r.get("product"),
                    "in_force": True, "effective_from": None, "verification_state": r.get("verification_state", "official_list"),
                    "source_url": r.get("source_url"), "matched_via": r.get("matched_via")})
    for r in kb.regulations_for_family(card["base"]):
        d = r.to_dict()
        out.append({"key": d["key"], "type": d["regulation_type"], "scheme": d.get("scheme"), "title": d["title"],
                    "in_force": r.in_force(today), "effective_from": d.get("effective_from"), "verification_state": d.get("verification_state"),
                    "source_url": d.get("source_url")})
    return out


@router.get("/corpus/stats", summary="Size and composition of the Indian Standards corpus")
async def stats():
    c = get_corpus()
    return {**c.stats(), "division_list": getattr(c, "divisions", [])}


@router.get("/corpus/search", summary="Search the corpus (BM25 + dense over title and scope clause)")
async def search(q: str = Query(..., min_length=2), k: int = 20):
    return get_corpus().search(q, k)


@router.post("/corpus/recommend", summary="Recommend Indian Standards + allied standards + edition status + certification")
async def recommend(query: str = Body(..., embed=True), top_k: int = Body(5, embed=True), expand: int = Body(3, embed=True),
                    division: Optional[str] = Body(None, embed=True), db: AsyncSession = Depends(get_db)):
    from app.services.multilingual import detect_language, translate_to_english
    c = get_corpus()
    if not c.ready:
        raise HTTPException(503, "Corpus not built — run scripts/corpus_harvest.py, corpus_catalogue.py, corpus_fetch_text.py, corpus_build.py")
    lang = detect_language(query)
    q_en, translated = (query, False)
    reading = []
    if lang != "en":
        q_en, translated = await translate_to_english(query, lang)
        if "(" in q_en:                            # offline reading → expose how each word was read
            from app.services.multilingual import lexicon_translate
            reading = lexicon_translate(query)[1]
    kb = await KnowledgeBase.from_db(db)
    today = date.today()
    import re as _re
    terms = _re.findall(r"\(([^)]+)\)", q_en) if translated else []
    if terms:                                   # dictionary fallback → search with the recognised English terms
        q_en = " ".join(terms + _re.findall(r"[A-Za-z0-9./]+", _re.sub(r"\([^)]*\)", " ", q_en)))
        results = c.search(q_en, top_k, dense_query=query, division=division or None)
    else:
        results = c.search(q_en, top_k, dense_query=query, division=division or None)
    for i, r in enumerate(results):
        r["status"] = _status(r, kb)
        r["certification"] = _certification(r, kb, today)
        if i < expand:
            r["allied"] = c.allied(r["base"])
    return {"query": query, "language": lang, "query_en": q_en, "translated": translated, "reading": reading, "results": results,
            "dense_index": c.emb is not None, "disclaimer": DISCLAIMER}


@router.get("/corpus/standard", summary="One standard: catalogue, scope, allied standards, cited-by, status, certification")
async def standard(base: str = Query(...), db: AsyncSession = Depends(get_db)):
    c = get_corpus()
    card = c.card(base)
    if not card.get("known"):
        raise HTTPException(404, f"{base} is not in the corpus")
    kb = await KnowledgeBase.from_db(db)
    card["status"] = _status(card, kb)
    card["certification"] = _certification(card, kb, date.today())
    card["allied"] = c.allied(base, limit_per_kind=50)
    card["disclaimer"] = DISCLAIMER
    return card


@router.get("/corpus/dependency-tree", summary="Transitive normative-reference closure of a standard (depth 1–4), each edge with its clause")
async def dependency_tree(base: str = Query(...), depth: int = Query(2, ge=1, le=4), normative_only: bool = Query(True)):
    c = get_corpus()
    if base not in c.catalogue:
        raise HTTPException(404, f"{base} is not in the corpus")
    return c.dependency_tree(base, depth, normative_only)


@router.get("/corpus/labs", summary="Testing route: BIS labs and BIS-recognised labs for a standard, with charges (BIS LIMS)")
async def labs(base: str = Query(...), city: Optional[str] = Query(None)):
    c = get_corpus()
    d = c.labs.get(base)
    if not d:
        from app.services.corpus_service import family_of
        fam = [b for b in c.labs if family_of(b) == family_of(base)]
        d = c.labs.get(fam[0]) if fam else None
        if d:
            d = {**d, "matched_via": fam[0]}
    if not d:
        return {"base": base, "count": 0, "labs": [], "note": "No lab listed on BIS LIMS for this standard in our snapshot.", "meta": c.labs_meta}
    rows = d["labs"]
    if city:
        rows = [r for r in rows if (r.get("city") or "").lower().startswith(city.lower()) or city.lower() in r["lab"].lower()]
    return {"base": base, **{k: v for k, v in d.items() if k != "labs"}, "labs": rows, "meta": c.labs_meta,
            "lims_url": "https://lims.bis.gov.in/home/search_is_number/"}


@router.post("/corpus/recommend-document", summary="Upload a tender / specification (PDF, DOCX, TXT, scan) → recommended standards with evidence")
async def recommend_document(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    from app.engine.docparse import parse_document
    from app.services.corpus_service import check_citations, recommend_items
    data = await file.read()
    doc = parse_document(data, file.filename or "document.txt")
    pages = [{"page": p.page_no, "text": p.text, "tables": p.tables} for p in doc.pages]
    out = recommend_items(pages)
    out["citation_check"] = check_citations([{"family": x["base"], "citation": f"{x['base']}:{x['year']}" if x["year"] else x["base"], "body": "BIS"}
                                             for x in out["cited_in_document"]])
    out["document"] = {"filename": file.filename, "pages": doc.page_count, "ocr_pages": doc.ocr_pages, "sha256": doc.sha256}
    out["disclaimer"] = DISCLAIMER
    return out


async def _spec_block(base: str, item: Optional[str], db: AsyncSession) -> dict:
    from app.engine.spec_block import build
    c = get_corpus()
    card = c.card(base)
    if not card.get("known"):
        raise HTTPException(404, f"{base} is not in the corpus")
    kb = await KnowledgeBase.from_db(db)
    status = _status(card, kb)
    replaced_note = None
    if status.get("level") == "bad" and status.get("in_force"):
        from app.engine.std_refs import family_of
        new_base = status["in_force"] if status["in_force"] in c.catalogue else family_of(status["in_force"])
        if new_base in c.catalogue and new_base != base:           # draft for the standard that replaced it
            replaced_note = f"{base} is withdrawn/superseded — this block is drafted for {new_base}."
            base, card = new_base, c.card(new_base)
            status = _status(card, kb)
    if status.get("title_in_force"):
        card = {**card, "title": status["title_in_force"]}          # the edition in force may have a different title
    block = build(card, c.allied(base, limit_per_kind=50), _certification(card, kb, date.today()), status, item, labs=c.labs.get(base))
    if replaced_note:
        block["notes"].insert(0, replaced_note)
        block["replaced"] = replaced_note
    return block


@router.get("/corpus/spec-block", summary="Exportable specification block (ready-to-paste tender clauses with citations)")
async def spec_block(base: str = Query(...), item: Optional[str] = Query(None), db: AsyncSession = Depends(get_db)):
    return await _spec_block(base, item, db)


@router.post("/corpus/spec-block.docx", summary="Several specification blocks as one Word document")
async def spec_block_docx(blocks: list = Body(..., embed=True), title: Optional[str] = Body(None, embed=True), db: AsyncSession = Depends(get_db)):
    from fastapi.responses import Response
    from app.engine.spec_block import to_docx
    built = [await _spec_block(b["base"], b.get("item"), db) for b in blocks[:30]]
    return Response(to_docx(built, title or "Technical specification — Indian Standards"),
                    media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": 'attachment; filename="specification_indian_standards.docx"'})


@router.get("/corpus/evidence", summary="Benchmark + real-tender study results (for the Evidence page)")
async def evidence():
    import json as _json
    import os as _os
    root = _os.path.join(_os.path.dirname(__file__), "..", "..", "data", "evaluation")
    out = {}
    for name in ("corpus_benchmark", "corpus_benchmark_with_aliases", "real_tender_study", "real_tender_spotcheck", "retrieval_ablation"):
        p = _os.path.join(root, name + ".json")
        if _os.path.exists(p):
            out[name] = _json.load(open(p, encoding="utf-8"))
    out["corpus"] = get_corpus().stats()
    return out


_annot_cache: dict = {}


@router.post("/corpus/annotate", summary="Batch check of short item texts (e.g. GeM category names): cited IS status, or a suggested IS")
async def annotate(texts: list = Body(..., embed=True), db: AsyncSession = Depends(get_db)):
    """Used by the browser extension to annotate bid listings: for every text, the Indian Standards it names (with
    edition status, amendments and compulsory certification) — or, when it names none, SpecSure's suggestion with a
    confidence level (abstaining when not confident)."""
    import re as _re
    from app.engine.corpus_parse import citations as find_cites, normalise
    c = get_corpus()
    kb = await KnowledgeBase.from_db(db)
    today = date.today()
    out = []
    for t in texts[:60]:
        t = (t or "").strip()[:400]
        if t in _annot_cache:
            out.append(_annot_cache[t])
            continue
        norm = normalise(_re.sub(r"\bSection\b", "Sec", t, flags=_re.I))
        cited = []
        hits = find_cites(norm, set(c.catalogue))
        if not hits:                            # "IS 550" named without part while the catalogue holds its parts
            for m in _re.finditer(r"\bIS\s*[:/]?\s*(\d{2,5})\b(?!\s*\()", norm):
                parts = [b for b in c.catalogue if b.startswith(f"IS {int(m.group(1))} (Part ")]
                hits += [{"base": b, "year": None} for b in sorted(parts)[:1]]
        for x in hits:
            card = c.card(x["base"])
            st = _status(card, kb)
            cited.append({"base": x["base"], "title": card.get("title"), "year": x.get("year"), "status": {k: st.get(k) for k in ("level", "text", "in_force", "replacement")},
                          "amendments": st.get("amendments"), "certification": [{"scheme": r["scheme"], "title": r["title"]} for r in _certification(card, kb, today)][:2]})
        suggestion = None
        if not cited:
            q = _re.sub(r"\((?:V\d+|Q\d+)\)|\b(?:ISI\s+Marked\s+)?(?:to|as per|conforming to)?\s*IS\s*[:/]?\s*\d{2,5}.*$", "", t, flags=_re.I).strip() or t
            res = c.search(q, 3)
            if res and res[0]["confidence"] in ("high", "medium"):
                r0 = res[0]
                st = _status(r0, kb)
                suggestion = {"base": r0["base"], "title": r0["title"], "confidence": r0["confidence"],
                              "status": {k: st.get(k) for k in ("level", "text", "in_force")},
                              "certification": [{"scheme": r["scheme"], "title": r["title"]} for r in _certification(r0, kb, today)][:2],
                              "alternatives": [{"base": r["base"], "title": r["title"], "confidence": r["confidence"]} for r in res[1:3]]}
        row = {"text": t, "cited": cited, "suggestion": suggestion}
        if len(_annot_cache) > 5000:
            _annot_cache.clear()
        _annot_cache[t] = row
        out.append(row)
    return {"results": out, "disclaimer": DISCLAIMER}
