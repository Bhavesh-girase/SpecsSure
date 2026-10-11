"""
Step 1 of the Indian Standards corpus pipeline: harvest catalogue metadata for every Indian Standard published on the
Internet Archive by Public.Resource.Org (identifiers gov.in.is.*; CC0 label, "Right to Information Act 2005").

Output: var/corpus/archive_metadata.jsonl  (one raw record per archived document)
Usage:  python scripts/corpus_harvest.py
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

OUT = os.path.join(os.path.dirname(__file__), "..", "var", "corpus", "archive_metadata.jsonl")
API = "https://archive.org/services/search/v1/scrape"
FIELDS = "identifier,title,date,description,subject,publicdate"


def fetch(params):
    url = API + "?" + urllib.parse.urlencode(params)
    for attempt in range(6):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SpecSure-research/0.1 (SIH 2026 prototype)"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            wait = 5 * (attempt + 1)
            print(f"  retry in {wait}s: {e}", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError("archive.org scrape API unavailable")


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    params = {"q": "identifier:gov.in.is.*", "fields": FIELDS, "count": 5000}
    n = 0
    with open(OUT, "w", encoding="utf-8") as f:
        while True:
            d = fetch(params)
            for it in d.get("items", []):
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
                n += 1
            print(f"{n} / {d.get('total')}")
            if not d.get("cursor"):
                break
            params["cursor"] = d["cursor"]
            time.sleep(1)
    print("wrote", n, "records to", OUT)


if __name__ == "__main__":
    main()
