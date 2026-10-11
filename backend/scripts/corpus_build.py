"""
Step 4: parse every downloaded standard text into the corpus graph.

Input : data/corpus/is_catalogue.jsonl.gz, var/corpus/text/*.txt.gz
Output: data/corpus/is_graph.jsonl.gz — one record per designation (latest archived English edition that has text):
        scope, revision, reaffirmed, equivalents, supersedes_text, typed relations with clause + snippet.
Only facts and short snippets are stored; the full text stays in var/ and is never redistributed.
"""
import gzip
import json
import os
import sys
import time
from collections import Counter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from app.engine.corpus_parse import kind_from_title, parse  # noqa: E402

CAT = os.path.join(ROOT, "data", "corpus", "is_catalogue.jsonl.gz")
TXT = os.path.join(ROOT, "var", "corpus", "text")
OUT = os.path.join(ROOT, "data", "corpus", "is_graph.jsonl.gz")


def main():
    cat = [json.loads(l) for l in gzip.open(CAT, "rt", encoding="utf-8")]
    known = {r["base"] for r in cat}
    title = {}
    latest = {}
    for r in cat:
        if r["variant"] == "hindi":
            continue
        title.setdefault(r["base"], r["title"])
        path = os.path.join(TXT, r["id"] + ".txt.gz")
        if not os.path.exists(path):
            continue
        cur = latest.get(r["base"])
        if cur is None or (r["year"] or 0) > (cur["year"] or 0):
            latest[r["base"]] = r
    t0 = time.time()
    kinds, n, with_scope, with_refs, edges = Counter(), 0, 0, 0, 0
    with gzip.open(OUT, "wt", encoding="utf-8") as out:
        for base, r in sorted(latest.items()):
            try:
                text = gzip.open(os.path.join(TXT, r["id"] + ".txt.gz"), "rt", encoding="utf-8", errors="ignore").read()
            except Exception:  # noqa: BLE001
                continue
            p = parse(text, known, base)
            rels = []
            for x in p["relations"]:
                k = kind_from_title(title.get(x["base"], ""))
                kinds[k] += 1
                rels.append({"base": x["base"], "year": x["year"], "clauses": x["clauses"], "kind": k,
                             "snippet": (x["snippet"] or "")[:220]})
            rec = {"base": base, "id": r["id"], "year": r["year"], "doc_kind": kind_from_title(r["title"]), "scope": p["scope"],
                   "revision": p["revision"], "reaffirmed": p["reaffirmed"], "equivalents": p["equivalents"],
                   "supersedes_text": p["supersedes_text"], "has_references_clause": p["has_references_clause"], "relations": rels}
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
            with_scope += bool(p["scope"])
            with_refs += p["has_references_clause"]
            edges += len(rels)
            if n % 2000 == 0:
                print(n, f"{time.time() - t0:.0f}s", flush=True)
    stats = {"standards_parsed": n, "with_scope": with_scope, "with_references_clause": with_refs, "relations": edges,
             "relations_by_kind": dict(kinds.most_common()), "built": time.strftime("%Y-%m-%d %H:%M")}
    json.dump(stats, open(os.path.join(ROOT, "data", "corpus", "build_stats.json"), "w"), indent=1)
    print(json.dumps(stats, indent=1))


if __name__ == "__main__":
    main()
