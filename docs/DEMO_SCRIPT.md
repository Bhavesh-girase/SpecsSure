# Judge Demo Script

## Core demo — the Indian Standards engine (≈ 4 minutes) — lead with this

Backup: a 100-second recorded film of this flow is in `docs/media/specsure_demo.mp4` (also served at `/specsure_demo.mp4`).

| Time | Screen | Say | Show |
|---|---|---|---|
| 0:00 | Find Standards | "The knowledge base is the Indian Standards themselves: **29,875 standards** — 19,492 full texts parsed into **80,834 typed links**, current editions of **29,607** from the **BIS portal** (checked today), 828 compulsory-certification rows and **821 GeM categories** that name their standard." | stats strip |
| 0:20 | "PVC insulated copper wire for house wiring, 450/750 V, FR" | "IS 694 first, matched on its Scope clause — the *Why* line shows keyword rank, meaning rank and coverage. Edition in force and every amendment from the BIS portal. **Where to test**: 52 BIS-recognised labs from BIS LIMS, full test from ₹6,750 — filter by city. Then the **compliance tree**: depth 1 → its references; depth 2 → the test methods those call up." | result card, labs, compliance tree |
| 1:00 | Chip **स्प्लिट एयर कंडीशनर**, then **ಸೀಲಿಂಗ್ ಫ್ಯಾನ್** | "Procurement Hindi is mostly English written in Devanagari. We read it offline: स्प्लिट → *split* by sound skeleton SPLT, कंडीशनर → *conditioner*. → IS 1391 (Part 2). Kannada ceiling fan → IS 374. No LLM, every word's reading shown." | reading chips |
| 1:30 | "LED luminaire for road and street lights" → Spec block | "Archived text is the 2012 edition, but the BIS portal says **IS 10322 (Part 5/Sec 3):2026** is in force — we flag it and draft the clause for the 2026 edition, with CRS registration. Withdrawn standards are redrafted for their replacement: IS 13849 → IS 15683." | status notice, spec block, Word |
| 2:00 | **Browser extension** on a GeM bid listing (`/extension` screenshots or live bidplus page) | "Officers don't work in our app — they work on GeM. The extension annotates every live bid: named standard, edition in force, amendments, ISI/CRS — or our suggestion, or an honest *no confident match*. Open a bid PDF → items, cited standards, forgotten test methods, copy-ready clause." | badges, side panel |
| 2:40 | Upload a real tender (Union Bank fire-extinguisher RFP) | "Item by item: IS 15683 with the ISI-mark QCO; abstains where no standard fits." | item table |
| 3:10 | Evidence | "Measured, not claimed. **GeM's own category names: 80.4 % top-1, 91 % top-10** with every alias switched off; when we say *Recommended* we're right 90 % of the time, and 91 % of vague or service requests get no recommendation. Real documents: 63 tenders and GeM bids, 1,542 pages — 12 of 23 institutional tenders cite no standard at all; our *Recommended* items were right 17/21 and 10/12 on spot-check; *Possible* is labelled verify. Indian languages are our weakest area — 39 % top-1 / 71 % top-3 on a held-out set — and we show that too." | /evidence (layers, ablation, study) |
| 3:45 | Close | "Deterministic, offline, sourced and dated — AI assists, the officer decides." | — |

## Tender compiler demo (≈ 7 minutes)

**Setup:** `docker compose up --build` (or local mode). The demo tender, a clean LED tender and a demo bid are seeded automatically. Everything is fictional and labelled.

| Time | Screen | Say | Show |
|---|---|---|---|
| 0:00 | Home | "Most teams built a BIS search or a PDF chatbot. We built a **compiler** for tenders — it proves things." | pipeline strip, 12 capability tiles |
| 0:30 | Demo tender → Readiness | "One upload: 25 requirements, 34 findings, readiness 18, **BLOCKED** — the system refuses to let this be published." | gauge, checklist, blocking issues; click *Publish* → 409 message |
| 1:00 | Formal proofs | "This isn't an LLM opinion. Clause 4.2 says yield ≥ 500, Clause 7.2 says ≤ 480 — the Z3 solver returns the minimal unsatisfiable core. 7.2 even contradicts IS 1786 Fe 500D, which the tender itself cites." | UNSAT cards |
| 1:40 | Standards · QCO · time | "Clause 3.1 cites IS 8112:1989. As of the tender date it was withdrawn and merged into IS 269:2015 — and the Cement QCO applies. Change the date → the answer changes." | citation table, time machine |
| 2:15 | Market restriction | "Carbon ≤ 0.18 % looks harmless. Product-space counting shows it leaves **1 of 12** licensed manufacturers; relaxing to the IS limit restores 6. That's GFR Rule 144 evidence, not a feeling." | funnel + clause table |
| 2:50 | Linter | "38 rules with stable IDs, like ESLint. Tick autofixes → SpecSure writes the corrigendum in standard government phrasing." | preview draft corrigendum |
| 3:20 | Corrigenda | "Apply Corrigendum 1 — contradiction fixed. Now Corrigendum 2, which 'tightens' strength…" | Apply 1, Apply 2 |
| 3:45 | Readiness / Proofs | "**Regression caught**: 550 × 1.15 = 632.5 > 600 — three clauses plus an engineering axiom are jointly impossible. A human reviewer would miss this." | delta banner, 4-element UNSAT core |
| 4:15 | Pre-bid | "Before publishing, we predict what bidders will ask — backed by our institutional memory: last year the same carbon clause drew two queries and a corrigendum." | likelihood bars, precedents, approve → propagate |
| 4:45 | Radar | "Standards change. Inject an amendment to IS 1786 → every dependent tender is re-validated and its owner notified. A change to the *test method* IS 1608 reaches IS 1786 tenders through the dependency graph." | simulate, notifications, what-if |
| 5:20 | Bidder → demo bid | "Now the contractor's side. Bid Mirror shows the bid as the evaluator will see it: carbon 0.21 % from the NABL report violates 0.18 %; the **BIS licence expires before the bid due date**; Agt is only claimed in the datasheet." | matrix with page-level evidence, action items |
| 6:00 | Passport | "We issue a Product Compliance Passport as a W3C Verifiable Credential signed with Ed25519. Anyone can verify it offline. Change one value — the signature fails." | verify → tamper → fail |
| 6:30 | Audit | "Every compile, decision and passport is in a hash-chained ledger with the knowledge-base snapshot hash — reproducible and tamper-evident." | verify chain |
| 6:50 | Close | "Deterministic where it matters, AI only to explain, humans decide. It even runs as an MCP server so any AI assistant uses our proofs instead of guessing." | — |

### Extended demo — Tender Studio → Marketplace → Comparative (≈ 4 minutes)

| Time | Screen | Say | Show |
|---|---|---|---|
| 0:00 | Studio | "An officer types — or speaks — one line, even with a typo: *need a tender of 500 light bulbs and 100 meteres*." | Understand request |
| 0:20 | Questions | "It asks only four things. '100 meteres of what?' is ranked from the knowledge graph: lamps are usually bought with wiring cable." | pick answers |
| 0:45 | Draft | "Generate. It cites IS 16102 (Part 1):**2026** — the 2012 edition was withdrawn on 2 August 2026 — plus the CRS order, BEE label and the 2003 Electrical Wires & Cables QCO. Then our own compiler audits the draft: READY." | basis legend, gauge, compiler passes |
| 1:15 | Why panel | "Click any sentence: why it exists, which edition, which order, with the graph path and its verification state." | clause 3.8 |
| 1:35 | Time machine | "Set the date to 1 June 2026: the watchlist warns that the 2012 edition only runs until 2 August." | date field |
| 1:50 | Competition | "Ask for 5-star fans in 1200 mm: only 2 makers qualify — we never silently change the officer's choice, we show it and suggest 1-star alternatives." | competition meter |
| 2:15 | Market | "Contractor side: the bid form is generated from the tender. Drop a licence, a datasheet and a phone-scan of a NABL report — PP-OCRv6 reads it at 97 % and fills the form." | autofill readout |
| 2:50 | Match Index | "Live Tender Match Index: coverage, evidence strength, knock-outs, and exactly what to fix — change the product vs attach a document." | right panel |
| 3:20 | Buyer → Bids | "The committee gets a comparative statement: Chandni's registration expires before the bid due date and was issued against the withdrawn 2012 edition." | comparative table |
| 3:45 | Graph | "All of this is one temporal knowledge graph — exportable to Neo4j." | /kg |

### Full lifecycle — officer ↔ contractor ↔ committee (≈ 4 minutes)

Seeded tender: *6000 LED bulbs 9 W B22 and 2000 m 1.5 sq mm FR wire* (est. ₹5.73 lakh → Make in India applies). Three sealed bids: Gyan Jyoti (Class-II, ₹72), Harit Lighting (MSE + Class-I, ₹79), Chandni (non-local, ₹58 but non-responsive).

| Time | Screen | Say | Show |
|---|---|---|---|
| 0:00 | Home → role switch | "A government portal both sides actually use: officer, contractor, citizen/auditor — English or Hindi, accessible (text size, high contrast, skip link)." | toggle हिन्दी, A+ |
| 0:20 | Officer Workspace | "Every tender in one pipeline, with the next action computed: fix blockers, reply to queries, evaluate, award." | KPIs, pending actions, stage trackers |
| 0:45 | Contractor Workspace (Harit) | "Days left, item lists, my sealed bids with their commitment hash." | open tenders, my bids |
| 1:05 | Bid form → advisor + query | "Before spending money: Bid / No-Bid advice, back-scheduled from the due date — licence renewal must start by 15 Sep, so it's RISKY. Ask a question: it's auto-linked to Clause 3.7, a duplicate is detected." | advisor card, raise query |
| 1:40 | Bid form → price bid | "The price is sealed: only SHA-256(prices + bid id + salt) enters the public ledger. MSE and Make-in-India class are declared here." | section 6 |
| 2:00 | Cockpit → Bidder queries | "The officer sees the query with a draft reply generated from the compiler's evidence; publishing hides the bidder's identity." | publish reply |
| 2:20 | Cockpit → Evaluation & award | "Open financial bids: every price re-hashed and matched against the ledger. Chandni's ₹58 is never considered — technically non-responsive. L1 is Gyan Jyoti at ₹72, Class-II; Harit is Class-I within 20 % → matches L1 for 50 % of a divisible item; the MSE 25 % is already satisfied. Cable: no bid → re-tender flag." | integrity table, steps, allocation bars |
| 3:15 | Record award → PDF | "Committee records the award; contract ₹4,32,000; evaluation report PDF; the award notice appears on the public tender page and in Harit's workspace." | report.pdf, /market/{id}, /contractor |
| 3:45 | Audit ledger | "Every step — query, bid, opening, award — is in the hash chain." | verify |

**Likely questions**
* *Is the data real?* Standards/QCO coverage is curated from public sources with a per-record verification state; market, labs and history are synthetic and labelled. Production plugs in GeM, BIS licence and NABL data.
* *Why an SMT solver?* Contradictions across clauses (including derived quantities) are a satisfiability problem; a solver gives a proof and a minimal explanation, an LLM gives a guess.
* *What if the parser misses a clause?* Every requirement shows its source span; unmatched numbers are flagged (`weak_value_parse`, `no_unit`), and the planted-issue benchmark tracks regressions.
* *Is the knowledge graph a real graph DB?* An in-process typed property graph (NetworkX) rebuilt deterministically from the curated registry and cached by the snapshot hash; one click exports Cypher for Neo4j. For a demo it removes an operational dependency; at scale the same schema runs in Neo4j.
* *Why not let an LLM write the tender?* The LLM has no notion of "edition in force on 25-09-2026" or of which QCO applies; the graph does. We generate deterministically, then verify with the same compiler that audits human tenders. An LLM may only propose item matches, which are validated against the catalogue.
* *Which OCR and why not Tesseract?* PaddleOCR PP-OCRv6 via RapidOCR (ONNX, CPU) — better on low-resolution scans and tables; a Devanagari model covers Hindi; domain repair fixes compliance-critical confusions.
* *Is the Make in India / MSE logic official?* It implements the published orders (PPP-MII 2017 rev. 2020: 20 % margin, 50 % for divisible items, exempt < ₹5 lakh; MSE 2012: L1 + 15 %, 25 % share) as a transparent proposal with every step cited; the committee decides and the note says to confirm against current DoE/DPIIT/MSME instructions.
* *Why commitments instead of encryption?* A commitment proves the price was fixed at submission without revealing it; production would add encryption at rest and key release at the opening ceremony.
* *Accuracy?* Planted-issue recall 29/29 and zero critical false alarms on the clean tender (small self-authored set); retrieval top-3 100 % on 8 queries offline. We state the limits openly.
