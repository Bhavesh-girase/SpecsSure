"""
Parameter ontology + product-domain detection.

Loaded once from data/engine/*.json. Pure, deterministic, cached.
"""
from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "engine")


def data_path(name: str) -> str:
    return os.path.abspath(os.path.join(DATA_DIR, name))


@lru_cache(maxsize=None)
def load_json(name: str):
    with open(data_path(name), "r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def parameters() -> Dict[str, dict]:
    return load_json("parameters.json")["parameters"]


@lru_cache(maxsize=1)
def derived_relations() -> List[dict]:
    return load_json("parameters.json")["derived_relations"]


@lru_cache(maxsize=1)
def _compiled_synonyms() -> List[Tuple[str, re.Pattern, int]]:
    out = []
    for pid, p in parameters().items():
        for syn in p["synonyms"]:
            # longer synonyms get priority (more specific)
            out.append((pid, re.compile(r"(?<![A-Za-z])" + syn, re.IGNORECASE), len(syn)))
    out.sort(key=lambda t: -t[2])
    return out


DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "steel": ["tmt", "rebar", "reinforcement bar", "deformed steel", "deformed bar", "fe 500", "fe500", "fe 415", "fe 550",
              "steel bar", "hsd bar", "structural steel", "sariya", "सरिया", "reinforcement steel", "reinforcing steel"],
    "cement": ["cement", "opc", "ppc", "portland", "सीमेंट", "clinker"],
    "concrete": ["concrete", "rcc", "m25", "m30", "m20", "ready mix"],
    "cables": ["cable", "wire", "wiring", "conductor", "pvc insulated", "xlpe", "frls", "flexible cord"],
    "water": ["drinking water", "potable", "packaged water", "tds", "coliform", "पानी"],
    "lighting": ["led", "luminaire", "street light", "streetlight", "lamp", "lighting fixture", "bulb", "बल्ब"],
    "fans": ["ceiling fan", "ceiling type fan", "sweep", "air delivery", "पंखा"],
    "electrical": ["mcb", "miniature circuit breaker", "circuit breaker", "breaking capacity", "tripping characteristic"],
    "solar": ["solar", "photovoltaic", "pv module", "almm", "सौर"],
    "geotextile": ["geotextile", "geo-textile", "geo textile", "non-woven", "needle punched"],
    "pipes": ["hdpe pipe", "pe pipe", "pvc pipe", "polyethylene pipe", "upvc"],
}


@lru_cache(maxsize=1)
def _domain_patterns() -> Dict[str, List[re.Pattern]]:
    out = {}
    for dom, kws in DOMAIN_KEYWORDS.items():
        pats = []
        for k in kws:
            if re.search(r"[\u0900-\u097F]", k):
                pats.append(re.compile(re.escape(k)))
            else:
                # word-bounded so that "reinforcement" is not "cement" and "bulbous" is not "bulb"
                pats.append(re.compile(r"(?<![a-z0-9])" + re.escape(k) + r"(?:s|es)?(?![a-z0-9])"))
        out[dom] = pats
    return out


ORDER_TITLE = re.compile(r"(?:[A-Z][\w\-]*,?\s+(?:and\s+|or\s+)?){1,16}\((?:Quality Control|Requirements? (?:of|for) Compulsory Registration)\)\s+Order,?\s*(?:\d{4})?")


def detect_domains(text: str) -> List[str]:
    # the name of a regulation ("Electrical Wires, Cables, Appliances … (Quality Control) Order") says nothing about the product
    low = ORDER_TITLE.sub(" ", text or "").lower()
    scores = []
    for dom, pats in _domain_patterns().items():
        s = sum(len(p.findall(low)) for p in pats)
        if s:
            scores.append((dom, s))
    scores.sort(key=lambda t: -t[1])
    return [d for d, _ in scores]


def find_parameters(sentence: str, domains: Optional[List[str]] = None) -> List[Tuple[str, int, int]]:
    """Return non-overlapping (param_id, start, end) matches, most specific first, domain-filtered."""
    found: List[Tuple[str, int, int]] = []
    taken: List[Tuple[int, int]] = []
    params = parameters()
    for pid, rx, _ in _compiled_synonyms():
        pdoms = params[pid].get("domains", [])
        if domains and "general" not in pdoms and not any(d in pdoms for d in domains):
            continue
        for m in rx.finditer(sentence):
            s, e = m.start(), m.end()
            if any(not (e <= ts or s >= te) for ts, te in taken):
                continue
            taken.append((s, e))
            found.append((pid, s, e))
    found.sort(key=lambda t: t[1])
    return found


def param_label(pid: str) -> str:
    return parameters().get(pid, {}).get("label", pid.replace("_", " ").title())


def param_unit(pid: str) -> str:
    return parameters().get(pid, {}).get("unit", "dimensionless")


def param_test(pid: str) -> Optional[dict]:
    return parameters().get(pid, {}).get("test")


@lru_cache(maxsize=1)
def standards_parameters() -> Dict[str, dict]:
    return load_json("standards_parameters.json")["standards"]


@lru_cache(maxsize=1)
def brand_lexicon() -> Dict[str, List[str]]:
    return load_json("brand_lexicon.json")["brands"]
