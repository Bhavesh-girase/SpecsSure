"""
Product Compliance Passport as a W3C Verifiable Credential (VC Data Model 2.0).

The passport binds a product to: applicable standards, certification (licence) status, test results
with lab/accreditation, tender linkage, deviation history and a hashed evidence bundle. It is signed
with an Ed25519 Data Integrity proof following the `eddsa-jcs-2022` cryptosuite (W3C Data Integrity
EdDSA Cryptosuites v1.0): proofValue = Ed25519( SHA-256(JCS(proofConfig)) || SHA-256(JCS(document)) ),
multibase base58-btc encoded. The issuer is a `did:key`, so anyone can verify the passport offline —
no call to SpecSure is required. Aligned in spirit with the EU Digital Product Passport.

This demo issuer is *not* an official authority; in production the signing key would belong to BIS /
the procuring entity / an accredited certification body.
"""
from __future__ import annotations

import base64
import hashlib
import io
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

from app.engine.ledger import jcs

_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
KEY_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "var", "keys"))


def b58encode(b: bytes) -> str:
    n = int.from_bytes(b, "big")
    out = ""
    while n > 0:
        n, r = divmod(n, 58)
        out = _B58[r] + out
    pad = len(b) - len(b.lstrip(b"\0"))
    return "1" * pad + out


def b58decode(s: str) -> bytes:
    n = 0
    for ch in s:
        n = n * 58 + _B58.index(ch)
    full = n.to_bytes((n.bit_length() + 7) // 8, "big") if n else b""
    pad = len(s) - len(s.lstrip("1"))
    return b"\0" * pad + full


def _load_or_create_key():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization

    env = os.getenv("SPECSURE_ISSUER_KEY_B64")
    if env:
        return Ed25519PrivateKey.from_private_bytes(base64.b64decode(env))
    os.makedirs(KEY_DIR, exist_ok=True)
    path = os.path.join(KEY_DIR, "issuer_ed25519.key")
    if os.path.exists(path):
        with open(path, "rb") as f:
            return Ed25519PrivateKey.from_private_bytes(f.read())
    k = Ed25519PrivateKey.generate()
    with open(path, "wb") as f:
        f.write(k.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()))
    return k


def did_key_from_public(pub: bytes) -> str:
    return "did:key:z" + b58encode(b"\xed\x01" + pub)


def public_from_did_key(did: str) -> bytes:
    raw = b58decode(did.split(":")[-1].split("#")[0][1:])
    assert raw[:2] == b"\xed\x01", "not an Ed25519 did:key"
    return raw[2:]


def issuer() -> Tuple[object, str]:
    from cryptography.hazmat.primitives import serialization
    k = _load_or_create_key()
    pub = k.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return k, did_key_from_public(pub)


def _hash_data(doc: Dict, proof_config: Dict) -> bytes:
    return hashlib.sha256(jcs(proof_config).encode()).digest() + hashlib.sha256(jcs(doc).encode()).digest()


def issue(subject: Dict, valid_until: Optional[str] = None, name: str = "SpecSure Demo Issuer (not an official authority)") -> Dict:
    key, did = issuer()
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    doc = {
        "@context": ["https://www.w3.org/ns/credentials/v2"],
        "id": f"urn:uuid:{uuid.uuid4()}",
        "type": ["VerifiableCredential", "ProductCompliancePassport"],
        "issuer": {"id": did, "name": name},
        "validFrom": now,
        "credentialSubject": subject,
    }
    if valid_until:
        doc["validUntil"] = valid_until if "T" in valid_until else f"{valid_until}T23:59:59Z"
    vm = f"{did}#{did.split(':')[-1]}"
    proof_config = {"@context": doc["@context"], "type": "DataIntegrityProof", "cryptosuite": "eddsa-jcs-2022",
                    "created": now, "verificationMethod": vm, "proofPurpose": "assertionMethod"}
    sig = key.sign(_hash_data(doc, proof_config))
    proof = {k: v for k, v in proof_config.items() if k != "@context"}
    proof["proofValue"] = "z" + b58encode(sig)
    return {**doc, "proof": proof}


def verify(vc: Dict) -> Dict:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    try:
        proof = dict(vc["proof"])
        doc = {k: v for k, v in vc.items() if k != "proof"}
        pv = proof.pop("proofValue")
        proof_config = {"@context": doc["@context"], **proof}
        pub = public_from_did_key(proof["verificationMethod"])
        Ed25519PublicKey.from_public_bytes(pub).verify(b58decode(pv[1:]), _hash_data(doc, proof_config))
        expired = False
        if doc.get("validUntil"):
            expired = doc["validUntil"] < datetime.now(timezone.utc).isoformat()
        return {"verified": True, "issuer": doc["issuer"]["id"], "cryptosuite": proof.get("cryptosuite"), "expired": expired}
    except Exception as e:
        return {"verified": False, "error": str(e) or e.__class__.__name__}


def qr_data_uri(text: str) -> Optional[str]:
    try:
        import qrcode
        img = qrcode.make(text)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None


def build_subject(bid: Dict, twin: Dict, evidence_docs: list) -> Dict:
    lic = next((d["meta"] for d in evidence_docs if d["meta"].get("licence_no")), {})
    rep = next((d["meta"] for d in evidence_docs if d["meta"].get("doc_type") == "test_report"), {})
    params = [r for r in bid["rows"] if r["kind"] == "parameter" and r.get("evidence")]
    tests = []
    for r in params:
        best = max(r["evidence"], key=lambda e: e.get("strength", 0))
        tests.append({"parameter": r["parameter"], "value": best.get("raw_value"), "requirement": r["required"],
                      "status": r["status"], "source": best.get("doc_name"), "page": best.get("page")})
    deviations = [{"clause": r["clause_key"], "parameter": r["parameter"] or r["requirement"][:60], "status": r["status"],
                   "detail": r["explanation"][:200]} for r in bid["rows"] if r["status"] in ("NON_COMPLIANT", "CONFLICTING_EVIDENCE")]
    return {
        "type": "Product",
        "product": {"name": bid.get("product_name") or "Offered product", "manufacturer": bid.get("bidder"),
                    "domain": ", ".join(bid.get("scope_domains", []))},
        "applicableStandards": sorted({ds.get("resolved") for d, ds in twin.get("domain_standards", {}).items()
                                       if not bid.get("scope_domains") or d in bid.get("scope_domains")} - {None}),
        "certification": {"licenceNumber": lic.get("licence_no"), "validUntil": lic.get("valid_to"), "grade": lic.get("grade"),
                          "status": lic.get("status"), "verificationNote": "Verify live status on the BIS portal"},
        "testResults": tests,
        "laboratory": {"name": rep.get("lab"), "accreditation": rep.get("nabl_certificate"), "reportNo": rep.get("report_no"),
                       "reportDate": rep.get("report_date")},
        "inspection": [],
        "tenderLinkage": [{"tender": twin["tender"].get("title"), "compliance_score": bid.get("compliance_score"), "verdict": bid.get("verdict")}],
        "deviationHistory": deviations,
        "evidenceBundle": [{"file": d["meta"]["doc_name"], "sha256": d["meta"]["sha256"], "type": d["meta"]["doc_type"]} for d in evidence_docs],
    }
