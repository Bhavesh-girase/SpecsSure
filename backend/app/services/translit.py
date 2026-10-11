"""
Indic-script loanword matcher.

Procurement text in Indian languages is full of English technical words written in the local script — "स्प्लिट एयर
कंडीशनर", "ಸೀಲಿಂಗ್ ಫ್ಯಾನ್", "সিলিং ফ্যান", "சிமெண்ட்", "ట్రాన్స్‌ఫార్మర్". No dictionary lists them all, but they are
recoverable: romanise the word, reduce it to a consonant skeleton with sound classes that survive the script (Tamil has no
voiced/unvoiced distinction, Hindi writes "f" as फ = ph, English "tion" sounds "shan"), and look that skeleton up in the
vocabulary of Indian Standard titles. Spelled-out acronyms ("यूपीएस" = U-P-S, "एमसीबी" = M-C-B) are segmented into
letter names first.

Deterministic, offline, explainable: every match can be shown as  स्प्लिट → "split" (skeleton SPLT).
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple

SCRIPT_RANGES = [("devanagari", 0x0900, 0x097F), ("bengali", 0x0980, 0x09FF), ("gurmukhi", 0x0A00, 0x0A7F), ("gujarati", 0x0A80, 0x0AFF),
                 ("oriya", 0x0B00, 0x0B7F), ("tamil", 0x0B80, 0x0BFF), ("telugu", 0x0C00, 0x0C7F), ("kannada", 0x0C80, 0x0CFF),
                 ("malayalam", 0x0D00, 0x0D7F)]

# Devanagari letter names (for spelled acronyms)
LETTERS_DEV = {"ए": "A", "बी": "B", "सी": "C", "डी": "D", "ई": "E", "एफ": "F", "जी": "G", "एच": "H", "आई": "I", "जे": "J", "के": "K",
               "एल": "L", "एम": "M", "एन": "N", "ओ": "O", "पी": "P", "क्यू": "Q", "आर": "R", "एस": "S", "टी": "T", "यू": "U", "वी": "V",
               "डब्ल्यू": "W", "एक्स": "X", "वाई": "Y", "ज़ेड": "Z", "जेड": "Z"}


def script_of(word: str) -> Optional[str]:
    for ch in word:
        cp = ord(ch)
        for name, lo, hi in SCRIPT_RANGES:
            if lo <= cp <= hi:
                return name
    return None


def acronym(word: str) -> Optional[str]:
    """'यूपीएस' → 'UPS', 'एमसीबी' → 'MCB' (greedy segmentation into Devanagari letter names; ≥ 2 letters)."""
    w = word.replace("़", "")                      # nukta
    out, i = [], 0
    names = sorted(LETTERS_DEV, key=len, reverse=True)
    while i < len(w):
        for n in names:
            if w.startswith(n.replace("़", ""), i):
                out.append(LETTERS_DEV[n])
                i += len(n.replace("़", ""))
                break
        else:
            return None
    return "".join(out) if len(out) >= 2 else None


def romanise(word: str) -> Optional[str]:
    sc = script_of(word)
    if not sc:
        return None
    try:
        from indic_transliteration import sanscript
        from indic_transliteration.sanscript import transliterate
    except Exception:  # noqa: BLE001
        return None
    w = word.replace("ॉ", "ो").replace("ॅ", "े")     # chandra o / chandra e (ऑ, ॅ) → o / e
    w = w.replace("‌", "").replace("‍", "")
    scheme = {"devanagari": sanscript.DEVANAGARI, "bengali": sanscript.BENGALI, "gurmukhi": sanscript.GURMUKHI, "gujarati": sanscript.GUJARATI,
              "oriya": sanscript.ORIYA, "tamil": sanscript.TAMIL, "telugu": sanscript.TELUGU, "kannada": sanscript.KANNADA,
              "malayalam": sanscript.MALAYALAM}[sc]
    try:
        r = transliterate(w, scheme, sanscript.ITRANS)
    except Exception:  # noqa: BLE001
        return None
    return r


def _classes(s: str) -> str:
    """Consonant skeleton with script-robust sound classes. Input: lower-case latin approximating pronunciation."""
    s = s.lower()
    lead_vowel = bool(re.match(r"[aeiou]", s))
    rules = [("chh", "S"), ("ch", "S"), ("sh", "S"), ("ph", "F"), ("bh", "P"), ("dh", "T"), ("th", "T"), ("kh", "K"), ("gh", "K"),
             ("jh", "S"), ("ng", "N"), ("ck", "K"), ("qu", "KP"), ("x", "KS")]
    for a, b in rules:
        s = s.replace(a, b)
    table = {"k": "K", "g": "K", "q": "K", "c": "K", "s": "S", "z": "S", "j": "S", "t": "T", "d": "T", "p": "P", "b": "P", "f": "F",
             "v": "P", "w": "P", "m": "M", "n": "N", "l": "L", "r": "R"}
    out = []
    for ch in s:
        if ch in "SFPTKMN":
            c = ch
        else:
            c = table.get(ch)
        if c and (not out or out[-1] != c):
            out.append(c)
    key = "".join(out)
    key = re.sub(r"NK$", "N", key)                    # sIliMg / siliM / ceiling
    return ("A" + key) if lead_vowel else key


def english_key(word: str) -> str:
    w = word.lower()
    w = re.sub(r"tion|sion|ssion|cian", "shan", w)
    w = re.sub(r"ture\b", "char", w)
    w = re.sub(r"c(?=[eiy])", "s", w)
    w = re.sub(r"g(?=[eiy])", "j", w)
    w = re.sub(r"ough", "o", w)
    w = re.sub(r"^kn", "n", w)
    w = re.sub(r"gh", "", w)
    w = re.sub(r"(?<=[a-z])y\b", "i", w)
    return _classes(w)


def indic_key(roman: str) -> str:
    r = roman
    r = r.replace("M", "n").replace(".n", "n").replace("~N", "n").replace("~n", "n")     # anusvara / nasal marks
    r = re.sub(r"[AIUEO]", lambda m: m.group(0).lower(), r)                             # long vowels
    r = r.replace("R^i", "ri").replace("RRi", "ri").replace("è", "e")
    r = r.replace("T", "t").replace("D", "d").replace("N", "n").replace("Sh", "sh").replace("L", "l")
    r = re.sub(r"[^a-zA-Z]", "", r)
    r = re.sub(r"y(?=[aeiou])", "", r) if len(r) > 3 else r                             # phyAn → fan
    return _classes(r)


ROMAN_LETTERS = {"e": "A", "bi": "B", "si": "C", "di": "D", "i": "E", "ef": "F", "eph": "F", "ji": "G", "ech": "H", "ai": "I", "je": "J",
                 "ke": "K", "el": "L", "em": "M", "en": "N", "o": "O", "pi": "P", "kyu": "Q", "ar": "R", "es": "S", "ti": "T", "yu": "U",
                 "vi": "V", "dablyu": "W", "eks": "X", "vai": "Y", "zed": "Z", "jed": "Z"}
KNOWN_ACRONYMS = {"UPS", "LPG", "LED", "MCB", "RCCB", "ELCB", "RCBO", "PVC", "UPVC", "CPVC", "HDPE", "LDPE", "XLPE", "ACSR", "CFL", "BLDC",
                  "AAC", "RCC", "PCC", "TMT", "GI", "MS", "SS", "DI", "CI", "OPC", "PPC", "PSC", "CCTV", "PPE", "RO", "AC", "DC", "PV", "FRP",
                  "ERW", "ACB", "VCB", "DG", "CNG", "PNG", "ABS", "EPDM", "PTFE", "UV", "LT", "HT", "SPD", "PET", "PP", "HSD"}


def roman_acronym(roman: str) -> Optional[str]:
    r = roman.lower().replace("\u00e8", "e").replace("aa", "a").replace("ii", "i").replace("uu", "u")
    r = re.sub(r"[^a-z]", "", r)
    names = sorted(ROMAN_LETTERS, key=len, reverse=True)
    out, i = [], 0
    while i < len(r):
        for n in names:
            if r.startswith(n, i):
                out.append(ROMAN_LETTERS[n])
                i += len(n)
                break
        else:
            return None
    a = "".join(out)
    return a if len(out) >= 2 and a in KNOWN_ACRONYMS else None


def _norm_en(w: str) -> str:
    w = w.lower()
    for a, b in (("tion", "shan"), ("sion", "shan"), ("ture", "char"), ("ph", "f"), ("ck", "k"), ("qu", "kv"), ("x", "ks"), ("ee", "i"),
                 ("ea", "i"), ("ie", "i"), ("ei", "i"), ("oo", "u"), ("ai", "e"), ("ay", "e"), ("w", "v")):
        w = w.replace(a, b)
    w = re.sub(r"c(?=[eiy])", "s", w)
    w = re.sub(r"g(?=[eiy])", "j", w)
    w = w.replace("c", "k").replace("y", "i")
    return re.sub(r"(.)\1+", r"\1", w)


def _norm_in(r: str) -> str:
    r = r.replace("M", "n").replace("\u00e8", "e").replace("R^i", "ri")
    r = re.sub(r"[AIUEO]", lambda m: m.group(0).lower(), r)
    r = r.replace("T", "t").replace("D", "d").replace("N", "n").replace("Sh", "sh").replace("L", "l")
    r = re.sub(r"[^a-zA-Z]", "", r).lower()
    r = r.replace("ph", "f").replace("ai", "e").replace("au", "o").replace("w", "v")
    r = re.sub(r"(?<=[kgtdpbj])h", "", r)
    r = re.sub(r"(?<=[^aeiou])a$", "", r)             # final schwa
    return re.sub(r"(.)\1+", r"\1", r)


_CLS = {c: k for k, cs in {"K": "kgq", "T": "td", "P": "pbvf", "S": "szj", "M": "m", "N": "n", "L": "l", "R": "r"}.items() for c in cs}


def wdist(a: str, b: str) -> float:
    """Weighted edit distance: vowel↔vowel 0.5, same sound class 0.4, 'h' / vowel insertions cheap."""
    V = set("aeiou")
    n, m = len(a), len(b)
    D = [[0.0] * (m + 1) for _ in range(n + 1)]
    ins = lambda ch: 0.5 if ch in V else (0.3 if ch in "hy" else 1.0)  # noqa: E731
    for i in range(1, n + 1):
        D[i][0] = D[i - 1][0] + ins(a[i - 1])
    for j in range(1, m + 1):
        D[0][j] = D[0][j - 1] + ins(b[j - 1])
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            x, y = a[i - 1], b[j - 1]
            if x == y:
                sub = 0.0
            elif x in V and y in V:
                sub = 0.5
            elif _CLS.get(x) and _CLS.get(x) == _CLS.get(y):
                sub = 0.4
            else:
                sub = 1.0
            D[i][j] = min(D[i - 1][j] + ins(x), D[i][j - 1] + ins(y), D[i - 1][j - 1] + sub)
    return D[n][m] / max(n, m, 1)


class LoanwordMatcher:
    def __init__(self):
        self.by_key: Dict[str, List[Tuple[int, str]]] = defaultdict(list)
        self.ready = False

    def build(self, vocab: Counter, bigrams: Optional[Counter] = None):
        self.bigrams = bigrams or Counter()
        by: Dict[str, List[Tuple[int, str]]] = defaultdict(list)
        for w, n in vocab.items():
            if len(w) < 3 or not w.isalpha() or n < 2:
                continue
            by[english_key(w)].append((n, w))
        for k in by:
            by[k].sort(reverse=True)
        self.by_key = by
        self.ready = True

    def candidates(self, word: str, max_d: float = 0.34) -> List[dict]:
        """Ranked English readings of an Indic-script word: [{"english", "roman", "key", "d"}] (best first)."""
        ac = acronym(word)
        if ac:
            return [{"english": ac, "roman": word, "key": "acronym", "d": 0.0}]
        rom = romanise(word)
        if not rom:
            return []
        ra = roman_acronym(rom)
        if ra:
            return [{"english": ra, "roman": rom, "key": "acronym", "d": 0.0}]
        if not self.ready:
            return []
        key = indic_key(rom)
        if len(key.lstrip("A")) < 2:
            return []
        norm = _norm_in(rom)
        out = []
        for n, w in self.by_key.get(key, [])[:60]:
            d = wdist(norm, _norm_en(w))
            if d <= max_d:
                out.append({"english": w, "roman": rom, "key": key, "d": round(d, 3), "n": n})
        out.sort(key=lambda x: (x["d"], -x["n"]))
        if len(out) > 1:                       # near-ties go to the more common title word ("pepar" → paper, not pepper)
            near = [x for x in out if x["d"] <= out[0]["d"] + 0.05]
            best = max(near, key=lambda x: x["n"])
            out.remove(best)
            out.insert(0, best)
        return out

    def match(self, word: str) -> Optional[dict]:
        c = self.candidates(word)
        return c[0] if c else None


MATCHER = LoanwordMatcher()


def set_vocabulary(vocab: Counter, bigrams: Optional[Counter] = None):
    MATCHER.build(vocab, bigrams)


def read_words(words: List[str]) -> List[Optional[dict]]:
    """Per-word best reading, using title bigrams to break ties ("সিলিং ফ্যান" → ceiling fan, not sealing fan)."""
    cands = [MATCHER.candidates(w)[:4] for w in words]
    best = [c[0] if c else None for c in cands]
    bg = getattr(MATCHER, "bigrams", None) or Counter()
    for i in range(len(words) - 1):
        a, b = cands[i], cands[i + 1]
        if not a or not b:
            continue
        pairs = [(bg.get((x["english"], y["english"]), 0), -(x["d"] + y["d"]), x, y) for x in a for y in b
                 if x["d"] <= a[0]["d"] + 0.12 and y["d"] <= b[0]["d"] + 0.12]
        pairs.sort(key=lambda p: (p[0], p[1]), reverse=True)
        if pairs and pairs[0][0] > 0:
            best[i], best[i + 1] = pairs[0][2], pairs[0][3]
    return best


def title_vocabulary(titles) -> Tuple[Counter, Counter]:
    c: Counter = Counter()
    bg: Counter = Counter()
    for t in titles:
        ws = re.findall(r"[a-z]{2,}", (t or "").lower())
        for w in set(x for x in ws if len(x) >= 3):
            c[w] += 1
        for x, y in zip(ws, ws[1:]):
            bg[(x, y)] += 1
    return c, bg


def strip_marks(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))
