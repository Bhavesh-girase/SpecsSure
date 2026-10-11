"""
Step 3: download the full-text layer (.txt) of archived Indian Standards into var/corpus/text/<identifier>.txt.gz.

Order: latest archived edition of every designation first (English), prioritising procurement-heavy divisions.
Resumable (skips files already present); polite concurrency.
Usage: python scripts/corpus_fetch_text.py [--limit N] [--divisions "Electrotechnical,Civil Engineering"] [--workers 8]
"""
import argparse
import concurrent.futures as cf
import gzip
import json
import os
import time
import urllib.parse
import urllib.request

ROOT = os.path.join(os.path.dirname(__file__), "..")
CAT = os.path.join(ROOT, "data", "corpus", "is_catalogue.jsonl.gz")
TXT = os.path.join(ROOT, "var", "corpus", "text")
UA = {"User-Agent": "SpecSure-research/0.1 (SIH 2026 prototype; contact via GitHub pranavmen/SpecsSure)"}
PRIORITY = ["Electrotechnical", "Civil Engineering", "Metallurgical Engineering", "Mechanical Engineering", "Chemical",
            "Electronics and Information Technology", "Petroleum, Coal, and Related Products", "Textiles", "Food and Agriculture",
            "Medical Equipment and Hospital Planning", "Production and General Engineering", "Transport Engineering", "Water Resources",
            "Management and Systems", None]


def plan(divisions=None):
    recs = [json.loads(l) for l in gzip.open(CAT, "rt", encoding="utf-8")]
    latest = {}
    for r in recs:
        if r["variant"] == "hindi":
            continue
        cur = latest.get(r["base"])
        if cur is None or (r["year"] or 0) > (cur["year"] or 0):
            latest[r["base"]] = r
    items = list(latest.values())
    if divisions:
        items = [r for r in items if r["division"] in divisions]
    items.sort(key=lambda r: PRIORITY.index(r["division"]) if r["division"] in PRIORITY else len(PRIORITY))
    return items


def txt_candidates(ident):
    tail = ident[len("gov.in."):]  # is.694.2010
    return [f"https://archive.org/download/{ident}/{tail}.txt", f"https://archive.org/download/{ident}/{tail}_djvu.txt"]


def listed_candidates(ident):
    """Newer uploads name files after the designation (e.g. SP68:2005_djvu.txt) — look them up in the item metadata."""
    try:
        with urllib.request.urlopen(urllib.request.Request(f"https://archive.org/metadata/{ident}/files", headers=UA), timeout=60) as resp:
            files = json.loads(resp.read().decode("utf-8")).get("result", [])
    except Exception:  # noqa: BLE001
        return []
    names = [f["name"] for f in files if f["name"].endswith(".txt") and not f["name"].endswith(("_meta.txt", "_files.txt"))]
    names.sort(key=lambda n: (not n.endswith("_djvu.txt"), len(n)))
    return [f"https://archive.org/download/{ident}/{urllib.parse.quote(n)}" for n in names]


def fetch_one(r):
    path = os.path.join(TXT, r["id"] + ".txt.gz")
    if os.path.exists(path):
        return "cached"
    for url in txt_candidates(r["id"]) + ["LIST"]:
        if url == "LIST":
            extra = listed_candidates(r["id"])
            for u in extra:
                try:
                    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=90) as resp:
                        data = resp.read()
                    if len(data) >= 200:
                        with gzip.open(path, "wb") as f:
                            f.write(data)
                        return "ok"
                except Exception:  # noqa: BLE001
                    continue
            break
        for attempt in range(3):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as resp:
                    data = resp.read()
                if len(data) < 200:
                    break
                with gzip.open(path, "wb") as f:
                    f.write(data)
                return "ok"
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    break
                time.sleep(3 * (attempt + 1))
            except Exception:  # noqa: BLE001
                time.sleep(3 * (attempt + 1))
    return "missing"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--divisions", default="")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--reverse", action="store_true", help="process the plan from the end (run alongside a forward process)")
    a = ap.parse_args()
    os.makedirs(TXT, exist_ok=True)
    items = plan([d.strip() for d in a.divisions.split(",") if d.strip()] or None)
    if a.reverse:
        items = items[::-1]
    if a.limit:
        items = items[: a.limit]
    t0 = time.time()
    stats = {"ok": 0, "cached": 0, "missing": 0}
    with cf.ThreadPoolExecutor(a.workers) as ex:
        for i, res in enumerate(ex.map(fetch_one, items), 1):
            stats[res] += 1
            if i % 250 == 0:
                print(f"{i}/{len(items)} {stats} {time.time() - t0:.0f}s", flush=True)
    print("done", stats, f"{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
