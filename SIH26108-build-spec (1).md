# SIH26108 — AI Recommendation Engine for Indian Standards in Procurement
## Full Analysis + Build Spec (agent-ready)

---

## 1. Problem Analysis — What's Actually Broken Today

| Current Practice | Failure Mode |
|---|---|
| Manual search of BIS catalog (keyword search on IS number/title) | Officer must already know roughly which standard applies — doesn't work for someone who only knows the *product*, not the *standard* |
| No relationship awareness | A primary standard (e.g. product spec) silently depends on test-method, terminology, and safety standards — these get missed, and the tender is later challenged/delayed |
| No version/amendment tracking | Officers cite withdrawn or superseded standards; amendments issued after the original IS are missed entirely |
| No certification linkage | BIS Product Certification / CRS / Hallmarking requirements aren't derived automatically — a separate manual check |
| English/keyword-only | Doesn't help officers who describe requirements in natural language or another Indian language |
| No explainability | Even when a match happens (BIS search or a naive keyword tool), there's no "why" — auditors can't trace the reasoning, which matters a lot in government procurement |

The real difficulty isn't retrieval — it's that **standards form a graph, not a list**, and no existing tool traverses that graph or explains its output in an auditable way.

---

## 2. Proposed Solution — Architecture

```
Tender/Product Spec (text, multilingual)
        │
        ▼
 [1] Query Understanding Layer  → normalize + extract entities (product type, attributes, use-case)
        │
        ▼
 [2] Hybrid Retrieval  → semantic search (embeddings) + keyword/BM25 fallback
        │
        ▼
 [2.5] Reranker  → cross-encoder rescoring of hybrid candidates before graph expansion
        │
        ▼
 [3] Standards Knowledge Graph  → traverse normative refs, test methods, terminology,
                                    safety, installation, related-product standards
        │
        ▼
 [4] Version/Amendment Resolver  → always resolve to latest live version + list amendments
        │
        ▼
 [5] Certification Mapper  → attach BIS Product Cert / CRS / Hallmarking flags
        │
        ▼
 [6] Explainability Layer  → deterministic reason-trace (which node, which edge, why)
        │                     optional LLM only rewrites the trace into readable prose
        ▼
 Recommended Standard Set + Relationship Map + Certification Requirements
```

This mirrors the pattern used successfully on your internship-recommendation platform: **retrieve → reason (structured, non-ML) → explain**, with an LLM used only at the very end for language polish — never for the actual decision. That's deliberate: a government-facing tool needs deterministic, auditable reasoning, not a black box.

### Why a graph, not just a vector database
Semantic search alone tells you "these standards are topically similar." It cannot tell you "IS 10322 (Part 5) is normatively referenced by IS 10322 (Part 1) as a mandatory test method." That relationship data has to be modeled explicitly — this is the actual differentiator the PS is asking for, and it's the piece most naive hackathon solutions (a chatbot over embeddings) will skip.

---

## 3. Where the Improvement Over a "Basic" Solution Comes From

A basic team will build: text box → embedding search → top-5 IS numbers → done. That's a weak entry. Your improvement should come from three things:

1. **The graph is the product.** Standards + their normative/test/safety/terminology relationships, modeled as a real graph (not just tags), with traversal depth control (e.g. "show me 1-hop mandatory refs" vs "show me the full dependency tree").
2. **Confidence + provenance on every recommendation.** Not just "IS 302" but "IS 302 (Part 1):2023, Amendment 2 (2024) — matched on semantic similarity 0.87 + keyword overlap on 'electrical safety', mandatory normative reference from IS 15885."
3. **A structured intake, not free text.** Let the officer either paste a tender paragraph OR fill a short structured form (product category, key specs) — structured input dramatically improves precision and is cheap to build. Free text should still work, but structured intake is your "harder to clone easily, easier to use well" lever (see §5).

---

## 4. Tech Stack (open-source, cost-optimized)

| Layer | Choice | Why |
|---|---|---|
| Embeddings | **`bge-m3`** or `intfloat/multilingual-e5-large` — **multilingual from day one, not English-only** | Open-weight, strong multilingual retrieval. Picking an English-only model (e.g. MiniLM) now and swapping later means re-indexing the entire corpus from scratch — since the PS requires multilingual input, the multilingual model has to be the starting choice, not a "v2 upgrade" |
| Vector store | **pgvector (inside PostgreSQL)** — or FAISS if you want a fully separate, swappable retrieval service | One database instead of two moving parts (Postgres + a standalone vector store) is less infra to run and demo, which directly serves the cost/effort-reduction requirement. FAISS remains a fine upgrade path if retrieval scale later outgrows pgvector |
| Knowledge graph | **NetworkX (in-process, Python)** for the build — Neo4j only if the timeline allows it later | Standards relationships are graph-shaped, but standing up and operating a Neo4j instance is infra overhead you don't need to prove the concept. NetworkX gives you the same traversal logic (normative refs, N-hop dependency trees) with zero extra service to install, configure, or keep alive during a demo. Migrate to Neo4j only once the relationship dataset is large enough that in-memory traversal genuinely struggles |
| Keyword fallback | **BM25 via `rank_bm25`** | Catches exact IS-number / exact-term queries embeddings sometimes miss |
| Reranker | **Open-weight cross-encoder, e.g. `bge-reranker-base` or `cross-encoder/ms-marco-MiniLM-L-6-v2`** | Rescoring the hybrid candidate pool before graph expansion means the graph gets built around a properly reranked set of standards, not just whatever raw retrieval happened to rank highest — cheap to run, meaningfully improves precision |
| Backend | **FastAPI** (Python) | Async-friendly, fast to scaffold, pairs naturally with the ML stack (vs Django which you used last time — FastAPI is lighter here since this is API-first with no heavy admin/CMS need) |
| Database | **PostgreSQL (+ pgvector)** | Standards metadata, version history, certification mappings, and now embeddings too — one store instead of a fragmented Postgres/FAISS split |
| Cache | **Redis** | Cache repeated queries and resolved standard trees (same fail-safe pattern as your internship platform) |
| LLM (explanation polish only — open-weight, self-hosted) | **`Llama-3.1-8B-Instruct` or `Mistral-7B-Instruct` via Ollama** | Self-hosted, zero per-call cost, no external API dependency at all — this is a hard requirement, not a preference, so no hosted API (OpenAI/Anthropic/etc.) belongs anywhere in this pipeline, including for extraction. It only rewrites a structured trace into prose — it never decides the recommendation |
| OCR (if parsing scanned tender PDFs) | **Tesseract** or **docTR** | Open source, handles scanned government PDFs |
| Frontend | **React** | Consistent with your prior stack; needed mainly for the structured-intake form + graph visualization (e.g. `react-flow` or `d3` for the relationship tree) |

**On the applicability-score formula:** if you publish a weighted formula (e.g. `0.45 × semantic + 0.20 × keyword + 0.20 × domain + 0.15 × graph`), say explicitly — in the UI and in any pitch — that these are your own engineering weights, not an official BIS methodology. It's fine to use, but stating it plainly up front heads off the obvious "where did these numbers come from?" question rather than looking evasive if asked later.

---

## 5. Cost/Effort Reduction + "Easy to use, hard to game"

**Cost/effort reduction (the actual ask, not just a feature):**
- Fully open-source stack → zero recurring inference cost, no API rate limits, runs offline/on-prem (important for a government system with data-sensitivity concerns).
- Cache resolved standard-trees (Redis) so repeated/similar tender queries don't re-run graph traversal + embedding search.
- Structured intake reduces re-queries — most of the officer's time cost today is trial-and-error keyword search; a form-driven flow with autocomplete on product category cuts that to one pass.
- Batch mode: allow uploading an entire tender document once and get every product line resolved together, instead of one search per line item (this is where most manual effort currently goes).

**Easy to use / hard to "crack":**
Read "harder to crack" as: hard for a rival team or a bad actor to trivially clone the value, and hard to get a wrong/manipulated recommendation past the system.
- The graph + provenance data is the moat — a UI can be copied in a day; a correctly modeled normative-reference graph across hundreds of standards cannot.
- Recommendations always carry a provenance trail (which node, which edge, which score) — this makes it hard to silently inject a wrong standard without the trace looking suspicious, and gives auditors something to check.
- Rate-limit + log all queries; version-pin every recommendation to a specific IS revision + amendment number so nothing "silently" goes stale.
- Confidence thresholds: below a cutoff, the system explicitly says "no confident match, needs manual review" instead of guessing — this is both a trust feature and a defense against garbage-in/garbage-out gaming.

---

## 6. Build Plan for an Agent (sequential + parallelizable)

**Sequential spine (each phase depends on the last):**
1. **Foundation** — FastAPI project scaffold, PostgreSQL schema (standards, versions, amendments, certifications, relationships), seed with a sample subset of real/mock IS data.
2. **Retrieval core** — multilingual embedding pipeline (bge-m3) + pgvector index + BM25 fallback over standard titles/scopes; verify with smoke queries in at least two languages.
3. **Graph layer** — NetworkX in-process schema for relationship types (normative, test-method, terminology, safety, installation, related-product); load relationships for the seed dataset; verify traversal queries (1-hop mandatory refs, full dependency tree).
4. **Reranking + Fusion** — run the cross-encoder reranker over the hybrid retrieval candidates, then combine the reranked results with graph traversal into a ranked, deduplicated recommendation set with confidence scores and provenance.
5. **Version/amendment resolver** — always resolve to the latest version, surface amendment list.
6. **Certification mapper** — rule-based mapping from standard/product category → BIS Product Cert / CRS / Hallmarking flags.
7. **Tender Gap Analyzer** — given a tender that already cites some standards, traverse the graph from those standards and flag normatively-related standards the tender does *not* cite (missing test-method, safety, or installation references); this reuses Phase 3's traversal logic on a different input (existing citations, not a fresh query), so it's a thin layer on top of the graph rather than new infrastructure.
8. **Explainability layer** — deterministic trace generator; optional Ollama-based prose polish (feature-flagged, falls back to template on failure — same pattern as your internship platform's LLM layers).
9. **Frontend** — structured intake form + free-text box + results view with relationship graph visualization + gap-analysis warnings.
10. **Integration + caching** — Redis caching, end-to-end pipeline test (single query, full chain — the internship-platform postmortem showed isolated phase tests miss integration bugs; do at least one true full-chain test here too).

**Can be built in parallel once Phase 1 (schema) is fixed:**
- Retrieval core (Phase 2) and Graph layer (Phase 3) are independent of each other — two agents/workstreams can build these simultaneously against the same schema.
- Frontend (Phase 9) can be scaffolded in parallel with Phases 2–7 against mocked API responses, then wired to the real backend once Phase 4 (fusion) is ready.
- Certification mapper (Phase 6) is independent of the graph/retrieval work and can be built anytime after Phase 1.
- Tender Gap Analyzer (Phase 7) can't start until Phase 3 (graph) is working, but doesn't depend on Phases 4–6, so it can run alongside them.

---

## 7. Open Questions Before an Agent Starts Building

1. **Data access**: Do you have (or can you scrape/mock) actual IS standard metadata — titles, scopes, normative references, amendment history? BIS doesn't have a public bulk API, so this likely needs to be a curated seed dataset for the demo (even 30–50 standards with real relationships would be a strong demo).
2. **Team size / timeline**: How many people, and is this a 36-hour hackathon build or a longer pre-build with a hackathon demo? This changes how many phases above are realistic.
3. **Hardware**: Will you have GPU access (even a laptop GPU) for embeddings/Ollama, or CPU-only? `bge-m3` + `Llama-3.1-8B` are both CPU-runnable but slower — worth knowing now so the multilingual model size can be picked correctly (e.g. a smaller multilingual model if CPU-only).
4. **Graph scale expectations**: The spec defaults to NetworkX (in-process, no extra service) for the build — this covers the seed dataset comfortably. Only worth revisiting toward Neo4j if you already know the demo needs to show hundreds of standards with dense cross-references, since that's the point where in-memory traversal starts to strain.
5. **Which languages, concretely**: The spec defaults to a multilingual embedding model so English isn't a special case that needs retrofitting later — but which specific languages should the demo actually exercise (Hindi only, or Hindi + Marathi + others)? That's a data-curation question (which standards/queries to prepare), not an architecture one.

Once you answer these, the spec above can be tightened into exact file-by-file instructions per phase.
