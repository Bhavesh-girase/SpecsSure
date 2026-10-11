"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, BarChart3, CheckCircle2, ExternalLink, FileSearch, Languages, Library, ShieldCheck, ShoppingCart, History, Network } from "lucide-react";
import { ErrorBox, Loading } from "@/components/ui";
import { Kpi, Notice, PageHead, SectionHead } from "@/components/gov-ui";
import { corpusEvidence } from "@/lib/api";

function Meter({ label, value, sub }: { label: string; value: number | undefined; sub?: string }) {
  const v = value ?? 0;
  return (
    <div>
      <div className="flex justify-between text-[0.875rem]"><span className="font-semibold text-[#0f2748]">{label}</span><span className="font-mono font-bold">{value === undefined ? "—" : `${v.toFixed(1)} %`}</span></div>
      <div className="h-2.5 bg-[#eef2f7] rounded-full overflow-hidden mt-1"><div className="h-full bg-[#1d4f93] rounded-full" style={{ width: `${Math.min(100, v)}%` }} /></div>
      {sub && <div className="text-[0.8125rem] text-slate-500 mt-0.5">{sub}</div>}
    </div>
  );
}

export default function EvidencePage() {
  const [d, setD] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { corpusEvidence().then(setD).catch((e) => setErr(e.message)); }, []);
  if (err) return <div className="max-w-4xl mx-auto p-8"><ErrorBox error={err} /></div>;
  if (!d) return <Loading label="Loading evaluation results…" />;
  const b = d.corpus_benchmark || {};
  const ba = d.corpus_benchmark_with_aliases || {};
  const st = d.real_tender_study || {};
  const s = st.summary || {};
  const c = d.corpus || {};
  const L = c.layers || {};
  const g = b.gem_categories;
  const ab = d.retrieval_ablation;
  const bs = s.by_source || {};
  return (
    <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-8">
      <PageHead icon={BarChart3} kicker="Evidence" title="How well does it work — measured, not claimed"
        sub="Every number on this page is produced by scripts in the repository (scripts/corpus_benchmark.py, scripts/real_tender_study.py) and can be re-run."
        right={<a href="/specsure_demo.mp4" target="_blank" rel="noreferrer" className="px-4 py-2 rounded-md bg-[#0f2748] text-white font-bold text-sm">▶ Watch the 100-second demo</a>} />

      <section className="space-y-3">
        <SectionHead title="Knowledge base — five layers, each with its source" sub="Full texts give the relationships; the BIS portal gives the edition in force; the certification list and GeM give the procurement reality." />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Kpi label="Indian Standards" value={c.designations?.toLocaleString("en-IN")} icon={Library} hint={L.archive_designations ? `${L.archive_designations.toLocaleString("en-IN")} with archived text + ${L.portal_only_designations?.toLocaleString("en-IN")} from the BIS catalogue` : "designations"} />
          <Kpi label="Full texts parsed" value={c.parsed_with_text?.toLocaleString("en-IN")} tone="blue" hint="scope, references, tests, terminology" />
          <Kpi label="Typed links" value={c.relations?.toLocaleString("en-IN")} tone="green" icon={Network} hint={L.relation_kinds ? `${(L.relation_kinds.test_method || 0).toLocaleString("en-IN")} test-method links · each with clause + snippet` : "each with its clause and snippet"} />
          <Kpi label="Editions checked on BIS portal" value={L.portal_designations?.toLocaleString("en-IN") || "—"} tone="saffron" icon={History} hint={L.portal_newer_edition_than_archive ? `${L.portal_newer_edition_than_archive.toLocaleString("en-IN")} have a newer edition than the archive · ${L.portal_fetched}` : "BIS e-Sale catalogue"} />
          <Kpi label="Status for every standard" value={L.catalogue_status?.toLocaleString("en-IN") || L.status_checked?.toLocaleString("en-IN") || "—"} tone="navy" hint={L.catalogue_status ? `BIS catalogue: ${L.catalogue_withdrawn?.toLocaleString("en-IN")} withdrawn · document type for ${L.catalogue_aspect?.toLocaleString("en-IN")} · amendment lists for ${L.status_checked}` : ""} />
          <Kpi label="Compulsory-certification rows" value={L.certification_rows?.toLocaleString("en-IN") || "828"} tone="green" icon={ShieldCheck} hint="BIS Scheme-I / II / X + hallmarking" />
          <Kpi label="GeM categories linked to an IS" value={L.gem_categories?.toLocaleString("en-IN") || "—"} tone="blue" icon={ShoppingCart} hint={L.gem_bids_harvested ? `from ${L.gem_bids_harvested.toLocaleString("en-IN")} live GeM bids` : ""} />
          <Kpi label="Testing labs linked" value={L.labs_distinct?.toLocaleString("en-IN") || "—"} tone="navy" hint={L.labs_standards ? `BIS LIMS: ${L.labs_entries?.toLocaleString("en-IN")} lab–standard entries with charges for ${L.labs_standards} standards` : ""} />
        </div>
      </section>

      <section className="space-y-3">
        <SectionHead title="Recommendation accuracy" sub="Benchmark numbers are computed with the product-name alias field switched off, because BIS’s product list is one of its sources." />
        <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-5">
          {g && <div className="bg-white border-2 border-[#1d4f93] rounded-lg p-4 shadow-card space-y-3">
            <div className="font-extrabold text-[#0f2748] flex items-center gap-2"><ShoppingCart className="w-4 h-4" />GeM category names <span className="text-[0.75rem] uppercase bg-[#1d4f93] text-white rounded px-1.5 py-0.5">independent</span></div>
            <p className="text-[0.875rem] text-slate-400">{g.cases} category names from live GeM bids; the IS that GeM names is the label, stripped from the query.</p>
            <Meter label="Top-1" value={g.top1} /><Meter label="Top-3" value={g.top3} /><Meter label="Top-10" value={g.top10} />
            {g.excluding_bis_list_names && <p className="text-[0.8125rem] text-slate-500">Names not in the BIS product list ({g.excluding_bis_list_names.cases}): top-1 {g.excluding_bis_list_names.top1} %, top-3 {g.excluding_bis_list_names.top3} %</p>}
          </div>}
          <div className="bg-white border border-[#d5deea] rounded-lg p-4 shadow-card space-y-3">
            <div className="font-extrabold text-[#0f2748] flex items-center gap-2"><ShieldCheck className="w-4 h-4" />BIS-authored labels</div>
            <p className="text-[0.875rem] text-slate-400">{b.cases} product → IS pairs from BIS’s compulsory-certification list. Product names resemble titles, so this is the easier test.</p>
            <Meter label="Top-1" value={b.top1} /><Meter label="Top-3" value={b.top3} /><Meter label="Top-10" value={b.top10} />
          </div>
          <div className="bg-white border border-[#d5deea] rounded-lg p-4 shadow-card space-y-3">
            <div className="font-extrabold text-[#0f2748] flex items-center gap-2"><FileSearch className="w-4 h-4" />Procurement language</div>
            <p className="text-[0.875rem] text-slate-400">{b.procurement_language?.cases} queries written the way buyers write (“GI pipes for water supply, medium class”).</p>
            <Meter label="Top-1" value={b.procurement_language?.top1} sub={ba.procurement_language ? `with trade-name aliases: ${ba.procurement_language.top1} %` : undefined} />
            <Meter label="Top-3" value={b.procurement_language?.top3} sub={ba.procurement_language ? `with trade-name aliases: ${ba.procurement_language.top3} %` : undefined} />
          </div>
          <div className="bg-white border border-[#d5deea] rounded-lg p-4 shadow-card space-y-3">
            <div className="font-extrabold text-[#0f2748] flex items-center gap-2"><Languages className="w-4 h-4" />Indian languages</div>
            <p className="text-[0.875rem] text-slate-400">{b.multilingual_heldout?.cases} held-out queries in Hindi, Marathi, Tamil, Telugu, Bengali and Kannada (written before the multilingual work), no LLM: glossary + loanword transliteration + bge-m3. Still our weakest area.</p>
            <Meter label="Held-out top-1" value={b.multilingual_heldout?.top1} sub={ba.multilingual_heldout ? `product mode: ${ba.multilingual_heldout.top1} %` : undefined} />
            <Meter label="Held-out top-3" value={b.multilingual_heldout?.top3} sub={ba.multilingual_heldout ? `product mode: ${ba.multilingual_heldout.top3} %` : undefined} />
            <p className="text-[0.8125rem] text-slate-500">Development set ({b.multilingual?.cases}): top-1 {b.multilingual?.top1} %, top-3 {b.multilingual?.top3} %</p>
          </div>
        </div>
      </section>

      {b.abstention && (
        <section className="space-y-3">
          <SectionHead title="Knowing when not to answer" sub="A recommendation engine for government procurement must not invent a standard. We measure both sides." />
          <div className="grid md:grid-cols-3 gap-4">
            <Kpi label="Vague / services queries without a “Recommended” answer" value={`${b.abstention.no_recommendation} %`} tone="green" hint={`${b.abstention.cases} queries (vague ${b.abstention.by_kind?.vague} %, services/software ${b.abstention.by_kind?.out_of_scope} %)`} />
            {g?.recommended_precision !== undefined && <Kpi label="Precision when SpecSure says “Recommended”" value={`${g.recommended_precision} %`} tone="blue" hint={`GeM category names; recommends on ${g.recommended_share} % of them`} />}
            {g?.confident_but_wrong !== undefined && <Kpi label="Confident but wrong" value={`${g.confident_but_wrong} %`} tone="red" hint="share of GeM queries answered “Recommended” with the wrong standard" />}
          </div>
        </section>
      )}

      {ab && (
        <section className="space-y-3">
          <SectionHead title="What each layer adds (ablation)" sub={ab.note} />
          <div className="bg-white border border-[#d5deea] rounded-lg overflow-x-auto shadow-card">
            <table className="gov-table">
              <thead><tr><th>Configuration</th>{ab.columns.map((col: string) => <th key={col} className="text-right">{col}</th>)}</tr></thead>
              <tbody>{ab.rows.map((r: any) => (
                <tr key={r.name} className={r.chosen ? "bg-[#f3fbf4]" : ""}><td className="font-semibold">{r.name}{r.chosen && <span className="ml-2 text-[0.75rem] uppercase bg-[#138808] text-white rounded px-1.5 py-0.5">default</span>}</td>
                  {r.values.map((v: any, i: number) => <td key={i} className="text-right font-mono">{v ?? "—"}</td>)}</tr>))}</tbody>
            </table>
          </div>
        </section>
      )}

      {st.summary && (
        <section className="space-y-3">
          <SectionHead title="Validation on real public tenders" sub={`${s.tenders_analysed} tender documents (${s.pages} pages) from government, PSU and public-sector-bank websites, run end-to-end. ${st.method}`} />
          {bs.gem && (
            <div className="grid md:grid-cols-2 gap-4">
              {[["Institutional tenders (PSUs, banks, universities, municipalities)", bs.institutional], ["GeM bid documents (downloaded from GeM, 27 Sep 2026)", bs.gem]].map(([label, x]: any) => x && (
                <div key={label} className="bg-white border border-[#d5deea] rounded-lg p-4 shadow-card">
                  <div className="text-[0.875rem] font-bold uppercase text-slate-500">{label}</div>
                  <div className="grid grid-cols-3 gap-2 mt-2 text-center">
                    <div><div className="text-[1.375rem] font-extrabold font-mono text-[#0f2748]">{x.tenders_analysed}</div><div className="text-[0.8125rem] text-slate-500">documents</div></div>
                    <div><div className="text-[1.375rem] font-extrabold font-mono text-[#c0262d]">{x.tenders_citing_no_IS}</div><div className="text-[0.8125rem] text-slate-500">cite no IS</div></div>
                    <div><div className="text-[1.375rem] font-extrabold font-mono text-[#c26a00]">{(x.tenders_citing_older_edition || 0)}</div><div className="text-[0.8125rem] text-slate-500">cite an older edition</div></div>
                  </div>
                  <div className="text-[0.8125rem] text-slate-400 mt-2">{x.items_found} items: {x.items_named || 0} name their IS, {x.items_recommended} recommended, {x.items_possible} possible, {x.items_abstained} abstained{x.tenders_citing_withdrawn ? ` · ${x.tenders_citing_withdrawn} cite a withdrawn standard` : ""}</div>
                </div>))}
            </div>
          )}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Kpi label="Tenders citing no Indian Standard" value={`${s.tenders_citing_no_IS} / ${s.tenders_analysed}`} tone="red" icon={AlertTriangle} />
            <Kpi label="Tenders citing an older edition" value={s.tenders_citing_older_edition} tone="saffron" />
            <Kpi label="Items found in the documents" value={s.items_found} tone="navy" />
            <Kpi label="Items with a confident IS" value={s.items_recommended} tone="green" icon={CheckCircle2} hint={`${s.items_possible} more ‘possible’; ${s.items_abstained} abstained`} />
          </div>
          {d.real_tender_spotcheck && (
            <div className="grid md:grid-cols-2 gap-4">
              <div className="bg-white border border-[#9bd3a3] rounded-lg p-4 shadow-card">
                <div className="text-[0.875rem] font-bold uppercase text-[#0d6b06]">Spot-check · “Recommended” items</div>
                <div className="text-[1.75rem] font-extrabold font-mono text-[#0d6b06]">{d.real_tender_spotcheck.recommended.correct} / {d.real_tender_spotcheck.recommended.n} correct</div>
                <p className="text-[0.875rem] text-slate-400">Trust these: the retrievers agree and the item’s words are covered by the standard.</p>
              </div>
              <div className="bg-white border border-[#f2cf8c] rounded-lg p-4 shadow-card">
                <div className="text-[0.875rem] font-bold uppercase text-[#8a5300]">Spot-check · “Possible” items (random 25)</div>
                <div className="text-[1.75rem] font-extrabold font-mono text-[#8a5300]">{d.real_tender_spotcheck.possible.correct} correct · {d.real_tender_spotcheck.possible.correct_or_partial} incl. partial</div>
                <p className="text-[0.875rem] text-slate-400">Treat as leads to verify — which is exactly how the UI labels them.</p>
              </div>
              {d.real_tender_spotcheck.gem && <>
                <div className="bg-white border border-[#9bd3a3] rounded-lg p-4 shadow-card">
                  <div className="text-[0.875rem] font-bold uppercase text-[#0d6b06]">GeM bids · “Recommended” items</div>
                  <div className="text-[1.75rem] font-extrabold font-mono text-[#0d6b06]">{d.real_tender_spotcheck.gem.recommended.correct} / {d.real_tender_spotcheck.gem.recommended.n} correct</div>
                  <p className="text-[0.875rem] text-slate-400">Items whose GeM bid names no standard; the misses were a wrong part (XLPE 3.3–33 kV → Part 2) and cable lugs.</p>
                </div>
                <div className="bg-white border border-[#f2cf8c] rounded-lg p-4 shadow-card">
                  <div className="text-[0.875rem] font-bold uppercase text-[#8a5300]">GeM bids · “Possible” items</div>
                  <div className="text-[1.75rem] font-extrabold font-mono text-[#8a5300]">{d.real_tender_spotcheck.gem.possible.correct} correct · {d.real_tender_spotcheck.gem.possible.correct_or_partial} partial / {d.real_tender_spotcheck.gem.possible.n}</div>
                  <p className="text-[0.875rem] text-slate-400">Weak — exactly why these are shown as “verify”, never as a recommendation.</p>
                </div>
              </>}
              <p className="md:col-span-2 text-[0.8125rem] text-slate-500">{d.real_tender_spotcheck.method} Reviewer: {d.real_tender_spotcheck.reviewer}.</p>
            </div>
          )}
          <Notice tone="info">SpecSure abstains on items with no confident match (medical devices, IT networking, stage equipment and similar) rather than guessing — {s.items_abstained} of {s.items_found} items. Compulsory-certification items without any ISI / BIS-licence / CRS clause in the tender: {s.tenders_with_compulsory_items_but_no_certification_clause} tender(s).</Notice>
          <div className="bg-white border border-[#d5deea] rounded-lg overflow-x-auto shadow-card">
            <table className="gov-table">
              <thead><tr><th>Buyer</th><th>Source</th><th className="text-right">Pages</th><th className="text-right">Items</th><th>Recommended / possible / abstained</th><th>IS cited in the tender</th><th>Flags</th></tr></thead>
              <tbody>
                {st.tenders.filter((t: any) => !t.error).map((t: any) => (
                  <tr key={t.url}>
                    <td><a href={t.url} target="_blank" rel="noreferrer" className="font-semibold text-[#1d4f93] hover:underline inline-flex items-center gap-1">{t.org}<ExternalLink className="w-3 h-3" /></a></td>
                    <td className="text-[0.8125rem]">{t.source === "gem" ? <span title={t.category}>GeM {t.bid}</span> : "institutional"}</td>
                    <td className="text-right font-mono">{t.pages}</td>
                    <td className="text-right font-mono">{t.items}</td>
                    <td className="font-mono">{t.counts.named ? `${t.counts.named} named · ` : ""}{t.counts.recommended} / {t.counts.possible} / {t.counts.none}</td>
                    <td className="text-[0.8125rem]">{t.is_cited.length ? t.is_cited.slice(0, 5).join(", ") + (t.is_cited.length > 5 ? ` +${t.is_cited.length - 5}` : "") : <span className="text-[#8a1414] font-semibold">none</span>}</td>
                    <td className="text-[0.8125rem]">
                      {(t.named_withdrawn?.length > 0 || t.cited_withdrawn?.length > 0) && <div className="text-[#8a1414] font-semibold">withdrawn: {[...(t.named_withdrawn || []), ...(t.cited_withdrawn || [])].join(", ")}</div>}
                      {t.named_newer_edition?.length > 0 && <div className="text-[#8a5300] font-semibold">newer edition in force: {t.named_newer_edition.join(", ")}</div>}
                      {t.cited_older_edition.length > 0 && <div className="text-[#8a5300] font-semibold">older edition: {t.cited_older_edition.join(", ")}</div>}
                      {t.cited_unknown.length > 0 && <div className="text-[#8a1414]">unknown: {t.cited_unknown.join(", ")}</div>}
                      {t.items_needing_compulsory_certification.length > 0 && !t.mentions_certification && <div className="text-[#8a1414] font-semibold">compulsory-certification item, no ISI/BIS clause</div>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {s.tenders_failed > 0 && <p className="text-[0.8125rem] text-slate-500">{s.tenders_failed} document(s) could not be downloaded from our cloud environment (blocked or HTML pages); GeM bid documents are reachable from India — add them to data/evaluation/real_tenders.json and re-run.</p>}
        </section>
      )}
    </div>
  );
}
