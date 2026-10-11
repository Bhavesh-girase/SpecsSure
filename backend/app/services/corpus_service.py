"""
Indian Standards corpus: catalogue of ~22k archived standards + the typed graph parsed from their text.

recommend(query) → the most relevant Indian Standards for a product description / specification, each with
  * why it matched (scope clause), committee, division, editions found, amendments, reaffirmation, ISO/IEC equivalence
  * allied standards grouped the way the problem statement asks: normative references, test methods, terminology,
    safety, installation, sampling, packing & marking, related product/material standards — each with the clause and
    snippet that links them
  * mandatory certification from the regulation registry (QCO / CRS / BEE …) where the standard is covered
  * edition status: the archived text's year vs. the edition in force in the curated registry, flagged when they differ

Retrieval: BM25 over title + scope + committee (always available) fused (RRF) with dense retrieval over the same text
when embeddings have been built (scripts/corpus_embed.py, multilingual-e5). Queries in Hindi etc. are translated when a
translator is available; the multilingual embeddings also match non-English queries directly.
"""
from __future__ import annotations

import gzip
import json
import math
import os
import re
import threading
from collections import defaultdict
from typing import Dict, List, Optional

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CAT = os.path.join(ROOT, "data", "corpus", "is_catalogue.jsonl.gz")
GRAPH = os.path.join(ROOT, "data", "corpus", "is_graph.jsonl.gz")
STATS = os.path.join(ROOT, "data", "corpus", "build_stats.json")
EMB = os.getenv("CORPUS_EMB_FILE") or os.path.join(ROOT, "data", "corpus", "scope_emb.npy")   # built by scripts/corpus_embed.py
EMB_IDS = EMB.replace(".npy", "_ids.json")
E5 = "intfloat/multilingual-e5-small"
MODEL_FILES = {                                    # dense index per embedding model (int8 files: scripts/quantize_emb.py)
    "BAAI/bge-m3": os.path.join(ROOT, "data", "corpus", "scope_emb_bgem3.i8.npy"),
    E5: os.path.join(ROOT, "data", "corpus", "scope_emb.npy"),
}
CERT = os.path.join(ROOT, "data", "corpus", "compulsory_certification.json")
ALIASES = os.path.join(ROOT, "data", "corpus", "procurement_aliases.json")
PORTAL = os.path.join(ROOT, "data", "corpus", "bis_portal.json.gz")        # scripts/bis_portal_catalogue.py
BIS_STATUS = os.path.join(ROOT, "data", "corpus", "bis_status.json")       # scripts/bis_portal_status.py
GEM = os.path.join(ROOT, "data", "corpus", "gem_categories.json")          # scripts/gem_categories.py
LABS = os.path.join(ROOT, "data", "corpus", "bis_labs.json")              # scripts/bis_labs.py — testing route
KYS = os.path.join(ROOT, "data", "corpus", "bis_kys.json.gz")              # scripts/bis_kys_catalogue.py — status of every standard
PORTAL_URL = "https://standardsbis.bsbedge.com/BIS_SearchStandard.aspx?Standard_Number={q}&id=0"


def portal_query(base: str) -> str:
    """'IS 10322 (Part 5/Sec 3)' → 'IS 10322 : Part 5 : Sec 3' (the portal's own designation format)."""
    m = re.match(r"(\S+ [\w.-]+)(?: \((.*)\))?$", base)
    if not m:
        return base
    q = m.group(1)
    for seg in (m.group(2) or "").split("/"):
        if seg:
            q += " : " + seg
    return q


def gem_split(name: str) -> str:
    import hashlib
    k = re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()
    return "train" if int(hashlib.md5(k.encode()).hexdigest(), 16) % 2 == 0 else "test"


def family_of(base: str) -> str:
    return re.sub(r" \(Part [^)]*\)$", "", base)

# procurement shorthand → words used in standard titles / scopes
ABBREV = {
    "hdpe": "high density polyethylene", "ldpe": "low density polyethylene", "pvc": "polyvinyl chloride pvc", "upvc": "unplasticized polyvinyl chloride pvc",
    "cpvc": "chlorinated polyvinyl chloride", "opc": "ordinary portland cement", "ppc": "portland pozzolana cement", "psc": "portland slag cement",
    "tmt": "high strength deformed steel bars thermo mechanically treated", "rebar": "deformed steel bars reinforcement",
    "sariya": "deformed steel bars reinforcement", "led": "led light emitting diode", "mcb": "miniature circuit breakers", "rccb": "residual current circuit breakers",
    "elcb": "earth leakage circuit breakers", "gi": "galvanized iron", "ms": "mild steel", "ss": "stainless steel", "di": "ductile iron", "ci": "cast iron",
    "rcc": "reinforced cement concrete", "pcc": "plain cement concrete", "aac": "autoclaved aerated concrete", "frls": "flame retardant low smoke",
    "xlpe": "cross linked polyethylene", "acsr": "aluminium conductor steel reinforced", "ups": "uninterruptible power", "cfl": "compact fluorescent lamps",
    "ac": "air conditioner", "ppe": "personal protective equipment", "pv": "photovoltaic", "bldc": "brushless dc",
    "taar": "wire cable", "bulb": "lamp", "light": "luminaires lighting lamp", "speaker": "loudspeakers", "woofer": "loudspeakers", "ladder": "ladders", "fitting": "luminaires", "tubelight": "fluorescent lamp", "geyser": "storage water heater", "paver": "paving blocks", "drinking": "potable",
    "energy": "watthour", "meter": "meters", "lpg": "liquefied petroleum gases cylinders", "cylinder": "welded low carbon steel cylinders",
    "enamel": "enamel synthetic", "napkin": "sanitary napkins", "footwear": "footwear shoes", "tank": "storage tanks", "tubelight": "fluorescent lamp", "pankha": "fan", "cement": "cement", "paint": "paint enamel",
}


KIND_LABEL = {
    "normative": "Normative references (Clause 2 of the standard)",
    "test_method": "Test methods", "terminology": "Terminology", "safety": "Safety", "installation": "Installation & code of practice",
    "sampling": "Sampling", "packaging_marking": "Packing & marking", "material": "Materials & components",
    "dimensions": "Dimensions & tolerances",
    "allied_product": "Related product standards",
}
DEPENDENCY_KINDS = {"test_method", "sampling", "terminology", "material", "packaging_marking", "dimensions", "safety", "installation"}
STOP = set("a an the of for and or to in on with by at from as is are be this that shall used use using type types "
           "specification standard indian requirements general part section".split())
ACCESSORY = {"fitting", "accessory", "accessorie", "component", "spare", "joint", "coupling", "flange", "gasket", "clamp", "bracket",
             "adaptor", "adapter", "valve", "handle", "cap", "cover", "lid", "part", "tool", "gauge", "mould", "die"}
GUIDE_RE = re.compile(r"\b(code of practice|guide|guidelines|recommendations?|glossary|handbook|layout|design of|selection|storage|stacking|"
                      r"installation|maintenance|safety code)\b", re.I)
CONF_HIGH_COV = float(os.getenv("CORPUS_CONF_HIGH_COV", "0.6"))
CONF_MED_COV = float(os.getenv("CORPUS_CONF_MED_COV", "0.4"))
PRIOR_W = float(os.getenv("CORPUS_PRIOR_W", "0.006"))
DENSE_W = float(os.getenv("CORPUS_DENSE_W", "1.0"))
GEM_PRIOR_W = float(os.getenv("CORPUS_GEM_PRIOR_W", "0.004"))
WITHDRAWN_DEMOTE = int(os.getenv("CORPUS_WITHDRAWN_DEMOTE", "6"))
ASPECT_KIND = {"methods of tests": "test_method", "terminology": "terminology", "dimensions": "dimensions"}
PORTAL_DEMOTE = int(os.getenv("CORPUS_PORTAL_DEMOTE", "2"))     # title-only standards (no scope text) rank after equally good archived ones
TEST_Q = re.compile(r"\b(test|testing|method|methods|determination|measurement|sampling|glossary|vocabulary|terminology)\b", re.I)


def _stem(w: str) -> str:
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 4 and w.endswith(("ses", "xes", "ches", "shes")):
        return w[:-2]
    if len(w) > 3 and w.endswith("s") and not w.endswith(("ss", "us", "is")):
        return w[:-1]
    return w


def _tok(s: str) -> List[str]:
    return [_stem(w) for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if w not in STOP and len(w) > 1]


def confidence(sig: dict) -> str:
    """high / medium / low from agreement between the lexical and dense retrievers and query-word coverage.
    Thresholds calibrated on data/evaluation (see scripts/corpus_benchmark.py → calibration)."""
    lr, dr, cov = sig.get("lex_rank"), sig.get("dense_rank"), sig.get("coverage") or 0.0
    if (sig.get("alias") or "").startswith("exact:"):
        return "high"
    alias_contains = (sig.get("alias") or "").startswith("contains:")
    both = lr is not None and lr < 5 and (not sig.get("dense_available") or (dr is not None and dr < 10))
    if both and cov >= CONF_HIGH_COV:
        return "high"
    if alias_contains or (cov >= CONF_MED_COV and ((lr is not None and lr < 15) or (dr is not None and dr < 5))):
        return "medium"
    return "low"


def _title_kind(title: str) -> str:
    from app.engine.corpus_parse import kind_from_title
    return kind_from_title(title)


def _norm_phrase(s: str) -> str:
    return " ".join(_stem(w) for w in re.findall(r"[a-z0-9]+", (s or "").lower()))


def expand_query(q: str) -> str:
    extra = [ABBREV[w] for w in re.findall(r"[a-z]+", q.lower()) if w in ABBREV]
    return q + (" " + " ".join(extra) if extra else "")


class Corpus:
    def __init__(self):
        self.ready = False
        self.catalogue: Dict[str, List[dict]] = defaultdict(list)
        self.graph: Dict[str, dict] = {}
        self.cited_by: Dict[str, List[dict]] = defaultdict(list)
        self.docs: List[str] = []
        self.emb = None
        self.emb_ids: List[str] = []
        self.cert: Dict[str, List[dict]] = defaultdict(list)
        self.portal: Dict[str, dict] = {}
        self.portal_meta: dict = {}
        self.bis_status: Dict[str, dict] = {}
        self.bis_status_meta: dict = {}
        self.gem: Dict[str, List[dict]] = defaultdict(list)
        self.gem_meta: dict = {}
        self.kys: Dict[str, dict] = {}
        self.kys_meta: dict = {}
        self.labs: Dict[str, dict] = {}
        self.labs_meta: dict = {}

    # ------------------------------------------------------------------ loading
    def load(self):
        if not os.path.exists(CAT):
            return self
        for line in gzip.open(CAT, "rt", encoding="utf-8"):
            r = json.loads(line)
            if r["variant"] != "hindi":
                self.catalogue[r["base"]].append(r)
        for eds in self.catalogue.values():
            eds.sort(key=lambda e: e["year"] or 0)
        self._load_portal()
        self._fill_divisions()
        if os.path.exists(GRAPH):
            for line in gzip.open(GRAPH, "rt", encoding="utf-8"):
                g = json.loads(line)
                self.graph[g["base"]] = g
                for rel in g["relations"]:
                    self.cited_by[rel["base"]].append({"base": g["base"], "clauses": rel["clauses"]})
        from app.engine.corpus_parse import relation_kind
        _kind_cache: Dict[str, str] = {}
        for g in self.graph.values():                 # re-type relations with the cited standard's (portal-updated) title
            for rel in g["relations"]:
                k = _kind_cache.get(rel["base"])
                if k is None:
                    k = _kind_cache[rel["base"]] = relation_kind(self.title_of(rel["base"])) if rel["base"] in self.catalogue else rel["kind"]
                rel["kind"] = k
        if os.path.exists(CERT):
            for r in json.load(open(CERT, encoding="utf-8"))["rows"]:
                self.cert[r["base"]].append(r)
        # product-name aliases: BIS's own product names from the compulsory-certification list + buyer trade names
        self.aliases: Dict[str, List[str]] = defaultdict(list)
        if os.getenv("CORPUS_ALIASES", "1") != "0":
            for b, rows in self.cert.items():
                self.aliases[b] += [r.get("product") or "" for r in rows]
            if os.path.exists(ALIASES):
                for b, names in json.load(open(ALIASES, encoding="utf-8"))["aliases"].items():
                    self.aliases[b] += names
            if os.getenv("CORPUS_GEM_ALIASES", "1") != "0":
                split = os.getenv("CORPUS_GEM_ALIAS_SPLIT")          # "train": only half of the GeM names (held-out evaluation)
                for b, cats in self.gem.items():
                    self.aliases[b] += [x["category"] for x in cats if not split or gem_split(x["category"]) == split]
        self.alias_phrases: Dict[str, List[str]] = defaultdict(list)     # normalised phrase → standards
        for b, names in self.aliases.items():
            for n in names:
                k = _norm_phrase(n)
                if len(k) >= 3 and b not in self.alias_phrases[k]:
                    self.alias_phrases[k].append(b)
        self._build_bm25()
        try:                                          # vocabulary for reading English loanwords written in Indic scripts
            from app.services import translit
            names = [self.title_of(b) for b in self.catalogue] + [x["category"] for v in self.gem.values() for x in v] + list(ABBREV.values()) + [" ".join(ABBREV)] * 3
            translit.set_vocabulary(*translit.title_vocabulary(names))
        except Exception:  # noqa: BLE001
            pass
        self._load_embeddings()
        self._pos = {b: i for i, b in enumerate(self.docs)}
        self._max_cited = math.log1p(max((len(v) for v in self.cited_by.values()), default=1)) or 1.0
        self.ready = True
        return self

    def _load_portal(self):
        """BIS e-Sale portal: current editions (+ standards published after the archive), status and amendments of key
        standards, and GeM categories that name a standard. Portal-only standards join the catalogue title-only."""
        if os.path.exists(PORTAL) and os.getenv("CORPUS_PORTAL", "1") != "0":
            d = json.load(gzip.open(PORTAL, "rt", encoding="utf-8"))
            self.portal, self.portal_meta = d["standards"], d["meta"]
            for b, e in self.portal.items():
                if b in self.catalogue or re.search(r"\bH\d|\(HINDI\)|BI-LINGUAL", b + " " + e["title"], re.I):
                    continue
                if not re.search(r"[A-Za-z]{3,}", e["title"]):
                    continue
                self.catalogue[b].append({"base": b, "designation": f"{b}:{e['current']}", "year": e["current"], "variant": None,
                                          "title": e["title"], "division": None, "committee": None, "committee_code": None,
                                          "amendments": None, "equivalence": None, "supersedes_raw": None, "superseded_by_raw": None,
                                          "source": PORTAL_URL.format(q=portal_query(b).replace(" ", "%20")), "origin": "bis_portal"})
        if os.path.exists(LABS):
            d = json.load(open(LABS, encoding="utf-8"))
            self.labs, self.labs_meta = d["standards"], d["meta"]
        if os.path.exists(KYS) and os.getenv("CORPUS_PORTAL", "1") != "0":
            d = json.load(gzip.open(KYS, "rt", encoding="utf-8"))
            self.kys, self.kys_meta = d["standards"], d["meta"]
        if os.path.exists(BIS_STATUS):
            d = json.load(open(BIS_STATUS, encoding="utf-8"))
            self.bis_status, self.bis_status_meta = d["standards"], d["meta"]
        if os.path.exists(GEM):
            d = json.load(open(GEM, encoding="utf-8"))
            self.gem_meta = d["meta"]
            fams: Dict[str, List[str]] = defaultdict(list)
            for b in self.catalogue:
                fams[family_of(b)].append(b)
            for x in d["categories"]:
                targets = [x["standard"]] if x["standard"] in self.catalogue else fams.get(x["standard"], [])[:8]
                for b in targets:
                    self.gem[b].append(x)

    def _fill_divisions(self):
        """BIS division for every standard: from the archive record, else from the technical-committee code prefix
        (CED → Civil Engineering, ETD → Electrotechnical …, learned from the archive), else unknown."""
        votes: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for eds in self.catalogue.values():
            e = eds[-1]
            code = (e.get("committee_code") or "").split(" ")[0]
            if e.get("division") and code:
                votes[re.sub(r"\d+", "", code)][e["division"]] += 1
        prefix_div = {k: max(v.items(), key=lambda kv: kv[1])[0] for k, v in votes.items()}
        self.division_of: Dict[str, Optional[str]] = {}
        for b, eds in self.catalogue.items():
            e = eds[-1]
            div = next((x.get("division") for x in reversed(eds) if x.get("division")), None)
            if not div:
                code = e.get("committee_code") or (self.bis_status.get(b) or {}).get("committee") or (self.kys.get(b) or {}).get("committee") or ""
                div = prefix_div.get(re.sub(r"[\d\s]+", "", code.split(" ")[0]) if code else "")
            self.division_of[b] = div
        self.divisions = sorted({d for d in self.division_of.values() if d})

    def edition_status(self, base: str) -> dict:
        """Edition in force, status and amendments — BIS portal first (dated), then the archive."""
        eds = self.catalogue.get(base) or []
        archived = [e for e in eds if e.get("origin") != "bis_portal"]
        arch_year = archived[-1]["year"] if archived else None
        p = self.portal.get(base)
        st = self.bis_status.get(base)
        fetched = self.portal_meta.get("fetched") or self.bis_status_meta.get("fetched")
        out = {"base": base, "archived_year": arch_year, "source": None, "fetched": fetched, "status": None,
               "edition_in_force": None, "title_in_force": None, "reaffirmed": None, "amendments": [], "amendments_count": None,
               "concurrent": [], "committee": None, "equivalent": None, "newer_than_archive": False, "in_portal": bool(p)}
        if st:
            out.update({"source": "BIS e-Sale portal (standard page)", "status": st["status"], "edition_in_force": st["edition"],
                        "title_in_force": st["title"], "reaffirmed": st.get("reaffirmed"), "amendments": st.get("amendments") or [],
                        "amendments_count": st.get("amendments_count"), "committee": st.get("committee"), "equivalent": st.get("equivalent"),
                        "superseded_by": st.get("superseded_by")})
            if st["status"].lower() == "withdrawn":
                out["replacement"] = self._replacement(st.get("superseded_by"))
        elif self.kys.get(base):
            k = self.kys[base]
            stt = (k.get("status") or "").strip()
            withdrawn = stt.lower().startswith("withdrawn")
            out.update({"source": "BIS Know-Your-Standards catalogue", "status": "Withdrawn" if withdrawn else ("Active" if stt.lower().startswith("active") else (stt or "Listed")),
                        "edition_in_force": k["edition"], "title_in_force": k.get("title"), "committee": k.get("committee"),
                        "amendments_count": k.get("amendments"), "equivalent": k.get("equivalent"), "fetched": self.kys_meta.get("fetched"),
                        "aspect": k.get("aspect"), "iso_degree": k.get("iso_degree")})
            if withdrawn:
                note = k.get("withdrawn_note")
                out["superseded_by"] = note if isinstance(note, str) and len(note) > 2 else None
                out["replacement"] = self._replacement(out["superseded_by"])
        elif p:
            out.update({"source": "BIS e-Sale portal (catalogue)", "status": "Listed", "edition_in_force": f"{base}:{p['current']}",
                        "title_in_force": p["title"]})
        elif base in self.bis_status_meta.get("not_found_in_active_search", []) or (self.portal and archived):
            out.update({"source": "BIS e-Sale portal (not listed)", "status": "Not listed"})
        if p:
            out["concurrent"] = [f"{base}:{y}" for y, _, flag in p["editions"] if flag == "concurrent"]
        yr = int(out["edition_in_force"].rsplit(":", 1)[1]) if out["edition_in_force"] else None
        out["year_in_force"] = yr
        out["newer_than_archive"] = bool(yr and arch_year and yr > arch_year)
        return out

    def _replacement(self, txt: Optional[str]) -> Optional[str]:
        """'IS 269 : 2015' / 'IS/IEC 60947-1:2004' / 'IS 1180 (PART 1) : 2014' → a designation in the catalogue."""
        if not txt:
            return None
        m = re.match(r"\s*((?:IS|SP)(?:/[A-Z]+)*)\s*([\w.]+?)(?:-(\d+))?\s*(?:\(\s*PART\s*(\w+)\s*\)|:\s*Part\s*(\w+))?\s*(?::\s*\d{4})?(?:\s|,|$)", txt, re.I)
        if not m:
            return None
        part = m.group(3) or m.group(4) or m.group(5)
        b = f"{m.group(1).upper()} {m.group(2)}" + (f" (Part {part})" if part else "")
        if b in self.catalogue:
            return b
        fam = f"{m.group(1).upper()} {m.group(2)}"
        return fam if fam in self.catalogue else b

    def title_of(self, base: str) -> str:
        for e in reversed(self.catalogue.get(base) or []):
            t = (e.get("title") or "").strip()
            if t and not t.startswith("gov.in.") and len(t) > 3:
                return t
        return base

    def _fields_of(self, base: str):
        eds = self.catalogue[base]
        latest = eds[-1]
        g = self.graph.get(base) or {}
        titles = []
        for e in eds:
            t = (e.get("title") or "").strip()
            if t and not t.startswith("gov.in.") and t.lower() not in [x.lower() for x in titles]:
                titles.append(t)
        p = self.portal.get(base)
        if p:
            for _, t, _f in p["editions"][-2:]:
                if t and t.lower() not in [x.lower() for x in titles]:
                    titles.append(t)
        title = f"{base} " + " ".join(titles)
        body = " ".join(x for x in [g.get("scope") or "", latest.get("committee") or ""] if x)
        return title, body

    def _build_bm25(self):
        """Two-field BM25 (title weighted 2×, scope + committee 1×)."""
        self.docs = list(self.catalogue.keys())
        self.fields = {}
        for name in ("title", "body", "alias"):
            tf, df, lens = [], defaultdict(int), []
            for b in self.docs:
                toks = _tok(" ".join(self.aliases.get(b, []))) if name == "alias" else _tok(self._fields_of(b)[0 if name == "title" else 1])
                c: Dict[str, int] = defaultdict(int)
                for t in toks:
                    c[t] += 1
                tf.append(c)
                lens.append(len(toks))
                for t in c:
                    df[t] += 1
            n = len(self.docs)
            post: Dict[str, List[int]] = defaultdict(list)
            for i, c in enumerate(tf):
                for t in c:
                    post[t].append(i)
            self.fields[name] = {"tf": tf, "lens": lens, "avgdl": (sum(lens) / n) if n else 1, "post": post,
                                 "idf": {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}}

    def _bm25(self, query: str, k: int = 60) -> List[tuple]:
        q = set(_tok(query))
        scores: Dict[int, float] = defaultdict(float)
        k1, bb = 1.2, 0.75
        for name, w in (("title", 2.0), ("body", 1.0), ("alias", 1.5)):
            f = self.fields[name]
            for t in q:
                idf = f["idf"].get(t)
                if not idf:
                    continue
                for i in f["post"][t]:
                    x = f["tf"][i][t]
                    scores[i] += w * idf * x * (k1 + 1) / (x + k1 * (1 - bb + bb * f["lens"][i] / max(1, f["avgdl"])))
        return sorted(scores.items(), key=lambda kv: -kv[1])[:k]

    def _load_embeddings(self, model_name: Optional[str] = None):
        from app.config import settings
        name = model_name or settings.CORPUS_EMBEDDING_MODEL
        path = os.getenv("CORPUS_EMB_FILE") or MODEL_FILES.get(name) or EMB
        ids_path = path.replace(".i8.npy", "_ids.json").replace(".npy", "_ids.json") if path.endswith(".i8.npy") else path.replace(".npy", "_ids.json")
        self._emb_for = name
        if not (os.path.exists(path) and os.path.exists(ids_path)):
            self.emb = None
            return
        try:
            import numpy as np
            if path.endswith(".i8.npy"):
                q = np.load(path)
                scale = np.load(path.replace(".i8.npy", ".scale.npy")).astype("float32")
                self.emb = q.astype("float32") * (scale[:, None] / 127.0)
            else:
                self.emb = np.load(path).astype("float32")
            self.emb_ids = json.load(open(ids_path))
        except Exception:  # noqa: BLE001
            self.emb = None

    def _dense(self, query: str, k: int = 60) -> List[tuple]:
        if self.emb is None:
            return []
        import numpy as np
        m = corpus_model()
        if m is None:
            return []
        if getattr(self, "_emb_for", None) != _active_name:          # model fell back (e.g. bge-m3 not downloadable) → matching index
            self._load_embeddings(_active_name)
            if self.emb is None:
                return []
        v = np.asarray(m.encode([query_prefix(_active_name) + query], normalize_embeddings=True, show_progress_bar=False)[0], dtype="float32")
        if v.shape[0] != self.emb.shape[1]:
            return []
        v /= (np.linalg.norm(v) or 1)
        sims = self.emb @ v
        idx = np.argsort(-sims)[:k]
        pos = {b: i for i, b in enumerate(self.docs)}
        return [(pos[self.emb_ids[i]], float(sims[i])) for i in idx if self.emb_ids[i] in pos]

    # ------------------------------------------------------------------ queries
    def stats(self) -> dict:
        if getattr(self, "_stats", None) is None:
            self._stats = self._compute_stats()
        return self._stats

    def _compute_stats(self) -> dict:
        s = json.load(open(STATS)) if os.path.exists(STATS) else {}
        kinds: Dict[str, int] = defaultdict(int)
        for g in self.graph.values():
            for r in g["relations"]:
                kinds[r["kind"]] += 1
        archived = {b for b, eds in self.catalogue.items() if any(e.get("origin") != "bis_portal" for e in eds)}
        newer = 0
        for b in archived & set(self.portal):
            ay = max((e["year"] or 0) for e in self.catalogue[b] if e.get("origin") != "bis_portal")
            if self.portal[b]["current"] > ay:
                newer += 1
        layers = {"archive_designations": len(archived), "portal_only_designations": len(self.catalogue) - len(archived),
                  "portal_designations": len(self.portal), "portal_fetched": self.portal_meta.get("fetched"),
                  "portal_newer_edition_than_archive": newer,
                  "status_checked": len(self.bis_status), "status_withdrawn": sum(1 for v in self.bis_status.values() if v["status"] == "Withdrawn"),
                  "amendments_listed": sum(len(v.get("amendments") or []) for v in self.bis_status.values()),
                  "gem_categories": self.gem_meta.get("categories"), "gem_bids_harvested": self.gem_meta.get("harvested_bids"),
                  "catalogue_status": len(self.kys), "catalogue_withdrawn": sum(1 for v in self.kys.values() if (v.get("status") or "").lower().startswith("withdrawn")),
                  "catalogue_aspect": sum(1 for v in self.kys.values() if v.get("aspect")),
                  "labs_standards": len(self.labs), "labs_distinct": self.labs_meta.get("distinct_labs"), "labs_entries": self.labs_meta.get("lab_entries"),
                  "certification_rows": sum(len(v) for v in self.cert.values()), "relation_kinds": dict(kinds)}
        return {"designations": len(self.catalogue), "documents": sum(len(v) for v in self.catalogue.values()), "layers": layers,
                "parsed_with_text": len(self.graph), "relations": sum(len(g["relations"]) for g in self.graph.values()),
                "dense_index": self.emb is not None, "build": s,
                "divisions": _count(e[-1]["division"] for e in self.catalogue.values()),
                "source": "Internet Archive — Public.Resource.Org collection of Indian Standards (CC0 label, Right to Information Act 2005)"}

    def certification(self, base: str) -> List[dict]:
        """Compulsory-certification rows from the BIS scheme pages for this standard (or its parent part)."""
        rows = list(self.cert.get(base, []))
        parent = re.sub(r"/Sec \d+\)$", ")", base)
        if parent != base:
            rows += [dict(r, matched_via=parent) for r in self.cert.get(parent, [])]
        return rows

    def search(self, query: str, k: int = 20, dense_query: Optional[str] = None, alias_query: Optional[str] = None,
               division: Optional[str] = None) -> List[dict]:
        """dense_query: the original (possibly non-English) text — the multilingual embeddings match it directly,
        while BM25 uses the English / translated form."""
        lex = self._bm25(expand_query(query), 80)
        dens = [self._dense(query, 80)]
        if dense_query and dense_query != query:
            dens.append(self._dense(dense_query, 80))
        want_tests = bool(TEST_Q.search(query))

        qwords = set(_tok(query))

        def demote(i: int) -> int:
            base = self.docs[i]
            title = self.title_of(base)
            k = self.kys.get(base) or {}
            aspect = (k.get("aspect") or "").lower()
            kind = ASPECT_KIND.get(aspect) or (self.graph.get(base) or {}).get("doc_kind") or _title_kind(title)
            d = 0
            if WITHDRAWN_DEMOTE and (k.get("status") or "").lower().startswith("withdrawn"):
                d += WITHDRAWN_DEMOTE           # withdrawn standards stay findable but rank after standards in force
            if not want_tests and kind in ("test_method", "terminology", "sampling"):
                d += 6                      # product queries should surface product standards first
            tw = set(_tok(title))
            acc = (tw & ACCESSORY) - qwords
            if acc:
                d += 4                      # "pipes" should not rank "pipe fittings" first unless fittings were asked for
            if not want_tests and (aspect == "code of practice" or (not aspect and GUIDE_RE.search(title))) and not GUIDE_RE.search(query):
                d += 3                      # codes of practice / guides / recommendations after product specifications
            if base.startswith("SP "):
                d += 3
            if base not in self.graph and (self.catalogue.get(base) or [{}])[-1].get("origin") == "bis_portal":
                d += PORTAL_DEMOTE
            return d

        fused: Dict[int, float] = defaultdict(float)
        for li, lst in enumerate([lex] + dens):
            w = 1.0 if li == 0 else DENSE_W
            for rank, (i, _) in enumerate(lst):
                fused[i] += w / (20 + rank + demote(i))
        # product-name alias: the buyer's words equal (or contain) a product name BIS / buyers use for a standard
        alias_hit: Dict[int, str] = {}
        qn = _norm_phrase(alias_query or query)
        pos_of = self._pos
        for phrase, bases in self.alias_phrases.items():
            exact = phrase == qn
            contained = not exact and len(phrase.split()) >= 2 and f" {phrase} " in f" {qn} "
            if exact or contained:
                for b in bases:
                    i = pos_of.get(b)
                    if i is not None and (i not in alias_hit or exact):
                        fused[i] += 0.12 if exact else 0.05
                        alias_hit[i] = ("exact:" if exact else "contains:") + phrase
        # authority prior: standards that many other standards depend on are more likely to be the main product
        # standard (small nudge; certification status is shown but deliberately NOT used for ranking)
        use_gem = GEM_PRIOR_W > 0 and os.getenv("CORPUS_ALIASES", "1") != "0" and os.getenv("CORPUS_GEM_ALIASES", "1") != "0"
        for i in list(fused):
            fused[i] += PRIOR_W * math.log1p(len(self.cited_by.get(self.docs[i], ()))) / self._max_cited
            if use_gem and self.gem.get(self.docs[i]):
                # procurement prior: how often GeM buyers actually buy against this standard (live bids) — off in benchmarks
                fused[i] += GEM_PRIOR_W * math.log1p(sum(x["bids"] for x in self.gem[self.docs[i]])) / 5.5
        out = sorted(((i, sc) for i, sc in fused.items()), key=lambda kv: -kv[1])
        if division:                                   # structured intake: restrict to one BIS division (metadata filter)
            out = [(i, sc) for i, sc in out if self.division_of.get(self.docs[i]) == division]
        lex_rank = {i: r for r, (i, _) in enumerate(lex)}
        lex_score = {i: sc for i, sc in lex}
        den_rank: Dict[int, int] = {}
        for lst in dens:
            for r, (i, _) in enumerate(lst):
                den_rank[i] = min(r, den_rank.get(i, 999))
        cards = []
        for pos, (i, sc) in enumerate(out[:k]):
            c = self.card(self.docs[i], score=sc)
            sig = {"alias": alias_hit.get(i), "lex_rank": lex_rank.get(i), "lex_score": round(lex_score.get(i, 0.0), 2), "dense_rank": den_rank.get(i),
                   "coverage": self._coverage(query, self.docs[i]), "dense_available": any(dens),
                   "margin": round(sc - out[pos + 1][1], 5) if pos + 1 < len(out) else None}
            c["signals"] = sig
            c["confidence"] = confidence(sig)
            if c.get("origin") == "bis_portal" and c["confidence"] == "high":
                c["confidence"] = "medium"            # title only (no scope text to confirm the match) → at most "possible"
                sig["title_only"] = True
            if (c.get("aspect") or "").lower() in ("system standard", "service specification", "process specification") and c["confidence"] == "high":
                c["confidence"] = "medium"            # management-system / service standards rarely are the product standard a tender needs
            if c.get("withdrawn") and c["confidence"] == "high":
                c["confidence"] = "medium"            # a withdrawn standard is never "recommended" — its replacement is shown instead
                sig["withdrawn"] = True
            cards.append(c)
        return cards

    def _coverage(self, query: str, base: str) -> float:
        """Share of the query's content words (after procurement-shorthand expansion) found in the standard's titles + scope."""
        q = {w for w in _tok(query) if not w.isdigit() and len(w) > 2}
        if not q:
            return 0.0
        title, body = self._fields_of(base)
        have = set(_tok(title)) | set(_tok(body)) | set(_tok(" ".join(self.aliases.get(base, []))))
        exp = set(_tok(expand_query(query))) - set(_tok(query))
        hit = {w for w in q if w in have}
        # a shorthand word counts as covered when its expansion is covered ("hdpe" → "polyethylene")
        for w in q - hit:
            if w in ABBREV and set(_tok(ABBREV[w])) & have:
                hit.add(w)
        return round(len(hit) / len(q), 2) if q else 0.0

    def card(self, base: str, score: Optional[float] = None) -> dict:
        eds = self.catalogue.get(base) or []
        if not eds:
            return {"base": base, "known": False}
        latest = eds[-1]
        archived = [e for e in eds if e.get("origin") != "bis_portal"]
        g = self.graph.get(base) or {}
        return {"base": base, "known": True, "title": self.title_of(base), "division": self.division_of.get(base) if hasattr(self, "division_of") else latest["division"], "committee": latest["committee"],
                "committee_code": latest["committee_code"], "latest_archived_year": archived[-1]["year"] if archived else None,
                "editions": [e["year"] for e in archived if e["year"]], "amendments": latest["amendments"], "equivalence": latest["equivalence"],
                "supersedes_raw": latest.get("supersedes_raw"), "superseded_by_raw": latest.get("superseded_by_raw"),
                "scope": g.get("scope"), "doc_kind": g.get("doc_kind"), "revision": g.get("revision"), "reaffirmed": g.get("reaffirmed"),
                "equivalents": g.get("equivalents") or [], "parsed": bool(g), "score": round(score, 5) if score is not None else None,
                "source": latest["source"], "origin": latest.get("origin", "archive"),
                "withdrawn": ((self.kys.get(base) or {}).get("status") or "").lower().startswith("withdrawn") or (self.bis_status.get(base) or {}).get("status") == "Withdrawn",
                "aspect": (self.kys.get(base) or {}).get("aspect"),
                "labs": ({"count": self.labs[base]["count"], "min_charges": self.labs[base]["min_charges"], "cities": len(self.labs[base]["cities"])}
                         if base in self.labs else None),
                "gem_categories": [{"category": x["category"], "bids": x["bids"]} for x in self.gem.get(base, [])[:4]]}

    def dependency_tree(self, base: str, depth: int = 2, normative_only: bool = True, max_nodes: int = 120) -> dict:
        """Transitive closure of what a standard pulls in: its normative references (clause 2 / Annex A), their normative
        references, and so on — the full set of documents a supplier must satisfy when a tender cites `base`.
        Every edge carries the clause it was read from; withdrawn nodes are marked with their replacement."""
        nodes: Dict[str, dict] = {}
        edges: List[dict] = []
        frontier = [base]
        nodes[base] = {"base": base, "title": self.title_of(base), "depth": 0, "kind": "root"}
        for d in range(1, max(1, min(depth, 4)) + 1):
            nxt = []
            for b in frontier:
                for r in (self.graph.get(b) or {}).get("relations", []):
                    normative = "references" in r["clauses"] or r["kind"] in DEPENDENCY_KINDS
                    if normative_only and not normative:
                        continue
                    if r["base"] == b:
                        continue
                    edges.append({"from": b, "to": r["base"], "kind": r["kind"], "normative": normative, "clauses": r["clauses"],
                                  "cited_edition": r.get("year"), "snippet": (r.get("snippet") or "")[:160]})
                    if r["base"] not in nodes and len(nodes) < max_nodes:
                        es = self.edition_status(r["base"]) if r["base"] in self.catalogue else {}
                        nodes[r["base"]] = {"base": r["base"], "title": self.title_of(r["base"]) if r["base"] in self.catalogue else None,
                                            "depth": d, "kind": r["kind"], "known": r["base"] in self.catalogue,
                                            "status": es.get("status"), "edition_in_force": es.get("edition_in_force"),
                                            "replacement": es.get("replacement")}
                        nxt.append(r["base"])
            frontier = nxt
            if not frontier:
                break
        edges = [e for e in edges if e["to"] in nodes]
        by_depth: Dict[int, int] = defaultdict(int)
        for n in nodes.values():
            by_depth[n["depth"]] += 1
        return {"base": base, "depth": depth, "normative_only": normative_only, "nodes": list(nodes.values()), "edges": edges,
                "counts": {"nodes": len(nodes) - 1, "edges": len(edges), "by_depth": dict(by_depth),
                           "withdrawn": sum(1 for n in nodes.values() if n.get("status") == "Withdrawn")},
                "truncated": len(nodes) >= max_nodes}

    def allied(self, base: str, limit_per_kind: int = 12) -> dict:
        g = self.graph.get(base)
        groups: Dict[str, List[dict]] = defaultdict(list)
        if g:
            for r in g["relations"]:
                c = self.card(r["base"])
                item = {"base": r["base"], "title": c.get("title"), "cited_edition": r["year"], "latest_archived_year": c.get("latest_archived_year"),
                        "clauses": r["clauses"], "snippet": r["snippet"], "kind": r["kind"]}
                if "references" in r["clauses"]:
                    groups["normative"].append(item)
                if r["kind"] != "allied_product" or "references" not in r["clauses"]:
                    groups[r["kind"]].append(item)
        cited = self.cited_by.get(base, [])
        return {"groups": [{"kind": k, "label": KIND_LABEL.get(k, k), "items": v[:limit_per_kind], "total": len(v)}
                           for k, v in sorted(groups.items(), key=lambda kv: list(KIND_LABEL).index(kv[0]) if kv[0] in KIND_LABEL else 99)],
                "cited_by": [{"base": c["base"], "title": self.card(c["base"]).get("title"), "clauses": c["clauses"]} for c in cited[:25]],
                "cited_by_total": len(cited)}


ADMIN_RE = re.compile(r"\b(bid|bidder|emd|earnest|validity|payment|submission|tender fee|deadline|penalty|liquidated|arbitration|"
                      r"jurisdiction|signature|telephone|e-?mail|publication|opening|pre-?bid|corrigendum|estimated cost|delivery|warranty)\b", re.I)
TECH_RE = re.compile(r"\b(\d+(?:\.\d+)?\s*(?:mm|cm|m|kg|g|mpa|n/mm2?|v|kv|w|kw|kva|a|ma|hz|%|°c|sq\.? ?mm|litres?|l|lm/w)\b|grade|conform|"
                     r"specification|material|shall be of|made of|type|class|IS \d)", re.I)
SUBJECT_RE = re.compile(r"(?:Name of Work\s*[:\-]\s*|^\s*(?:Supply|Procurement|Purchase|Providing|Supply and installation) of\s+)([^\n]{6,160})", re.I | re.M)
HEAD_RE = re.compile(r"^\s*(\d{1,2})\.?\s+([A-Z][A-Za-z &/,\-()]{2,60})\s*$", re.M)


def recommend_document(pages: List[dict], k: int = 10) -> dict:
    """Standards for a whole document (tender / specification).

    Queries are built from the document's structure: the subject ("Supply of …" / "Name of Work"), each technical section
    (heading + its clauses) and each technical clause read in the context of its section heading. Evidence = the text
    that pulled each standard. IS numbers already cited in the document are reported separately."""
    from app.engine.corpus_parse import citations as find_cites, normalise
    c = get_corpus()
    cited: Dict[str, dict] = {}
    queries: List[tuple] = []                 # (weight, page, query, evidence)
    for p in pages:
        txt = normalise(p["text"])
        for x in find_cites(txt, set(c.catalogue)):
            cited.setdefault(x["base"], {"base": x["base"], "year": x["year"], "page": p["page"]})
        for m in SUBJECT_RE.finditer(txt[:4000]):
            subj = m.group(1).strip(" .")
            queries.append((3.0, p["page"], subj, m.group(0).strip()))
        heads = list(HEAD_RE.finditer(txt))
        spans = [(h.group(2).strip(), h.end(), heads[i + 1].start() if i + 1 < len(heads) else len(txt)) for i, h in enumerate(heads)] or \
                [("", 0, len(txt))]
        for head, s0, s1 in spans:
            body = txt[s0:s1]
            clauses = [re.sub(r"\s+", " ", x).strip() for x in re.split(r"\n(?=\s*\d+(?:\.\d+)+\s)", body) if x.strip()]
            tech = [cl for cl in clauses if TECH_RE.search(cl) and not (ADMIN_RE.search(cl) and not re.search(r"\bIS \d", cl))]
            if not tech or ADMIN_RE.search(head):
                continue
            queries.append((2.0, p["page"], f"{head} " + " ".join(tech)[:600], f"{head}: " + " ".join(tech)[:240]))
            for cl in tech[:12]:
                queries.append((1.0, p["page"], f"{head} {cl}"[:500], cl[:240]))
    agg: Dict[str, dict] = {}
    for w, page, q, ev in queries[:240]:
        lex = c._bm25(expand_query(q), 1)
        if not lex or lex[0][1] < 10:
            continue
        for rank, r in enumerate(c.search(q, 5)):
            a = agg.setdefault(r["base"], {"card": r, "score": 0.0, "evidence": []})
            a["score"] += w / (1 + rank)
            if len(a["evidence"]) < 3 and ev not in [e["text"] for e in a["evidence"]]:
                a["evidence"].append({"page": page, "text": ev})
    ranked = sorted(agg.values(), key=lambda a: -a["score"])[:k]
    return {"queries": len(queries), "cited_in_document": list(cited.values()),
            "recommended": [{**a["card"], "doc_score": round(a["score"], 2), "evidence": a["evidence"],
                             "already_cited": a["card"]["base"] in cited} for a in ranked]}


def recommend_items(pages: List[dict]) -> dict:
    """Item-level recommendation for a real tender: find what is being bought, recommend per item with a confidence
    level, and abstain (status "none") when no Indian Standard matches confidently."""
    from app.engine.corpus_parse import citations as find_cites, normalise
    from app.engine.tender_items import extract_items, item_query, item_section, spec_context
    c = get_corpus()
    cited: Dict[str, dict] = {}
    for p in pages:
        for x in find_cites(normalise(p["text"]), set(c.catalogue)):
            cited.setdefault(x["base"], {"base": x["base"], "year": x["year"], "page": p["page"]})
    items = extract_items(pages)
    if not items:
        from app.engine.tender_items import split_products
        for p in pages[:3]:
            for m in SUBJECT_RE.finditer(p["text"][:4000]):
                for part in split_products(m.group(1).strip(" .")):
                    items.append({"text": part, "qty": None, "page": p["page"], "source": "subject", "is_service": False})
    out = []
    known = set(c.catalogue)
    for it in items:
        named = find_cites(normalise(re.sub(r"\bSection\b", "Sec", it["text"], flags=re.I)), known)
        if not named:
            for m in re.finditer(r"\bIS\s*[:/]?\s*(\d{2,5})\b(?!\s*\()", it["text"]):
                parts = sorted(b for b in known if b.startswith(f"IS {int(m.group(1))} (Part "))
                named += [{"base": b, "year": None} for b in parts[:1]]
        if named:                               # the item itself names its standard (GeM "… ISI Marked to IS 15683")
            cands = []
            for x in named[:2]:
                cd = c.card(x["base"])
                cands.append({"base": x["base"], "title": cd.get("title"), "confidence": "named", "latest_archived_year": cd.get("latest_archived_year"),
                              "doc_kind": cd.get("doc_kind"), "certification": [{"scheme": r["scheme"], "order": r.get("order")} for r in c.certification(x["base"])][:2],
                              "already_cited": True, "edition": c.edition_status(x["base"])})
            out.append({**it, "context": None, "status": "named", "candidates": cands})
            continue
        sec = item_section(pages, it["text"])
        ctx = sec or spec_context(pages, it["text"])
        q = item_query(it["text"])
        # the item's own section sharpens the lexical query ("Cement" + "Ordinary Portland Cement 43 Grade …");
        # generic specification text only informs the dense retriever
        lex_q = (q + " " + " ".join(re.findall(r"[A-Za-z][A-Za-z0-9\-]+", sec)[:14])) if sec else q
        res = c.search(lex_q, 5, dense_query=(q + ". " + ctx[:300]) if ctx else None, alias_query=q)
        for r in res:                           # confidence is judged against the item words, not the added context
            r["signals"]["coverage"] = c._coverage(q, r["base"])
            r["confidence"] = confidence(r["signals"])
            if (r.get("origin") == "bis_portal" or r.get("withdrawn")) and r["confidence"] == "high":
                r["confidence"] = "medium"
        top = res[0] if res else None
        status = top["confidence"] if top else "low"
        if it.get("is_service") and status != "high":
            status = "service"
        status = {"high": "recommended", "medium": "possible", "low": "none"}.get(status, status)
        cands = [{"base": r["base"], "title": r["title"], "confidence": r["confidence"], "latest_archived_year": r.get("latest_archived_year"),
                  "doc_kind": r.get("doc_kind"), "certification": [{"scheme": x["scheme"], "order": x.get("order")} for x in c.certification(r["base"])][:2],
                  "already_cited": r["base"] in cited} for r in res[:3]]
        out.append({**it, "context": ctx[:240] if ctx else None, "status": status, "candidates": cands})
    counts = {k: sum(1 for x in out if x["status"] == k) for k in ("named", "recommended", "possible", "none", "service")}
    return {"items": out, "counts": counts, "cited_in_document": list(cited.values()),
            "note": "‘recommended’ = the lexical and semantic retrievers agree and the item's words are covered by the standard's title/scope "
                    "(≈88 % top-1 precision on the benchmark); ‘possible’ = verify; ‘none’ = no confident Indian Standard — we abstain rather than guess."}


def check_citations(citations: List[dict]) -> dict:
    """Corpus cross-check of every IS citation in a tender: does the standard exist, is a newer edition archived, is it
    under compulsory certification, and which of its own normative references / test methods the tender does not cite."""
    from app.engine.std_refs import year_of
    c = get_corpus()
    if not c.ready:
        return {"available": False}
    fams = {}
    for x in citations:
        if x.get("body") and x["body"] != "BIS":
            continue
        f = x.get("family")
        if f and f not in fams:
            fams[f] = {"family": f, "citation": x.get("citation") or x.get("raw"), "clause_key": x.get("clause_key"), "cited_year": year_of(x.get("citation") or "")}
    cited_bases = set(fams)
    rows, missing = [], []
    for f, info in fams.items():
        base = f if f in c.catalogue else re.sub(r" \(Part [^)]*\)$", "", f)
        card = c.card(base) if base in c.catalogue else {"known": False}
        row = {**info, "found": bool(card.get("known")), "base": base if card.get("known") else None, "title": card.get("title"),
               "latest_archived_year": card.get("latest_archived_year"), "amendments": card.get("amendments"),
               "certification": [{"scheme": r["scheme"], "order": r.get("order")} for r in c.certification(base)][:3]}
        es = c.edition_status(base) if card.get("known") else {}
        row["edition"] = {k: es.get(k) for k in ("status", "edition_in_force", "year_in_force", "superseded_by", "replacement", "amendments", "source", "fetched")} if es else None
        yr_now = es.get("year_in_force") or row["latest_archived_year"]
        row["newer_edition_archived"] = bool(row["cited_year"] and yr_now and yr_now > row["cited_year"])
        row["withdrawn"] = es.get("status") == "Withdrawn"
        g = c.graph.get(base) or {}
        not_cited = []
        for rel in g.get("relations", []):
            if rel["base"] in cited_bases or re.sub(r" \(Part [^)]*\)$", "", rel["base"]) in cited_bases:
                continue
            if "references" in rel["clauses"] or rel["kind"] in ("test_method", "safety", "installation"):
                dep = c.edition_status(rel["base"])
                if dep.get("status") == "Withdrawn" and (not dep.get("replacement") or dep["replacement"] in cited_bases or dep["replacement"] == base):
                    continue
                not_cited.append({"base": dep.get("replacement") if dep.get("status") == "Withdrawn" else rel["base"],
                                  "title": c.card(rel["base"]).get("title"), "kind": rel["kind"], "normative": "references" in rel["clauses"],
                                  "via_replacement": rel["base"] if dep.get("status") == "Withdrawn" else None})
        row["not_cited_dependencies"] = not_cited[:10]
        rows.append(row)
        if not card.get("known"):
            missing.append(f)
    return {"available": True, "citations": rows, "unknown": missing,
            "newer_editions": [r["family"] for r in rows if r["newer_edition_archived"]],
            "withdrawn": [r["family"] for r in rows if r.get("withdrawn")],
            "note": "Cross-check against the archived Indian Standards corpus. Normative references of a cited standard apply through it; "
                    "listing key test methods explicitly in the tender avoids disputes. Confirm current editions on the BIS portal."}


def _count(it):
    d: Dict[str, int] = defaultdict(int)
    for x in it:
        d[x or "Unclassified"] += 1
    return dict(sorted(d.items(), key=lambda kv: -kv[1]))


_model_lock = threading.Lock()
_model = None
_model_failed = False


def passage_prefix(name: str) -> str:
    return "passage: " if "e5" in (name or "").lower() else ""


def query_prefix(name: str) -> str:
    return "query: " if "e5" in (name or "").lower() else ""


_active_name: Optional[str] = None


def corpus_model():
    """Sentence-transformer used for the corpus dense index (loaded lazily; None when disabled or unavailable).
    Falls back from the configured model (default BAAI/bge-m3) to multilingual-e5-small when it cannot be loaded."""
    global _model, _model_failed, _active_name
    from app.config import settings
    name = settings.CORPUS_EMBEDDING_MODEL
    if _model_failed or name.lower() in ("none", "", "off"):
        return None
    with _model_lock:
        if _model is None:
            from sentence_transformers import SentenceTransformer
            for cand in ([name, E5] if name != E5 else [name]):
                try:
                    _model = SentenceTransformer(cand, device="cpu")
                    if "bge-m3" in cand:
                        _model.max_seq_length = 160
                    _active_name = cand
                    break
                except Exception:  # noqa: BLE001
                    continue
            if _model is None:
                _model_failed = True
                return None
    return _model


def active_model_name() -> Optional[str]:
    return _active_name


_lock = threading.Lock()
_corpus: Optional[Corpus] = None


def get_corpus() -> Corpus:
    global _corpus
    with _lock:
        if _corpus is None:
            _corpus = Corpus().load()
    return _corpus


def reload_corpus() -> Corpus:
    global _corpus
    with _lock:
        _corpus = Corpus().load()
    return _corpus
