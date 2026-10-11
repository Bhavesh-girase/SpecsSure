"""Ablation on FIXED case sets (cases answerable without the BIS-portal layer), so configurations are compared on identical
queries. Usage: CORPUS_ALIASES=0 [CORPUS_PORTAL=0] [CORPUS_EMBEDDING_MODEL=..] python scripts/exp_fixed.py name"""
import json, os, re, sys, time
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("CORPUS_ALIASES", "0")
from eval_sets import gem_cases, score, family
from app.services.corpus_service import Corpus

FIX = os.path.join(ROOT, "var", "exp", "fixed_cases.json")


def build_fixed():
    os.environ["CORPUS_PORTAL"] = "0"
    c = Corpus().load()
    rows = json.load(open(os.path.join(ROOT, "data", "corpus", "compulsory_certification.json"), encoding="utf-8"))["rows"]
    seen, bis = set(), []
    for r in rows:
        q = re.sub(r"\s+", " ", (r.get("product") or "")).strip(" -–—")
        q = re.split(r" — ", q)[0] if r["scheme"].startswith("Scheme-II") else q
        if len(q) < 6 or r["base"] not in c.catalogue or (q.lower(), r["base"]) in seen:
            continue
        seen.add((q.lower(), r["base"]))
        bis.append({"query": q, "expected": [r["base"], family(r["base"])] if " (Part" in r["base"] else [r["base"]]})
    pq = json.load(open(os.path.join(ROOT, "data", "evaluation", "procurement_queries.json"), encoding="utf-8"))["cases"]
    json.dump({"bis": bis, "gem": gem_cases(c), "procurement": pq}, open(FIX, "w"), indent=0, ensure_ascii=False)
    del os.environ["CORPUS_PORTAL"]


def main():
    name = sys.argv[1]
    if not os.path.exists(FIX):
        build_fixed()
    sets = json.load(open(FIX, encoding="utf-8"))
    c = Corpus().load()
    t0 = time.time()
    out = {"name": name, "env": {k: v for k, v in os.environ.items() if k.startswith("CORPUS_")}}
    for k in os.getenv("EXP_SETS", "gem,bis,procurement").split(","):
        r = score(c, sets[k])
        out[k] = {kk: v for kk, v in r.items() if kk != "misses"}
        print(name, k, out[k], flush=True)
    out["secs"] = round(time.time() - t0)
    json.dump(out, open(os.path.join(ROOT, "var", "exp", f"fixed_{name}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
