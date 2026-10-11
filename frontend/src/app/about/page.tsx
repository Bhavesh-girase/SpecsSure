"use client";

import Link from "next/link";
import { Accessibility, BookOpenCheck, Cpu, Info, Lock, Scale, ShieldAlert, Users } from "lucide-react";
import { PageHead, SectionHead } from "@/components/gov-ui";
import { T } from "@/lib/prefs";

const ARCH = [
  ["Indian Standards corpus", "19,704 designations from 22,024 archived standards (Public.Resource.Org, CC0 / RTI Act); scope, references, terminology and test clauses parsed into a typed dependency graph; BIS compulsory-certification lists linked by IS number."],
  ["Document parsing & OCR", "PDF / DOCX / scans → clause tree with pages. RapidOCR (PaddleOCR PP-OCRv6 + PP-OCRv5 Devanagari) with domain-aware repair."],
  ["Requirement extraction", "Typed requirements with units normalised (N/mm² ↔ MPa, lm/W, sq mm …) and source spans."],
  ["Hybrid retrieval", "Dense + BM25 with reciprocal-rank fusion, cross-encoder reranking and metadata filters over the standards corpus."],
  ["Temporal knowledge graph", "Item → parameter → standard → amendment → QCO / CRS / BEE → test → lab → policy, each edge with validity dates and a source."],
  ["Formal verification", "Clauses compiled to SMT constraints (Z3) — contradictions reported with a minimal unsatisfiable core."],
  ["Rule engine & linter", "38 deterministic rules with stable IDs, fingerprinted findings, autofix to draft corrigendum, SARIF export."],
  ["Bid evaluation", "Match Index per clause, sealed-bid commitments, L1 → Make in India → MSE preference steps, award record."],
  ["Audit ledger", "Every compile, query, bid, opening and award is hash-chained with the knowledge-base snapshot hash."],
];

export default function AboutPage() {
  return (
    <div className="max-w-[1100px] mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-8">
      <PageHead icon={Info} kicker="About the portal" title={<T en="About SpecSure" hi="स्पेकश्योर के बारे में" />}
        sub="AI Recommendation Engine for Indian Standards in Procurement — Smart India Hackathon 2026, problem statement SIH26108 (theme: Smart Automation, category: Software)." />

      <section className="space-y-3">
        <SectionHead title="The problem we solve" />
        <div className="bg-white border border-[#d5deea] rounded-lg p-5 text-[1rem] leading-relaxed text-[#334155] space-y-3 shadow-card">
          <p>Public procurement specifications must cite the right Indian Standard, the edition and amendments in force, the applicable Quality Control Order, certification scheme and
            acceptance tests. In practice tenders cite withdrawn editions, contradict themselves, omit tests, or restrict competition without anyone noticing until bids arrive — and
            bidders cannot tell early whether their product and paperwork will pass.</p>
          <p>The recommender is built from the standards themselves: the scope clause of every archived Indian Standard is searchable in any Indian language,
            and each standard’s own References, Terminology and test clauses give its allied standards — with the clause that links them.</p>
          <p>SpecSure connects the whole chain — <b>Tender → Requirement → Standard → Amendment → Normative reference → QCO → Certification → Test → Evidence → Supplier / Product → Compliance → Award</b> —
            and serves both sides: the procurement officer who drafts and evaluates, and the contractor who bids.</p>
        </div>
      </section>

      <section className="space-y-3">
        <SectionHead title="How it works" sub="Evidence-first: deterministic engines decide, the optional language model only rephrases evidence and is always labelled." />
        <div className="grid sm:grid-cols-2 gap-3">
          {ARCH.map(([t, d]) => (
            <div key={t} className="bg-white border border-[#d5deea] rounded-lg p-4 flex gap-3 shadow-card">
              <Cpu className="w-5 h-5 text-[#1d4f93] shrink-0 mt-0.5" />
              <div><div className="font-bold text-[1rem] text-[#0f2748]">{t}</div><p className="text-[0.875rem] text-slate-400">{d}</p></div>
            </div>
          ))}
        </div>
      </section>

      <section id="disclaimer" className="space-y-3 scroll-mt-24">
        <SectionHead title="Disclaimer & data sources" />
        <div className="bg-[#fff8ec] border border-[#f2d8a7] rounded-lg p-5 text-[0.9375rem] leading-relaxed text-[#4a3200] space-y-2">
          <p className="flex gap-2"><ShieldAlert className="w-4 h-4 shrink-0 mt-0.5" /><b>This is a hackathon prototype, not an official website of the Government of India or of any ministry, department or the Bureau of Indian Standards.</b></p>
          <p>Every standard, amendment and order carries a verification state: <i>source_checked</i> (compared with an official source), <i>curated_unverified</i> (entered from secondary material)
            or <i>simulated</i> (created for demonstration). Always confirm on the official BIS, DPIIT, MSME and GeM portals.</p>
          <p>All organisations, bidders, licences, registration numbers and test reports in the demo are fictional. Procurement-policy logic (Make in India, MSE preference, GFR references) is
            implemented from published orders as decision support; the competent authority decides.</p>
        </div>
      </section>

      <section id="accessibility" className="space-y-3 scroll-mt-24">
        <SectionHead title="Accessibility statement" />
        <div className="bg-white border border-[#d5deea] rounded-lg p-5 text-[0.9375rem] text-[#334155] shadow-card">
          <p className="flex gap-2 mb-2"><Accessibility className="w-4 h-4 text-[#1d4f93] shrink-0 mt-0.5" />Designed towards WCAG 2.1 AA and the Guidelines for Indian Government Websites (GIGW 3.0):</p>
          <ul className="list-disc ml-6 space-y-1">
            <li>“Skip to main content” link, landmark regions and breadcrumbs on every page</li>
            <li>Text resize (A- / A / A+ / A++) and a high-contrast mode in the top bar, remembered per browser</li>
            <li>Bilingual interface (English / हिन्दी) for navigation, home and workspaces; Hindi / Hinglish accepted as input</li>
            <li>Visible keyboard focus, labelled form controls, ARIA state on toggles and the stage tracker</li>
            <li>Colour is never the only signal — every status also has text</li>
            <li>Reduced-motion preference respected</li>
          </ul>
        </div>
      </section>

      <section id="privacy" className="space-y-3 scroll-mt-24">
        <SectionHead title="Privacy & security" />
        <div className="bg-white border border-[#d5deea] rounded-lg p-5 text-[0.9375rem] text-[#334155] space-y-2 shadow-card">
          <p className="flex gap-2"><Lock className="w-4 h-4 text-[#1d4f93] shrink-0 mt-0.5" />Financial bids are sealed with a salted SHA-256 commitment; only the commitment is written to the audit ledger until opening.</p>
          <p className="flex gap-2"><Scale className="w-4 h-4 text-[#1d4f93] shrink-0 mt-0.5" />Uploaded documents are screened for prompt-injection text before any language model sees them; published clarifications hide the bidder’s identity.</p>
          <p className="flex gap-2"><BookOpenCheck className="w-4 h-4 text-[#1d4f93] shrink-0 mt-0.5" />Login and role-based access control are intentionally out of scope for this prototype; the role selector only switches the workspace view.</p>
        </div>
      </section>

      <section className="space-y-3">
        <SectionHead title="Team" />
        <div className="bg-white border border-[#d5deea] rounded-lg p-5 text-[0.9375rem] text-[#334155] flex items-center gap-3 shadow-card">
          <Users className="w-5 h-5 text-[#1d4f93]" /> Team <b className="text-[#0f2748]">CodeNova</b> · Smart India Hackathon 2026 · PS SIH26108.
          <span className="flex-1" />
          <Link href="/ledger" className="text-[#1d4f93] font-semibold hover:underline">Verify the audit ledger</Link>
        </div>
      </section>
    </div>
  );
}
