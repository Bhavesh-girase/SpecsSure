"""
Unit normalisation for tender requirements and bidder evidence.

Every numeric value that enters the constraint engine is converted to the
canonical unit of its parameter (see data/engine/parameters.json) so that
"500 N/mm2", "500 MPa" and "5098 kgf/cm2" compare correctly.

The table is deliberately explicit (no heuristics) so conversions are auditable.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Tuple

# canonical unit -> {alias -> factor to canonical}
_UNIT_TABLE = {
    "MPa": {
        "mpa": 1.0, "n/mm2": 1.0, "n/mm^2": 1.0, "n/mm²": 1.0, "n/sq mm": 1.0, "n/sq.mm": 1.0,
        "n/mm**2": 1.0, "gpa": 1000.0, "kpa": 0.001, "kgf/cm2": 0.0980665, "kg/cm2": 0.0980665,
        "kgf/cm²": 0.0980665, "kg/cm²": 0.0980665, "kg/sq cm": 0.0980665, "psi": 0.00689476, "ksi": 6.89476,
    },
    "mm": {"mm": 1.0, "millimetre": 1.0, "millimeter": 1.0, "cm": 10.0, "m": 1000.0, "km": 1000000.0, "micron": 0.001,
           "microns": 0.001, "µm": 0.001, "um": 0.001, "inch": 25.4, "in": 25.4, '"': 25.4},
    "kg/m": {"kg/m": 1.0, "kg/metre": 1.0, "kg/meter": 1.0, "g/m": 0.001},
    "percent": {"%": 1.0, "percent": 1.0, "per cent": 1.0, "pct": 1.0},
    "m**2/kg": {"m2/kg": 1.0, "m²/kg": 1.0, "sq.m/kg": 1.0, "sq m/kg": 1.0, "m^2/kg": 1.0, "m**2/kg": 1.0,
                "cm2/g": 0.1, "cm²/g": 0.1, "sq cm/g": 0.1},
    "minute": {"min": 1.0, "mins": 1.0, "minute": 1.0, "minutes": 1.0, "h": 60.0, "hr": 60.0, "hrs": 60.0,
               "hour": 60.0, "hours": 60.0},
    "kg": {"kg": 1.0, "kgs": 1.0, "kilogram": 1.0, "kilograms": 1.0, "g": 0.001, "tonne": 1000.0, "t": 1000.0,
           "mt": 1000.0},
    "V": {"v": 1.0, "volt": 1.0, "volts": 1.0, "kv": 1000.0, "mv": 0.001},
    "kV": {"kv": 1.0, "v": 0.001},
    "mm**2": {"mm2": 1.0, "mm²": 1.0, "sq mm": 1.0, "sq. mm": 1.0, "sq.mm": 1.0, "sqmm": 1.0, "mm^2": 1.0,
              "mm**2": 1.0},
    "ohm/km": {"ohm/km": 1.0, "Ω/km": 1.0, "ω/km": 1.0, "ohms/km": 1.0, "mohm/m": 1.0},
    "mg/L": {"mg/l": 1.0, "mg/litre": 1.0, "mg/liter": 1.0, "ppm": 1.0, "g/l": 1000.0},
    "W": {"w": 1.0, "watt": 1.0, "watts": 1.0, "kw": 1000.0, "wp": 1.0, "watt peak": 1.0, "kwp": 1000.0},
    "K": {"k": 1.0, "kelvin": 1.0},
    "A": {"a": 1.0, "amp": 1.0, "amps": 1.0, "ampere": 1.0, "amperes": 1.0, "ma": 0.001},
    "kA": {"ka": 1.0},
    "m**3/min": {"m3/min": 1.0, "m³/min": 1.0, "cmm": 1.0, "cu m/min": 1.0, "cum/min": 1.0},
    "m**3/min/W": {"m3/min/w": 1.0, "m³/min/w": 1.0, "cmm/w": 1.0, "m3/min per watt": 1.0, "m³/min per watt": 1.0},
    "lm/W": {"lm/w": 1.0, "lumen/watt": 1.0, "lumens/watt": 1.0, "lm per watt": 1.0},
    "g/m**2": {"g/m2": 1.0, "g/m²": 1.0, "gsm": 1.0, "g/sq m": 1.0, "g/m^2": 1.0, "g/m**2": 1.0},
    "N": {"n": 1.0, "newton": 1.0, "newtons": 1.0, "kn": 1000.0},
    "day": {"day": 1.0, "days": 1.0, "week": 7.0, "weeks": 7.0, "month": 30.0, "months": 30.0,
            "year": 365.0, "years": 365.0},
    "month": {"month": 1.0, "months": 1.0, "year": 12.0, "years": 12.0, "day": 1 / 30.0, "days": 1 / 30.0},
    "dimensionless": {"": 1.0},
}

# regex fragment matching any known unit token (longest first so "kgf/cm2" beats "kg")
_ALL_ALIASES = sorted({a for t in _UNIT_TABLE.values() for a in t if a}, key=len, reverse=True)
# a unit token must not run into a following letter ("0.95 at" is not "0.95 A"; "5 km" is not "5 K")
UNIT_REGEX = "(?:(?:" + "|".join(re.escape(a) for a in _ALL_ALIASES) + r")(?![A-Za-z]))"

NON_SI_UNITS = {"kg/cm2", "kgf/cm2", "kg/cm²", "kgf/cm²", "kg/sq cm", "psi", "ksi", "inch", "in", '"'}


@dataclass
class Normalized:
    value: float
    unit: str
    original_unit: Optional[str]
    factor: float
    converted: bool


def canonical_alias(unit: Optional[str]) -> str:
    if not unit:
        return ""
    u = unit.strip().lower().replace(" ", " ")
    u = re.sub(r"\s+", " ", u)
    u = u.rstrip(".")
    return u


def convert(value: float, unit: Optional[str], canonical: str) -> Optional[Normalized]:
    """Convert value in `unit` to the canonical unit. Returns None if incompatible."""
    table = _UNIT_TABLE.get(canonical)
    if table is None:
        return None
    alias = canonical_alias(unit)
    if canonical == "dimensionless":
        return Normalized(value, canonical, unit, 1.0, False)
    if alias == "":
        # value given without unit: assume canonical but mark it
        return Normalized(value, canonical, None, 1.0, False)
    factor = table.get(alias)
    if factor is None:
        # try squeezing spaces
        factor = table.get(alias.replace(" ", ""))
    if factor is None:
        return None
    return Normalized(value * factor, canonical, unit, factor, factor != 1.0)


def unit_family(unit: Optional[str]) -> Optional[str]:
    """Which canonical family a raw unit belongs to (first match)."""
    alias = canonical_alias(unit)
    if not alias:
        return None
    for canon, table in _UNIT_TABLE.items():
        if alias in table or alias.replace(" ", "") in table:
            return canon
    return None


def is_non_si(unit: Optional[str]) -> bool:
    return canonical_alias(unit) in NON_SI_UNITS


_NUM = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"


def parse_number(s: str) -> Optional[float]:
    try:
        return float(s.replace(",", ""))
    except (ValueError, AttributeError):
        return None


def split_value_unit(text: str) -> Tuple[Optional[float], Optional[str]]:
    """'565 N/mm2' -> (565.0, 'N/mm2')"""
    m = re.search(rf"({_NUM})\s*({UNIT_REGEX})?", text, re.IGNORECASE)
    if not m:
        return None, None
    return parse_number(m.group(1)), (m.group(2) or None)


NUMBER_REGEX = _NUM
