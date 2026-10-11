"""
Procurement Institutional Memory.

Every compiled tender, pre-bid question and corrigendum becomes precedent. When a new tender is
drafted, each clause is matched against historical clauses (TF-IDF cosine with character n-grams —
robust to wording changes, no GPU needed; swap in the embedding service for semantic matching) to
surface "this wording generated 2 pre-bid queries and a corrigendum in DEMO/PWD/2024/0118".
"""
from __future__ import annotations

import json
import os
from collections import Counter
from functools import lru_cache
from typing import Dict, List, Optional

HISTORY = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "demo", "history.json"))


@lru_cache(maxsize=1)
def _seed_history() -> List[dict]:
    try:
        with open(HISTORY, encoding="utf-8") as f:
            return json.load(f)["tenders"]
    except FileNotFoundError:
        return []


class Memory:
    def __init__(self, extra_tenders: Optional[List[dict]] = None):
        self.tenders = list(_seed_history()) + list(extra_tenders or [])
        self.clauses = [{**c, "tender_ref": t["ref"], "tender_title": t["title"], "year": t.get("year")}
                        for t in self.tenders for c in t.get("clauses", [])]
        self._vec = None
        self._mat = None
        self._tvec = None
        self._tmat = None

    def _fit(self):
        if self._vec is not None or not self.clauses:
            return
        from sklearn.feature_extraction.text import TfidfVectorizer
        self._vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1, sublinear_tf=True)
        self._mat = self._vec.fit_transform([c["text"] for c in self.clauses])
        self._tvec = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", sublinear_tf=True)
        self._tmat = self._tvec.fit_transform([t["title"] + " " + " ".join(c["text"] for c in t.get("clauses", [])) for t in self.tenders])

    def clause_precedents(self, text: str, k: int = 3, min_score: float = 0.35) -> List[dict]:
        if not self.clauses or not text:
            return []
        self._fit()
        from sklearn.metrics.pairwise import cosine_similarity
        sims = cosine_similarity(self._vec.transform([text]), self._mat)[0]
        idx = sims.argsort()[::-1][:k]
        out = []
        for i in idx:
            if sims[i] < min_score:
                continue
            c = self.clauses[i]
            out.append({"score": round(float(sims[i]), 3), "tender_ref": c["tender_ref"], "tender_title": c["tender_title"],
                        "clause_key": c["key"], "text": c["text"], "issues": c.get("issues", []),
                        "prebid_questions": c.get("prebid_questions", []), "resolution": c.get("resolution")})
        return out

    def similar_tenders(self, text: str, k: int = 3) -> List[dict]:
        if not self.tenders:
            return []
        self._fit()
        from sklearn.metrics.pairwise import cosine_similarity
        sims = cosine_similarity(self._tvec.transform([text]), self._tmat)[0]
        idx = sims.argsort()[::-1][:k]
        return [{"score": round(float(sims[i]), 3), "ref": self.tenders[i]["ref"], "title": self.tenders[i]["title"],
                 "year": self.tenders[i].get("year"), "outcome": self.tenders[i].get("outcome")} for i in idx if sims[i] > 0.02]

    def recurring_patterns(self) -> List[dict]:
        cnt = Counter(i for c in self.clauses for i in c.get("issues", []))
        qs = Counter()
        for c in self.clauses:
            for i in c.get("issues", []):
                qs[i] += len(c.get("prebid_questions", []))
        return [{"rule_id": r, "occurrences": n, "prebid_questions_generated": qs[r]} for r, n in cnt.most_common()]

    def question_rate(self, rule_id: str) -> float:
        occ = [c for c in self.clauses if rule_id in c.get("issues", [])]
        if not occ:
            return 0.0
        return min(1.0, sum(1 for c in occ if c.get("prebid_questions")) / len(occ))


def twin_to_memory_record(twin: dict, ref: str) -> dict:
    """Turn a compiled tender into a memory record (its findings become 'issues' of each clause)."""
    by_clause: Dict[str, List[str]] = {}
    for f in twin.get("findings", []):
        if f.get("clause_key"):
            by_clause.setdefault(f["clause_key"], []).append(f["rule_id"])
    return {"ref": ref, "title": twin["tender"]["title"], "year": (twin["tender"].get("as_of") or "")[:4],
            "domains": twin["tender"].get("domains", []), "outcome": f"readiness {twin['readiness']['score']}",
            "clauses": [{"key": c["key"], "text": c["text"], "issues": sorted(set(by_clause.get(c["key"], []))), "prebid_questions": []}
                        for c in twin["clauses"] if c.get("text")]}
