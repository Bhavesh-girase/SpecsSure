"""Shared compile context passed to linter rules (built by app.engine.compiler)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional

from app.engine.extractor import ExtractionResult, Requirement
from app.engine.kb import KnowledgeBase
from app.engine.tender_ir import TenderIR, Clause
from app.engine.constraints import VerificationResult

DOMAIN_DEFAULT_STANDARD = {
    "steel": "IS 1786", "cement": "IS 269", "cables": "IS 694", "water": "IS 10500",
    "lighting": "IS 10322 (Part 5/Sec 1)", "geotextile": "IS 16391", "pipes": "IS 4984", "concrete": "IS 456",
    "fans": "IS 374", "electrical": "IS/IEC 60898", "solar": "IS 14286 (Part 1/Sec 1)",
}


@dataclass
class CompileContext:
    ir: TenderIR
    ex: ExtractionResult
    kb: KnowledgeBase
    as_of: date
    resolutions: List[dict] = field(default_factory=list)          # one per citation occurrence
    domain_standards: Dict[str, dict] = field(default_factory=dict)  # domain -> {family, grade, resolved, regulations...}
    verification: Optional[VerificationResult] = None
    market: List[dict] = field(default_factory=list)
    missing_dependencies: List[dict] = field(default_factory=list)
    test_plan: Optional[dict] = None
    memory_hits: List[dict] = field(default_factory=list)

    @property
    def clauses(self) -> List[Clause]:
        return self.ir.clauses

    @property
    def reqs(self) -> List[Requirement]:
        return self.ex.requirements

    def clause(self, key: Optional[str]) -> Optional[Clause]:
        if key is None:
            return None
        return next((c for c in self.ir.clauses if c.key == key), None)

    def full_text(self) -> str:
        return "\n".join(f"{c.key} {c.heading} {c.text}" for c in self.ir.clauses)

    def delivery_days(self) -> Optional[float]:
        vals = [r.norm.get("max") for r in self.reqs if r.parameter == "delivery_period" and r.norm.get("max") is not None]
        return min(vals) if vals else None
