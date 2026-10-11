"""
Status, reaffirmation, technical committee and amendment list for the standards that matter most in procurement
(compulsory-certification standards, GeM category standards, benchmark and real-tender standards), read from the BIS
standards e-Sale portal search results and amendment pages (fetched from a machine in India on the date below).

Input : var/bis/status2.jsonl (raw result text), var/bis/amendments.jsonl
Output: data/corpus/bis_status.json  {base: {status, edition, year, reaffirmed, committee, equivalent, amendments:[{no, year}]}}
"""
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from bis_portal_catalogue import norm_designation  # noqa: E402

FETCHED = "2026-09-27"


MARK = re.compile(r"Technical Committee : (?P<tc>[A-Z]+ ?\d+)\s*(?:Superseeded by :\s*(?P<sup>.*?)\s*)?Status : (?P<status>[A-Za-z ]+?)\s*No\. of Amendments : (?P<amd>\d+)")
HEAD = re.compile(r"(?:^|\s)\d{1,2} (?P<des>(?:IS|SP)(?:/[A-Z]+)* ?[A-Z]?\d[\w.-]*(?: : (?:Part|PART|Sec|SEC|Subsec|SUBSEC|OD) [\w.-]+(?: to [\w.-]+)?)*)"
                  r"(?:\s*-?\s*\((?:Active|Active,\s*Concurrent Running)\))?\s*:\s*(?P<year>\d{4})\s*(?:\(Reaffirmed Year : (?P<reaff>\d{4})\s*\))?"
                  r"\s*(?:\((?P<eq>[^)]{2,80})\))?\s*(?P<title>.*)$")


def parse_entries(text: str):
    text = text.split("Custcode")[0]
    out, pos = [], 0
    for m in MARK.finditer(text):
        head = text[pos:m.start()]
        pos = m.end()
        head = re.sub(r"^\s*(?:Login to Download|Price within India : ₹ [\d,.]+ Price Outside India : ₹ [\d,.]+)\s*", "", head)
        h = None
        for h in HEAD.finditer(head):
            pass
        if not h:
            continue
        out.append({"des": h.group("des"), "year": h.group("year"), "reaff": h.group("reaff"), "eq": h.group("eq"),
                    "title": h.group("title").strip(" -"), "tc": m.group("tc"), "status": m.group("status").strip(),
                    "superseded_by": (m.group("sup") or "").strip() or None, "amd": m.group("amd")})
    return out


def main():
    amd = {}
    for line in open(os.path.join(ROOT, "var", "bis", "amendments.jsonl"), encoding="utf-8"):
        r = json.loads(line)
        amd[r["parentid"]] = r["amendments"]
    out, not_found = {}, []
    for line in open(os.path.join(ROOT, "var", "bis", "status2.jsonl"), encoding="utf-8"):
        r = json.loads(line)
        want = r["base"]
        best = None
        for e in parse_entries(r.get("text") or ""):
            b, _ = norm_designation(e["des"])
            if b == want:
                active = e["status"].lower() == "active"
                if best is None or (active, int(e["year"])) > (best["status"].lower() == "active", int(best["year"])):
                    best = e
        if not best:
            not_found.append(want)
            continue
        pid = next((p for p, s in r["amd_links"] if norm_designation(s)[0] == want), None)
        amds = sorted(amd.get(pid, []), key=lambda a: a["no"])
        out[want] = {"status": best["status"].capitalize(), "edition": f"{want}:{best['year']}", "year": int(best["year"]),
                     "reaffirmed": int(best["reaff"]) if best.get("reaff") else None, "committee": best["tc"],
                     "equivalent": best.get("eq"), "title": best["title"].strip(" -"),
                     "superseded_by": best.get("superseded_by"),
                     "amendments_count": int(best["amd"]), "amendments": [{"no": a["no"], "year": a["year"]} for a in amds]}
    meta = {"source": "BIS standards e-Sale portal (standardsbis.bsbedge.com) — search results and amendment pages",
            "fetched": FETCHED, "standards": len(out), "not_found_in_active_search": not_found,
            "note": "Status as shown by the portal (Active / Withdrawn, with 'Superseded by'). Designations not found were not "
                    "returned by the portal search — verify on the BIS portal."}
    json.dump({"meta": meta, "standards": out}, open(os.path.join(ROOT, "data", "corpus", "bis_status.json"), "w"), indent=0, ensure_ascii=False)
    import collections
    print(len(out), "with status;", collections.Counter(v["status"] for v in out.values()), len(not_found), "not found:", not_found[:20])


if __name__ == "__main__":
    main()
