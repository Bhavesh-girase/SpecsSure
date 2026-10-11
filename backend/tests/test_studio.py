"""Tender Studio (intent → verified tender), Procurement Knowledge Graph, Smart Bid Form and OCR repair."""
import json
from datetime import date

import pytest

from conftest import read


# ------------------------------------------------------------------ intent parsing
@pytest.mark.parametrize("text,expect", [
    ("need a tender 0f 500 light bulbs and 100 meteres", [("led_lamp", 500, "nos"), ("pvc_cable", 100, "m")]),
    ("500 LED bulb 9 watt aur 100 meter 2.5 sq mm taar chahiye, 30 din mein, budget 2 lakh", [("led_lamp", 500, "nos"), ("pvc_cable", 100, "m")]),
    ("पाँच सौ बल्ब और सौ मीटर तार", [("led_lamp", 500, "nos"), ("pvc_cable", 100, "m")]),
    ("Need 400 bags of 53 grade cement and 5 tonnes Fe 500D TMT 8mm 12mm 16mm", [("opc_cement", 20, "MT"), ("tmt_steel", 5, "MT")]),
    ("2 coils of 4 sq mm FRLS copper wire", [("pvc_cable", 180, "m")]),
])
def test_intent_parse(text, expect):
    from app.engine.intent import parse
    r = parse(text)
    got = [(l["item_id"], l["quantity"], l["unit"]) for l in r["line_items"]]
    assert got == [(i, float(q), u) for i, q, u in expect]


def test_intent_asks_only_what_matters():
    from app.engine.intent import apply_answers, parse
    r = parse("need a tender of 500 light bulbs and 100 meteres")
    ids = {q["id"] for q in r["questions"]}
    assert "L2.item" in ids                                  # "100 metres of what?"
    q = next(q for q in r["questions"] if q["id"] == "L2.item")
    assert q["default"] == "pvc_cable" and "often bought with" in q["options"][0]["why"]
    assert "L1.rated_power" in ids and "L1.efficacy" not in ids   # practice defaults are not asked
    r2 = parse("500 LED bulb 9 watt aur 100 meter 2.5 sq mm taar, 30 din mein, budget 2 lakh")
    assert r2["globals"] == {"budget_inr": 200000.0, "delivery_days": 30}
    assert r2["line_items"][0]["slots"]["rated_power"] == 9.0 and r2["line_items"][1]["slots"]["conductor_area"] == 2.5
    done = apply_answers(r, {"L2.item": "pvc_cable"})
    assert done["complete"]


# ------------------------------------------------------------------ knowledge graph
def test_kg_temporal_edition_and_watchlist(kb):
    from app.engine.kg import get_kg
    kg = get_kg(kb)
    s = kg.stats()
    assert s["node_types"]["item"] >= 8 and s["edge_types"]["MANDATES"] > 0
    b = kg.bundle("led_lamp", date(2026, 9, 25))
    p1 = next(x for x in b["standards"] if x["designation"] == "IS 16102 (Part 1)")
    assert p1["cite_as"] == "IS 16102 (Part 1):2026" and not p1["concurrent_editions"]
    assert {g["key"] for g in b["regulations_in_force"]} >= {"CRS-MEITY", "BEE-SL-LED"}
    early = kg.bundle("led_lamp", date(2026, 6, 1))
    assert any(w["type"] == "edition_withdrawal" and w["subject"] == "IS 16102 (Part 1):2012" for w in early["watchlist"])
    solar = kg.bundle("solar_pv_module", date(2026, 9, 25), horizon_days=240)
    assert "ALMM-LIST-II" in {g["key"] for g in solar["regulations_in_force"]}
    assert any(w["subject"] == "IS/IEC 61730-1:2016" for w in solar["watchlist"])
    assert "item:pvc_cable" in kg.impacted_items("reg:QCO-CABLES")
    assert kg.explain_path("item:pvc_cable", "reg:QCO-CABLES")
    assert "MERGE" in kg.export_cypher()[:400]


# ------------------------------------------------------------------ synthesis
@pytest.mark.parametrize("text,answers", [
    ("need a tender of 500 light bulbs and 100 meteres", {"L2.item": "pvc_cable"}),
    ("Need 400 bags of 53 grade cement and 5 tonnes Fe 500D TMT 8mm 12mm 16mm", {}),
    ("120 solar panels 540Wp for school rooftop, budget 20 lakh", {}),
    ("need 30 street lights 90W IP66", {}),
    ("20 ceiling fans 1200mm, 50 MCB 16A C curve", {}),
])
def test_generated_tenders_pass_their_own_compiler(kb, text, answers):
    from app.engine.intent import apply_answers, parse
    from app.engine.synthesizer import synthesize
    g = synthesize(apply_answers(parse(text), answers), kb, date(2026, 9, 25), {"organisation": "Demo Dept"})
    final = g["verification"]["final"]
    assert final["counts"]["critical"] == 0 and final["counts"]["major"] == 0, g["verification"]["open_findings"]
    assert final["gate"] == "READY"
    for s in g["sections"]:
        for c in s["clauses"]:
            assert c["basis"] in ("standard", "regulation", "buyer", "buyer_default", "practice", "policy", "repair")
    # every standard cited in the text is the edition in force
    assert "IS 16102 (Part 1):2012" not in g["text"]


def test_competition_guard_and_buyer_choice_warning(kb):
    from app.engine.intent import parse
    from app.engine.synthesizer import synthesize, competition
    g = synthesize(parse("20 ceiling fans 1200mm 5 star"), kb, date(2026, 9, 25), {})
    comp = g["lines"][0]["competition"]
    assert not comp["ok"] and "binding constraint" in comp["warning"]      # stated choice is never silently changed
    assert g["lines"][0]["slots"]["star_rating"] == 5
    c = competition("led_lamp", {"efficacy": 125, "rated_power": 9})
    assert c["available"] and c["eligible_manufacturers"] < c["licensed_manufacturers"]


def test_docx_export(kb):
    from app.engine.intent import parse
    from app.engine.synthesizer import synthesize, to_docx
    g = synthesize(parse("500 LED bulbs 9 watt B22"), kb, date(2026, 9, 25), {})
    assert to_docx(g)[:2] == b"PK"


# ------------------------------------------------------------------ bid form & match index
def test_bid_form_scoring(kb):
    from app.engine.bidform import autofill, derive_form, infer_scope, score
    from app.engine.compiler import compile_ir
    from app.engine.docparse import parse_document, parse_text
    from app.engine.evidence import extract_evidence
    from app.engine.intent import parse
    from app.engine.synthesizer import synthesize
    from app.engine.tender_ir import build_ir
    g = synthesize(parse("500 LED bulbs 9 watt B22 and 100 metres 1.5 sq mm FR copper wire within 30 days"), kb, date(2026, 9, 25), {})
    tw = compile_ir(build_ir(parse_text(g["text"], "g.txt")), kb)
    form = derive_form(tw)
    assert {f["type"] for f in form["fields"]} >= {"certificate", "number", "standard", "test_report", "declaration"}
    good = [extract_evidence(parse_document(read(f"bidder/led/{n}"), n)) for n in ("registration_jyoti_led.txt", "datasheet_jyoti_led.txt")]
    bad = [extract_evidence(parse_document(read(f"bidder/led/{n}"), n)) for n in ("registration_chandni_led.txt", "datasheet_chandni_led.txt")]
    ga, ba = autofill(form, good), autofill(form, bad)
    for a in (ga, ba):
        for f in form["fields"]:
            if f["type"] == "declaration":
                a[f["id"]] = {"accepted": True}
    sg = score(form, ga, date(2026, 9, 25), infer_scope(form, good))
    sb = score(form, ba, date(2026, 9, 25), infer_scope(form, bad))
    assert sg["knockouts"] == 0 and sb["knockouts"] >= 2 and sb["match_index"] <= 49 < sg["match_index"]
    assert any(p["kind"] == "substantive" and "Renew" in p["action"] for p in sb["path_to_compliance"])
    # declared value contradicting the document is a conflict
    ga2 = json.loads(json.dumps(ga))
    eff = next(f["id"] for f in form["fields"] if f.get("parameter") == "luminous_efficacy")
    ga2[eff]["value"] = 130
    assert next(r for r in score(form, ga2, date(2026, 9, 25), ["lighting"])["results"] if r["field_id"] == eff)["status"] == "CONFLICT"


# ------------------------------------------------------------------ OCR
def test_ocr_domain_repair():
    from app.engine.ocr import repair
    t, log = repair("Efficacy 1l0 Im/W; yield 5OO N/rnm2 as per IS l786; licence CML - 123")
    assert "110 lm/W" in t and "500 N/mm2" in t and "IS 1786" in t and "CM/L-123" in t
    assert len(log) >= 5


def test_ocr_scanned_report():
    pytest.importorskip("rapidocr")
    from app.engine.docparse import parse_document
    from app.engine.evidence import extract_evidence
    p = parse_document(read("bidder/led/test_report_scan_jyoti_led.png"), "scan.png")
    e = extract_evidence(p)
    vals = {i["parameter"]: i["value"] for i in e["items"] if i["kind"] == "parameter"}
    assert vals.get("luminous_efficacy") == 112 and vals.get("power_factor") == 0.94
    assert e["meta"]["nabl_certificate"] == "TC-DEMO-0808" and p.meta()["ocr"][0]["mean_conf"] > 0.85


# ------------------------------------------------------------------ API
@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c


def test_studio_and_marketplace_api(client):
    B = "/api/v1"
    p = client.post(f"{B}/studio/parse", json={"text": "need a tender of 500 light bulbs and 100 meteres"}).json()
    assert len(p["line_items"]) == 2
    g = client.post(f"{B}/studio/generate", json={"intent": p, "answers": {"L2.item": "pvc_cable"}, "as_of": "2026-09-25"}).json()
    assert g["verification"]["final"]["gate"] == "READY"
    s = client.post(f"{B}/studio/save", json={"intent": p, "answers": {"L2.item": "pvc_cable"}, "as_of": "2026-09-25", "publish": True}).json()
    assert s["status"] == "published"
    tid = s["tender_id"]
    assert client.get(f"{B}/tenders/{tid}/generation").json()["verification"]["passes"]
    assert client.get(f"{B}/tenders/{tid}/generated.docx").content[:2] == b"PK"
    assert any(t["id"] == tid for t in client.get(f"{B}/market/tenders").json())
    form = client.get(f"{B}/tenders/{tid}/bid-form").json()
    assert form["field_count"] > 10
    sc = client.post(f"{B}/tenders/{tid}/bid-form/score", json={"answers": {}}).json()
    assert sc["tier"] == "NON_RESPONSIVE"          # nothing answered → licence missing is a knock-out
    files = [("files", ("registration_jyoti_led.txt", read("bidder/led/registration_jyoti_led.txt"))),
             ("files", ("datasheet_jyoti_led.txt", read("bidder/led/datasheet_jyoti_led.txt")))]
    af = client.post(f"{B}/tenders/{tid}/bid-form/autofill", files=files).json()
    assert af["scope"] == ["lighting"] and af["answers"]
    sub = client.post(f"{B}/tenders/{tid}/bid-form/submit", data={"bidder": "Test Bidder", "answers": json.dumps(af["answers"]), "scope": "lighting"},
                      files=files).json()
    assert sub["bid_id"] and sub["match_index"] > 0
    comp = client.get(f"{B}/tenders/{tid}/comparative").json()
    assert comp["bidders"][0]["bidder"] == "Test Bidder"
    assert client.get(f"{B}/kg/stats").json()["nodes"] > 100
    assert client.get(f"{B}/kg/items/led_lamp").json()["standards"]
    assert client.get(f"{B}/kg/node", params={"id": "item:led_lamp"}).json()["graph"]["nodes"]
    d = client.get(f"{B}/demo").json()
    assert d["studio_tender_id"]
    demo_comp = client.get(f"{B}/tenders/{d['studio_tender_id']}/comparative").json()
    assert len(demo_comp["bidders"]) == 3 and demo_comp["bidders"][0]["knockouts"] == 0
