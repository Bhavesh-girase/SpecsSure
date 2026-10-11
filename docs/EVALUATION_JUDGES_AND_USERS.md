# SpecSure — evaluation from the judges' and the users' side (27 Sep 2026)

Problem statement SIH26108 (Ministry of Consumer Affairs / BIS): *an AI-powered recommendation engine that identifies the
applicable Indian Standards for a procurement specification, with related standards, versions, certification and
explanations, usable in natural language and Indian languages.*

## 1. What a judge will check — and what SpecSure answers

| PS expectation | Weak answer most teams give | SpecSure (verifiable in the app) |
|---|---|---|
| A knowledge base of Indian Standards | 50–900 hand-typed rows, demo data | **29,875 designations**: 19,704 with archived full text (19,492 parsed) + 10,171 published after the archive, taken from the **BIS e-Sale catalogue** (29,607 designations exported on 27 Sep 2026) |
| Relationships between standards | a few manual edges | **80,834 typed links read from the standards' own clauses** (normative references, 19,622 test-method links, terminology, sampling, dimensions, packing, safety…) each with clause + snippet; **compliance tree** = transitive closure to depth 1–4 (IS 1786 → 7 → 29 → 37 standards) |
| Latest version / amendments | "check BIS portal" | **Status and document type for 29,710 designations** from the BIS Know-Your-Standards catalogue (21,291 active, 6,072 withdrawn — withdrawn ones rank last and are never "Recommended"); edition in force from the BIS e-Sale portal; **amendment lists and replacements** for 1,138 procurement-critical standards (IS 8112 → IS 269:2015, IS 13849 → IS 15683, IS 13947 → IS/IEC 60947). 3,823 standards have a newer edition than the archived text — flagged in every answer |
| Testing (what the bidder must do next) | not addressed | **Where to test**: 482 BIS / BIS-recognised labs for 823 standards from BIS LIMS — 8,805 lab–standard entries with full-test charges, clauses tested and city filter (IS 694: 52 labs, from ₹6,750) |
| Certification (ISI / CRS / hallmarking) | a flag on a few products | **828 rows** parsed from BIS "Products under Compulsory Certification" (Scheme-I/II/X + hallmarking), shown with the QCO and written into the spec clause |
| Natural language + Indian languages | English only, or an LLM API call | Offline: procurement glossary (hi, mr, ta, te, bn, kn) + a **loanword transliteration matcher** ("स्प्लिट एयर कंडीशनर" → split air conditioner, "ಸೀಲಿಂಗ್ ಫ್ಯಾನ್" → ceiling fan, "यूपीएस" → UPS) + **bge-m3** multilingual embeddings. The reading is shown word by word |
| Explainability | "AI says so" | Scope clause highlighted, reason trace (keyword rank, meaning rank, coverage, alias), confidence Recommended / Possible / abstain, every spec-clause sentence with its source and the date the edition was checked |
| Works on real procurement | typed demo queries | Item-level analysis of real tender PDFs incl. **GeM bid documents**; **browser extension** that annotates live GeM bid listings; exportable spec blocks (copy / Word) |
| Evidence | none | Benchmarks with independent labels (BIS list, **GeM category names**), held-out Indian-language set, real-tender study, spot-check, ablation — all scripts in the repo |

## 2. Numbers (reproducible: `python scripts/corpus_benchmark.py`)

Clean = all product-name aliases switched off (the BIS list and GeM names are sources of the alias field).

| Test (labels written by) | cases | top-1 | top-3 | top-10 |
|---|---|---|---|---|
| **GeM category names** (GeM; IS stripped from the name) | 403 | 80.4 % | 86.1 % | 91.3 % |
| BIS compulsory-certification products (BIS) | 803 | 83.8 % | 90.7 % | 93.4 % |
| Procurement-language queries (team) | 40 | 70.0 % | 90.0 % | 97.5 % |
| Indian languages — development set (team) | 44 | 56.8 % | 75.0 % | — |
| **Indian languages — held-out set** (team, written before the multilingual work) | 28 | 39.3 % | 71.4 % | — |

**Knowing when not to answer:** on 35 vague or services/software requests, 91.4 % got no "Recommended" standard;
when SpecSure does say "Recommended" on GeM names it is right 89.6 % of the time (confident-but-wrong on 8.4 % of queries).

Product mode (aliases + GeM procurement prior on; GeM scored only on the half of category names it has never seen):
GeM unseen half 82.3 % / 88.7 %, procurement 82.5 % / 92.5 %, BIS list 93.5 % (leaky — the list is an alias source),
Indian-language held-out 50.0 % / 78.6 %.

What each layer added (`data/evaluation/retrieval_ablation.json`, shown on the Evidence page): the BIS-portal layer
raised procurement top-1 70 → 75 % (current titles) and made 82 more BIS-list and 8 more GeM cases answerable (standards
the archive lacks); bge-m3 lifted the Indian-language held-out set to 46 % / 71 % (e5: 43 % / 64 %); before the
multilingual work (small glossary, no transliteration) that set scored 7 % / 11 %. bge-m3 costs ≈ 270 ms per query on
2 CPU cores (e5: ≈ 115 ms) — SpecSure falls back to e5 automatically when bge-m3 is not available.

## 3. Real procurement documents

`scripts/real_tender_study.py` — 63 documents, 1,542 pages (per-document table with source links on the Evidence page):

| | Institutional tenders (PSUs, banks, universities, municipalities) | GeM bid documents (downloaded from GeM, 27 Sep 2026) |
|---|---|---|
| documents / pages | 23 / 1,011 | 40 / 531 |
| cite no Indian Standard at all | **12 of 23** | 13 of 40 |
| cite an older edition / a withdrawn standard | 3 / 3 | 0 / 0 |
| items found → named / recommended / possible / abstained | 400 → 5 / 33 / 129 / 228 | 89 → 31 / 12 / 11 / 34 |
| spot-check "Recommended" (AI-assisted, to be confirmed) | **17 / 21 correct** (19 incl. partial) | **10 / 12 correct** |
| spot-check "Possible" | 4 / 25 correct, 13 incl. partial | 0 / 11 correct, 4 partial |

Reading: when SpecSure says **Recommended** it is right ~85 % of the time on real documents; **Possible** is a lead that
needs a person (shown as "verify"); on most items (medical, IT, services, custom parts) it **abstains** instead of
guessing. GeM bids usually name their standard in the category — there the value is the edition check (e.g. road-lighting
luminaires: IS 10322 (Part 5/Sec 3) is now the 2026 edition) and the certification and test-method bundle.

## 4. The users

**Procurement officer (buyer).** Needs the right IS, the edition in force, the certification rule and a clause to paste —
in minutes, in their language, and defensible in audit.
→ Find Standards (text / voice / Hindi…), sector filter, spec block with sources → Word; tender upload with item table;
browser side panel on GeM/CPPP; every answer says what was checked on the BIS portal and when.

**Bidder / vendor.** Needs to know which standard, which licence (ISI / CRS), which tests — before bidding.
→ The same card lists the certification scheme and QCO, the test-method standards (compliance tree) and the amendments;
the extension shows it next to each live GeM bid.

**BIS / auditor.** Needs traceability and no hallucination.
→ Deterministic retrieval + rules; LLM optional and never decides; sources and dates on every line; abstention.

## 5. Honest gaps

- **Full text only up to the archive.** 10,171 newer standards are title-only (marked "BIS catalogue · title only" and
  capped at "Possible"); their references cannot be read without the documents.
- **Status/amendments verified for 1,138 standards**, not all 29,875 (the rest show the catalogue edition). The harvester
  (`bis_status.py` pattern) can run for all — ≈ 2 h from an Indian connection.
- **Indian languages remain the weakest area** (46 % top-1 held-out). Transliterated English works well; native words need
  the glossary. An LLM translator (optional, pluggable) or a fine-tuned model would close it.
- **Labels of the team-written sets are ours** (AI-assisted); GeM and BIS labels are external.
- GeM blocks some cloud IP ranges — harvesting ran from an Indian machine.
