"""Tender lifecycle: sealed financial bids, Make in India / MSE preference, queries, advice, award, dashboards."""
import pytest

from app.engine.evaluation import commitment, evaluate

TWIN = {"tender": {"domains": ["lighting"]}}
GEN = {"lines": [{"index": 1, "item_id": "led_lamp", "item_label": "LED lamp", "quantity": 6000, "unit": "nos"}]}


def _bid(i, name, price, mse=False, cls="non-local", knock=0):
    fin = {"lines": {"1": {"unit_price": price}}}
    res = [{"knockout": True, "group": "lighting", "label": "Efficacy", "clause_key": "3.3", "detail": "below minimum"}] if knock else []
    return {"bid_id": f"b{i}", "bidder": name, "score": {"results": res, "match_index": 90}, "scope": ["lighting"], "financial": fin,
            "declarations": {"mse": mse, "mii_class": cls}, "commitment": commitment(f"b{i}", fin, "s"), "salt": "s"}


def test_mii_then_mse_allocation():
    ev = evaluate(TWIN, GEN, [_bid(1, "A", 72, cls="II"), _bid(2, "B", 79, mse=True, cls="I"), _bid(3, "C", 58, knock=1)], estimated_value=600000)
    ln = ev["lines"][0]
    assert ev["mii_applicable"] and ln["l1"]["bidder"] == "A"
    alloc = {a["bidder"]: a["quantity"] for a in ln["allocation"]}
    assert alloc == {"A": 3000, "B": 3000}                       # divisible item: 50 % to the Class-I bidder matching L1
    assert all(a["unit_price"] == 72 for a in ln["allocation"])
    assert ev["recommended_contract_value"] == 432000
    assert all(i["verified"] for i in ev["integrity"])


def test_mse_only_and_exemption():
    small = {"lines": [{**GEN["lines"][0], "quantity": 100}]}
    ev = evaluate(TWIN, small, [_bid(1, "A", 72), _bid(2, "M", 80, mse=True)])
    assert not ev["mii_applicable"]                              # below ₹5 lakh
    alloc = {a["bidder"]: a["quantity"] for a in ev["lines"][0]["allocation"]}
    assert alloc == {"A": 75, "M": 25}                           # MSE within L1+15 % gets 25 % at L1


def test_tampered_price_is_detected_and_sealed_view_hides_prices():
    b = _bid(1, "A", 72)
    b["financial"] = {"lines": {"1": {"unit_price": 60}}}       # changed after sealing
    ev = evaluate(TWIN, GEN, [b])
    assert ev["integrity"][0]["verified"] is False
    sealed = evaluate(TWIN, GEN, [_bid(1, "A", 72)], financial_open=False)
    assert sealed["lines"][0]["bids"][0]["unit_price"] is None and sealed["recommended_contract_value"] is None


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c


def test_lifecycle_api(client):
    B = "/api/v1"
    tid = client.get(f"{B}/demo").json()["studio_tender_id"]
    ev = client.get(f"{B}/tenders/{tid}/evaluation").json()
    assert ev["financial_open"] is False and ev["bids_received"] == 3
    q = client.post(f"{B}/tenders/{tid}/queries", json={"bidder": "Harit", "question": "Is a BEE 3 star label acceptable for the LED lamps under clause 3.7?"}).json()
    assert q["clause_key"] == "3.7" and q["draft_response"]
    dup = client.post(f"{B}/tenders/{tid}/queries", json={"bidder": "Other", "question": "Is BEE 3 star label acceptable for LED lamps under clause 3.7"}).json()
    assert dup["duplicate_of"] == q["qid"]
    assert client.get(f"{B}/tenders/{tid}/queries", params={"public": True}).json() == []
    client.post(f"{B}/tenders/{tid}/queries/{q['qid']}/answer", json={"response": "Yes, not less than 3 star.", "status": "published"})
    pub = client.get(f"{B}/tenders/{tid}/queries", params={"public": True}).json()
    assert len(pub) == 1 and "from" not in pub[0]
    adv = client.post(f"{B}/tenders/{tid}/bid-form/advice", json={"answers": {}, "scope": ["lighting"]}).json()
    assert adv["verdict"] and adv["plan"]
    assert client.post(f"{B}/tenders/{tid}/award", json={"officer": "o"}).status_code == 409
    ev = client.post(f"{B}/tenders/{tid}/open-financial", json={"officer": "TEC"}).json()
    led = next(l for l in ev["lines"] if l["item_id"] == "led_lamp")
    assert {a["bidder"].split(" ")[0] for a in led["allocation"]} == {"Gyan", "Harit"}
    assert all(i["verified"] for i in ev["integrity"])
    ev = client.post(f"{B}/tenders/{tid}/award", json={"officer": "TEC", "remarks": "as proposed"}).json()
    assert ev["stage"] == "awarded" and ev["award"]["contract_value"] == 432000
    assert client.get(f"{B}/tenders/{tid}/evaluation/report.pdf").content[:4] == b"%PDF"
    assert client.post(f"{B}/tenders/{tid}/bid-form/submit", data={"bidder": "late"}).status_code == 409
    o = client.get(f"{B}/dashboard/officer").json()
    assert o["counts"]["awarded"] >= 1
    k = client.get(f"{B}/dashboard/contractor", params={"bidder": "Harit Lighting Udyog (fictional)"}).json()
    assert k["bids"][0]["result"] == "awarded"
    assert client.get(f"{B}/stats").json()["kg_nodes"] > 100
