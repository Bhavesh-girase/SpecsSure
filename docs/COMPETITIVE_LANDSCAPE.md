# Competitive landscape — public projects on PS SIH26108 (surveyed 27 Sep 2026)

28 public GitHub repositories on the same problem statement were cloned and scanned (data files, code, READMEs).
Counts below are distinct IS numbers found in each project's data files; they are an upper bound on the size of its
knowledge base.

| Project | Knowledge base | What stands out | Gaps vs SpecSure |
|---|---|---|---|
| **RAGbait / ManakSetu** (Gmax-13) | ETD + LITD (electrical & electronics) subset; ~2.5k standards in the graph; 87k passages; BIS "Know Your Standards" catalogue | strongest competitor: full-text dependency edges with verbatim sentences, currency check against the BIS catalogue, abstention "critic" with hard gates, evaluation of *confident-but-wrong* and *confident-on-vague*, 63-second promo film | one division family only; no certification data beyond a curated table; no GeM/real-tender study; no multilingual; no browser integration; needs a Groq API key |
| **IS Copilot** (a1creator284 / rajaryan1111) | 741 demo standards, 25 certification rows | polished React app, **live Vercel demo**, Hinglish lexicon, 6-component confidence breakdown, 10 gap types, spec generator, evidence Q&A | demo dataset; edges curated; no real editions/amendments |
| **ManakMitra** (Vatsal057) | ~306 standards (clean CSV) | assembly workflow, Bhashini/IndicTrans mention, docx, WhatsApp idea, "where to test" idea | small data; testing idea without lab data |
| vishusharma sih26108 | 846 standards JSON | simple chatbot | no graph, no certification |
| rishiiicreates SIH-2026 | 625 QCO Scheme-I rows | QCO list, Neo4j mention | no full text |
| NormAI, NORMVAULT, StandardsIQ, BIS-Assistant, Standard-Setu, SURE, Bis-system, others | 3–260 standards | LLM RAG chat, dossiers, GeM clause generators, dashboards | curated tens of standards; LLM-dependent |
| kishorkumar939 BIS_AI | 84 rules | a **Chrome extension** widget on gem.gov.in | rule table only; no bid annotation |

## Where SpecSure is ahead (and can prove it)

- **Coverage:** 29,875 standards (all divisions) — 19,492 full texts parsed into 80,834 typed links; the next-largest public
  graph covers one division family.
- **Authority of status:** status and document type (Product Specification / Method of test / Code of practice …) for
  **29,710 designations** from the BIS Know-Your-Standards catalogue, current editions for 29,607 from the BIS e-Sale
  portal, amendment lists and replacements for 1,138 procurement-critical standards.
- **Procurement reality:** 821 GeM categories linked to their standard; a benchmark written by GeM (403 category names);
  63 real tender / GeM bid documents analysed; browser extension that annotates live GeM listings.
- **Testing route (unique):** labs from BIS LIMS for 823 standards — 482 BIS / BIS-recognised labs, 8,805 lab–standard
  entries with full-test charges and clauses tested.
- **Multilingual without an LLM:** glossary + loanword transliteration + bge-m3, measured on a held-out set.
- **Evaluation discipline:** independent labels (GeM, BIS), held-out multilingual set, abstention set, precision of
  "Recommended", ablation, spot-checks — all reproducible scripts.

## Ideas adopted from the field (27 Sep)

- From RAGbait: whole-catalogue status via BIS Know-Your-Standards (done, all divisions), abstention metrics
  (*confident-but-wrong*, vague/out-of-scope set — done), a short demo film (done).
- From IS Copilot / ManakMitra: read-aloud & voice loop (done), testing-lab route (done with real LIMS data).
- Not adopted: LLM-generated answers as the primary output (hallucination risk; SpecSure stays deterministic, LLM optional).

## Remaining things competitors have that we do not

- A public **live URL** (IS Copilot on Vercel). SpecSure's bge-m3 index needs ~3 GB RAM; a small public demo would need
  the e5 fallback on a free tier or a paid VM.
- Passage-level retrieval over every clause (RAGbait: 87k passages). SpecSure retrieves on title + scope and cites
  clauses for relationships; clause-level retrieval would sharpen "why" for long standards.
