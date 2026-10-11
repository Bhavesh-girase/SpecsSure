"""Exports: Excel compliance matrix / findings register, PDF readiness report, evidence package ZIP."""
from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime
from typing import Dict, List, Optional

STATUS_FILL = {"COMPLIANT": "C6EFCE", "CLAIMED_ONLY": "FFF2CC", "DECLARATION": "DDEBF7", "NEEDS_CLARIFICATION": "FCE4D6",
               "MISSING_EVIDENCE": "F8CBAD", "CONFLICTING_EVIDENCE": "F4B084", "NON_COMPLIANT": "FF9999"}
SEV_FILL = {"critical": "FF9999", "major": "F8CBAD", "minor": "FFF2CC", "info": "DDEBF7"}


def _ws_table(ws, headers: List[str], rows: List[List], widths: Optional[List[int]] = None, fills: Optional[List[Optional[str]]] = None, fill_col: int = 0):
    from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
    thin = Side(style="thin", color="BBBBBB")
    ws.append(headers)
    for c in ws[ws.max_row]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1F3864")
        c.alignment = Alignment(vertical="center", wrap_text=True)
    for i, r in enumerate(rows):
        ws.append(r)
        for c in ws[ws.max_row]:
            c.alignment = Alignment(vertical="top", wrap_text=True)
            c.border = Border(top=thin, bottom=thin, left=thin, right=thin)
        if fills and fills[i]:
            ws.cell(row=ws.max_row, column=fill_col + 1).fill = PatternFill("solid", fgColor=fills[i])
    for i, w in enumerate(widths or []):
        ws.column_dimensions[chr(65 + i)].width = w
    ws.freeze_panes = ws.cell(row=ws.min_row + 1, column=1)


def compliance_matrix_xlsx(bid: Dict) -> bytes:
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Compliance Matrix"
    ws.append([f"Compliance Matrix — {bid.get('bidder')} — {bid.get('tender_title')}"])
    ws.append([f"Generated {datetime.now().strftime('%d-%m-%Y %H:%M')} by SpecSure Bid Mirror. Verdict: {bid['verdict']} · Score {bid['compliance_score']}%"])
    ws.append([])
    rows, fills = [], []
    for r in bid["rows"]:
        ev = r.get("evidence") or []
        best = max(ev, key=lambda e: e.get("strength", 0)) if ev else {}
        rows.append([r["status"], r.get("clause_key"), r.get("parameter") or r.get("kind"), r.get("requirement"), r.get("required") or "",
                     best.get("raw_value") or best.get("snippet") or "", best.get("doc_name") or "", best.get("page") or "", r.get("explanation")])
        fills.append(STATUS_FILL.get(r["status"]))
    _ws_table(ws, ["Status", "Clause", "Parameter", "Tender requirement", "Required", "Offered / evidence", "Document", "Page", "Explanation"],
              rows, [20, 8, 26, 48, 14, 22, 26, 6, 60], fills)
    ws2 = wb.create_sheet("Action items")
    _ws_table(ws2, ["#", "Action"], [[i + 1, a] for i, a in enumerate(bid.get("action_items", []))], [5, 120])
    ws3 = wb.create_sheet("Documents")
    _ws_table(ws3, ["File", "Type", "SHA-256", "Licence / Lab", "Valid to / Report date"],
              [[d.get("doc_name"), d.get("doc_type"), d.get("sha256"), d.get("licence_no") or d.get("lab") or "", d.get("valid_to") or d.get("report_date") or ""]
               for d in bid.get("documents", [])], [34, 14, 66, 34, 20])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def findings_xlsx(twin: Dict) -> bytes:
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Findings"
    ws.append([f"Tender Linter Report — {twin['tender'].get('title')}"])
    rd = twin["readiness"]
    ws.append([f"Readiness {rd['score']} / 100 · Gate {rd['gate']} · KB snapshot {twin['provenance']['kb_snapshot'][:12]}"])
    ws.append([])
    rows, fills = [], []
    for f in twin["findings"]:
        rows.append([f["severity"].upper(), f["rule_id"], f["rule_name"], f.get("clause_key") or "", f.get("page") or "", f["message"],
                     f.get("suggestion") or "", f.get("basis") or "", f.get("review_status", "open")])
        fills.append(SEV_FILL.get(f["severity"]))
    _ws_table(ws, ["Severity", "Rule", "Name", "Clause", "Page", "Finding", "Suggestion", "Basis", "Review"], rows,
              [10, 12, 28, 8, 6, 70, 60, 40, 12], fills)
    ws2 = wb.create_sheet("Requirements")
    _ws_table(ws2, ["ID", "Clause", "Kind", "Parameter", "Min", "Max", "Unit", "Governing standard", "Test method", "Text"],
              [[r["id"], r["clause_key"], r["kind"], r.get("parameter_label") or "", r["norm"].get("min"), r["norm"].get("max"), r["norm"].get("unit"),
                (r.get("links") or {}).get("governing_standard"), (r.get("links") or {}).get("test_method"), r["text"]] for r in twin["requirements"]],
              [12, 8, 16, 28, 8, 8, 10, 22, 20, 80])
    ws3 = wb.create_sheet("Checklist")
    _ws_table(ws3, ["Pre-publication check", "OK?"], [[c["item"], "YES" if c["ok"] else "NO"] for c in rd["checklist"]], [70, 8],
              ["C6EFCE" if c["ok"] else "FF9999" for c in rd["checklist"]], 1)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def readiness_pdf(twin: Dict, title: Optional[str] = None) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm, bottomMargin=15 * mm,
                            title=title or "SpecSure Tender Readiness Report")
    ss = getSampleStyleSheet()
    small = ss["BodyText"].clone("small", fontSize=8, leading=10)
    story = [Paragraph(title or "Tender Readiness Report", ss["Title"]),
             Paragraph(f"<b>{twin['tender'].get('title')}</b>", ss["Heading3"]),
             Paragraph(f"As-of date: {twin['tender'].get('as_of')} · Readiness <b>{twin['readiness']['score']}</b>/100 · Gate <b>{twin['readiness']['gate']}</b>", ss["BodyText"]),
             Paragraph(f"Knowledge-base snapshot {twin['provenance']['kb_snapshot'][:16]} · engine {twin['provenance']['engine']} · solver {twin['provenance']['solver']}", small),
             Spacer(1, 6)]
    cl = [["Pre-publication check", "Status"]] + [[Paragraph(c["item"], small), "PASS" if c["ok"] else "FAIL"] for c in twin["readiness"]["checklist"]]
    t = Table(cl, colWidths=[140 * mm, 25 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3864")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                           ("GRID", (0, 0), (-1, -1), 0.3, colors.grey), ("FONTSIZE", (0, 0), (-1, -1), 8)]
                          + [("BACKGROUND", (1, i + 1), (1, i + 1), colors.HexColor("#C6EFCE" if c["ok"] else "#FF9999")) for i, c in enumerate(twin["readiness"]["checklist"])]))
    story += [t, Spacer(1, 8), Paragraph("Findings", ss["Heading2"])]
    rows = [["Sev.", "Rule", "Clause", "Finding / suggestion"]]
    for f in twin["findings"]:
        rows.append([f["severity"], f["rule_id"], f.get("clause_key") or "", Paragraph(f"{f['message']}<br/><i>{f.get('suggestion') or ''}</i>", small)])
    ft = Table(rows, colWidths=[16 * mm, 22 * mm, 14 * mm, 128 * mm], repeatRows=1)
    ft.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3864")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey), ("FONTSIZE", (0, 0), (-1, -1), 7), ("VALIGN", (0, 0), (-1, -1), "TOP")]
                           + [("BACKGROUND", (0, i + 1), (0, i + 1), colors.HexColor("#" + SEV_FILL.get(f["severity"], "FFFFFF"))) for i, f in enumerate(twin["findings"])]))
    story += [ft, Spacer(1, 8),
              Paragraph("Decision-support output. AI/solver findings require review by the competent authority; standards data must be verified on the official BIS portal.", small)]
    doc.build(story)
    return buf.getvalue()


def evidence_package_zip(bid: Dict, files: List[Dict], passport: Optional[Dict] = None) -> bytes:
    """files: [{name, bytes}] — packaged with a SHA-256 manifest so the bundle is tamper-evident."""
    import hashlib
    buf = io.BytesIO()
    manifest = {"generated": datetime.now().isoformat(), "bidder": bid.get("bidder"), "tender": bid.get("tender_title"),
                "verdict": bid.get("verdict"), "compliance_score": bid.get("compliance_score"), "files": []}
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("compliance_matrix.xlsx", compliance_matrix_xlsx(bid))
        for f in files:
            z.writestr(f"evidence/{f['name']}", f["bytes"])
            manifest["files"].append({"path": f"evidence/{f['name']}", "sha256": hashlib.sha256(f["bytes"]).hexdigest()})
        if passport:
            z.writestr("product_compliance_passport.vc.json", json.dumps(passport, indent=2))
        z.writestr("manifest.json", json.dumps(manifest, indent=2))
    return buf.getvalue()


def evaluation_pdf(tender_title: str, reference: str, ev: Dict, award: Optional[Dict] = None) -> bytes:
    """Evaluation & award recommendation report for the Tender Evaluation Committee."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm, bottomMargin=15 * mm,
                            title="Evaluation report")
    ss = getSampleStyleSheet()
    small = ss["BodyText"].clone("small", fontSize=8, leading=10)
    head = [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3864")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey), ("FONTSIZE", (0, 0), (-1, -1), 8), ("VALIGN", (0, 0), (-1, -1), "TOP")]
    story = [Paragraph("Technical & Financial Evaluation — Recommendation", ss["Title"]),
             Paragraph(f"<b>{tender_title}</b> ({reference})", ss["Heading3"]),
             Paragraph(f"Estimated value: Rs {ev.get('estimated_value') or 0:,.0f} · Make in India preference: "
                       f"{'applicable' if ev.get('mii_applicable') else 'not applicable (below Rs 5 lakh)'}", small), Spacer(1, 6)]
    integ = [["Bidder", "Sealed financial bid", "Commitment verified"]] + [[i["bidder"], "yes" if i["sealed"] else "no",
                                                                            {True: "VERIFIED", False: "MISMATCH", None: "-"}[i["verified"]]] for i in ev["integrity"]]
    t = Table(integ, colWidths=[80 * mm, 45 * mm, 45 * mm])
    t.setStyle(TableStyle(head))
    story += [Paragraph("Bid integrity", ss["Heading2"]), t, Spacer(1, 6)]
    for ln in ev["lines"]:
        story.append(Paragraph(f"Item {ln['index']}: {ln['label']} — {ln['quantity']:g} {ln['unit']}", ss["Heading2"]))
        rows = [["Bidder", "Technical", "Unit price", "MSE", "MII class"]]
        for b in ln.get("bids", []):
            rows.append([Paragraph(b["bidder"], small), "Responsive" if b["responsive"] else Paragraph("Non-responsive: " + "; ".join(b["reasons"][:2]), small),
                         f"Rs {b['unit_price']:,.2f}" if b.get("unit_price") is not None else "sealed", "yes" if b["mse"] else "no", b["mii_class"]])
        bt = Table(rows, colWidths=[45 * mm, 65 * mm, 25 * mm, 12 * mm, 23 * mm], repeatRows=1)
        bt.setStyle(TableStyle(head))
        story += [bt, Spacer(1, 4)]
        for s in ln.get("steps", []):
            story.append(Paragraph(f"• <b>{s['step']}</b>: {s['text']}", small))
        for f in ln.get("flags", []):
            story.append(Paragraph(f"⚠ {f['text']}", small))
        if ln.get("allocation"):
            al = [["Recommended supplier", "Quantity", "Unit price", "Value", "Basis"]] + [
                [a["bidder"], f"{a['quantity']:g} {ln['unit']}", f"Rs {a['unit_price']:,.2f}", f"Rs {a['value']:,.2f}", a["basis"]] for a in ln["allocation"]]
            at = Table(al, colWidths=[55 * mm, 25 * mm, 25 * mm, 30 * mm, 35 * mm])
            at.setStyle(TableStyle(head))
            story += [Spacer(1, 3), at]
        story.append(Spacer(1, 6))
    if ev.get("recommended_contract_value") is not None:
        story.append(Paragraph(f"<b>Recommended total contract value: Rs {ev['recommended_contract_value']:,.2f}</b>", ss["BodyText"]))
    if award:
        story.append(Paragraph(f"Committee decision recorded by {award.get('by')} on {award.get('at')}: {award.get('remarks') or ''}", small))
    story += [Spacer(1, 6), Paragraph(ev["note"], small),
              Paragraph("Generated by SpecSure (prototype, SIH 2026). Decision support only — the competent authority decides.", small)]
    doc.build(story)
    return buf.getvalue()
