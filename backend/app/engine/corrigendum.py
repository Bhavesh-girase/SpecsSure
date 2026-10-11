"""
Corrigendum Intelligence — "git for tenders".

* parses corrigenda written in the usual Indian procurement phrasing
  ("Clause 4.3 shall be read as …", "Clause 3.4 is deleted", "New Clause 4.6 is added …")
* applies them chronologically to the original clause tree → canonical (latest effective) tender
* keeps a full version history per clause with word-level diffs and "blame"
  (which document last changed this clause, on which date)
* the canonical tender is re-compiled, so a corrigendum that *fixes* one issue but *introduces*
  a new contradiction is caught immediately (regression detection)
* reverse direction: approved linter autofixes are rendered into a draft corrigendum
"""
from __future__ import annotations

import copy
import difflib
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional, Tuple

from app.engine.tender_ir import Clause, TenderIR, classify_section

KEY = r"(?P<key>(?:[A-Z][a-z]+-[IVX0-9]+/)?\d{1,2}(?:\.\d{1,3}){0,4})"
MODIFY = re.compile(rf"(?:Clause|Cl\.?|Para(?:graph)?|Item)\s*(?:No\.?\s*)?{KEY}\s*(?:of (?:the )?(?:tender|NIT|bid|RFP)[\w ]*?)?\s*"
                    r"(?:shall (?:now )?be read as|shall stand (?:amended|modified) as|is (?:hereby )?(?:amended|modified|revised) (?:to read|as)|"
                    r"stands (?:amended|modified|revised) as|may be read as|is replaced (?:by|with)|to be read as)\s*[:\-–]?\s*(?P<text>.+)", re.I)
DELETE = re.compile(rf"(?:Clause|Cl\.?|Para(?:graph)?|Item)\s*(?:No\.?\s*)?{KEY}\s*(?:of (?:the )?(?:tender|NIT)[\w ]*?)?\s*(?:is|stands|has been|shall be)\s*(?:hereby\s*)?(?:deleted|withdrawn|omitted|dropped)", re.I)
ADD = re.compile(rf"(?:New|Additional|A new)\s+(?:Clause|Cl\.?|Para(?:graph)?)\s*(?:No\.?\s*)?{KEY}\s*(?:is|shall be|has been|stands)\s*(?:hereby\s*)?(?:added|inserted|incorporated|introduced)"
                 r"(?:\s*after (?:Clause|Cl\.?)\s*[\d.]+)?\s*(?:as (?:follows|under))?\s*[:\-–]?\s*(?P<text>.+)", re.I)
ISSUED = re.compile(r"(?:Date(?: of issue)?|Dated|Issued on)\s*[:\-]?\s*(\d{1,2})[./\-](\d{1,2})[./\-](20\d{2})", re.I)
NUMBER = re.compile(r"(?:Corrigendum|Addendum|Amendment)\s*(?:No\.?|#)\s*(\d+)", re.I)


@dataclass
class CorrOp:
    op: str                 # modify | delete | add
    clause_key: str
    text: Optional[str]
    raw: str

    def to_dict(self):
        return self.__dict__.copy()


@dataclass
class ParsedCorrigendum:
    name: str
    number: Optional[int]
    issued_on: Optional[str]
    operations: List[CorrOp]
    unparsed: List[str] = field(default_factory=list)

    def to_dict(self):
        return {"name": self.name, "number": self.number, "issued_on": self.issued_on,
                "operations": [o.to_dict() for o in self.operations], "unparsed": self.unparsed}


def _clean(text: str) -> str:
    t = text.strip().strip("\"“”'")
    return t.rstrip("\"“”'").strip()


def parse_corrigendum(text: str, name: str = "corrigendum") -> ParsedCorrigendum:
    ops: List[CorrOp] = []
    unparsed: List[str] = []
    num = NUMBER.search(text or "")
    iss = ISSUED.search(text or "")
    issued = None
    if iss:
        try:
            issued = date(int(iss.group(3)), int(iss.group(2)), int(iss.group(1))).isoformat()
        except ValueError:
            issued = None
    # items may span several lines — join continuation lines to their item
    items: List[str] = []
    for line in (text or "").splitlines():
        s = line.strip()
        if not s:
            continue
        if re.match(r"^(?:\d{1,2}[.)]|\(\w\)|[-•*])\s+", s) or re.match(r"^(?:Clause|New|Additional|Cl\.)", s, re.I):
            items.append(re.sub(r"^(?:\d{1,2}[.)]|\(\w\)|[-•*])\s+", "", s))
        elif items and not re.match(r"^(?:DEMO|CORRIGENDUM|Tender No|Date|The following|In partial|All other)", s, re.I):
            items[-1] += " " + s
    for it in items:
        m = ADD.search(it)
        if m:
            ops.append(CorrOp("add", m.group("key"), _clean(m.group("text")), it))
            continue
        m = DELETE.search(it)
        if m:
            ops.append(CorrOp("delete", m.group("key"), None, it))
            continue
        m = MODIFY.search(it)
        if m:
            ops.append(CorrOp("modify", m.group("key"), _clean(m.group("text")), it))
            continue
        if re.search(r"\bclause\b", it, re.I):
            unparsed.append(it)
    return ParsedCorrigendum(name, int(num.group(1)) if num else None, issued, ops, unparsed)


def word_diff(a: str, b: str) -> List[List[str]]:
    wa, wb = (a or "").split(), (b or "").split()
    out: List[List[str]] = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, wa, wb).get_opcodes():
        if tag == "equal":
            out.append(["=", " ".join(wa[i1:i2])])
        elif tag == "delete":
            out.append(["-", " ".join(wa[i1:i2])])
        elif tag == "insert":
            out.append(["+", " ".join(wb[j1:j2])])
        else:
            out.append(["-", " ".join(wa[i1:i2])])
            out.append(["+", " ".join(wb[j1:j2])])
    return out


def _split_heading(text: str, fallback: str) -> Tuple[str, str]:
    hm = re.match(r"^([A-Z][A-Za-z /&()\-]{2,60}?)\s*[:\-–]\s+(.*)$", text or "", re.S)
    if hm:
        return hm.group(1).strip(), hm.group(2).strip()
    return fallback, text


def _natkey(k: str):
    return [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", k.split("#")[0])]


def merge(base: TenderIR, corrigenda: List[ParsedCorrigendum], base_date: Optional[str] = None) -> Dict:
    """Apply corrigenda in chronological order. Returns canonical IR + history + changelog + blame."""
    clauses: List[Clause] = [copy.deepcopy(c) for c in base.clauses]
    history: Dict[str, List[dict]] = {c.key: [{"version": 1, "change": "original", "doc": base.doc_name, "date": base_date,
                                                "text": c.text, "heading": c.heading}] for c in clauses}
    deleted: Dict[str, Clause] = {}
    changelog: List[dict] = []
    ordered = sorted(corrigenda, key=lambda c: (c.issued_on or "9999", c.number or 0))
    for corr in ordered:
        for op in corr.operations:
            idx = next((i for i, c in enumerate(clauses) if c.key == op.clause_key), None)
            entry = {"doc": corr.name, "corrigendum_no": corr.number, "date": corr.issued_on, "op": op.op,
                     "clause_key": op.clause_key, "raw": op.raw}
            if op.op == "modify":
                if idx is None:
                    entry["warning"] = f"Clause {op.clause_key} not found in the current tender — treated as an addition."
                    op = CorrOp("add", op.clause_key, op.text, op.raw)
                else:
                    c = clauses[idx]
                    heading, body = _split_heading(op.text or "", c.heading)
                    before = c.text
                    c.heading, c.text = heading, body
                    ver = len(history.setdefault(c.key, [])) + 1
                    history[c.key].append({"version": ver, "change": "modified", "doc": corr.name, "date": corr.issued_on,
                                           "text": body, "heading": heading, "diff": word_diff(before, body)})
                    entry.update({"before": before, "after": body, "diff": word_diff(before, body)})
                    changelog.append(entry)
                    continue
            if op.op == "delete":
                if idx is None:
                    entry["warning"] = f"Clause {op.clause_key} not found (already deleted?)."
                    changelog.append(entry)
                    continue
                c = clauses.pop(idx)
                deleted[c.key] = c
                history.setdefault(c.key, []).append({"version": len(history.get(c.key, [])) + 1, "change": "deleted",
                                                      "doc": corr.name, "date": corr.issued_on, "text": None,
                                                      "diff": word_diff(c.text, "")})
                entry.update({"before": c.text, "after": None})
                changelog.append(entry)
                continue
            if op.op == "add":
                if idx is not None:
                    entry["warning"] = f"Clause {op.clause_key} already exists — applied as a modification."
                    c = clauses[idx]
                    before = c.text
                    c.heading, c.text = _split_heading(op.text or "", c.heading)
                    history[c.key].append({"version": len(history[c.key]) + 1, "change": "modified", "doc": corr.name,
                                           "date": corr.issued_on, "text": c.text, "diff": word_diff(before, c.text)})
                    changelog.append(entry)
                    continue
                heading, body = _split_heading(op.text or "", "Added clause")
                parent = op.clause_key.rsplit(".", 1)[0] if "." in op.clause_key else None
                ref = next((c for c in clauses if c.key == parent), None) or (clauses[-1] if clauses else None)
                new = Clause(key=op.clause_key, heading=heading, text=body, page_start=ref.page_start if ref else 1,
                             page_end=ref.page_end if ref else 1, doc_name=corr.name, section=ref.section if ref else "",
                             section_type=(ref.section_type if ref else classify_section(heading)), parent=parent)
                # insert after the last clause that sorts before the new key
                pos = len(clauses)
                for i, c in enumerate(clauses):
                    if _natkey(c.key) > _natkey(op.clause_key):
                        pos = i
                        break
                clauses.insert(pos, new)
                history.setdefault(op.clause_key, []).append({"version": 1, "change": "added", "doc": corr.name, "date": corr.issued_on,
                                                              "text": body, "heading": heading, "diff": word_diff("", body)})
                entry.update({"before": None, "after": body})
                changelog.append(entry)
    canonical = TenderIR(doc_name=base.doc_name + " (canonical)", doc_type="tender", title=base.title, clauses=clauses,
                         sections=base.sections, meta={**base.meta, "corrigenda_applied": [c.name for c in ordered]})
    blame = {k: {"version": v[-1]["version"], "doc": v[-1]["doc"], "date": v[-1]["date"], "change": v[-1]["change"]} for k, v in history.items()}
    return {"canonical": canonical, "history": history, "changelog": changelog, "blame": blame,
            "deleted": sorted(deleted), "applied": [c.to_dict() for c in ordered]}


def canonical_text(ir: TenderIR, blame: Optional[Dict] = None) -> str:
    lines = [ir.title, "=" * min(len(ir.title), 80), ""]
    for c in ir.clauses:
        tag = ""
        if blame and c.key in blame and blame[c.key]["change"] != "original":
            b = blame[c.key]
            tag = f"   [{b['change']} by {b['doc']} on {b['date']}]"
        lines.append(f"{c.key} {c.heading}: {c.text}{tag}".rstrip())
    return "\n".join(lines)


def fixes_to_corrigendum(twin: dict, fingerprints: List[str], number: int, issued_on: str, tender_ref: str = "") -> Dict:
    """Render approved linter autofixes as a draft corrigendum in standard phrasing."""
    clauses = {c["key"]: dict(c) for c in twin["clauses"]}
    touched: Dict[str, str] = {}
    deletes: List[str] = []
    adds: List[Tuple[str, str]] = []
    applied = []
    for f in twin["findings"]:
        if f["fingerprint"] not in fingerprints or not f.get("fix"):
            continue
        fx = f["fix"]
        k = fx.get("clause_key")
        cur = touched.get(k, clauses.get(k, {}).get("text", ""))
        if fx["op"] == "replace" and k in clauses:
            if fx["find"] in cur:
                new = cur.replace(fx["find"], fx["replace"], 1)
                new = re.sub(r"\s{2,}", " ", re.sub(r"\s+([,.;])", r"\1", new)).replace(", ,", ",").replace(" ,", ",").strip()
                new = re.sub(r"\b(shall be|be) ,", r"\1", new)
                touched[k] = new
                applied.append(f["fingerprint"])
        elif fx["op"] == "replace_clause" and k in clauses:
            touched[k] = fx["text"]
            applied.append(f["fingerprint"])
        elif fx["op"] == "append" and k in clauses:
            touched[k] = (cur.rstrip() + " " + fx["text"]).strip()
            applied.append(f["fingerprint"])
        elif fx["op"] == "delete_clause" and k in clauses:
            deletes.append(k)
            applied.append(f["fingerprint"])
        elif fx["op"] == "add_clause":
            base = fx.get("after_key") or (list(clauses)[-1] if clauses else "1")
            root = base.split(".")[0]
            siblings = [c for c in clauses if c.split(".")[0] == root and "." in c]
            n = max([int(re.findall(r"\d+", c.split(".")[-1])[0]) for c in siblings] or [0]) + 1 + len([a for a in adds if a[0].split(".")[0] == root])
            adds.append((f"{root}.{n}", fx["text"]))
            applied.append(f["fingerprint"])
    items = []
    for k, txt in touched.items():
        if k in deletes:
            continue
        heading = clauses[k].get("heading", "")
        items.append(f'Clause {k} shall be read as: "{heading}: {txt}"' if heading and not txt.startswith(heading) else f'Clause {k} shall be read as: "{txt}"')
    for k in deletes:
        items.append(f"Clause {k} is deleted.")
    for k, txt in adds:
        items.append(f'New Clause {k} is added: "{txt}"')
    body = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(items))
    text = (f"DRAFT CORRIGENDUM No. {number}\nTender No. {tender_ref}\nDate of issue: {date.fromisoformat(issued_on).strftime('%d-%m-%Y')}\n\n"
            f"The following changes are made to the tender document. All other terms and conditions remain unchanged.\n\n{body}\n\n"
            f"[Generated by SpecSure from {len(applied)} approved finding(s). Requires approval by the competent authority before issue.]")
    return {"text": text, "applied_findings": applied, "items": items}
