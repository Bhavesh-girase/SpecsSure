# SpecSure API Reference (v2)

Base URL: `/api/v1` (interactive OpenAPI docs at `/docs`). The frontend reaches the API through a Next.js rewrite, so browsers never need CORS.

## Buyer — Tender Digital Twin
| Method | Path | Purpose |
|---|---|---|
| GET | `/tenders` | list tenders with readiness, gate, finding counts |
| POST | `/tenders` | multipart: `title`, `reference_no?`, `organisation?`, `status?`, `as_of_date?`, `text?`, `files[]`, `doc_types?` (csv: tender/annexure/corrigendum/prebid/auto) → compile |
| GET | `/tenders/{id}` | `{summary, twin}` — full Digital Twin |
| POST | `/tenders/{id}/documents` | add corrigendum / annexure / pre-bid doc → re-compile (returns delta) |
| POST | `/tenders/{id}/compile` | re-validate |
| PATCH | `/tenders/{id}` | `{status?, as_of_date?}` — publishing returns **409** while critical findings are open |
| PATCH | `/tenders/{id}/findings/{fingerprint}` | `{review_status: open|accepted|dismissed|fixed, reviewer, comment}` (dismiss needs comment) |
| POST | `/tenders/{id}/findings/{fingerprint}/explain` | `{lang: hi|en|…}` LLM explanation (labelled AI; template fallback) |
| POST | `/tenders/{id}/autofix` | `{fingerprints[], apply?}` → draft corrigendum (and issue it if `apply`) |
| POST | `/tenders/{id}/prebid/{qid}` | `{status: approved|rejected|published, final_response?}` |
| POST | `/tenders/{id}/prebid-propagate` | approved clarifications → draft corrigendum |
| GET | `/tenders/{id}/canonical?format=json|text` | merged tender + blame + changelog |
| GET | `/tenders/{id}/clauses/{key}/history` | versions with word diffs |
| GET | `/tenders/{id}/sarif` | SARIF 2.1.0 |
| GET | `/tenders/{id}/export/findings.xlsx` · `/export/report.pdf` · `/twin.json` | exports |

## Bidder — Bid Mirror & Passport
| Method | Path | Purpose |
|---|---|---|
| GET | `/bids?tender_id=` | list |
| POST | `/bids` | multipart: `bidder`, `product_name?`, `tender_id` **or** `tender_file`, `files[]` |
| GET | `/bids/{id}` | compliance matrix, evidence, passports |
| POST | `/bids/{id}/rerun` | re-mirror stored evidence against the latest tender version |
| GET | `/bids/{id}/export/matrix.xlsx` · `/export/evidence-package.zip` | exports (ZIP has SHA-256 manifest) |
| POST | `/bids/{id}/passport` | issue W3C VC passport |
| GET | `/passports` · `/passports/{id}` | list / get with verification + QR |
| POST | `/passports/verify` | verify any credential JSON |

## Tender Studio (v2.1)
| Method | Path | Purpose |
|---|---|---|
| GET | `/studio/catalogue` | item classes (KG item layer) + example requests |
| POST | `/studio/parse` | `{text}` → line items, globals (budget, delivery), minimal questions |
| POST | `/studio/generate` | `{intent, answers?, as_of?, meta?, overrides?}` → verified draft with sections, per-clause provenance, verification passes, competition, watchlist, registers, route advice |
| POST | `/studio/save` | same body + `publish?` → creates tender (draft/published) and compiles it |
| POST | `/studio/docx` | `{generation}` → Word file with traceability annex |
| GET | `/tenders/{id}/generation` · `/tenders/{id}/generated.docx` | provenance / Word for a saved Studio tender |

## Procurement Knowledge Graph
| Method | Path | Purpose |
|---|---|---|
| GET | `/kg/stats` | node/edge counts, snapshot |
| GET | `/kg/search?q=` | find nodes |
| GET | `/kg/node?id=&depth=&as_of=` | node + neighbourhood (validity on the date), impacted items |
| GET | `/kg/items/{item_id}?as_of=` | requirements bundle with KG paths |
| GET | `/kg/path?a=&b=` · `/kg/impact?node=` | explanation path · reverse impact |
| GET | `/kg/export.cypher` · `/kg/export.jsonld` | exports |

## Contractor marketplace & smart bid form
| Method | Path | Purpose |
|---|---|---|
| GET | `/market/tenders` | published tenders with items, due date, bid count |
| GET | `/tenders/{id}/bid-form` | derived form |
| POST | `/tenders/{id}/bid-form/score` | `{answers, scope?}` → Match Index |
| POST | `/tenders/{id}/bid-form/autofill` | multipart `files[]` → answers with sources, OCR readout, inferred scope |
| POST | `/tenders/{id}/bid-form/submit` | multipart `bidder, product_name?, answers (JSON), scope?, files[]` → bid |
| GET | `/tenders/{id}/comparative` | comparative statement of technical bids |
| GET | `/ocr/engines` · POST `/ocr` | OCR engines · OCR a file (lines, confidence, boxes, repairs) |

## Regulatory Radar
| Method | Path | Purpose |
|---|---|---|
| GET | `/radar/scenarios` | demo scenarios |
| POST | `/radar/simulate/{key}` | inject SIMULATED event → re-validate affected tenders |
| POST | `/radar/events` | record a human-confirmed event `{event_type, subject, title, summary?, effective_from?, source_url?, new_is_number?}` |
| GET | `/radar/events` | event log with impact |
| GET | `/radar/impact?standard=` | what-if impact set & affected tenders |
| GET | `/radar/qco-impact` | tenders under mandatory certification |
| POST | `/radar/watch` | hash official pages; raise pending-triage events |
| GET | `/notifications` · POST `/notifications/read` | notifications |

## Standards intelligence
| Method | Path | Purpose |
|---|---|---|
| GET | `/temporal/resolve?citation=&as_of=` | as-of resolution |
| GET | `/temporal/timeline?citation=` | editions, amendments, regulations |
| GET | `/equivalence/standards` · `/equivalence?a=&b=&grade_a=&grade_b=` | comparison (never auto-equivalent) |
| POST | `/reviews` · GET `/reviews` | human decisions (equivalence, justification …) |
| POST | `/lint` | `{text, as_of?, sarif?}` stateless lint |
| GET | `/rules` | rule catalogue |
| GET | `/memory/search?q=` | institutional memory |
| POST | `/analyze` · `/analyze/quick` · GET `/analyze/{id}` | standards recommendation pipeline (v1, now with computed provenance & abstention) |
| POST | `/search` · GET `/standards` · `/standards/{is}` · `/standards/{is}/graph` | registry & search |

## Governance
| Method | Path | Purpose |
|---|---|---|
| GET | `/ledger?subject_id=` | hash-chained audit entries |
| GET | `/ledger/verify` | recompute chain → `{valid, entries, head}` or `{valid:false, broken_at, reason}` |

## Demo
| Method | Path | Purpose |
|---|---|---|
| GET | `/demo` | demo ids + sample files |
| POST | `/demo/seed` | (re)seed demo tender, clean LED tender and demo bid |
| POST | `/demo/tenders/{id}/corrigendum/{1|2}` | apply demo corrigenda |
| GET | `/demo/files/{path}` | download sample documents |


## Lifecycle — queries, advice, evaluation, award, dashboards

| Method | Path | Purpose |
|---|---|---|
| POST | `/tenders/{id}/bid-form/submit` | now also accepts `financial` (JSON `{"lines":{"1":{"unit_price":72}}}`) and `declarations` (`{"mse":true,"mii_class":"I","local_content":64}`); returns the sealed `financial_commitment` |
| POST | `/tenders/{id}/queries` | contractor query `{bidder, question, clause_key?}` → located clause, duplicate check, draft reply |
| GET | `/tenders/{id}/queries?public=true` | queries (public → published replies only, bidder hidden) |
| POST | `/tenders/{id}/queries/{qid}/answer` | officer reply `{response, status: published|approved|rejected}` |
| POST | `/tenders/{id}/bid-form/advice` | Bid / No-Bid verdict + back-scheduled preparation plan |
| GET | `/tenders/{id}/evaluation` | technical → sealed financial → L1 → Make in India → MSE → allocation proposal |
| POST | `/tenders/{id}/close-bidding` | stop submissions |
| POST | `/tenders/{id}/open-financial` | verify every price against its ledgered commitment and reveal prices |
| POST | `/tenders/{id}/award` | record the committee decision (status → awarded) |
| GET | `/tenders/{id}/evaluation/report.pdf` | evaluation & award report |
| GET | `/dashboard/officer`, `/dashboard/contractor?bidder=` | role workspaces |
| GET | `/stats` | portal statistics |
