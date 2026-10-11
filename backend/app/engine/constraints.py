"""
Formal verification of tender requirements with an SMT solver (Microsoft Z3).

Every quantitative requirement becomes a tracked linear constraint over real variables
(one variable per <domain>.<parameter>). Domain physics / definitions from the ontology are added
as background constraints (e.g. tensile >= (TS/YS) x yield). If the conjunction is UNSAT the solver
returns an *unsat core* which we shrink to a Minimal Unsatisfiable Subset (MUS): the smallest set of
clauses that cannot all be true at once. That MUS *is* the explanation — no LLM involved.

When satisfiable we compute the feasible window of every variable (min/max via Optimize), which is
what the Tender Digital Twin shows as "what a compliant product must look like".

Falls back to interval arithmetic if z3 is not installed.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from app.engine import ontology
from app.engine.extractor import Requirement

logger = logging.getLogger(__name__)

try:
    import z3  # type: ignore
    HAVE_Z3 = True
except Exception:  # pragma: no cover
    HAVE_Z3 = False

SKIP_OPS = {"enum"}
SKIP_PARAMS = {"bag_mass"}


@dataclass
class Atom:
    label: str                 # requirement id or "REL:<id>" or "STD:<...>"
    var: str                   # domain.param (or expression description for relations)
    kind: str                  # requirement | relation | standard
    lo: Optional[float] = None
    hi: Optional[float] = None
    text: str = ""
    clause_key: Optional[str] = None
    page: Optional[int] = None
    description: str = ""

    def to_dict(self):
        return self.__dict__.copy()


@dataclass
class Conflict:
    atoms: List[Atom]
    explanation: str
    variables: List[str]
    witness: Optional[str] = None
    involves_standard: bool = False

    def to_dict(self):
        return {"atoms": [a.to_dict() for a in self.atoms], "explanation": self.explanation, "variables": self.variables,
                "witness": self.witness, "involves_standard": self.involves_standard,
                "clauses": sorted({a.clause_key for a in self.atoms if a.clause_key})}


@dataclass
class VerificationResult:
    satisfiable: bool
    engine: str
    conflicts: List[Conflict] = field(default_factory=list)
    windows: Dict[str, Dict[str, Optional[float]]] = field(default_factory=dict)
    atoms: List[Atom] = field(default_factory=list)
    standard_conflicts: List[Conflict] = field(default_factory=list)

    def to_dict(self):
        return {"satisfiable": self.satisfiable, "engine": self.engine,
                "conflicts": [c.to_dict() for c in self.conflicts],
                "standard_conflicts": [c.to_dict() for c in self.standard_conflicts],
                "windows": self.windows, "constraint_count": len(self.atoms)}


def _ckey(k: Optional[str]):
    import re as _re
    return [int(x) for x in _re.findall(r"\d+", k or "")] or [999]


def _fmt(v: Optional[float]) -> str:
    if v is None:
        return "—"
    return f"{v:g}"


def atoms_from_requirements(reqs: List[Requirement]) -> List[Atom]:
    atoms = []
    for r in reqs:
        if r.kind != "parameter" or not r.parameter or r.op in SKIP_OPS or r.parameter in SKIP_PARAMS:
            continue
        lo, hi = r.norm.get("min"), r.norm.get("max")
        if lo is None and hi is None:
            continue
        unit = r.norm.get("unit", "")
        desc = f"{r.parameter_label} " + (f"= {_fmt(lo)}" if lo == hi and lo is not None else
                                           (f"≥ {_fmt(lo)}" if hi is None else (f"≤ {_fmt(hi)}" if lo is None else f"in [{_fmt(lo)}, {_fmt(hi)}]")))
        desc += f" {unit if unit not in ('dimensionless',) else ''}".rstrip()
        atoms.append(Atom(label=r.id, var=f"{r.domain or 'general'}.{r.parameter}", kind="requirement", lo=lo, hi=hi,
                          text=r.text, clause_key=r.clause_key, page=r.page, description=desc))
    return atoms


def standard_atoms(domain: str, family: str, grade: Optional[str]) -> List[Atom]:
    sp = ontology.standards_parameters().get(family)
    if not sp:
        return []
    g = grade if grade in sp["grades"] else sp.get("default_grade")
    out = []
    for pid, b in sp["grades"].get(g, {}).items():
        out.append(Atom(label=f"STD:{family}:{g}:{pid}", var=f"{domain}.{pid}", kind="standard", lo=b.get("min"), hi=b.get("max"),
                        text=f"{family} grade {g}: {ontology.param_label(pid)}", clause_key=None,
                        description=f"{family} ({g}) requires {ontology.param_label(pid)} "
                                    + (f"≥ {_fmt(b.get('min'))}" if b.get("min") is not None else "")
                                    + (" and " if b.get("min") is not None and b.get("max") is not None else "")
                                    + (f"≤ {_fmt(b.get('max'))}" if b.get("max") is not None else "")))
    return out


def _relations_for(vars_present: set) -> List[dict]:
    rels = []
    domains = {v.split(".")[0] for v in vars_present}
    for rel in ontology.derived_relations():
        if not rel["requires"]:
            continue
        for d in domains:
            if all(f"{d}.{p}" in vars_present for p in rel["requires"]):
                rels.append({**rel, "domain": d})
    return rels


# ---------------------------------------------------------------------------------------------
def verify(atoms: List[Atom], std_atoms: Optional[List[Atom]] = None, max_conflicts: int = 6) -> VerificationResult:
    if not HAVE_Z3:
        return _verify_intervals(atoms, std_atoms or [])
    res = _verify_z3(atoms, max_conflicts)
    if std_atoms:
        # second pass: does any single tender requirement contradict the standard the tender itself cites?
        for a in atoms:
            relevant = [s_ for s_ in std_atoms if s_.var.split(".")[0] == a.var.split(".")[0]]
            if not relevant:
                continue
            sub = _verify_z3([a] + relevant, 1, windows=False)
            for c in sub.conflicts:
                if any(x.kind == "standard" for x in c.atoms) and any(x.label == a.label for x in c.atoms):
                    c.involves_standard = True
                    res.standard_conflicts.append(c)
    return res


def _build(atoms: List[Atom]):
    vars_present = {a.var for a in atoms}
    zv = {v: z3.Real(v) for v in vars_present}
    tracked: List[Tuple[object, Atom, object]] = []
    for a in atoms:
        x = zv[a.var]
        parts = []
        if a.lo is not None:
            parts.append(x >= z3.RealVal(str(a.lo)))
        if a.hi is not None:
            parts.append(x <= z3.RealVal(str(a.hi)))
        tracked.append((z3.Bool(a.label), a, z3.And(*parts) if len(parts) > 1 else parts[0]))
    rel_atoms = []
    for rel in _relations_for(vars_present):
        d = rel["domain"]
        env = {p: zv[f"{d}.{p}"] for p in rel["requires"]}
        op = ">=" if ">=" in rel["expr"] else "<="
        lhs, rhs = rel["expr"].split(op)
        l_, r_ = eval(lhs.strip(), {}, env), eval(rhs.strip(), {}, env)  # expressions come from our own ontology file
        expr = (l_ >= r_) if op == ">=" else (l_ <= r_)
        a = Atom(label=f"REL:{rel['id']}:{d}", var="; ".join(f"{d}.{p}" for p in rel["requires"]), kind="relation",
                 text=rel["description"], description=rel["description"])
        rel_atoms.append(a)
        tracked.append((z3.Bool(a.label), a, expr))
    nonneg = [x >= 0 for x in zv.values()]
    return zv, tracked, nonneg, rel_atoms


def _check(tracked, nonneg, subset_labels=None):
    s = z3.Solver()
    s.set("timeout", 5000)
    s.add(*nonneg)
    for b, a, e in tracked:
        if subset_labels is None or a.label in subset_labels:
            s.assert_and_track(e, b)
    return s, s.check()


def _minimize(tracked, nonneg, core_labels: List[str]) -> List[str]:
    mus = list(core_labels)
    for lab in list(mus):
        trial = [l for l in mus if l != lab]
        if not trial:
            continue
        _, r = _check(tracked, nonneg, set(trial))
        if r == z3.unsat:
            mus = trial
    return mus


def _explain(atoms: List[Atom]) -> Tuple[str, Optional[str]]:
    reqs = [a for a in atoms if a.kind in ("requirement", "standard")]
    rels = [a for a in atoms if a.kind == "relation"]
    by_var: Dict[str, List[Atom]] = {}
    for a in reqs:
        by_var.setdefault(a.var, []).append(a)
    if len(by_var) == 1 and not rels:
        var = next(iter(by_var))
        los = [a.lo for a in reqs if a.lo is not None]
        his = [a.hi for a in reqs if a.hi is not None]
        lab = ontology.param_label(var.split(".")[1])
        witness = f"max lower bound {_fmt(max(los) if los else None)} > min upper bound {_fmt(min(his) if his else None)}"
        where = " and ".join(f"Clause {a.clause_key}" if a.clause_key else a.label.replace("STD:", "") for a in reqs)
        return (f"No product can satisfy {where} simultaneously: {lab} is required to be "
                + " and ".join(a.description.replace(lab, "").strip() for a in reqs) + ".", witness)
    parts = [f"Clause {a.clause_key}: {a.description}" if a.clause_key else a.description for a in reqs]
    parts += [f"Engineering relation: {r.description}" for r in rels]
    # numeric witness for the classic ratio case
    witness = None
    vals = {a.var.split(".")[1]: a for a in reqs}
    if {"yield_strength", "ts_ys_ratio", "tensile_strength"} <= set(vals):
        ys, rt, ts = vals["yield_strength"], vals["ts_ys_ratio"], vals["tensile_strength"]
        if ys.lo is not None and rt.lo is not None and ts.hi is not None:
            need = ys.lo * rt.lo
            witness = f"{_fmt(ys.lo)} × {_fmt(rt.lo)} = {need:g} MPa minimum tensile strength, but the tender caps it at {_fmt(ts.hi)} MPa"
    return ("These requirements are jointly impossible — " + "; ".join(parts) + ".", witness)


def _verify_z3(atoms: List[Atom], max_conflicts: int, only_with_standard: bool = False, windows: bool = True) -> VerificationResult:
    zv, tracked, nonneg, rel_atoms = _build(atoms)
    all_atoms = atoms + rel_atoms
    lab2atom = {a.label: a for _, a, _ in tracked}
    remaining = {a.label for _, a, _ in tracked}
    conflicts: List[Conflict] = []
    first_sat = None
    for _ in range(max_conflicts):
        s, r = _check(tracked, nonneg, remaining)
        if first_sat is None:
            first_sat = (r == z3.sat)
        if r != z3.unsat:
            break
        core = [str(b) for b in s.unsat_core()]
        mus = _minimize(tracked, nonneg, core)
        mus_atoms = sorted([lab2atom[l] for l in mus], key=lambda a: (a.kind == "relation", _ckey(a.clause_key), a.label))
        if not [a for a in mus_atoms if a.kind != "relation"]:
            break
        expl, witness = _explain(mus_atoms)
        involves_std = any(a.kind == "standard" for a in mus_atoms)
        if not only_with_standard or involves_std:
            conflicts.append(Conflict(mus_atoms, expl, sorted({a.var for a in mus_atoms if a.kind != "relation"}), witness, involves_std))
        # remove the tender-side atoms of this MUS and look for further independent conflicts
        drop = [l for l in mus if not l.startswith("REL:")]
        if only_with_standard:
            drop = [l for l in drop if not l.startswith("STD:")] or drop
        for l in drop:
            remaining.discard(l)
    win: Dict[str, Dict[str, Optional[float]]] = {}
    if windows:
        # feasible window per variable over the contradiction-free constraint set (interval projection;
        # exact bounds for linear constraints, conservative where engineering relations are non-linear)
        for a in atoms:
            if a.label not in remaining:
                continue
            w = win.setdefault(a.var, {"min": None, "max": None})
            if a.lo is not None:
                w["min"] = a.lo if w["min"] is None else max(w["min"], a.lo)
            if a.hi is not None:
                w["max"] = a.hi if w["max"] is None else min(w["max"], a.hi)
    return VerificationResult(satisfiable=bool(first_sat), engine=f"z3 {z3.get_version_string()}",
                              conflicts=conflicts, windows=win, atoms=all_atoms)


def _opt(tracked, nonneg, labels, x, minimize: bool) -> Optional[float]:
    o = z3.Optimize()
    o.set("timeout", 3000)
    o.add(*nonneg)
    for b, a, e in tracked:
        if a.label in labels:
            o.add(e)
    h = o.minimize(x) if minimize else o.maximize(x)
    if o.check() != z3.sat:
        return None
    v = (o.lower(h) if minimize else o.upper(h))
    try:
        if z3.is_rational_value(v):
            return float(v.numerator_as_long()) / float(v.denominator_as_long())
        s = str(v)
        if "oo" in s or "epsilon" in s:
            return None
        return float(s)
    except Exception:
        return None


def _verify_intervals(atoms: List[Atom], std_atoms: List[Atom]) -> VerificationResult:
    """Fallback without z3: per-variable interval intersection (no cross-variable relations)."""
    def run(ats):
        by_var: Dict[str, List[Atom]] = {}
        for a in ats:
            by_var.setdefault(a.var, []).append(a)
        conflicts, windows = [], {}
        for v, group in by_var.items():
            lo = max([a.lo for a in group if a.lo is not None], default=None)
            hi = min([a.hi for a in group if a.hi is not None], default=None)
            windows[v] = {"min": lo, "max": hi}
            if lo is not None and hi is not None and lo > hi:
                lo_a = max((a for a in group if a.lo is not None), key=lambda a: a.lo)
                hi_a = min((a for a in group if a.hi is not None), key=lambda a: a.hi)
                expl, w = _explain([lo_a, hi_a])
                conflicts.append(Conflict([lo_a, hi_a], expl, [v], w, any(a.kind == "standard" for a in (lo_a, hi_a))))
        return conflicts, windows
    c, w = run(atoms)
    sc, _ = run(atoms + std_atoms)
    return VerificationResult(satisfiable=not c, engine="interval-propagation (z3 unavailable)", conflicts=c, windows=w,
                              atoms=atoms, standard_conflicts=[x for x in sc if x.involves_standard])
