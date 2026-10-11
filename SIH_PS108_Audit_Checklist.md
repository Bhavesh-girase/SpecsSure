# SIH PS-108 — Master Feature & Gap Audit Checklist (v2.1 — Tender Compiler + Tender Studio / Knowledge Graph / Smart Bid Form)

> **Legend:** ✅ implemented & evidenced · 🟡 partial · ❌ missing · ⏸ deferred by decision (authentication / authorisation is out of scope for this iteration)
>
> **Re-audited:** 2026-09-25 after the v2 upgrade. Evidence paths are relative to the repo root. Every ✅ below is exercised by the automated test-suite (`backend/tests`, 50 tests) and/or the benchmark (`python -m scripts.evaluate_compiler`).
>
> **v1 → v2:** v1 audit was 80 ✅ / 34 🟡 / 132 ❌ (39 %). In v2 every in-scope item is ✅ except three partials (5.8 live licence lookup, 16 source monitoring = hash-watch + human triage, 18.5 inspection records); all authentication/authorisation items are ⏸ deferred.

---

## What changed architecturally

The v1 code was a *standards recommender* (text → retrieve → graph expand). v2 adds a **Tender Compiler** (`backend/app/engine/`) that treats a tender like source code:

```
documents → Tender IR (clause AST, pages, spans) → typed requirements (units normalised)
          → temporal resolution (edition / amendments / QCO as-of date) → Z3 formal verification (UNSAT cores)
          → market-feasibility model counting → 38-rule linter with autofix + SARIF → Digital Twin graph
          → readiness gate → (corrigendum merge ↺ | pre-bid prediction | radar re-validation | Bid Mirror | VC passport)
```

All decisions are deterministic and reproducible (knowledge-base snapshot hash + engine version are written to a hash-chained ledger). The LLM is optional and only rephrases findings behind injection screening.

Also fixed from v1: `frontend/src/lib` was git-ignored (frontend could not build from the repo) · provenance scores were hard-coded constants (now computed) · `GET /analyze/{id}` ignored the id · LangGraph state dropped `recommended_standards` (the pipeline returned an empty list) · Python `hash()` made stored embeddings irreproducible across restarts · a real API key was committed in `.env.example` (removed — **rotate it**).

---

## 0. Repository / Architecture

| # | Check | Status | Evidence |
|---|---|---|---|
| 0.1 | Frontend application | ✅ | `frontend/` Next.js 14; now builds (restored `src/lib/api.ts`, `utils.ts`; `.gitignore` fixed) |
| 0.2 | Backend/API | ✅ | `backend/app/main.py` — 10 routers, OpenAPI at `/docs` |
| 0.3 | Database | ✅ | PostgreSQL+pgvector (docker) **or zero-config SQLite**; forward auto-migration in `app/db/init_db.py` |
| 0.4 | Authentication / authorisation | ⏸ | Deferred per instruction |
| 0.5 | Document upload pipeline | ✅ | `POST /tenders` (multi-file, typed), `POST /tenders/{id}/documents`, `POST /bids` |
| 0.6 | PDF/document parsing | ✅ | `app/engine/docparse.py` — PyMuPDF text + table finder, python-docx in body order, optional Docling |
| 0.7 | OCR | ✅ | `docparse.py` — scanned-page detection → PyMuPDF/Tesseract → pytesseract → RapidOCR; images accepted |
| 0.8 | AI/LLM integration | ✅ | `llm_service.py` (optional); `POST /tenders/{id}/findings/{fp}/explain` (Hindi / plain English, evidence-fenced) |
| 0.9 | RAG pipeline | ✅ | LangGraph pipeline (`app/orchestrator`) — now with metadata filtering & real provenance |
| 0.10 | Vector database | ✅ | pgvector column + in-memory cosine fallback |
| 0.11 | Metadata storage | ✅ | 12 new tables in `app/models/tender.py` |
| 0.12 | Logging / error handling | ✅ | structured logging + hash-chained audit ledger (`app/engine/ledger.py`) |
| 0.13 | Test suite | ✅ | `backend/tests/` — 50 tests: engine units, API end-to-end, and `test_studio.py` (intent parsing, KG temporal queries, generated tenders pass their own compiler, bid-form scoring, OCR) |
| 0.14 | Docker / deployment | ✅ | `docker-compose.yml` (pgvector, backend, standalone Next.js), backend Dockerfile with tesseract |

## 1. Tender Document Ingestion

| # | Check | Status | Evidence |
|---|---|---|---|
| 1.1 | Upload tender PDF | ✅ | `docparse._parse_pdf` |
| 1.2 | Upload DOC/DOCX | ✅ | `docparse._parse_docx` (paragraphs + tables in document order, heading styles) |
| 1.3 | Multiple documents per tender | ✅ | `TenderDocument` table; volumes/annexures combined with key-collision prefixing (`tender_service._combine`) |
| 1.4 | OCR for scanned tender / bidder scans | ✅ | `app/engine/ocr.py` — RapidOCR 3 running PaddleOCR **PP-OCRv6** (ONNX, CPU) + PP-OCRv5 Devanagari ensemble, row re-assembly for tables, domain-aware repair (`Im/W→lm/W`, `IS l786→IS 1786`, `5OO→500`), per-page confidence + warnings; Tesseract only as last resort. `POST /ocr` |
| 1.5 | Preserve page numbers | ✅ | `PageText.page_no` → `Clause.page_start/page_end` → every requirement & finding |
| 1.6 | Section/heading structure | ✅ | `tender_ir.build_ir` — clause numbering, headings, section typing (technical/testing/delivery/…) |
| 1.7 | Extract tables | ✅ | PyMuPDF `find_tables`, DOCX tables, pipe tables → clause `tables` + row-level requirements |
| 1.8 | Extract annexures | ✅ | `ANNEX` detector → `Annexure-II/3.1` clause keys |
| 1.9 | Extract corrigenda | ✅ | `app/engine/corrigendum.py` — modify / delete / add parsing, number & issue date |
| 1.10 | Pre-bid clarification documents | ✅ | `prebid.parse_prebid_document` → `PrebidItem(source=received)` linked to clauses |
| 1.11 | Document version tracking | ✅ | per-clause versions + blame (`twin.corrigenda.history/blame`), SHA-256 per document |
| 1.12 | Source-document provenance | ✅ | document → page → clause → character span on every requirement/finding/evidence |

## 2. Requirement Extraction Engine

| # | Check | Status | Evidence |
|---|---|---|---|
| 2.1 | Detect technical clauses | ✅ | section typing + modality detection (`extractor.py`) |
| 2.2 | Identify product/category | ✅ | `ontology.detect_domains` (clause-local and tender-level) + grade detection (Fe 500D, 43 grade) |
| 2.3 | Technical parameters | ✅ | 40-parameter ontology `data/engine/parameters.json` with synonyms |
| 2.4 | Numerical values | ✅ | min / max / range / eq / enum / tolerance parser (`parse_constraint`), number words ("fifteen days") |
| 2.5 | Units | ✅ | `app/engine/units.py` — explicit conversion table (N/mm² ↔ MPa ↔ kgf/cm², cm²/g → m²/kg …) |
| 2.6 | Tolerances | ✅ | "± t", "± t %", "(+a/−b)", "with a tolerance of ± 5 %" |
| 2.7 | Performance requirements | ✅ | performance-category parameters (efficacy, oxygen index, smoke density …) |
| 2.8 | Testing requirements | ✅ | `kind=testing` + parameter → test-method mapping |
| 2.9 | Certification requirements | ✅ | `kind=certification` (ISI, CM/L, CRS, R-number, licence) |
| 2.10 | Delivery requirements | ✅ | `delivery_period` with anchor detection |
| 2.11 | Inspection requirements | ✅ | `kind=inspection` |
| 2.12 | Acceptance criteria | ✅ | `kind=acceptance` + `SS-ACC-001` when absent |
| 2.13 | Structured requirement schema | ✅ | `extractor.Requirement` (id, clause, page, span, op, normalised bounds, flags, citations, grade, modality) |

## 3. BIS / Indian Standards Intelligence

| # | Check | Status | Evidence |
|---|---|---|---|
| 3.1–3.7, 3.9–3.15 | Retrieval, semantic, BM25, vector, hybrid RRF, reranking, product mapping, scope, explanation, confidence, citations, allied, normative refs, graph | ✅ | unchanged strengths from v1, plus metadata filtering (see 19.3) |
| 3.8 | Clause-to-standard mapping | ✅ | each requirement gets `links.governing_standard` / `test_method` / `certification` (`compiler._link_requirement`) |
| 3.11 | Standard confidence | ✅ | **now computed** (dense cosine, BM25, domain match, graph evidence) — v1 used constants 0.88/0.85/0.90/0.80 |

## 4. Standard Lifecycle / Temporal Intelligence

| # | Check | Status | Evidence |
|---|---|---|---|
| 4.1–4.7 | Current / withdrawn / superseded / revision / amendment / history / effective date | ✅ | `app/engine/temporal.py` + historical editions in `data/seed/standards_extended.json` |
| 4.8 | As-of-date validation | ✅ | `resolve(kb, citation, as_of)`; tender `as_of_date`; UI "time machine" re-compiles the twin |
| 4.9 | Historical lookup | ✅ | `GET /temporal/resolve`, `GET /temporal/timeline` (e.g. IS 1786 in 2000 → IS 1786:1985) |
| 4.10 | Future regulatory change detection | ✅ | `amendments_pending`, `regulations_upcoming`; rules `SS-STD-007`, `SS-STD-008`, `SS-CERT-002` |
| 4.11 | Tender affected by standard update | ✅ | `radar.impact_set` (reverse dependency traversal) + `affected()` |
| 4.12 | Revalidation after change | ✅ | `radar_service.process_event` re-compiles affected twins, stores delta, notifies |

## 5. QCO / Certification Intelligence

| # | Check | Status | Evidence |
|---|---|---|---|
| 5.1–5.4, 5.6, 5.7 | QCO retrieval, product/standard mapping, dates, mandatory flag, scheme | ✅ | `data/seed/regulations.json` (with `verification_state`), `KnowledgeBase.regulations_for_family` |
| 5.5 | Upcoming QCO detection | ✅ | temporal horizon; `SS-CERT-002` |
| 5.8 | Licence verification | 🟡 | Bid Mirror checks licence number, IS, grade, validity vs bid due date, status; live BIS CARE lookup not automated (no public API) |
| 5.9 | QCO conflict with tender | ✅ | `SS-CERT-001` (licence not required), `SS-CERT-003` (ISI vs CRS mismatch), `SS-CERT-004` (foreign standard for QCO product) |
| 5.10 | QCO impact on active tenders | ✅ | `GET /radar/qco-impact`, QCO simulation scenario |

## 6. Tender Linter (38 rules, `app/engine/linter.py`)

| # | Check | Status | Evidence |
|---|---|---|---|
| 6.1 | Vague language | ✅ | `SS-AMB-001`, `SS-AMB-002` |
| 6.2 | Non-measurable requirements | ✅ | `SS-AMB-001` (graded severity) |
| 6.3 | Missing units | ✅ | `SS-UNIT-001` (+ autofix inserting canonical unit) |
| 6.4 | Missing tolerances | ✅ | `SS-TOL-001` |
| 6.5 | Missing test methods | ✅ | `SS-TEST-001` (grouped by test, with NABL wording autofix), `SS-STD-006` |
| 6.6 | Missing acceptance criteria | ✅ | `SS-ACC-001` |
| 6.7 | Duplicate clauses | ✅ | `SS-DUP-001` (fuzzy, number-word normalised) |
| 6.8 | Conflicting clauses | ✅ | `SS-CON-001` — **Z3 SMT proof with minimal unsat core** |
| 6.9 | Impossible combinations | ✅ | multi-clause UNSAT via engineering axioms (e.g. UTS ≥ TS/YS × YS); `SS-UNIT-004` physically impossible values |
| 6.10 | Missing normative references | ✅ | `SS-STD-006` |
| 6.11 | Missing certification requirements | ✅ | `SS-CERT-001` |
| 6.12 | Suggested clarification | ✅ | `suggestion` + machine-applicable `fix` → draft corrigendum (`POST /tenders/{id}/autofix`) |
| 6.13 | Exact source clause | ✅ | clause key, page, quote, span; in-document highlighting in the UI |

## 7. Tender Contradiction Engine

| # | Check | Status | Evidence |
|---|---|---|---|
| 7.1 | Numeric contradictions | ✅ | `constraints.verify` (Z3) |
| 7.2 | Unit contradictions | ✅ | units normalised before solving; `SS-UNIT-003` inconsistent units |
| 7.3 | Standard contradictions | ✅ | `SS-CON-002` (clause vs cited standard, solver), `SS-CON-003` (weaker than standard) |
| 7.4 | Certification contradiction | ✅ | `SS-CERT-003`, `SS-CERT-004` |
| 7.5 | Date contradiction | ✅ | `SS-CON-004` (pre-bid after due date, short bid window) |
| 7.6 | Delivery vs compliance conflict | ✅ | `SS-CON-005` — delivery period shorter than mandatory test duration |
| 7.7 | Cross-section contradiction | ✅ | solver works over all clauses (e.g. Clause 4.2 technical vs Clause 7.2 testing) |
| 7.8 | Contradiction explanation | ✅ | MUS atoms + numeric witness ("550 × 1.15 = 632.5 > 600") |

## 8. Tender Digital Twin

| # | Check | Status | Evidence |
|---|---|---|---|
| 8.1 | Digital representation | ✅ | `compiler.compile_ir` → twin JSON (tender, clauses, requirements, citations, domain standards, verification, market, tests, findings, readiness, graph, provenance) |
| 8.2 | Map every requirement | ✅ | requirement ↔ clause ↔ page ↔ span |
| 8.3 | Standards → requirements | ✅ | `links.governing_standard` |
| 8.4 | Tests → requirements | ✅ | `links.test_method`, test plan |
| 8.5 | Certifications | ✅ | `links.certification` |
| 8.6 | Regulatory dependencies | ✅ | twin graph `standard → regulation → certification` |
| 8.7 | Unresolved requirements | ✅ | `requirement.unresolved`, `readiness.unresolved` |
| 8.8 | Readiness report | ✅ | score, gate, 6 sub-scores, coverage; PDF export |
| 8.9 | Pre-publication validation | ✅ | 11-point checklist; `PATCH /tenders/{id} status=published` returns **409** while critical findings are open |

## 9. Market Feasibility / Restriction Detector (`app/engine/market.py`)

| # | Check | Status | Evidence |
|---|---|---|---|
| 9.1 | Brand-specific requirements | ✅ | `SS-RES-001` brand lexicon + "or equivalent" / "only" logic (GFR 144(i)(b)) |
| 9.2 | Manufacturer-specific requirements | ✅ | `SS-RES-002` (model nos., approved makes, ®/™, OEM-only), `SS-RES-005` (restrictive eligibility) |
| 9.3 | Unnecessarily narrow parameters | ✅ | `SS-RES-003` — clause stricter than the standard *and* excluding most manufacturers |
| 9.4 | Restrictive combinations | ✅ | sequential funnel + `SS-RES-004` (< 3 manufacturers) |
| 9.5 | Product-space estimation | ✅ | model counting over catalogue (synthetic demo catalogue; pluggable for GeM/BIS data) |
| 9.6 | Market coverage | ✅ | restriction index, eligible manufacturers per domain |
| 9.7 | Clause causing restriction | ✅ | leave-one-out & relax-to-standard analysis per clause |
| 9.8 | Evidence for flag | ✅ | excluded manufacturers, funnel, standard bounds |
| 9.9 | Human review workflow | ✅ | finding review (accept/dismiss-with-justification/fixed) persisted by fingerprint + ledger |

## 10. Pre-Bid Clarification Intelligence (`app/engine/prebid.py`)

| # | Check | Status | Evidence |
|---|---|---|---|
| 10.1 | Predict bidder questions | ✅ | per-finding question templates |
| 10.2 | Question likelihood | ✅ | base rate ⊕ severity ⊕ historical question rate of similar clauses |
| 10.3 | Draft response | ✅ | evidence-linked draft, marked DRAFT |
| 10.4 | Link response to evidence | ✅ | finding evidence + precedents |
| 10.5 | Track approved clarification | ✅ | `PrebidItem.status`, `POST /tenders/{id}/prebid/{qid}` + ledger |
| 10.6 | Propagate to tender | ✅ | `POST /tenders/{id}/prebid-propagate` → draft corrigendum → merge → re-compile |

## 11. Corrigendum Intelligence

| # | Check | Status | Evidence |
|---|---|---|---|
| 11.1–11.8 | Multiple corrigenda, modified / deleted / added clauses, chronological merge, canonical tender, version history, latest effective requirement | ✅ | `corrigendum.merge`, `GET /tenders/{id}/canonical`, `GET /tenders/{id}/clauses/{key}/history`; **regression detection** (twin delta flags new contradictions introduced by a corrigendum) |

## 12. Contractor / Bidder — Bid Mirror (`app/engine/bidmirror.py`, `evidence.py`)

| # | Check | Status | Evidence |
|---|---|---|---|
| 12.1 | Contractor uploads tender | ✅ | `POST /bids` with `tender_file` (bidder copy is compiled) |
| 12.2–12.4 | Datasheets / certificates / test reports | ✅ | typed evidence extraction (table rows, key-values, licence no., validity, NABL cert, report date, "not tested") |
| 12.5 | Match product to requirements | ✅ | deterministic evaluation on normalised values |
| 12.6 | Clause-by-clause compliance | ✅ | 7 statuses incl. CLAIMED_ONLY and CONFLICTING_EVIDENCE |
| 12.7 | Missing evidence | ✅ | MISSING_EVIDENCE (+ "lab report explicitly says not tested") |
| 12.8 | Technical mismatch | ✅ | NON_COMPLIANT with the numbers |
| 12.9 | Certificate mismatch | ✅ | licence expiry vs bid due date, IS mismatch, grade mismatch, status |
| 12.10 | Evidence page mapping | ✅ | document, page, snippet per row |
| 12.11 | Compliance matrix | ✅ | `result.rows`, UI matrix |
| 12.12 | Export | ✅ | `matrix.xlsx`, tamper-evident `evidence-package.zip` (SHA-256 manifest) |

## 13. Requirement × Evidence Mapping

| # | Check | Status | Evidence |
|---|---|---|---|
| 13.1–13.6 | Source page, sources, compliance claims, evidence doc/page/snippet | ✅ | see §12 |
| 13.7 | Unsupported claim prevented | ✅ | evidence strength grading (lab 3 / licence 2 / claim 1); datasheet-only = CLAIMED_ONLY, never COMPLIANT; grounded-quote verification for any LLM text (`guardrails.verify_quote`) |
| 13.8 | Human verification status | ✅ | finding reviews, pre-bid approvals, equivalence decisions (`/reviews`) |

## 14. Standards Equivalence Engine (`app/engine/equivalence.py`)

| # | Check | Status | Evidence |
|---|---|---|---|
| 14.1–14.5 | Compare standards, scope, parameters, test methods, safety | ✅ | parameter-by-parameter strictness (IS 1786 vs BS 4449 / ASTM A615, IS 269 vs EN 197-1 / ASTM C150) |
| 14.6 | Certification implications | ✅ | "technical comparability ≠ legal substitutability under QCO" |
| 14.7 | Partial equivalence | ✅ | coverage profile + NOT_EQUIVALENT / PARTIALLY_COMPARABLE / TECHNICALLY_COMPARABLE |
| 14.8 | Avoid automatic conclusion | ✅ | `decision_status = AI_ANALYSIS_PENDING_HUMAN_APPROVAL` always |
| 14.9 | Human approval | ✅ | committee decision → `/reviews` + ledger |

## 15. Testing & Laboratory Intelligence (`app/engine/testplan.py`)

| # | Check | Status | Evidence |
|---|---|---|---|
| 15.1–15.2 | Required tests, test → standard | ✅ | parameter ontology test mapping |
| 15.3 | Required laboratory | ✅ | lab routing by scope (synthetic NABL-style directory) |
| 15.4 | Certification dependency | ✅ | twin graph test ↔ standard ↔ regulation |
| 15.5 | Duplicate tests | ✅ | consolidation ("one tensile test covers YS, UTS, elongation") + conflicting method detection |
| 15.6 | Testing plan | ✅ | parallel lab tracks, critical path, Gantt |
| 15.7 | Track test evidence | ✅ | Bid Mirror test-report evidence + passport test results |

## 16. Regulatory Change Radar (`app/engine/radar.py`, `services/radar_service.py`)

| # | Check | Status | Evidence |
|---|---|---|---|
| 16.1–16.4 | New standard / revision / amendment / QCO update | ✅ | event types + registry mutation; human-confirmed `POST /radar/events`; simulation scenarios |
| 16.5 | Upcoming enforcement date | ✅ | effective dates → `SS-STD-007/008`, `SS-CERT-002` |
| 16.6 | Affected tenders | ✅ | direct + reverse-graph dependents |
| 16.7 | Affected templates | ✅ | tenders with `status=template` are included in the scan |
| 16.8 | Trigger revalidation | ✅ | automatic re-compile with delta |
| 16.9 | Notify user | ✅ | `Notification` feed + navbar bell (per-user routing needs auth — ⏸) |
| — | Source monitoring | 🟡 | `POST /radar/watch` hashes official pages and raises *pending-triage* events; no automated gazette parsing (deliberately human-in-the-loop) |

## 17. Procurement Memory (`app/engine/memory.py`)

| # | Check | Status | Evidence |
|---|---|---|---|
| 17.1 | Historical tenders | ✅ | seed history + every published/closed twin becomes memory |
| 17.2 | Clarifications | ✅ | received / approved pre-bid items |
| 17.3 | Corrigenda | ✅ | stored as tender documents with history |
| 17.4 | Recurring ambiguity patterns | ✅ | `recurring_patterns()` |
| 17.5 | Similar tender retrieval | ✅ | TF-IDF similarity |
| 17.6 | Historical issue detection | ✅ | clause precedents with past questions & resolutions |
| 17.7 | Knowledge retrieval | ✅ | `GET /memory/search` |

## 18. Product Compliance Passport (`app/engine/passport.py`)

| # | Check | Status | Evidence |
|---|---|---|---|
| 18.1–18.8 | Identity, standards, certification, test results, inspection, tender linkage, deviation history, evidence bundle | ✅ (18.5 🟡) | **W3C Verifiable Credential 2.0**, Ed25519 `eddsa-jcs-2022` proof, `did:key` issuer, QR, offline verification, tamper detection; inspection records field present but no inspection-module source yet |

## 19. AI / RAG Reliability

| # | Check | Status | Evidence |
|---|---|---|---|
| 19.1, 19.2, 19.4, 19.8 | Hybrid retrieval, reranker, citations, retrieval evaluation | ✅ | v1 + honest offline benchmark (8 queries: top-1 87.5 %, top-3 100 %) |
| 19.3 | Metadata filtering | ✅ | status/provenance-aware demotion of superseded/withdrawn/foreign standards + best-edition-per-family (`orchestrator/nodes/retriever.py`) |
| 19.5 | Hallucination prevention | ✅ | decisions are deterministic; LLM only rephrases fenced evidence |
| 19.6 | Confidence | ✅ | computed provenance components |
| 19.7 | Unsupported-answer rejection | ✅ | abstention flag (`abstained`) below threshold |
| 19.9 | RAG / system evaluation | ✅ | `scripts/evaluate_compiler.py` — planted-issue recall 29/29, 0 critical false alarms on the clean tender (self-authored gold set; see README caveat) |
| 19.10 | Citation verification | ✅ | `guardrails.verify_quote` (exact / fuzzy alignment) |
| 19.11 | Prompt-injection protection | ✅ | `guardrails.scan_injection`, `sanitize_for_llm`, `SS-SEC-001`, bid security flags |
| 19.12 | Document-level access control | ⏸ | deferred (auth) |

## 20. Knowledge Graph

| # | Check | Status | Evidence |
|---|---|---|---|
| 20.1–20.13 | Standard, product, tender, requirement, QCO, certification, test nodes; amendment, supersedes, normative, standard→QCO, tender→requirement, requirement→standard edges | ✅ | twin graph (`compiler.build_graph`) + standards KG; typed edges `contains/states/governed_by/verified_by/amended_by/mandated_by/requires/superseded_by/flags` |
| 20.14 | **Procurement Knowledge Graph** (item layer) | ✅ | `app/engine/kg.py` + `data/engine/items.json`, `policies.json`: Item → Standard family → Edition (valid-time) → Amendment / Normative ref → Regulation (QCO, CRS, BEE label, ALMM) → Parameter → Test → Lab → Manufacturer → Product, + GFR / Make-in-India / MSE policy layer. ~500 nodes / ~1000 typed edges, cached by KB snapshot hash |
| 20.15 | Temporal graph queries | ✅ | `bundle(item, date)`, `resolve_designation(des, date)` (edition in force + concurrent editions, e.g. IS 16102 (Part 1):2012 → 2026 with concurrent running to 02-08-2026; IS/IEC 61730-1:2016 until 15-02-2027) |
| 20.16 | Impact & explanation queries | ✅ | `impacted_items(node)` (reverse traversal over governance/normative edges), `explain_path(a, b)`; `/kg/*` API; `/kg` explorer UI with time machine |
| 20.17 | Graph export | ✅ | `/kg/export.cypher` (Neo4j), `/kg/export.jsonld` |

## 20A. Tender Studio — intent → verified tender (buyer)

| # | Check | Status | Evidence |
|---|---|---|---|
| 20A.1 | Natural-language request → line items | ✅ | `app/engine/intent.py` — English / Hindi / Hinglish, number words (पाँच सौ, 2 lakh), typo-tolerant units ("meteres"), coils/bags → metres/MT |
| 20A.2 | Ask only the questions that matter | ✅ | mandatory buyer slots from the KG; "100 metres of what?" ranked by CO_PROCURED_WITH edges |
| 20A.3 | Voice input | ✅ | Web Speech API (en-IN / hi-IN) in `/studio` |
| 20A.4 | Tender generated from the KG as of the publication date | ✅ | `app/engine/synthesizer.py` — standards (edition in force), QCO/CRS/BEE/ALMM clauses, tests + labs, dependency closure (normative refs), GFR 161/170/171, MII, MSE |
| 20A.5 | Clause-level provenance ("why is this here?") | ✅ | every clause: basis (standard / regulation / buyer / default / practice / policy / repair) + KG path + verification state |
| 20A.6 | Self-verification loop | ✅ | generated text is compiled by the Tender Compiler; safe autofixes applied until no fixable critical/major remains; passes shown |
| 20A.7 | Competition guard | ✅ | relaxes *practice* defaults (never buyer choices) until ≥ 3 manufacturers qualify; warns and offers alternatives when a buyer choice is binding |
| 20A.8 | Regulatory watchlist | ✅ | concurrent-edition end dates, pending amendments, orders coming into force within the contract horizon |
| 20A.9 | Procurement route advice | ✅ | GFR 149 (GeM) / 161 thresholds by estimated value |
| 20A.10 | Export & publish | ✅ | Word (.docx) with clause-traceability annex; save as draft / publish (publish refused while BLOCKED) |

## 20B. Smart Bid Form + Tender Match Index (contractor)

| # | Check | Status | Evidence |
|---|---|---|---|
| 20B.1 | Contractor sees published tenders | ✅ | `/market`, `GET /market/tenders` |
| 20B.2 | Bid form generated from the canonical tender | ✅ | `app/engine/bidform.derive_form` — typed fields per requirement (numbers with units/bounds, sizes, certificate + validity, conformity, NABL report, undertakings) |
| 20B.3 | Autofill from documents incl. scans | ✅ | `bidform.autofill` + OCR; each value keeps document → page → snippet → evidence strength |
| 20B.4 | Match level to the actual tender | ✅ | `bidform.score` — Tender Match Index = 100 × (0.75 weighted coverage + 0.25 evidence confidence), knock-outs cap at 49; tiers; informational headroom; per-item sub-scores; live in UI |
| 20B.5 | Item-wise bidding | ✅ | scope per product group; other items not held against the bidder |
| 20B.6 | Integrity checks | ✅ | declared value vs document value → CONFLICT; licence expiring before bid due; licence against a superseded edition |
| 20B.7 | Path to compliance | ✅ | substantive (change the product) vs documentary (attach / fill) actions |
| 20B.8 | Buyer comparative statement | ✅ | `GET /tenders/{id}/comparative`, cockpit "Bids received" tab; single-responsive-bid warning |

## 21. Explainability

| # | Check | Status | Evidence |
|---|---|---|---|
| 21.1–21.4, 21.6 | Why standard / why flag / why non-compliant / evidence beside conclusion / AI vs authority | ✅ | every finding: message, quote, basis (GFR rule), evidence; solver witness; Bid Mirror explanations |
| 21.5 | Source page navigation | ✅ | clause-anchored document view with highlighted spans, page numbers, clause history |
| 21.7 | Human review mechanism | ✅ | reviews persist across re-compiles (fingerprints), dismissals need justification |

## 22. Security / Governance

| # | Check | Status | Evidence |
|---|---|---|---|
| 22.1–22.4 | RBAC, buyer / contractor / admin roles | ⏸ | deferred (UI already separates buyer and bidder workspaces) |
| 22.5 | Audit logs | ✅ | SHA-256 hash-chained ledger + `/ledger/verify` |
| 22.6 | Document access controls | ⏸ | deferred |
| 22.7 | Encryption | ⏸ | deferred (TLS at deployment proxy) |
| 22.8 | AI content marked | ✅ | "AI-generated" labels, deterministic by default |
| 22.9 | Human approval for high-risk decisions | ✅ | publish gate, dismissal justification, committee decisions for equivalence, approval before corrigendum issue |

## 23. Dashboard / UX

| # | Check | Status | Evidence |
|---|---|---|---|
| 23.1–23.6, 23.8, 23.9 | Upload, progress, requirements, recommendations, risk, evidence, timeline, graph | ✅ | v1 + tender cockpit (12 tabs) |
| 23.7 | Clause highlighting | ✅ | `components/tender/document.tsx` |
| 23.10 | Contractor dashboard | ✅ | `/bidder`, `/bids/[id]`, `/market`, `/market/[id]` (smart bid form) |
| 23.13 | Buyer authoring UI | ✅ | `/studio` (Tender Studio) |
| 23.14 | Knowledge-graph explorer | ✅ | `/kg` |
| 23.11 | Export PDF | ✅ | readiness report PDF |
| 23.12 | Export Excel | ✅ | findings register, compliance matrix |

---

## Remaining gaps (honest list)

1. **Authentication / RBAC / ACL / encryption** — deferred by instruction.
2. **Live data sources** — market catalogue, lab directory and history are *synthetic, labelled demo data*; QCO dates are marked `curated_unverified` where not checked. Production needs GeM catalogue, BIS licence (BIS CARE) and NABL scope feeds.
3. **Licence verification** is document-based; no public BIS CARE API was available for automation.
4. **Inspection-record module** for the passport (field exists, no source workflow).
6. **Item catalogue coverage** — the Tender Studio knows 8 item classes (LED lamp, LED street light, PVC wiring cable, ceiling fan, MCB, OPC cement, TMT steel, solar PV module); other items fall back to a clarifying question. Adding an item = one JSON entry. Numeric defaults marked *practice* are recommendations, not statutory limits.
7. **Hindi OCR** — the mobile Devanagari recogniser reads clean words but misses some conjuncts; PaddleOCR-VL (0.9B) is the drop-in for Hindi-heavy scans on a GPU box.
5. The benchmark gold set is small and self-authored; an independent labelled corpus of real tenders is the next step.
