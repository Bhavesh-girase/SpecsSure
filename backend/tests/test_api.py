"""End-to-end API tests (SQLite, offline models, demo seed)."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from app.main import app
    with TestClient(app) as c:
        yield c


def test_health_and_demo(client):
    assert client.get("/api/v1/health").json()["status"] == "ok"
    d = client.get("/api/v1/demo").json()
    assert d["tender_id"] and d["bid_id"]


def test_full_buyer_flow(client):
    d = client.get("/api/v1/demo").json()
    tid = d["tender_id"]
    tw = client.get(f"/api/v1/tenders/{tid}").json()["twin"]
    assert tw["readiness"]["gate"] == "BLOCKED" and tw["prebid"]
    fp = next(f["fingerprint"] for f in tw["findings"] if f["rule_id"] == "SS-AMB-001" and f["clause_key"] == "4.1")
    assert client.patch(f"/api/v1/tenders/{tid}/findings/{fp}", json={"review_status": "dismissed"}).status_code == 400
    r = client.patch(f"/api/v1/tenders/{tid}/findings/{fp}", json={"review_status": "dismissed", "comment": "Adjective is harmless here", "reviewer": "EE"})
    assert r.status_code == 200
    assert client.patch(f"/api/v1/tenders/{tid}", json={"status": "published"}).status_code == 409
    c1 = client.post(f"/api/v1/demo/tenders/{tid}/corrigendum/1").json()
    assert c1["delta"]["resolved"]
    again = client.get(f"/api/v1/tenders/{tid}").json()["twin"]
    assert next(f for f in again["findings"] if f["fingerprint"] == fp)["review_status"] == "dismissed"
    assert client.get(f"/api/v1/tenders/{tid}/clauses/4.3/history").json()["latest"]["change"] == "modified"
    assert client.get(f"/api/v1/tenders/{tid}/sarif").json()["version"] == "2.1.0"
    assert client.get(f"/api/v1/tenders/{tid}/export/report.pdf").content[:4] == b"%PDF"
    x = client.get(f"/api/v1/tenders/{tid}/export/findings.xlsx")
    assert x.status_code == 200 and x.content[:2] == b"PK"
    fps = [f["fingerprint"] for f in again["findings"] if f.get("fix") and f["rule_id"] == "SS-STD-003"]
    af = client.post(f"/api/v1/tenders/{tid}/autofix", json={"fingerprints": fps, "apply": True}).json()
    assert af["applied"] and not any(f["rule_id"] == "SS-STD-003" for f in client.get(f"/api/v1/tenders/{tid}").json()["twin"]["findings"])


def test_create_tender_from_text(client):
    r = client.post("/api/v1/tenders", data={"title": "Quick test", "text": "4.1 Material: Cement shall be OPC 43 grade of high quality as per IS codes. Delivery within 7 days."})
    assert r.status_code == 200 and r.json()["findings"] > 0


def test_bidder_flow_and_passport(client):
    d = client.get("/api/v1/demo").json()
    b = client.get(f"/api/v1/bids/{d['bid_id']}").json()
    assert b["result"]["rows"]
    p = client.post(f"/api/v1/bids/{d['bid_id']}/passport").json()
    assert p["verification"]["verified"]
    assert client.post("/api/v1/passports/verify", json=p["credential"]).json()["verified"]
    z = client.get(f"/api/v1/bids/{d['bid_id']}/export/evidence-package.zip")
    assert z.status_code == 200 and z.content[:2] == b"PK"


def test_bid_upload(client):
    d = client.get("/api/v1/demo").json()
    files = [("files", ("ds.txt", b"PRODUCT DATASHEET\n| Carbon | 0.15 % |\n| 0.2% Proof Stress | 560 N/mm2 (min) |", "text/plain"))]
    r = client.post("/api/v1/bids", data={"bidder": "X", "tender_id": d["tender_id"]}, files=files)
    assert r.status_code == 200 and r.json()["result"]["rows"]


def test_radar_revalidation(client):
    s = client.post("/api/v1/radar/simulate/amendment_is1786").json()
    assert s["affected_tenders"]
    assert client.get("/api/v1/notifications").json()
    assert client.get("/api/v1/radar/impact", params={"standard": "IS 1608 (Part 1):2018"}).json()["affected"]


def test_intel_endpoints(client):
    assert client.get("/api/v1/temporal/resolve", params={"citation": "IS 8112:1989", "as_of": "2026-10-01"}).json()["status"] == "withdrawn"
    assert client.get("/api/v1/equivalence", params={"a": "IS 269", "b": "EN 197-1", "grade_a": "43"}).json()["parameters"]
    assert len(client.get("/api/v1/rules").json()) >= 30
    assert client.post("/api/v1/lint", json={"text": "Bars shall conform to IS 1786 and yield stress shall not exceed 480 N/mm2 and yield stress shall not be less than 500 N/mm2."}).json()["verification"]["satisfiable"] is False
    assert client.get("/api/v1/memory/search", params={"q": "carbon content 0.18%"}).json()["clause_precedents"]


def test_ledger_integrity(client):
    v = client.get("/api/v1/ledger/verify").json()
    assert v["valid"] and v["entries"] > 5


def test_legacy_analyze_still_works(client):
    r = client.post("/api/v1/analyze", data={"text": "Supply of TMT bars Fe 500D conforming to IS 1786 for RCC work"})
    assert r.status_code == 200
    body = r.json()
    assert body["recommended_standards"]
    ex = body["recommended_standards"][0]["explanation"]
    assert not (ex["semantic_score"] == 0.88 and ex["keyword_score"] == 0.85)   # provenance must be real, not constants
    assert client.get(f"/api/v1/analyze/{body['analysis_id']}").json()["analysis_id"] == body["analysis_id"]
