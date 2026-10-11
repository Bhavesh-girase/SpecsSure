"""Indian Standards corpus: parser, certification layer and recommender API."""
import os

import pytest

from app.engine.corpus_parse import citations, kind_from_title, parse, scope_clause

IS694_EXCERPT = """
Indian Standard POLYVINYL CHLORIDE INSULATED UNSHEATHED AND SHEATHED CABLES/CORDS WITH RIGID AND FLEXIBLE CONDUCTOR
FOR RATED VOLTAGES UP TO AND INCLUDING 450/750 V ( Fourth Revision )
FOREWORD While formulating this standard, assistance has been drawn from IEC 60227-1 (2007-10). This standard supersedes IS 3035 (Part 1) : 1965.
1 GENERAL 1.1 Scope This standard covers general requirements of single and multicore cables/cords with rigid as well as flexible
annealed copper conductor insulated with polyvinyl chloride (PVC) for rated voltages up to and including 450/750 V.
2 REFERENCES The standards given below contain provisions which, through reference in this text, constitute provisions of this
standard. IS No. 1885 (Part 32) : 1993 4905 : 1968 5831 : 1984 Title Electrotechnical vocabulary 8130 : 1984 Conductors
10810 Methods of test for cables: (Part 0) : 1984 General (Part 1) : 1984 Annealing test
3 TERMINOLOGY For the purpose of this standard, the definitions given in 18:1885 (Part 32) shall apply.
4.2 The resistance of each conductor shall be in accordance with IS 8130, tested as per IS 10810 (Part 5).
"""
KNOWN = {"IS 1885 (Part 32)", "IS 4905", "IS 5831", "IS 8130", "IS 10810 (Part 0)", "IS 10810 (Part 1)", "IS 10810 (Part 5)", "IS 3035 (Part 1)", "IS 694"}


def test_parse_is694_excerpt():
    p = parse(IS694_EXCERPT, KNOWN, "IS 694")
    assert p["scope"].startswith("This standard covers general requirements")
    assert p["revision"] == "Fourth"
    refs = {r["base"]: r for r in p["relations"]}
    for b in ("IS 1885 (Part 32)", "IS 4905", "IS 5831", "IS 8130", "IS 10810 (Part 0)", "IS 10810 (Part 1)"):
        assert "references" in refs[b]["clauses"], b
    assert "terminology" in refs["IS 1885 (Part 32)"]["clauses"]          # OCR "18:1885" repaired
    assert "IS 10810 (Part 5)" in refs and "IS 694" not in refs
    assert any(e["standard"].startswith("IEC 60227") and e["degree"] == "derived from" for e in p["equivalents"])


def test_citation_formats_and_kinds():
    c = {x["base"] for x in citations("see IS 10322 (Part 5/Section 3) : 2012 and IS/IEC 62368: Part 1: 2023", None)}
    assert "IS 10322 (Part 5/Sec 3)" in c and "IS/IEC 62368 (Part 1)" in c
    assert kind_from_title("Methods of test for cables, Part 5: Conductor resistance test") == "test_method"
    assert kind_from_title("Electrotechnical Vocabulary, Part 32") == "terminology"
    assert kind_from_title("Methods for random sampling") == "sampling"
    assert kind_from_title("Portland Slag Cement - Specification") == "allied_product"
    assert scope_clause("1. Scope — Covers the test procedure to determine the flexibility of flexible cable. 2. Significance — x") \
        .startswith("Covers the test procedure")


CORPUS = os.path.join(os.path.dirname(__file__), "..", "data", "corpus", "is_catalogue.jsonl.gz")


@pytest.mark.skipif(not os.path.exists(CORPUS), reason="corpus not built")
def test_recommender_api():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as client:
        s = client.get("/api/v1/corpus/stats").json()
        assert s["designations"] > 15000
        r = client.post("/api/v1/corpus/recommend", json={"query": "helmet for two wheeler riders", "top_k": 5}).json()
        top = r["results"][0]
        assert top["base"] == "IS 4151"
        assert any("Helmet" in (c.get("title") or "") or c["scheme"].startswith("Scheme-I") for c in top["certification"])
        d = client.get("/api/v1/corpus/standard", params={"base": "IS 694"}).json()
        assert d["title"].upper().startswith("POLYVINYL CHLORIDE")
        assert any(c["scheme"].startswith("Scheme-I") for c in d["certification"])


def test_item_extraction_from_tables_and_lines():
    from app.engine.tender_items import extract_items, split_products
    pages = [{"page": 3, "text": "1.1 Name of Work: Supply of Cement and TMT Reinforcement Steel for Construction of G+3 PHC\n", "tables": [
        [["Sl No.", "Details / Particulars", "Uploaded (Yes/No)"], ["A", "PAN No. (enclose copy)", ""], ["B", "Whether you have trained staff?", ""]],
        [["Item No.", "Description", "Qty.", "EMD (Rs.)"], ["1.", "Intraoral scanner", "01 No.", "Rs. 45,000/-"], ["2.", "Steel almirah with 4 shelves", "10 Nos", ""]],
    ]}]
    items = [i["text"] for i in extract_items(pages)]
    assert "Intraoral scanner" in items and "Steel almirah with 4 shelves" in items
    assert not any("PAN" in i or "Whether" in i for i in items)            # document checklists are not items
    assert split_products("Cement and TMT Reinforcement Steel for Construction of G+3 PHC") == ["Cement", "TMT Reinforcement Steel"]


def test_confidence_rules():
    from app.services.corpus_service import confidence
    assert confidence({"alias": "exact:gi pipe"}) == "high"
    assert confidence({"lex_rank": 0, "dense_rank": 1, "dense_available": True, "coverage": 1.0}) == "high"
    assert confidence({"lex_rank": 30, "dense_rank": 40, "dense_available": True, "coverage": 0.25}) == "low"


@pytest.mark.skipif(not os.path.exists(CORPUS), reason="corpus not built")
def test_spec_block_and_document_items():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as client:
        b = client.get("/api/v1/corpus/spec-block", params={"base": "IS 694", "item": "house wiring cable"}).json()
        heads = [c["heading"] for c in b["clauses"]]
        assert heads[0] == "Standard" and "Mandatory certification" in heads and "IS 8130" in b["text"]
        w = client.get("/api/v1/corpus/spec-block", params={"base": "IS 8112"}).json()
        assert w["edition"].startswith("IS 269") and "withdrawn" in w["replaced"]
        d = client.post("/api/v1/corpus/spec-block.docx", json={"blocks": [{"base": "IS 694"}]})
        assert d.content[:2] == b"PK"
        demo = os.path.join(os.path.dirname(__file__), "..", "data", "demo", "tender_led_streetlight.txt")
        r = client.post("/api/v1/corpus/recommend-document", files={"file": ("t.txt", open(demo, "rb").read())}).json()
        assert r["items"] and r["items"][0]["status"] == "recommended"
        assert r["items"][0]["candidates"][0]["base"].startswith(("IS 16107", "IS 10322"))


def test_portal_designations_and_relation_kinds():
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
    from bis_portal_catalogue import norm_designation
    from bis_portal_status import parse_entries
    from app.engine.corpus_parse import relation_kind
    assert norm_designation("IS 10322 : Part 5 : Sec 3") == ("IS 10322 (Part 5/Sec 3)", None)
    assert norm_designation("IS 6192 (Active,Concurrent Running)") == ("IS 6192", "concurrent")
    assert norm_designation("IS/IEC 60947 : PART 1")[0] == "IS/IEC 60947 (Part 1)"
    ents = parse_entries("You Searched for - is 8112 1 IS 8112 : 2013 Ordinary Portland Cement, 43 Grade Technical Committee : CED 2 "
                         "Superseeded by : IS 269 : 2015 Status : withdrawn No. of Amendments : 9 2 IS 18112 : 2025 Digital Television "
                         "Receiver Technical Committee : LITD 07 Status : Active No. of Amendments : 1 Login to Download Custcode")
    assert ents[0]["des"] == "IS 8112" and ents[0]["status"] == "withdrawn" and ents[0]["superseded_by"] == "IS 269 : 2015"
    assert ents[1]["des"] == "IS 18112" and ents[1]["status"] == "Active"
    assert relation_kind("Metallic Materials - Bend Test") == "test_method"
    assert relation_kind("Rolling and cutting tolerances for hot rolled steel products") == "dimensions"


def test_gem_item_named_standard():
    from app.engine.tender_items import extract_items
    pages = [{"page": 1, "text": "Bid Number: GEM/2026/B/8030166\nBid Details\nItem Category\nPortable Fire Extinguishers (V3) ISI Marked to IS 15683 (Q2)\nMSE Relaxation", "tables": []},
             {"page": 5, "text": "Portable Fire Extinguishers (V3) ISI Marked To IS 15683 ( 223 pieces ) \nBis Required\nYes", "tables": []}]
    items = extract_items(pages)
    assert len(items) == 1 and items[0]["qty"] == "223 pieces" and "IS 15683" in items[0]["text"]


@pytest.mark.skipif(not os.path.exists(os.path.join(os.path.dirname(__file__), "..", "data", "corpus", "bis_status.json")), reason="portal data not built")
def test_edition_status_tree_and_annotate():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services.corpus_service import get_corpus
    c = get_corpus()
    es = c.edition_status("IS 8112")
    assert es["status"] == "Withdrawn" and es["replacement"] == "IS 269"
    t = c.dependency_tree("IS 1786", 2)
    assert t["counts"]["nodes"] > t["counts"]["by_depth"].get(1, 0) > 0
    assert any(n["base"] == "IS 1608" for n in t["nodes"])             # tensile test reached through the references
    with TestClient(app) as cl:
        r = cl.post("/api/v1/corpus/annotate", json={"texts": ["Portable Fire Extinguishers (V3) ISI Marked to IS 15683", "Safes (V3) ISI Marked to IS 550"]}).json()
        a, b = r["results"]
        assert a["cited"][0]["base"] == "IS 15683" and a["cited"][0]["certification"]
        assert b["cited"][0]["base"].startswith("IS 550 (Part")
        blk = cl.get("/api/v1/corpus/spec-block", params={"base": "IS 13849"}).json()
        assert blk.get("replaced") and "IS 15683" in blk["text"]


@pytest.mark.skipif(not os.path.exists(os.path.join(os.path.dirname(__file__), "..", "data", "corpus", "bis_labs.json")), reason="lab data not built")
def test_labs_and_catalogue_status():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services.corpus_service import get_corpus
    c = get_corpus()
    assert c.edition_status("IS 10005")["status"] == "Withdrawn"          # from the BIS Know-Your-Standards catalogue
    with TestClient(app) as cl:
        r = cl.get("/api/v1/corpus/labs", params={"base": "IS 694", "city": "Delhi"}).json()
        assert r["count"] > 10 and r["labs"] and all("delhi" in ((l["city"] or "") + " " + l["lab"]).lower() for l in r["labs"])
        assert r["labs"][0]["charges_total"] <= r["labs"][-1]["charges_total"]
