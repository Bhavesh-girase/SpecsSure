import re
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.product_ontology import ProductCategory
from app.models.standard import Standard, StandardStatus
from app.schemas.analysis import SpecHealth, SpecGap
from app.services.graph_service import graph_service

logger = logging.getLogger(__name__)

AMBIGUOUS_PROCUREMENT_RULES = [
    {
        "pattern": r"\b(high quality|good quality|best quality|superior quality)\b",
        "severity": "warning",
        "description": "Vague qualitative adjective '{match}' used instead of quantified acceptance thresholds.",
        "suggestion": "Replace with explicit numerical thresholds (e.g. minimum tensile strength, chemical purity limits, or specific BIS Grade designation)."
    },
    {
        "pattern": r"\b(durable|long lasting|heavy duty)\b",
        "severity": "warning",
        "description": "Unquantified durability claim '{match}' without accelerated life or endurance testing criteria.",
        "suggestion": "Define durability through accelerated weathering/aging tests or minimum cycle endurance per relevant Indian Standard."
    },
    {
        "pattern": r"\b(weather resistant|all weather|weatherproof)\b",
        "severity": "warning",
        "description": "Subjective weather resistance statement '{match}' without environmental test standard.",
        "suggestion": "Specify IP Ingress Protection rating (IS/IEC 60529) or Salt Spray corrosion test duration (IS 9000)."
    },
    {
        "pattern": r"\b(corrosion resistant|rust free|rust resistant)\b",
        "severity": "warning",
        "description": "Vague corrosion resistance claim '{match}'.",
        "suggestion": "Specify galvanic coating thickness (IS 4759 / IS 1367) or salt spray exposure hours per IS 9844."
    },
    {
        "pattern": r"\b(suitable for|as required|as applicable|as per site requirements)\b",
        "severity": "info",
        "description": "Open-ended clause '{match}' gives excessive discretion, risking non-compliant vendor substitutions.",
        "suggestion": "Define exact site operating conditions (temperature range, load capacity, working pressure)."
    },
    {
        "pattern": r"\b(as per standard|as per IS code|as per BIS)\b",
        "severity": "critical",
        "description": "Ambiguous generic reference '{match}' without specifying the IS number, year, or part.",
        "suggestion": "Specify the full Indian Standard designation (e.g. 'IS 269:2015' or 'IS 1786:2008 Grade Fe 500D')."
    },
    {
        "pattern": r"\b(or equivalent|or similar|equivalent make)\b",
        "severity": "warning",
        "description": "Equivalence clause '{match}' lacks objective benchmarks for technical evaluation.",
        "suggestion": "Append 'subject to meeting identical ISO/IS test parameters with third-party NABL accredited laboratory test certificate'."
    },
    {
        "pattern": r"\b(good finish|fine finish|smooth finish)\b",
        "severity": "info",
        "description": "Qualitative aesthetic term '{match}'.",
        "suggestion": "Specify surface roughness Ra value (IS 3073) or visual defect inspection criteria per BIS sampling standards."
    },
    {
        "pattern": r"\b(adequate strength|sufficient strength|strong)\b",
        "severity": "critical",
        "description": "Indefinite structural requirement '{match}'.",
        "suggestion": "Mandate minimum characteristic compressive or tensile strength in MPa/N-mm2 tested as per IS test codes."
    },
    {
        "pattern": r"\b(reputed manufacturer|standard brand|leading brand)\b",
        "severity": "warning",
        "description": "Brand-biased or vague vendor qualification term '{match}'.",
        "suggestion": "Require valid BIS license (ISI mark) and minimum 3 years audited manufacturing experience instead of brand names."
    }
]

class SpecAnalyzer:
    @classmethod
    async def analyze_spec_health(
        cls,
        input_text: str,
        extracted_requirements: List[Dict[str, Any]],
        product_identity: Optional[str],
        validated_standards: List[Any],
        db: AsyncSession
    ) -> SpecHealth:
        """
        Calculates holistic Specification Health Score (0-100) and detects gaps,
        ambiguities, parameter omissions, and outdated standard citations.
        """
        gaps: List[SpecGap] = []
        
        # 1. Ambiguity Detection
        ambiguity_gaps = cls.detect_ambiguities(input_text)
        gaps.extend(ambiguity_gaps)
        
        # 2. Conflict Detection
        conflict_gaps = cls.detect_conflicts(extracted_requirements)
        gaps.extend(conflict_gaps)
        
        # 3. Currency / Lifecycle Check for cited standards
        currency_gaps = await cls.detect_outdated_standards(input_text, db)
        gaps.extend(currency_gaps)
        
        # 4. Parameter Completeness Check against Product Ontology
        param_gaps = await cls.detect_parameter_gaps(product_identity, extracted_requirements, db)
        gaps.extend(param_gaps)

        # 5. Missing Normative Test Dependencies
        cited_is_numbers = [s.is_number for s in validated_standards if hasattr(s, "is_number")]
        normative_gaps = await graph_service.find_missing_dependencies(cited_is_numbers, db)
        for ng in normative_gaps:
            gaps.append(SpecGap(
                gap_type=ng["gap_type"],
                severity=ng["severity"],
                description=ng["description"],
                suggestion=ng["suggestion"],
                affected_standard=ng.get("affected_standard"),
                clause_reference=ng.get("clause_reference")
            ))

        # Calculate Sub-scores
        clarity_deductions = sum(15 if g.severity == "critical" else 8 for g in ambiguity_gaps)
        clarity_score = max(0, 100 - clarity_deductions)

        currency_deductions = sum(25 if g.severity == "critical" else 10 for g in currency_gaps)
        currency_score = max(0, 100 - currency_deductions)

        completeness_deductions = sum(15 if g.severity == "critical" else 8 for g in param_gaps + [g for g in gaps if g.gap_type == "missing_normative_test"])
        completeness_score = max(0, 100 - completeness_deductions)

        # Conflict deductions
        conflict_deductions = sum(20 for g in conflict_gaps)

        overall_score = max(
            0,
            int((completeness_score * 0.40) + (currency_score * 0.35) + (clarity_score * 0.25) - conflict_deductions)
        )

        summary = cls._generate_health_summary(overall_score, gaps)

        return SpecHealth(
            overall_score=overall_score,
            completeness_score=completeness_score,
            currency_score=currency_score,
            clarity_score=clarity_score,
            gaps=gaps,
            summary=summary
        )

    @staticmethod
    def detect_ambiguities(text: str) -> List[SpecGap]:
        """Scans procurement text for vague qualitative terms."""
        gaps = []
        for rule in AMBIGUOUS_PROCUREMENT_RULES:
            matches = re.finditer(rule["pattern"], text, re.IGNORECASE)
            for m in matches:
                matched_text = m.group(0)
                gaps.append(SpecGap(
                    gap_type="ambiguous_term",
                    severity=rule["severity"],
                    description=rule["description"].format(match=matched_text),
                    suggestion=rule["suggestion"],
                    clause_reference=f"Found: '{matched_text}'"
                ))
        return gaps

    @staticmethod
    def detect_conflicts(extracted_requirements: List[Dict[str, Any]]) -> List[SpecGap]:
        """Detects conflicting values specified for the same technical parameter."""
        gaps = []
        param_values: Dict[str, List[str]] = {}
        for req in extracted_requirements:
            param = req.get("parameter", "").strip().lower()
            val = str(req.get("value", "")).strip()
            if param and val:
                param_values.setdefault(param, []).append(val)

        for param, values in param_values.items():
            unique_vals = list(set(values))
            if len(unique_vals) > 1:
                gaps.append(SpecGap(
                    gap_type="conflict",
                    severity="critical",
                    description=f"Conflicting values detected for '{param.title()}': {', '.join(unique_vals)}.",
                    suggestion=f"Reconcile contradictory specifications for '{param.title()}' to avoid procurement disputes."
                ))
        return gaps

    @staticmethod
    async def detect_outdated_standards(text: str, db: AsyncSession) -> List[SpecGap]:
        """Checks if text explicitly cites superseded, withdrawn, or older revisions of IS codes."""
        gaps = []
        is_pattern = r'\bIS\s*:?\s*(\d{2,5}(?:\s*\(?Part\s*\d+\)?)?(?:\s*:\s*\d{4})?)\b'
        matches = re.findall(is_pattern, text, re.IGNORECASE)
        
        for match in set(matches):
            clean_is = f"IS {match.strip()}"
            stmt = select(Standard).where(Standard.is_number.ilike(f"%{clean_is}%"))
            res = await db.execute(stmt)
            std = res.scalars().first()
            
            if std and std.status in [StandardStatus.SUPERSEDED, StandardStatus.WITHDRAWN]:
                gaps.append(SpecGap(
                    gap_type="outdated_reference",
                    severity="critical",
                    description=f"Specification cites {std.is_number}, which is {std.status.value.upper()}.",
                    suggestion=f"Update reference to active standard {std.superseded_by or 'current active edition'} to ensure legal and technical compliance.",
                    affected_standard=std.is_number
                ))
        return gaps

    @staticmethod
    async def detect_parameter_gaps(
        product_identity: Optional[str],
        extracted_requirements: List[Dict[str, Any]],
        db: AsyncSession
    ) -> List[SpecGap]:
        """Matches product to ontology template and flags missing mandatory parameters."""
        gaps = []
        if not product_identity:
            return gaps

        # Query ontology category matching product identity keywords
        stmt = select(ProductCategory)
        res = await db.execute(stmt)
        categories = res.scalars().all()
        
        matched_cat = None
        for cat in categories:
            if cat.category_name.lower() in product_identity.lower() or product_identity.lower() in cat.category_name.lower():
                matched_cat = cat
                break
            if cat.keywords:
                for kw in [k.strip().lower() for k in cat.keywords.split(",")]:
                    if kw in product_identity.lower():
                        matched_cat = cat
                        break
            if matched_cat:
                break

        if matched_cat and matched_cat.parameter_template:
            template = matched_cat.parameter_template
            extracted_params = {
                r.get("parameter", "").lower() for r in extracted_requirements
            }
            
            # Check essential categories (chemical, mechanical, physical)
            for group_name in ["mechanical", "physical", "chemical", "electrical"]:
                required_group = template.get(group_name, [])
                for expected_param in required_group[:3]: # check top critical params
                    p_lower = expected_param.lower()
                    if not any(p_lower in ep or ep in p_lower for ep in extracted_params):
                        gaps.append(SpecGap(
                            gap_type="missing_parameter",
                            severity="warning",
                            description=f"Missing essential {group_name} parameter: '{expected_param}' for {matched_cat.category_name}.",
                            suggestion=f"Define specific limit or test value for '{expected_param}' per {matched_cat.primary_standard_is or 'applicable standard'}.",
                            affected_standard=matched_cat.primary_standard_is
                        ))
        return gaps

    @staticmethod
    def _generate_health_summary(score: int, gaps: List[SpecGap]) -> str:
        critical_count = sum(1 for g in gaps if g.severity == "critical")
        warning_count = sum(1 for g in gaps if g.severity == "warning")
        
        if score >= 85:
            return f"Specification is robust (Score: {score}/100) with clear technical parameters. {len(gaps)} minor enhancement opportunities identified."
        elif score >= 60:
            return f"Specification is moderately defined (Score: {score}/100). Found {critical_count} critical issues and {warning_count} ambiguous clauses requiring refinement before tender floating."
        else:
            return f"Specification is high-risk (Score: {score}/100) due to {critical_count} critical gaps, missing test method citations, or outdated standards. Immediate revision recommended."

spec_analyzer = SpecAnalyzer()
