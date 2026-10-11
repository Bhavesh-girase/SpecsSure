# SpecSure — PPT Showcase Guide & Content Blueprint

> **Purpose:** A deep-audit of the entire repository — every engine module, service, frontend page, data pipeline, evaluation script, and competitive edge — distilled into slide-ready content blocks. Use this as the master checklist for what to include and highlight in the SIH presentation.

---

## 🔥 The "Wow" Moments — Lead With These

### 1. Formal Proof of Contradictions (Z3 SMT Solver)
- **File:** `engine/constraints.py` (322 lines)
- **What it does:** Every quantitative requirement becomes a tracked linear constraint. Z3 proves if the set of clauses is satisfiable or not. On UNSAT → **Minimal Unsatisfiable Subset (MUS)** with arithmetic witness.
- **Demo moment:** Clause 4.2 says yield ≥ 500, Clause 7.2 says ≤ 480. The solver doesn't "think" — it **proves** this is impossible with the exact conflict set.
- **Why it matters:** No other SIH26108 team uses formal verification. LLMs guess; Z3 proves.
- **Slide idea:** Side-by-side: LLM says "these might conflict" vs Z3 says "UNSAT — here is the proof and the minimal set of clauses causing it."

### 2. Tender Compiler — Treats a Tender as Source Code
- **File:** `engine/compiler.py` (353 lines)
- **Pipeline:** Documents → Parse → Clause AST → Extract typed requirements → Resolve standards → Z3 verify → Market analyse → Lint (38 rules) → Readiness gate
- **Key number:** Planted-issue recall **29/29**, zero critical false alarms, ~15 ms mean compile
- **Slide idea:** Show the pipeline diagram. The readiness gate that **refuses to publish** a tender with critical issues (HTTP 409).

### 3. "One Sentence to a Complete Tender" — Tender Studio
- **Files:** `engine/intent.py` (469 lines), `engine/synthesizer.py` (567 lines)
- **Demo:** Officer types "need a tender of 500 light bulbs and 100 meteres" → intent parser → KG bundles → clause plan → render → **the tender compiler audits its own draft** → self-repair loop → competition guard
- **Hinglish/Hindi support:** "500 LED bulb 9 watt aur 100 meter 2.5 sq mm taar chahiye, 30 din mein" works too
- **The self-check loop** is the killer feature: the system generates AND verifies.

### 4. Procurement Knowledge Graph (Temporal)
- **File:** `engine/kg.py` (438 lines)
- **Schema:** Item → Standard → Edition → Amendment → Regulation → Parameter → Test → Lab → Manufacturer + Policy layer
- **Key:** Every edge carries `valid_from`, `valid_to`, `source_url`, `verification_state`
- **Export:** Neo4j (Cypher) and JSON-LD
- **Demo moment:** Change the date → the graph changes. "Time machine" for standards.

### 5. Product Compliance Passport — W3C Verifiable Credential
- **File:** `engine/passport.py` (165 lines)
- **Spec:** W3C VC Data Model 2.0, `eddsa-jcs-2022` proof, Ed25519 signature, `did:key` issuer
- **Verifiable offline:** No call to SpecSure required
- **Tamper detection:** Change one value → signature fails
- **Aligned with:** EU Digital Product Passport vision

---

## 📊 Numbers That Impress Judges

| Metric | Value | Source |
|---|---|---|
| Indian Standards in knowledge base | **29,875** | BIS KYS catalogue + BIS e-Sale portal |
| Full texts parsed | **19,492** (of 19,704 distinct) | Internet Archive (Public.Resource.Org) |
| Typed links from standards' own text | **80,834** | Scope, references, test methods, terminology |
| Status of every standard (active/withdrawn) | **29,710** | BIS Know-Your-Standards DataTables API |
| Current editions | **29,607** | BIS e-Sale portal (27 Sep 2026) |
| Compulsory certification rows | **828** | BIS Scheme-I/II/X + hallmarking |
| GeM categories linked | **821** (from 3,794 live bids) | GeM public bid listing |
| BIS-recognised testing labs | **482** for 823 standards | BIS LIMS |
| Lab-standard entries with charges | **8,805** | BIS LIMS |
| Tender compiler recall (planted issues) | **29/29** | `scripts/evaluate_compiler.py` |
| Critical false alarms (clean tender) | **0** | Same benchmark |
| Mean compile time | **~15 ms** (demo tender ~100 ms) | Measured 25 Sep 2026 |
| Standards retrieval top-1 / top-3 (offline) | **87.5% / 100%** | `scripts/run_evaluation.py` |
| GeM category name top-1 (clean) | **80.4%** | 403 labels by GeM |
| "Recommended" precision | **89.6%** | GeM names |
| Vague/service request abstention rate | **91.4%** | 35 cases |
| Real tender documents tested | **63** (1,542 pages) | `scripts/real_tender_study.py` |
| "Recommended" correct on real docs | **~85%** | Spot-check |
| Competitor repos surveyed | **28** | `docs/COMPETITIVE_LANDSCAPE.md` |
| Pytest test count | **50** | Backend test suite |
| Engine modules | **36** | `backend/app/engine/` |
| API endpoints | **60+** | `docs/api-reference.md` |
| Linter rules | **38** with stable IDs | `engine/linter.py` (889 lines!) |
| Frontend pages | **19** | Next.js app directory |

---

## 🏗️ Feature Blocks for PPT Slides

### Block A: Standards Intelligence (Core PS Requirement)
- **Hybrid retrieval:** 3-field BM25 (title ×2, scope ×1, aliases ×1.5) + bge-m3 multilingual dense index, fused with RRF
- **Confidence gating:** Abstains rather than guessing; withdrawn/title-only never "Recommended"
- **Compliance tree:** Transitive closure of normative references + test methods (IS 1786 → 7 → 29 → 37 standards)
- **Spec block generator:** Copy-ready clauses with every sentence sourced, Word export
- **Files:** `services/corpus_service.py` (55K!), `services/retrieval_service.py`, `engine/spec_block.py`

### Block B: Temporal Standards Engine
- **File:** `engine/temporal.py` (7K)
- **What it does:** Resolves any citation as-of a date — handles withdrawn, superseded, merged families (IS 8112 → IS 269), amendments in force vs pending, QCOs upcoming within horizon
- **Demo:** Change the as-of date → IS 16102 switches from 2012 to 2026 edition

### Block C: Tender Linter — "ESLint for Tenders"
- **File:** `engine/linter.py` (889 lines, 52K!)
- **38 rules** across 9 categories: ambiguity, drafting, measurability, standards, certification, contradiction, restriction, completeness, security
- **GFR 2017 basis:** Rules cite Rule 144(i), 144(iii) etc.
- **Stable IDs:** Findings are fingerprinted → review status survives re-compilation
- **SARIF 2.1.0 export:** Industry-standard code-scanning format
- **Autofixes:** Draft corrigendum in standard government phrasing

### Block D: Market Restriction Analysis
- **File:** `engine/market.py` (10K)
- **Product-space funnel:** Filters licensed manufacturers by each clause in document order
- **Leave-one-out:** "Drop this clause → how many manufacturers return?"
- **Relax-to-standard:** "Use the IS limit instead of the tender's limit → how many?"
- **GFR Rule 144 evidence:** Objective proof of restriction, not an opinion
- **Demo:** Carbon ≤ 0.18% leaves 1 of 12; relaxing to IS limit restores 6

### Block E: Corrigendum Management — "Git for Tenders"
- **File:** `engine/corrigendum.py` (14K)
- **Per-clause history, word diffs, blame**
- **Regression detection:** Corrigendum 2 breaks something Corrigendum 1 fixed → caught
- **Draft generation:** From approved pre-bid answers or linter autofixes

### Block F: Smart Bid Form + Tender Match Index
- **File:** `engine/bidform.py` (30K — 447 lines!)
- **Form derivation:** From the canonical tender (after corrigenda) — always matches the latest version
- **OCR autofill:** Drop a scanned NABL report → PP-OCRv6 reads it → form fills itself (97% accuracy)
- **Match Index:** Knock-outs, coverage, confidence, headroom — transparent scoring
- **Path to compliance:** What to attach (curable) vs what to change (substantive)

### Block G: OCR Engine
- **File:** `engine/ocr.py` (229 lines)
- **Primary:** RapidOCR 3.x with PaddleOCR PP-OCRv6 (ONNX, CPU, ~2s/page)
- **Devanagari:** PP-OCRv5 Devanagari recogniser for Hindi pages
- **Domain repair:** Fixes OCR confusions that matter: "Im/W" → "lm/W", "IS l786" → "IS 1786", "5OO N/mm2" → "500 N/mm2"
- **Fallback chain:** PP-OCRv6 → PP-OCRv5 Devanagari → Tesseract

### Block H: Multilingual — Offline, Explainable
- **Files:** `services/translit.py` (288 lines), `services/multilingual.py` (16K)
- **Loanword transliteration:** "स्प्लिट एयर कंडीशनर" → split (skeleton SPLT) + air (skeleton AR) + conditioner (skeleton KNDSNR) → IS 1391 (Part 2)
- **Acronym detection:** "यूपीएस" → UPS, "एमसीबी" → MCB
- **Scripts:** Devanagari, Bengali, Gurmukhi, Gujarati, Oriya, Tamil, Telugu, Kannada, Malayalam
- **No LLM required:** Every match explainable word-by-word
- **Voice:** Web Speech API for input and output

### Block I: Bid Evaluation & Award Engine
- **File:** `engine/evaluation.py` (213 lines)
- **Full lifecycle:** Technical evaluation → Sealed financial opening (SHA-256 verified) → L1 → Make in India (Class-I 20% margin) → MSE (L1+15%, 25% share) → Award
- **Policy compliance:** PPP-MII 2017 (revised 2020), MSE Order 2012 — every step cited
- **Financial integrity:** Sealed-bid commitment verified against ledger
- **Output:** PDF evaluation report, comparative statement

### Block J: Trust & Governance
- **Hash-chained audit ledger:** `engine/ledger.py` — every compile, review, decision is hash-chained with document hashes + KB snapshot hash + engine version
- **Guardrails:** `engine/guardrails.py` — prompt-injection screening, evidence fencing, grounded-quote verification
- **Review persistence:** Finding fingerprints survive re-compilation; dismissals require justification
- **Publish gate:** HTTP 409 while critical findings are open

### Block K: MCP Server
- **File:** `mcp_server.py` (76 lines)
- **Tools:** `lint_tender`, `lint_tender_sarif`, `resolve_standard`, `check_contradictions`, `compare_standards`
- **Integration:** Claude Desktop, IDE agents, GeM-side copilots
- **Philosophy:** "The assistant converses, SpecSure proves"

### Block L: Browser Extension (Manifest V3)
- **Files:** `extension/` — `manifest.json`, `content.js`, `sidepanel.js`, `background.js`
- **GeM bid listing:** Annotates every bid with IS status, amendments, certification
- **Bid document analysis:** Items, cited standards, forgotten test methods
- **Context menu:** Select text on any page → "Find Indian Standards"
- **No data leaves the machine** except to the SpecSure API

### Block M: Government Portal UI
- **GIGW-compliant:** Skip link, A-/A/A+/A++ text size, high contrast, English/Hindi
- **Role workspaces:** Officer, Contractor, Citizen/Auditor
- **Lifecycle:** Query → Sealed bid → Technical evaluation → Financial opening → L1 → MII → MSE → Award → PDF → Ledger

---

## 🎯 Slides to Add/Strengthen in the PPT

### Slide: "Intent to Tender in 60 Seconds" (Tender Studio)
- **Content:** Show the NL input → questions → verified draft flow
- **Key visual:** The self-repair loop diagram from `synthesizer.py`
- **Talking point:** "The same compiler that audits human tenders verifies the AI-generated draft"

### Slide: "The Contractor's Side" (Bid Form + Match Index)
- **Content:** Form derivation → OCR autofill → Match Index → Path to compliance
- **Key visual:** Before/after of a scanned test report → filled form fields
- **Talking point:** "Drop a phone photo of a NABL report — PP-OCRv6 reads it at 97% and fills the form"

### Slide: "Sealed Bids & Fair Evaluation"
- **Content:** SHA-256 commitment → integrity verification → L1 → Make in India → MSE
- **Key visual:** The evaluation pipeline with policy citations
- **Talking point:** "Every price is re-hashed at opening and matched against the ledger commitment"

### Slide: "Knowledge Graph Explorer" 
- **Content:** Interactive temporal graph with date slider
- **Key visual:** Screenshot of `/kg` page showing Item → Standard → Edition → Regulation edges
- **Talking point:** "Change the date, and the graph changes. Every edge carries validity dates and a source URL."

### Slide: "28 Competitors, One Clear Leader"
- **Content:** Table from `COMPETITIVE_LANDSCAPE.md`
- **Key highlights:** 
  - Next-largest KB: ~2,500 standards (one division). Ours: 29,875 (all divisions)
  - No competitor has real BIS LIMS lab data
  - No competitor has Z3 formal verification
  - No competitor has a browser extension
  - No competitor has the tender compiler + linter + corrigendum + market analysis

### Slide: "Data Pipeline — Not Hand-Curated"
- **Content:** List the 28 scripts in `backend/scripts/`
- **Key scripts to highlight:**
  - `bis_kys_catalogue.py` — BIS Know-Your-Standards (29,710 standards)
  - `bis_portal_status.py` — Status and amendments from BIS portal
  - `bis_labs.py` — Testing labs from BIS LIMS (482 labs)
  - `gem_categories.py` — GeM procurement categories (821)
  - `corpus_benchmark.py` — Reproducible evaluation
  - `real_tender_study.py` — 63 real documents
- **Talking point:** "Every data source has its own script. Re-run to refresh. Every answer is dated."

### Slide: "Honest About Limitations"
- **Full text only for pre-2020 standards** (10,171 newer ones are title-only)
- **Indian languages are the weakest area** (39% top-1 held-out)
- **Labels of team-written sets are ours**
- **Status/amendments verified for 1,138 standards**, not all 29,875
- **Talking point:** "We show our weak numbers. 39% top-1 on Indian languages is poor — and the Evidence page says so."

---

## 🧪 Technical Depth Slides (for judge Q&A)

### How Z3 Encoding Works
- One real variable per `<domain>.<parameter>` (e.g., `steel.yield_strength`)
- Domains prevent cross-contamination (cement vs concrete compressive strength)
- Engineering axioms tracked too: UTS ≥ (TS/YS) × YS
- On UNSAT: deletion-based MUS minimisation → minimal explanation set
- Iterative conflict enumeration for independent conflicts
- Fallback: interval arithmetic if Z3 not installed

### How the Intent Parser Works
- Deterministic first: number words (English/Hindi/Devanagari digits/lakh-crore)
- Typo-tolerant unit matching (rapidfuzz)
- Item matching against KG item layer aliases
- Slot extraction: 9 W, 2.5 sq mm, Fe 500D, B22, 4000 K, IP66
- Questions generated from KG's mandatory slots + CO_PROCURED_WITH disambiguation
- Optional LLM: only proposes items, validated against catalogue

### How Transliteration Works
- Romanise Indic script word → reduce to consonant skeleton
- Sound classes survive script differences (Tamil has no voiced/unvoiced)
- Hindi "फ" = "ph" → "f", "tion" → "shan"
- Spelled-out acronyms segmented: "यूपीएस" → U-P-S → UPS
- Match skeleton against vocabulary of 29,875 standard titles

### How the Competition Guard Works
- After generating a tender, count eligible manufacturers per clause
- If < 3 manufacturers: try relaxing "practice" defaults (never buyer choices)
- Shows the officer the tradeoff, never silently changes their choice
- Uses the same market funnel from `engine/market.py`

---

## 🖥️ Frontend Pages to Screenshot for PPT

| Page | Route | What to Show |
|---|---|---|
| Home / Dashboard | `/` | Role cards, lifecycle strip, stats |
| Standards Search | `/recommend` | Result card with "Why", scope highlight |
| Compliance Tree + Labs | `/recommend` (expand) | Tree view + lab list with charges |
| Tender Analysis | `/tenders/[id]` | Readiness gauge, findings, proofs |
| Formal Proofs | `/tenders/[id]` → Proofs tab | UNSAT core cards |
| Market Restriction | `/tenders/[id]` → Market tab | Funnel chart |
| Linter | `/tenders/[id]` → Findings tab | Rule cards with autofixes |
| Corrigenda | `/tenders/[id]` → History tab | Word diffs, regression banner |
| Tender Studio | `/studio` | NL input → questions → draft |
| Knowledge Graph | `/kg` | Interactive graph with date slider |
| Marketplace | `/market` | Published tenders for contractors |
| Bid Form | `/market/[id]` | Autofill readout, Match Index |
| Bid Mirror | `/bidder` | Compliance matrix |
| Passport | `/passport` | VC with QR, verify/tamper |
| Audit Ledger | `/ledger` | Hash chain verification |
| Officer Workspace | `/officer` | Pipeline, pending actions |
| Contractor Workspace | `/contractor` | Open tenders, sealed bids |
| Evidence | `/evidence` | Benchmark charts, ablation |
| Extension | `/extension` | Screenshots of GeM annotation |

---

## 🎬 Demo Flow for the PPT (Recommended Order)

1. **Open with the problem** (12 of 23 tenders cite no standard)
2. **Show standards search** — "PVC insulated copper wire" → IS 694 with full card
3. **Switch to Hindi** — "स्प्लिट एयर कंडीशनर" → word-by-word reading → IS 1391
4. **Show the compliance tree** — IS 694 → 15 standards → where to test
5. **Upload a real tender** — items extracted, standards per item
6. **Show the demo tender** — Readiness BLOCKED, 34 findings
7. **Show the formal proof** — Z3 UNSAT: clauses 4.2 ∧ 7.2
8. **Show market restriction** — Carbon ≤ 0.18% → 1 of 12 manufacturers
9. **Apply corrigendum** — Fix → break → **regression caught** (3-clause impossibility)
10. **Tender Studio** — "500 light bulbs and 100 meteres" → 4 questions → verified draft
11. **Contractor bid** — OCR autofill → Match Index → Compliance Passport
12. **Evaluation** — Sealed bids → L1 → Make in India → Award → PDF
13. **Audit ledger** — Verify hash chain
14. **Extension** — GeM bid listing annotated
15. **Close with benchmarks** — 29,875 standards, 80,834 links, GeM 80.4% top-1

---

## 📌 Key Talking Points for Judges

1. **"We treat a tender as source code"** — AST, static analysis, SMT, SARIF, git-style history, Dependabot
2. **"AI assists, the officer decides"** — LLM is optional, never decides; all findings deterministic
3. **"Proofs, not guesses"** — Z3 returns minimal unsat cores, not "this might conflict"
4. **"Measured on external labels"** — GeM category names (403, by GeM), BIS list (803, by BIS)
5. **"Shows its weak spots"** — Indian languages 39% top-1 displayed on the Evidence page
6. **"28 competitors surveyed"** — largest competitor has ~2,500 standards in one division
7. **"One graph, two sides"** — Same KG powers buyer (studio) and seller (bid form)
8. **"Works where officers already are"** — Extension on GeM pages, MCP for AI assistants
9. **"Every answer dated"** — BIS portal checked 27 Sep 2026; spec blocks carry the check date
10. **"Runs offline on a CPU"** — No GPU, no API key, no internet required for core features
