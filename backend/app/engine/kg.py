"""
Procurement Knowledge Graph (PKG) — one typed, temporal, provenance-carrying graph that connects

    Item ─GOVERNED_BY→ Standard family ─HAS_EDITION→ Edition ─SUPERSEDED_BY→ Edition
      │                     │  ▲                          └─NORMATIVE_REF / TEST_METHOD / SAFETY_REQ→ Edition
      │                     │  └─MANDATES── Regulation (QCO · CRS · BEE label · ALMM)   [valid-time]
      │                     └─SPECIFIES→ Parameter ─MEASURED_BY→ Test-method family ←ACCREDITED_FOR─ Lab
      ├─HAS_SLOT→ Parameter            (what the buyer must decide)
      ├─SUBJECT_TO→ Policy             (GFR 2017 rules, Make-in-India, MSE policy)
      ├─CO_PROCURED_WITH→ Item         (used to disambiguate "100 metres" next to "500 bulbs")
      └─◀INSTANCE_OF─ Product ◀MAKES─ Manufacturer   (market layer → competition estimates)

Every node/edge carries `valid_from` / `valid_to`, `source_url` and `verification_state`, so a query can be
asked *as of a date* and every answer returns the path that produced it ("why is this clause here?").

It is built deterministically from the same curated registry the compiler uses (KnowledgeBase snapshot +
data/engine/*.json), cached by the snapshot hash, and exportable to Neo4j (Cypher) and JSON-LD.
"""
from __future__ import annotations

import json
import re
from datetime import date, timedelta
from functools import lru_cache
from typing import Dict, Iterable, List, Optional, Tuple

import networkx as nx

from app.engine import ontology
from app.engine.kb import KnowledgeBase, StdRecord, seed_kb
from app.engine.std_refs import base_number, family_of
from app.engine.temporal import resolve

REL_LABEL = {
    "GOVERNED_BY": "governed by", "HAS_EDITION": "has edition", "SUPERSEDED_BY": "superseded by", "NORMATIVE_REF": "normatively references",
    "TEST_METHOD": "tested by", "SAFETY_REQ": "safety requirement", "AMENDED_BY": "amended by", "MANDATES": "makes mandatory",
    "HAS_SLOT": "buyer decides", "SPECIFIES": "specifies", "MEASURED_BY": "measured by", "ACCREDITED_FOR": "accredited for",
    "SUBJECT_TO": "subject to", "CO_PROCURED_WITH": "often bought with", "INSTANCE_OF": "is a", "MAKES": "makes",
    "CONFORMS_TO": "certified to", "RELATED": "related to",
}
KB_REL = {"normative_reference": "NORMATIVE_REF", "test_method": "TEST_METHOD", "safety_requirement": "SAFETY_REQ",
          "superseded_by": "SUPERSEDED_BY", "installation_code": "RELATED", "design_code": "RELATED"}


def items() -> List[dict]:
    return ontology.load_json("items.json")["items"]


def policies() -> List[dict]:
    return ontology.load_json("policies.json")["policies"]


def item_by_id(item_id: str) -> Optional[dict]:
    return next((i for i in items() if i["id"] == item_id), None)


def _iso(d) -> Optional[str]:
    return d.isoformat() if d else None


class ProcurementKG:
    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
        self.g = nx.MultiDiGraph()
        self._build()

    # ------------------------------------------------------------------ build
    def _node(self, nid: str, ntype: str, label: str, **attrs):
        if nid in self.g:
            self.g.nodes[nid].update({k: v for k, v in attrs.items() if v is not None})
            self.g.nodes[nid]["type"], self.g.nodes[nid]["label"] = ntype, label
        else:
            self.g.add_node(nid, type=ntype, label=label, **{k: v for k, v in attrs.items() if v is not None})
        return nid

    def _edge(self, a: str, b: str, rel: str, **attrs):
        self.g.add_edge(a, b, key=rel, rel=rel, **{k: v for k, v in attrs.items() if v is not None})

    def _std_node(self, s: StdRecord) -> str:
        fam = self._node(f"fam:{s.family}", "standard_family", s.family, body="BIS" if s.family.startswith("IS") else "foreign")
        nid = self._node(f"std:{s.is_number}", "standard", s.is_number, title=s.title, status=s.status,
                         valid_from=_iso(s.effective_from or s.publication_date), valid_to=_iso(s.effective_to),
                         source_url=s.source_url, verification_state="curated")
        self._edge(fam, nid, "HAS_EDITION", valid_from=_iso(s.effective_from or s.publication_date), valid_to=_iso(s.effective_to))
        return nid

    def _build(self):
        kb = self.kb
        for s in kb.standards:
            self._std_node(s)
        for s in kb.standards:
            if s.superseded_by:
                nxt = kb.lookup(s.superseded_by)
                if nxt:
                    self._edge(f"std:{s.is_number}", f"std:{nxt.is_number}", "SUPERSEDED_BY", valid_from=_iso(s.effective_to))
        for r in kb.relations:
            a, b = kb.by_id.get(r.from_id), kb.by_id.get(r.to_id)
            if a and b and r.type != "superseded_by":
                self._edge(f"std:{a.is_number}", f"std:{b.is_number}", KB_REL.get(r.type, "RELATED"), clause=r.clause_reference)
        for a in kb.amendments:
            s = kb.by_id.get(a.standard_id)
            if not s:
                continue
            nid = self._node(f"amd:{s.is_number}#{a.number}", "amendment", f"Amd {a.number} to {s.is_number}", summary=a.summary,
                             valid_from=_iso(a.effective_from or a.published_at), source_url=a.source_url)
            self._edge(f"std:{s.is_number}", nid, "AMENDED_BY", valid_from=_iso(a.effective_from or a.published_at))
        for r in kb.regulations:
            nid = self._node(f"reg:{r.key}", "regulation", r.title, regulation_type=r.regulation_type, scheme=r.scheme,
                             authority=r.authority, valid_from=_iso(r.effective_from), valid_to=_iso(r.effective_to),
                             mandatory=r.mandatory, source_url=r.source_url, verification_state=r.verification_state)
            for f in r.families:
                fam_nodes = [n for n in self.g.nodes if n.startswith("fam:") and (n[4:] == f or base_number(n[4:]) == f or n[4:] == base_number(f))]
                if not fam_nodes:
                    fam_nodes = [self._node(f"fam:{f}", "standard_family", f)]
                for fn in fam_nodes:
                    self._edge(nid, fn, "MANDATES", valid_from=_iso(r.effective_from), valid_to=_iso(r.effective_to),
                               verification_state=r.verification_state)
        # parameters & test methods
        for pid, p in ontology.parameters().items():
            self._node(f"param:{pid}", "parameter", p["label"], unit=p.get("unit"), category=p.get("category"))
            t = p.get("test")
            if t:
                fam = self._family_node(t["standard"])
                self._edge(f"param:{pid}", fam, "MEASURED_BY", test=t.get("name"), discipline=t.get("discipline"), days=t.get("days"))
        for fam, sp in ontology.standards_parameters().items():
            fn = self._family_node(fam)
            for grade, bounds in (sp.get("grades") or {}).items():
                for pid, b in bounds.items():
                    if f"param:{pid}" in self.g:
                        self._edge(fn, f"param:{pid}", "SPECIFIES", grade=grade, min=b.get("min"), max=b.get("max"))
        # labs
        for lab in ontology.load_json("labs.json")["labs"]:
            ln = self._node(f"lab:{lab['id']}", "lab", lab["name"], city=lab.get("city"), accreditation=lab.get("accreditation"), synthetic=True)
            for sc in lab.get("scope", []):
                self._edge(ln, self._family_node(sc), "ACCREDITED_FOR")
        # policies
        for pol in policies():
            self._node(f"policy:{pol['key']}", "policy", pol["title"], summary=pol["summary"], source_url=pol.get("source_url"),
                       verification_state=pol.get("verification_state"), applies=pol.get("applies"))
        # items
        for it in items():
            inode = self._node(f"item:{it['id']}", "item", it["label"], domain=it["domain"], unit=it["default_unit"], hsn=it.get("hsn"))
            for s in it["standards"]:
                self._edge(inode, self._family_node(s["family"]), "GOVERNED_BY", role=s["role"])
            for sl in it["slots"]:
                if sl.get("param") and f"param:{sl['param']}" in self.g:
                    self._edge(inode, f"param:{sl['param']}", "HAS_SLOT", slot=sl["id"], basis=sl.get("basis"), default=json.dumps(sl.get("default")))
            for pol in policies():
                if pol.get("applies") in ("always", "advisory"):
                    self._edge(inode, f"policy:{pol['key']}", "SUBJECT_TO")
            for rel in it.get("related", []):
                self._edge(inode, f"item:{rel}", "CO_PROCURED_WITH")
        # market (synthetic catalogue)
        from app.engine.market import catalog
        for p in catalog():
            m = self._node(f"mfr:{p['manufacturer']}", "manufacturer", p["manufacturer"], synthetic=True)
            pn = self._node(f"prod:{p['id']}", "product", p["model"], bis_licence=p.get("bis_licence"), synthetic=True)
            self._edge(m, pn, "MAKES")
            if p.get("item"):
                self._edge(pn, f"item:{p['item']}", "INSTANCE_OF")
            self._edge(pn, self._family_node(family_of(p["standard"])), "CONFORMS_TO")

    def _family_node(self, designation: str) -> str:
        fam = family_of(designation)
        nid = f"fam:{fam}"
        if nid not in self.g:
            # try a base-number family (e.g. 'IS 228' vs 'IS 228 (Parts 1-24)')
            cand = next((n for n in self.g.nodes if n.startswith("fam:") and base_number(n[4:]) == base_number(fam) and n[4:].startswith(fam)), None)
            if cand:
                return cand
            self._node(nid, "standard_family", fam)
        return nid

    # ------------------------------------------------------------------ temporal helpers
    @staticmethod
    def _valid(attrs: dict, on: date) -> bool:
        vf, vt = attrs.get("valid_from"), attrs.get("valid_to")
        if vf and date.fromisoformat(vf) > on:
            return False
        if vt and date.fromisoformat(vt) < on:
            return False
        return True

    def resolve_designation(self, designation: str, on: date) -> dict:
        """'IS 16102 (Part 1)' -> the edition in force on `on` (e.g. 'IS 16102 (Part 1):2026'), with timeline and path."""
        prefix = designation.strip().upper()
        eds = [s for s in self.kb.standards if s.is_number.upper() == prefix or s.is_number.upper().startswith(prefix + ":")]
        if not eds:
            eds = [s for s in self.kb.standards if s.family.upper() == family_of(designation).upper()]
        eds.sort(key=lambda s: (s.effective_from or s.publication_date or date.min))
        from app.engine.temporal import _valid_on
        in_force = [s for s in eds if _valid_on(s, on)]
        chosen = in_force[-1] if in_force else None
        concurrent = [s for s in in_force[:-1]]
        res = resolve(self.kb, chosen.is_number if chosen else designation, on, horizon_days=540)
        return {
            "designation": designation, "cite_as": chosen.is_number if chosen else designation,
            "title": chosen.title if chosen else None, "status": "current" if chosen else "unknown",
            "concurrent_editions": [{"is_number": s.is_number, "valid_to": _iso(s.effective_to)} for s in concurrent],
            "timeline": [{"is_number": s.is_number, "status": s.status, "from": _iso(s.effective_from or s.publication_date),
                          "to": _iso(s.effective_to), "superseded_by": s.superseded_by} for s in eds],
            "amendments_in_force": res.amendments_in_force, "amendments_pending": res.amendments_pending,
            "source_url": chosen.source_url if chosen else None,
            "path": [f"fam:{family_of(designation)}", "HAS_EDITION", f"std:{chosen.is_number}"] if chosen else [],
        }

    def regulations_for(self, families: Iterable[str], on: date, horizon_days: int) -> Tuple[List[dict], List[dict]]:
        in_force, upcoming, seen = [], [], set()
        fams = list(families)
        for r in self.kb.regulations:
            hit = None
            for f in r.families:
                for fam in fams:
                    if f == fam or base_number(f) == fam or f == base_number(fam):
                        hit = fam
            if not hit or r.key in seen:
                continue
            seen.add(r.key)
            d = r.to_dict()
            d["via"] = hit
            d["path"] = [f"reg:{r.key}", "MANDATES", f"fam:{hit}"]
            if r.in_force(on):
                in_force.append(d)
            elif r.effective_from and on < r.effective_from <= on + timedelta(days=horizon_days):
                upcoming.append(d)
        return in_force, upcoming

    # ------------------------------------------------------------------ item queries
    def bundle(self, item_id: str, on: Optional[date] = None, horizon_days: int = 180) -> dict:
        """Everything a tender for this item must respect, as of a date — with the KG path for every fact."""
        on = on or date.today()
        it = item_by_id(item_id)
        if not it:
            raise KeyError(item_id)
        stds = []
        for s in it["standards"]:
            r = self.resolve_designation(s["family"], on)
            r["role"] = s["role"]
            r["path"] = [f"item:{item_id}", "GOVERNED_BY", f"fam:{family_of(s['family'])}"] + r["path"][1:]
            stds.append(r)
        fams = [family_of(s["family"]) for s in it["standards"]]
        regs_in, regs_up = self.regulations_for(fams, on, horizon_days)
        for g in regs_in + regs_up:
            g["path"] = [f"item:{item_id}", "GOVERNED_BY"] + g["path"][::-1][:1] + ["◀MANDATES", f"reg:{g['key']}"]
        watch = []
        for s in stds:
            for c in s["concurrent_editions"]:
                if c["valid_to"] and date.fromisoformat(c["valid_to"]) <= on + timedelta(days=horizon_days):
                    watch.append({"type": "edition_withdrawal", "date": c["valid_to"], "subject": c["is_number"],
                                  "message": f"{c['is_number']} remains valid only until {c['valid_to']} (concurrent running); the tender cites {s['cite_as']}."})
            for a in s["amendments_pending"]:
                watch.append({"type": "amendment", "date": a.get("effective_from"), "subject": s["cite_as"],
                              "message": f"Amendment {a['number']} to {s['cite_as']} takes effect on {a.get('effective_from')}."})
            for t in s["timeline"]:
                if t["from"] and on < date.fromisoformat(t["from"]) <= on + timedelta(days=horizon_days):
                    watch.append({"type": "new_edition", "date": t["from"], "subject": t["is_number"],
                                  "message": f"New edition {t['is_number']} takes effect on {t['from']}."})
        for g in regs_up:
            watch.append({"type": "regulation", "date": g.get("effective_from"), "subject": g["key"],
                          "message": f"{g['title']} comes into force on {g.get('effective_from')} — within the contract horizon."})
        # tests + labs
        tests = []
        for t in it.get("tests", []):
            fam = family_of(t["standard"])
            fn = self._family_node(t["standard"])
            labs = [self.g.nodes[u]["label"] for u, _, k in self.g.in_edges(fn, keys=True) if k == "ACCREDITED_FOR"]
            tests.append({**t, "cite_as": self.resolve_designation(t["standard"], on)["cite_as"], "labs": labs[:4],
                          "path": [f"item:{item_id}", "GOVERNED_BY", f"fam:{fam}", "◀ACCREDITED_FOR", "lab:*"]})
        pols = [p for p in policies()]
        market = self.market_summary(item_id)
        return {"item": {k: it[k] for k in ("id", "label", "domain", "default_unit", "unit_kind", "hsn")}, "as_of": on.isoformat(),
                "standards": stds, "regulations_in_force": regs_in, "regulations_upcoming": regs_up, "watchlist": sorted(watch, key=lambda w: w["date"] or ""),
                "tests": tests, "policies": [{"key": p["key"], "title": p["title"], "summary": p["summary"], "applies": p["applies"],
                                               "verification_state": p.get("verification_state"), "source_url": p.get("source_url")} for p in pols],
                "slots": it["slots"], "market": market}

    def market_summary(self, item_id: str) -> dict:
        prods = [n for n, _, k in self.g.in_edges(f"item:{item_id}", keys=True) if k == "INSTANCE_OF"]
        mfrs = {u for p in prods for u, _, k in self.g.in_edges(p, keys=True) if k == "MAKES"}
        return {"products": len(prods), "manufacturers": len(mfrs), "note": "synthetic demonstration catalogue"}

    # ------------------------------------------------------------------ graph views
    def node(self, nid: str) -> Optional[dict]:
        if nid not in self.g:
            return None
        return {"id": nid, **self.g.nodes[nid]}

    def neighbourhood(self, center: str, depth: int = 2, on: Optional[date] = None, limit: int = 120,
                      skip_types: Tuple[str, ...] = ("product", "manufacturer")) -> dict:
        if center not in self.g:
            return {"nodes": [], "edges": []}
        seen = {center: 0}
        frontier = [center]
        order = [center]
        for d in range(depth):
            nxt = []
            for n in frontier:
                # do not walk *through* hubs (policies, very connected families) — they would pull in the whole graph
                if n != center and (self.g.nodes[n].get("type") in ("policy", "parameter", "item") or self._core_degree(n) > 24):
                    continue
                nbrs = list(self.g.successors(n)) + list(self.g.predecessors(n))
                for m in nbrs:
                    if m in seen or self.g.nodes[m].get("type") in skip_types and m != center:
                        continue
                    if len(order) >= limit:
                        break
                    seen[m] = d + 1
                    order.append(m)
                    nxt.append(m)
            frontier = nxt
        nodes = []
        for n in order:
            a = self.g.nodes[n]
            valid = self._valid(a, on) if on else True
            nodes.append({"id": n, "type": a.get("type"), "label": a.get("label"), "depth": seen[n], "valid": valid,
                          **{k: a[k] for k in ("status", "valid_from", "valid_to", "verification_state", "title", "unit", "scheme") if k in a}})
        ids = set(order)
        edges = []
        for u, v, k, a in self.g.edges(keys=True, data=True):
            if u in ids and v in ids:
                edges.append({"source": u, "target": v, "rel": k, "label": REL_LABEL.get(k, k.lower()),
                              "valid": self._valid(a, on) if on else True, **{x: a[x] for x in ("role", "grade", "min", "max", "clause") if a.get(x) is not None}})
        return {"center": center, "nodes": nodes, "edges": edges}

    def _core_degree(self, n: str) -> int:
        market = {"MAKES", "INSTANCE_OF", "CONFORMS_TO"}
        return sum(1 for *_, k in self.g.in_edges(n, keys=True) if k not in market) + \
            sum(1 for *_, k in self.g.out_edges(n, keys=True) if k not in market)

    def search(self, q: str, limit: int = 20) -> List[dict]:
        ql = q.lower().strip()
        out = []
        for n, a in self.g.nodes(data=True):
            lab = (a.get("label") or "") + " " + (a.get("title") or "")
            if ql in lab.lower() or ql in n.lower():
                out.append({"id": n, "type": a.get("type"), "label": a.get("label")})
        typ_rank = {"item": 0, "standard_family": 1, "regulation": 2, "standard": 3, "policy": 4, "parameter": 5}
        out.sort(key=lambda x: (typ_rank.get(x["type"], 9), len(x["label"] or "")))
        return out[:limit]

    def explain_path(self, a: str, b: str) -> List[dict]:
        ug = self.g.to_undirected(as_view=True)
        try:
            p = nx.shortest_path(ug, a, b)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []
        steps = []
        for x, y in zip(p, p[1:]):
            if self.g.has_edge(x, y):
                k = next(iter(self.g[x][y]))
                steps.append({"from": x, "rel": k, "to": y, "text": f"{self.g.nodes[x]['label']} {REL_LABEL.get(k, k)} {self.g.nodes[y]['label']}"})
            else:
                k = next(iter(self.g[y][x]))
                steps.append({"from": y, "rel": k, "to": x, "text": f"{self.g.nodes[y]['label']} {REL_LABEL.get(k, k)} {self.g.nodes[x]['label']}"})
        return steps

    def impacted_items(self, nid: str) -> List[str]:
        """Items whose requirements change if `nid` (an edition, family or regulation) changes — reverse traversal
        over governance / normative-reference edges only (market edges are ignored)."""
        if nid not in self.g:
            return []
        follow = {"GOVERNED_BY", "NORMATIVE_REF", "TEST_METHOD", "SAFETY_REQ", "HAS_EDITION"}
        start = {nid}
        if nid.startswith("reg:"):
            start = {v for _, v, k in self.g.out_edges(nid, keys=True) if k == "MANDATES"}
        seen, stack, out = set(start), list(start), set()
        while stack:
            n = stack.pop()
            if n.startswith("item:"):
                out.add(n)
                continue
            preds = [(u, k) for u, _, k in self.g.in_edges(n, keys=True) if k in follow]
            if n.startswith("std:"):
                # an edition is reached through its family
                preds += [(u, "HAS_EDITION") for u, _, k in self.g.in_edges(n, keys=True) if k == "HAS_EDITION"]
            if n.startswith("fam:"):
                # references are recorded edition-to-edition: climb from every edition of this family
                for _, e, k in self.g.out_edges(n, keys=True):
                    if k == "HAS_EDITION":
                        preds += [(u, kk) for u, _, kk in self.g.in_edges(e, keys=True) if kk in follow - {"HAS_EDITION"}]
            for u, _ in preds:
                if u not in seen:
                    seen.add(u)
                    stack.append(u)
        return sorted(out)

    def stats(self) -> dict:
        types: Dict[str, int] = {}
        for _, a in self.g.nodes(data=True):
            types[a.get("type", "?")] = types.get(a.get("type", "?"), 0) + 1
        rels: Dict[str, int] = {}
        for _, _, k in self.g.edges(keys=True):
            rels[k] = rels.get(k, 0) + 1
        return {"nodes": self.g.number_of_nodes(), "edges": self.g.number_of_edges(), "node_types": types, "edge_types": rels,
                "snapshot": self.kb.snapshot_hash()[:16]}

    # ------------------------------------------------------------------ export
    def export_cypher(self) -> str:
        def esc(v):
            return json.dumps(v, ensure_ascii=False)
        lines = ["// SpecSure Procurement Knowledge Graph — import into Neo4j (cypher-shell < pkg.cypher)"]
        for n, a in self.g.nodes(data=True):
            label = re.sub(r"[^A-Za-z]", "", (a.get("type") or "Node").title())
            props = {k: v for k, v in a.items() if isinstance(v, (str, int, float, bool))}
            props["id"] = n
            lines.append(f"MERGE (x:{label} {{id:{esc(n)}}}) SET x += {{{', '.join(f'`{k}`:{esc(v)}' for k, v in props.items())}}};")
        for u, v, k, a in self.g.edges(keys=True, data=True):
            props = {x: y for x, y in a.items() if isinstance(y, (str, int, float, bool)) and x != "rel"}
            p = (" {" + ", ".join(f"`{x}`:{esc(y)}" for x, y in props.items()) + "}") if props else ""
            lines.append(f"MATCH (a {{id:{esc(u)}}}),(b {{id:{esc(v)}}}) MERGE (a)-[:{k}{p}]->(b);")
        return "\n".join(lines)

    def export_jsonld(self) -> dict:
        graph = []
        for n, a in self.g.nodes(data=True):
            obj = {"@id": f"urn:specsure:{n}", "@type": a.get("type"), "name": a.get("label")}
            for k in ("status", "valid_from", "valid_to", "source_url", "verification_state"):
                if a.get(k):
                    obj[k] = a[k]
            rels: Dict[str, List[str]] = {}
            for _, v, k in self.g.out_edges(n, keys=True):
                rels.setdefault(k, []).append(f"urn:specsure:{v}")
            obj.update(rels)
            graph.append(obj)
        return {"@context": {"@vocab": "https://specsure.example/pkg#", "name": "http://schema.org/name"}, "@graph": graph}


_CACHE: Dict[str, ProcurementKG] = {}


def get_kg(kb: Optional[KnowledgeBase] = None) -> ProcurementKG:
    kb = kb or seed_kb()
    h = kb.snapshot_hash()
    if h not in _CACHE:
        _CACHE.clear()
        _CACHE[h] = ProcurementKG(kb)
    return _CACHE[h]
