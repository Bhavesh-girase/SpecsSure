"""
Tamper-evident audit ledger (hash chain, transparency-log style).

Every consequential event — a compile (with input document hashes + knowledge-base snapshot hash +
engine version), a human review decision, an approved clarification, an issued passport, a
processed regulatory event — is appended as an entry whose hash covers the previous entry's hash:

    entry_hash_n = SHA-256( entry_hash_{n-1} || JCS(entry_n) )

Changing or deleting any historical entry breaks every later hash, which `verify_chain` detects.
The latest hash can be periodically published (e.g. in a gazette/website) as an external anchor.
"""
from __future__ import annotations

import hashlib
import json
from typing import Dict, List, Optional

GENESIS = "0" * 64


def jcs(obj) -> str:
    """JSON Canonicalization (RFC 8785) for the JSON subset we emit (sorted keys, no whitespace, UTF-8)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def payload_hash(payload: Dict) -> str:
    return hashlib.sha256(jcs(payload).encode("utf-8")).hexdigest()


def entry_hash(prev_hash: str, seq: int, ts: str, actor: str, action: str, subject_type: str, subject_id: str, p_hash: str) -> str:
    body = jcs({"seq": seq, "ts": ts, "actor": actor, "action": action, "subject_type": subject_type,
                "subject_id": subject_id, "payload_hash": p_hash})
    return hashlib.sha256((prev_hash + body).encode("utf-8")).hexdigest()


def verify_chain(entries: List[Dict]) -> Dict:
    prev = GENESIS
    for e in sorted(entries, key=lambda x: x["seq"]):
        if e["prev_hash"] != prev:
            return {"valid": False, "broken_at": e["seq"], "reason": "prev_hash does not match previous entry"}
        if payload_hash(e["payload"]) != e["payload_hash"]:
            return {"valid": False, "broken_at": e["seq"], "reason": "payload was modified"}
        h = entry_hash(prev, e["seq"], e["ts"], e["actor"], e["action"], e["subject_type"], e["subject_id"], e["payload_hash"])
        if h != e["entry_hash"]:
            return {"valid": False, "broken_at": e["seq"], "reason": "entry hash mismatch"}
        prev = h
    return {"valid": True, "entries": len(entries), "head": prev}
