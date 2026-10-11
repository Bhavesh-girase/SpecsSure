"""
Build the Indian Standards corpus end-to-end (resumable):

  1. corpus_harvest.py        archive.org catalogue metadata  → var/corpus/archive_metadata.jsonl
  2. corpus_catalogue.py      normalised catalogue            → data/corpus/is_catalogue.jsonl.gz
  3. corpus_fetch_text.py     full texts                      → var/corpus/text/*.txt.gz   (not redistributed)
  4. corpus_build.py          parsed facts + typed relations  → data/corpus/is_graph.jsonl.gz
  5. corpus_certification.py  BIS compulsory-certification     → data/corpus/compulsory_certification.json
  6. corpus_embed.py          dense index (multilingual-e5)   → data/corpus/scope_emb.npy
  7. corpus_benchmark.py      evaluation                       → data/evaluation/corpus_benchmark.json

Usage: python scripts/corpus_all.py [--skip-fetch]
"""
import subprocess
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
steps = ["corpus_harvest.py", "corpus_catalogue.py", "corpus_fetch_text.py", "corpus_build.py", "corpus_certification.py",
         "corpus_embed.py", "corpus_benchmark.py"]
if "--skip-fetch" in sys.argv:
    steps = [s for s in steps if s not in ("corpus_harvest.py", "corpus_fetch_text.py")]
for s in steps:
    print(f"\n=== {s}", flush=True)
    r = subprocess.run([sys.executable, os.path.join(HERE, s)])
    if r.returncode != 0:
        sys.exit(r.returncode)
