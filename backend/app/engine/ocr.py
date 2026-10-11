"""
OCR router for scanned tenders, licences and test reports.

Engine choice (researched Sept 2026): Tesseract / tesseract.js struggle with low-resolution scans, tables and
Devanagari. The primary engine here is **RapidOCR 3.x running PaddleOCR's PP-OCRv6 detector + recogniser as ONNX**
(CPU, ~2 s/page, no GPU, Apache-2.0), with the **PP-OCRv5 Devanagari recogniser** for Hindi pages. Heavier
vision-language OCR (PaddleOCR-VL, 0.9B, 109 languages) can be plugged in for complex layouts and Hindi-heavy
scans on a GPU box (the mobile Devanagari recogniser reads clean Hindi words but misses some conjuncts);
Tesseract remains only as a last-resort fallback.

    page image ─► PP-OCRv6 (det + rec) ──conf ≥ τ──► domain repair ─► text + per-line boxes + confidence
                         │ low conf / Devanagari detected
                         ▼
                  PP-OCRv5 Devanagari rec ─► pick higher-confidence line
                         │ nothing usable
                         ▼
                  Tesseract (if installed)

Domain-aware repair fixes OCR confusions that matter for compliance, and logs every change:
"Im/W"→"lm/W", "IS l786"→"IS 1786", "5OO N/mm2"→"500 N/mm2", "N/rnm2"→"N/mm2", "CML-"→"CM/L-".
"""
from __future__ import annotations

import io
import os
import re
import time
from dataclasses import dataclass, field, asdict
from functools import lru_cache
from typing import List, Optional, Tuple

LOW_CONF = float(os.getenv("SPECSURE_OCR_LOW_CONF", "0.80"))


@dataclass
class OcrLine:
    text: str
    conf: float
    box: List[List[float]] = field(default_factory=list)
    script: str = "latin"


@dataclass
class OcrResult:
    text: str
    lines: List[OcrLine]
    engine: str
    mean_conf: float
    repairs: List[dict]
    ms: float
    languages: List[str]

    def to_dict(self):
        d = asdict(self)
        d["line_count"] = len(self.lines)
        return d


@lru_cache(maxsize=4)
def _rapid(lang: str = "en"):
    from rapidocr import RapidOCR  # type: ignore
    if lang == "hi":
        from rapidocr import LangRec, ModelType, OCRVersion  # type: ignore
        return RapidOCR(params={"Rec.lang_type": LangRec.DEVANAGARI, "Rec.ocr_version": OCRVersion.PPOCRV5,
                                "Rec.model_type": ModelType.MOBILE, "Global.log_level": "error"})
    return RapidOCR(params={"Global.log_level": "error"})


def available_engines() -> List[str]:
    out = []
    try:
        import rapidocr  # noqa: F401
        out.append("rapidocr-ppocrv6")
    except Exception:
        pass
    try:
        import pytesseract  # noqa: F401
        import shutil
        if shutil.which("tesseract"):
            out.append("tesseract")
    except Exception:
        pass
    return out


def _run_rapid(img: bytes, lang: str) -> List[OcrLine]:
    eng = _rapid(lang)
    r = eng(img)
    txts = list(getattr(r, "txts", None) or [])
    scores = list(getattr(r, "scores", None) or [])
    boxes = getattr(r, "boxes", None)
    boxes = boxes.tolist() if boxes is not None and hasattr(boxes, "tolist") else [[] for _ in txts]
    return [OcrLine(t, float(s), b, "devanagari" if re.search(r"[ऀ-ॿ]", t) else "latin") for t, s, b in zip(txts, scores, boxes)]


def _group_rows(lines: List[OcrLine]) -> str:
    """Re-assemble reading order: boxes on the same visual row are joined with ' | ' (keeps table cells apart)."""
    if not lines or not lines[0].box:
        return "\n".join(l.text for l in lines)
    items = []
    for l in lines:
        ys = [p[1] for p in l.box]
        xs = [p[0] for p in l.box]
        items.append(((min(ys) + max(ys)) / 2, min(xs), max(ys) - min(ys), l.text))
    items.sort()
    rows: List[List[tuple]] = []
    for it in items:
        if rows and abs(rows[-1][0][0] - it[0]) < max(8.0, 0.5 * it[2]):
            rows[-1].append(it)
        else:
            rows.append([it])
    out = []
    for r in rows:
        r.sort(key=lambda t: t[1])
        out.append(" | ".join(t[3] for t in r) if len(r) > 1 else r[0][3])
    return "\n".join(out)


REPAIRS: List[Tuple[str, str, str]] = [
    (r"\b[Il1]m\s*/\s*W\b", "lm/W", "unit: lumen per watt"),
    (r"N\s*/\s*rn\s*m\s*(2|²)", r"N/mm\1", "unit: N/mm²"),
    (r"\bsq\.?\s*rnm\b", "sq mm", "unit: sq mm"),
    (r"(?<=\d)\s*rnm\b", " mm", "unit: mm"),
    (r"\bCM\s*/?\s*L\s*[-–—]\s*", "CM/L-", "BIS licence prefix"),
    (r"(?<=\d)\s*[o°]\s*C\b", " °C", "unit: degree Celsius"),
    (r"\b(IS|IEC)(?=\d{3,5}\b)", r"\1 ", "space after standard prefix"),
    (r"(?<=[a-z])(?=(?:TC|CM/L|IS)[-\s]?\d)", " ", "word boundary before identifier"),
]


def repair(text: str) -> Tuple[str, List[dict]]:
    log: List[dict] = []
    t = text
    for rx, rep, why in REPAIRS:
        for m in list(re.finditer(rx, t)):
            new = m.expand(rep)
            if new != m.group(0):
                log.append({"from": m.group(0), "to": new, "rule": why})
        t = re.sub(rx, rep, t)

    # standard numbers: "IS l786", "IS I786", "IS 1O786" -> digits
    def fix_is(m):
        body = m.group(2)
        fixed = body.translate(str.maketrans({"l": "1", "I": "1", "O": "0", "o": "0", "S": "5", "B": "8"}))
        if fixed != body:
            log.append({"from": m.group(0), "to": m.group(1) + fixed, "rule": "standard number digits"})
        return m.group(1) + fixed
    t = re.sub(r"\b(IS\s*[:.]?\s*)([0-9lIOoSB]{3,5})(?=\b|\s|:|\()", fix_is, t)

    # digits inside numbers: 5OO -> 500, 1l0 -> 110 (only when the token is mostly digits)
    def fix_num(m):
        tok = m.group(0)
        digits = sum(c.isdigit() for c in tok)
        if digits >= max(1, len(tok) - 2) and digits < len(tok):
            fixed = tok.translate(str.maketrans({"O": "0", "o": "0", "l": "1", "I": "1"}))
            if fixed != tok and fixed.replace(".", "").isdigit():
                log.append({"from": tok, "to": fixed, "rule": "letter/digit confusion in a number"})
                return fixed
        return tok
    t = re.sub(r"(?<![A-Za-z])[0-9OolI][0-9OolI.]{1,8}(?![A-Za-z])", fix_num, t)
    return t, log


def ocr_image(img: bytes, languages: Optional[List[str]] = None) -> OcrResult:
    t0 = time.time()
    langs = languages or [x.strip() for x in os.getenv("SPECSURE_OCR_LANGS", "en,hi").split(",") if x.strip()]
    lines: List[OcrLine] = []
    engine = "none"
    try:
        lines = _run_rapid(img, "en")
        engine = "rapidocr/PP-OCRv6"
        mean = sum(l.conf for l in lines) / len(lines) if lines else 0.0
        if "hi" in langs:
            # Devanagari lines are invisible to the Latin recogniser (dropped below its score threshold),
            # so the Devanagari recogniser always gets a pass and the two are ensembled box-by-box.
            hi = _run_rapid(img, "hi")
            if hi and any(l.script == "devanagari" for l in hi):
                # line-level ensemble: keep the more confident reading of each box
                merged = []
                for l in lines:
                    alt = next((h for h in hi if h.box and l.box and _iou(h.box, l.box) > 0.5), None)
                    better = alt and alt.script == "devanagari" and _deva_share(alt.text) >= 0.6 and alt.conf > l.conf + 0.05
                    merged.append(alt if better else l)
                extra = [h for h in hi if h.script == "devanagari" and h.conf >= 0.8 and _deva_share(h.text) >= 0.6
                         and not any(_iou(h.box, l.box) > 0.5 for l in lines if h.box and l.box)]
                lines = merged + extra
                engine = "rapidocr/PP-OCRv6 + PP-OCRv5-devanagari"
    except Exception:
        lines = []
    if not lines:
        try:
            import pytesseract  # type: ignore
            from PIL import Image
            txt = pytesseract.image_to_string(Image.open(io.BytesIO(img)), lang="eng+hin" if "hi" in langs else "eng")
            lines = [OcrLine(x, 0.0) for x in txt.splitlines() if x.strip()]
            engine = "tesseract"
        except Exception:
            lines = []
    raw = _group_rows(lines)
    text, log = repair(raw)
    mean = round(sum(l.conf for l in lines) / len(lines), 4) if lines and engine != "tesseract" else 0.0
    return OcrResult(text=text, lines=lines, engine=engine, mean_conf=mean, repairs=log, ms=round((time.time() - t0) * 1000, 1),
                     languages=sorted({l.script for l in lines}) or ["latin"])


def _deva_share(t: str) -> float:
    letters = [c for c in t if not c.isspace() and not c.isdigit() and c not in ".,:;-()|/"]
    return sum(1 for c in letters if "\u0900" <= c <= "\u097F") / len(letters) if letters else 0.0


def _iou(a, b) -> float:
    try:
        ax0, ay0 = min(p[0] for p in a), min(p[1] for p in a)
        ax1, ay1 = max(p[0] for p in a), max(p[1] for p in a)
        bx0, by0 = min(p[0] for p in b), min(p[1] for p in b)
        bx1, by1 = max(p[0] for p in b), max(p[1] for p in b)
        ix = max(0.0, min(ax1, bx1) - max(ax0, bx0))
        iy = max(0.0, min(ay1, by1) - max(ay0, by0))
        inter = ix * iy
        union = (ax1 - ax0) * (ay1 - ay0) + (bx1 - bx0) * (by1 - by0) - inter
        return inter / union if union > 0 else 0.0
    except Exception:
        return 0.0


def ocr_pdf_page(page, dpi: int = 200) -> OcrResult:
    pix = page.get_pixmap(dpi=dpi)
    return ocr_image(pix.tobytes("png"))
