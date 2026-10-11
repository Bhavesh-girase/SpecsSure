"""
Current-edition catalogue from the BIS standards e-Sale portal (standardsbis.bsbedge.com, "Download Search Result in
Excel" for every designation prefix). The portal lists the standards on sale — i.e. the editions in force, including
standards published after the archived corpus (2020–2026) and concurrent editions still valid for a transition period.

Input : var/bis/x_*.xls (HTML tables saved from the portal; fetched from a machine in India)
Output: data/corpus/bis_portal.json.gz  {base: {"current": year, "title": ..., "editions": [[year, title, flag]]}}
"""
import glob
import gzip
import html
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def norm_designation(s: str):
    """'IS 10322 : Part 5 : Sec 3' → ('IS 10322 (Part 5/Sec 3)', flag).  Returns (None, None) for Hindi editions."""
    s = re.sub(r"\s+", " ", s).strip()
    if re.search(r"hindi", s, re.I):
        return None, None
    flag = None
    if re.search(r"\(Active,\s*Concurrent Running\)|- \(Active\)", s, re.I):
        flag = "concurrent"
    s = re.sub(r"\s*(?:-\s*)?\((?:Active|Active,\s*Concurrent Running)\)", "", s, flags=re.I).strip(" -")
    m = re.match(r"^((?:IS|SP)(?:/[A-Z]+)*)\s*([A-Z]?\d[\w.-]*)(.*)$", s, re.I)
    if not m:
        return None, None
    pre, num, rest = m.group(1).upper(), m.group(2), m.group(3)
    parts = re.findall(r":\s*(PART|SEC|SUBSEC|OD)\s*([\w.-]+(?:\s*to\s*[\w.-]+)?)", rest, re.I)
    base = f"{pre} {num}"
    if parts:
        seg = []
        for kind, val in parts:
            k = kind.lower()
            val = re.sub(r"\s*to\s*", " to ", val)
            seg.append({"part": "Part", "sec": "Sec", "subsec": "Subsec", "od": "OD"}[k] + " " + val)
        base += " (" + "/".join(seg) + ")"
    return base, flag


def main():
    rows = {}
    for f in glob.glob(os.path.join(ROOT, "var", "bis", "x_*.xls")):
        t = open(f, encoding="utf-8", errors="ignore").read()
        for tr in re.findall(r"<tr>(.*?)</tr>", t, re.S):
            tds = [html.unescape(re.sub(r"<[^>]+>", "", x)).strip() for x in re.findall(r"<td>(.*?)</td>", tr, re.S)]
            if len(tds) < 4 or tds[0] == "S.No." or not tds[2].isdigit():
                continue
            base, flag = norm_designation(tds[1])
            if not base:
                continue
            title = re.sub(r"\s+", " ", tds[3].replace("\x9d", "")).strip()
            rows[(base, int(tds[2]), title)] = flag
    out = {}
    for (base, year, title), flag in rows.items():
        e = out.setdefault(base, {"editions": []})
        e["editions"].append([year, title, flag])
    for base, e in out.items():
        e["editions"].sort(key=lambda x: (x[0], x[2] is None))
        cur = [x for x in e["editions"] if x[2] is None] or e["editions"]
        e["current"], e["title"] = cur[-1][0], cur[-1][1]
    dst = os.path.join(ROOT, "data", "corpus", "bis_portal.json.gz")
    with gzip.open(dst, "wt", encoding="utf-8") as g:
        json.dump({"meta": {"source": "BIS standards e-Sale portal (standardsbis.bsbedge.com) search-result exports",
                            "fetched": "2026-09-27", "designations": len(out)}, "standards": out}, g, ensure_ascii=False)
    print(len(out), "designations →", dst)


if __name__ == "__main__":
    main()
