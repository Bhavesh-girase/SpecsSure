"""Multilingual evaluation only (same path as the API)."""
import asyncio, json, os, re, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("CORPUS_ALIASES", "0")
from eval_sets import match
from app.services.corpus_service import Corpus
from app.services.multilingual import detect_language, translate_to_english
c = Corpus().load()
ml = json.load(open(os.path.join(ROOT, "data", "evaluation", "procurement_queries.json"), encoding="utf-8"))[os.getenv("ML_SET", "multilingual")]
h1 = h3 = 0
for cs in ml:
    lang = detect_language(cs["query"])
    t, tr = asyncio.run(translate_to_english(cs["query"], lang)) if lang != "en" else (cs["query"], False)
    terms = re.findall(r"\(([^)]+)\)", t) if tr else []
    q = " ".join(terms + re.findall(r"[A-Za-z0-9./]+", re.sub(r"\([^)]*\)", " ", t))) if terms else t
    res = [x["base"] for x in c.search(q, 5, dense_query=cs["query"])]
    rank = next((i + 1 for i, b in enumerate(res) if match(b, cs["expected"])), None)
    h1 += bool(rank and rank == 1); h3 += bool(rank and rank <= 3)
    print(rank, cs["lang"], cs["query"], "|", q, "|", res[:3])
print(sys.argv[1] if len(sys.argv) > 1 else "", "cases", len(ml), "top1", round(100 * h1 / len(ml), 1), "top3", round(100 * h3 / len(ml), 1))
