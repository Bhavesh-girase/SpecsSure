"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft, Activity, ListChecks, FileText, Sigma, Store, BookMarked, FlaskConical, MessageCircleQuestion,
  GitBranch, Network, Download, Library, RefreshCw, Send, Briefcase, Users, Wand2, Store as StoreIcon, Gavel, MessagesSquare, ArrowRight,
} from "lucide-react";
import { EvaluationPanel, OfficerQueries } from "@/components/tender/lifecycle";
import { StagePill, StageTracker } from "@/components/gov-ui";
import { evaluation } from "@/lib/api";
import { Button, ErrorBox, Loading, Disclaimer } from "@/components/ui";
import { getTender, recompile, updateTender, fileUrl } from "@/lib/api";
import { gateStyle, cn } from "@/lib/utils";
import { Overview } from "@/components/tender/overview";
import { Findings } from "@/components/tender/findings";
import { DocumentView, Corrigenda } from "@/components/tender/document";
import { Proofs, Market, Standards, Tests } from "@/components/tender/analysis";
import { Prebid, Memory } from "@/components/tender/prebid";
import { TwinGraph, AuditTrail } from "@/components/tender/twin-graph";
import { BidsComparative, StudioProvenance } from "@/components/tender/bids";

type Tab = "overview" | "findings" | "document" | "proofs" | "market" | "standards" | "tests" | "prebid" | "corrigenda" | "graph" | "memory" | "exports" | "bids" | "studio" | "queries" | "evaluation";

type TabDef = { id: Tab; label: string; desc: string; icon: any; count?: number; alert?: boolean };

export default function TenderCockpit() {
  const { id } = useParams() as { id: string };
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const search = useSearchParams();
  const router = useRouter();
  const [tab, setTabS] = useState<Tab>((search?.get("tab") as Tab) || "overview");
  const [stage, setStage] = useState<string | null>(null);
  // keep the open section in the URL, so the back button, refresh and shared links return to the same place
  const setTab = (t: Tab) => {
    setTabS(t);
    router.replace(`/tenders/${id}?tab=${t}`, { scroll: false });
    requestAnimationFrame(() => document.getElementById("section-top")?.scrollIntoView({ behavior: "smooth", block: "start" }));
  };
  const load = useCallback(() => {
    evaluation(id).then((e: any) => setStage(e.stage)).catch(() => {});
    return getTender(id).then(setData).catch((e) => setErr(e.message));
  }, [id]);
  useEffect(() => { load(); }, [load]);
  if (err && !data) return <div className="max-w-4xl mx-auto p-8"><ErrorBox error={err} /></div>;
  if (!data) return <Loading label="Opening the tender and running all checks…" />;
  const { twin, summary } = data;
  const isDemo = (summary.reference_no || "").startsWith("DEMO/PWD");
  const open = twin.findings.filter((f: any) => ["open", "accepted", undefined].includes(f.review_status));
  const proofs = twin.verification.conflicts.length + twin.verification.standard_conflicts.length;
  const newQueries = (twin.prebid_received || []).filter((q: any) => q.status === "received").length;

  // Sections grouped by the job the officer is doing, in the order the work happens.
  const groups: { title: string; items: TabDef[] }[] = [
    { title: "Check before publishing", items: [
      { id: "overview", label: "Summary & readiness", icon: Activity, desc: "Overall readiness score, what is blocking publication, and the pre-publication checklist." },
      { id: "findings", label: "Issues found", icon: ListChecks, count: open.length, alert: open.length > 0,
        desc: "Every problem the automatic checker found, clause by clause, with a suggested fix. Accept, dismiss (with a reason) or fix each one." },
      { id: "proofs", label: "Impossible requirements", icon: Sigma, count: proofs, alert: proofs > 0,
        desc: "Clauses that can never be met at the same time — proven mathematically, e.g. one clause asks for ‘≥ 500’ and another for ‘≤ 480’." },
      { id: "standards", label: "Standards & certification", icon: BookMarked, count: twin.citations.length,
        desc: "Each Indian Standard cited, checked on the tender date: withdrawn or replaced editions, amendments in force and mandatory certification (QCO / CRS)." },
      { id: "market", label: "Fair competition", icon: Store,
        desc: "How many manufacturers can meet this specification, and which clauses unfairly shut them out (GFR Rule 144)." },
      { id: "tests", label: "Tests & labs", icon: FlaskConical, count: twin.test_plan.tests.length,
        desc: "The tests each requirement needs and BIS-recognised laboratories that can carry them out." },
    ] },
    { title: "Tender document", items: [
      { id: "document", label: "Clauses", icon: FileText, desc: "The tender text split into clauses, with the requirements SpecSure extracted from each." },
      { id: "corrigenda", label: "Corrigenda (changes)", icon: GitBranch, count: (twin.corrigenda?.changelog || []).length,
        desc: "All corrections merged in date order, so you always see the latest wording — with a history for every clause." },
      { id: "graph", label: "Connections map", icon: Network, desc: "The tender as a map: clauses → requirements → standards → tests → evidence." },
      { id: "memory", label: "Lessons from past tenders", icon: Library, desc: "Similar issues and clarifications from earlier tenders, so the same mistakes are not repeated." },
    ] },
    { title: "Bidding & award", items: [
      { id: "prebid", label: "Likely bidder questions", icon: MessageCircleQuestion, count: (twin.prebid || []).length,
        desc: "Questions bidders are likely to ask, predicted before publication, with draft answers you can approve." },
      { id: "queries", label: "Bidder queries", icon: MessagesSquare, count: newQueries, alert: newQueries > 0,
        desc: "Questions received from bidders and the replies you have published." },
      { id: "bids", label: "Bids received", icon: Users, desc: "All bids side by side, clause by clause." },
      { id: "evaluation", label: "Evaluation & award", icon: Gavel,
        desc: "Technical result, price ranking with Make in India and MSE preference, and recording the award." },
    ] },
    { title: "Records", items: [
      ...(summary.generated ? [{ id: "studio" as Tab, label: "How this draft was made", icon: Wand2, desc: "Why each clause of this generated tender exists — the item, standard, rule or policy behind it." }] : []),
      { id: "exports", label: "Downloads & audit trail", icon: Download, desc: "Excel, PDF and machine-readable exports, plus every recorded action on this tender." },
    ] },
  ];
  const all = groups.flatMap((g) => g.items);
  const cur = all.find((x) => x.id === tab) || all[0];
  const gate = twin.readiness.gate as string;
  const gateText = gate === "READY" ? "Ready to publish" : gate === "BLOCKED" ? "Blocked — fix critical issues" : "Needs review";

  return (
    <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-5">
      {/* header */}
      <div className="bg-white border border-[#d5deea] rounded-lg shadow-card overflow-hidden">
        <div className="h-1 tricolour" />
        <div className="p-5 space-y-4">
          <Link href="/tenders" className="inline-flex items-center gap-1.5 text-[0.875rem] font-semibold text-[#1d4f93] hover:underline"><ArrowLeft className="w-4 h-4" />All tenders</Link>
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0 flex-1 basis-[22rem]">
              <div className="text-[0.8125rem] uppercase tracking-wider text-[#b7862b] font-bold">Tender · <span className="font-mono normal-case tracking-normal">{summary.reference_no || summary.id}</span></div>
              <h1 className="text-2xl font-extrabold text-[#0f2748] leading-tight mt-0.5">{twin.tender.title}</h1>
              <dl className="flex flex-wrap gap-x-6 gap-y-1 mt-2 text-[0.9375rem]">
                <div className="flex gap-1.5"><dt className="text-slate-500">Buyer:</dt><dd className="font-semibold text-[#0f2748]">{summary.organisation || "—"}</dd></div>
                <div className="flex gap-1.5"><dt className="text-slate-500">Bid due:</dt><dd className="font-semibold text-[#0f2748]">{twin.tender.dates.bid_due || "—"}</dd></div>
                {twin.tender.domains.length > 0 && <div className="flex gap-1.5"><dt className="text-slate-500">Covers:</dt><dd className="font-semibold text-[#0f2748] capitalize">{twin.tender.domains.join(", ")}</dd></div>}
                {Object.keys(twin.tender.grades).length > 0 && <div className="flex gap-1.5"><dt className="text-slate-500">Grades:</dt><dd className="font-semibold text-[#0f2748]">{Object.entries(twin.tender.grades).map(([k, v]) => `${k} ${v}`).join(", ")}</dd></div>}
              </dl>
            </div>
            <button onClick={() => setTab("overview")} className={cn("shrink-0 rounded-lg border px-4 py-2.5 text-left", gateStyle(gate))} title="Readiness score out of 100">
              <div className="text-[0.75rem] font-bold uppercase tracking-wider opacity-80">Readiness</div>
              <div className="flex items-baseline gap-2"><span className="text-2xl font-extrabold font-mono">{Math.round(twin.readiness.score)}</span><span className="text-[0.875rem] font-bold">{gateText}</span></div>
            </button>
          </div>
          <div className="flex flex-wrap items-center gap-2 pt-3 border-t border-[#e2e8f0]">
            {stage && <StagePill stage={stage} />}
            <span className="flex-1" />
            {summary.status === "draft" && (
              <Button variant={gate === "BLOCKED" ? "ghost" : "success"} title={gate === "BLOCKED" ? "Publishing is blocked while critical issues are open" : "Publish this tender for bidding"}
                onClick={async () => { try { await updateTender(id, { status: "published" }); load(); } catch (e: any) { setErr(e.message); } }}>
                <Send className="w-4 h-4" />Publish
              </Button>)}
            <Button variant="ghost" title="Run every check again with the latest standards and rules" onClick={async () => { await recompile(id); load(); }}><RefreshCw className="w-4 h-4" />Re-check tender</Button>
            <Link href={`/bidder?tender=${id}`}><Button variant="ghost" title="Check a bidder's documents against this tender"><Briefcase className="w-4 h-4" />Check a bid (Bid Mirror)</Button></Link>
            {["published", "awarded"].includes(summary.status) && <Link href={`/market/${id}`}><Button variant="ghost"><StoreIcon className="w-4 h-4" />Open bid form</Button></Link>}
            {summary.generated && <a href={fileUrl(`/tenders/${id}/generated.docx`)}><Button variant="ghost"><Download className="w-4 h-4" />Download .docx</Button></a>}
          </div>
        </div>
      </div>
      {stage && <div className="bg-white border border-[#d5deea] rounded-lg p-4 shadow-card"><StageTracker stage={stage} /></div>}
      {err && <div onClick={() => setErr(null)} className="cursor-pointer"><ErrorBox error={err} /></div>}

      <div className="grid lg:grid-cols-[270px_minmax(0,1fr)] gap-6 items-start">
        {/* section navigation: sidebar on large screens, a dropdown on small ones */}
        <nav aria-label="Tender sections" className="lg:sticky lg:top-16">
          <label className="lg:hidden block">
            <span className="block text-[0.875rem] font-semibold text-[#0f2748] mb-1">Go to section</span>
            <select value={tab} onChange={(e) => setTab(e.target.value as Tab)}
              className="w-full rounded-md border border-[#c9d5e6] bg-white px-3 py-2.5 text-[0.9375rem] font-semibold text-[#0f2748]">
              {groups.map((g) => (
                <optgroup key={g.title} label={g.title}>
                  {g.items.map((x) => <option key={x.id} value={x.id}>{x.label}{x.count ? ` (${x.count})` : ""}</option>)}
                </optgroup>
              ))}
            </select>
          </label>
          <div className="hidden lg:block bg-white border border-[#d5deea] rounded-lg shadow-card py-2 max-h-[calc(100vh-6rem)] overflow-y-auto">
            {groups.map((g) => (
              <div key={g.title} className="py-1">
                <div className="px-4 pt-2 pb-1 text-[0.75rem] font-bold uppercase tracking-wider text-slate-500">{g.title}</div>
                <ul>
                  {g.items.map((x) => {
                    const on = x.id === tab;
                    const Icon = x.icon;
                    return (
                      <li key={x.id}>
                        <button onClick={() => setTab(x.id)} aria-current={on ? "page" : undefined}
                          className={cn("w-full flex items-center gap-2.5 px-4 py-2 text-left text-[0.9375rem] border-l-[3px] transition-colors",
                            on ? "border-[#ff9933] bg-[#eef4fb] text-[#0f2748] font-bold" : "border-transparent text-[#334155] hover:bg-[#f5f8fc] hover:text-[#0f2748]")}>
                          <Icon className={cn("w-4 h-4 shrink-0", on ? "text-[#1d4f93]" : "text-slate-500")} />
                          <span className="flex-1 leading-snug">{x.label}</span>
                          {x.count !== undefined && x.count > 0 && (
                            <span className={cn("min-w-[1.5rem] text-center px-1.5 rounded-full text-[0.75rem] font-bold", x.alert ? "bg-[#fdecec] text-[#a01818]" : "bg-[#eef2f7] text-[#475569]")}>{x.count}</span>)}
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ))}
          </div>
        </nav>

        <section className="min-w-0 space-y-4" aria-labelledby="section-title">
          <div id="section-top" className="border-b border-[#d5deea] pb-3">
            <h2 id="section-title" className="text-xl font-extrabold text-[#0f2748] flex items-center gap-2"><cur.icon className="w-5 h-5 text-[#1d4f93]" />{cur.label}</h2>
            <p className="text-[0.9375rem] text-slate-500 mt-1 max-w-3xl">{cur.desc}</p>
          </div>
      <div>
        {tab === "overview" && <Overview twin={twin} onJump={(t) => setTab(t as Tab)} />}
        {tab === "findings" && <Findings twin={twin} tenderId={id} onChanged={load} />}
        {tab === "proofs" && <Proofs twin={twin} />}
        {tab === "document" && <DocumentView twin={twin} />}
        {tab === "standards" && <Standards twin={twin} tenderId={id} onChanged={load} />}
        {tab === "market" && <Market twin={twin} />}
        {tab === "tests" && <Tests twin={twin} />}
        {tab === "prebid" && <Prebid twin={twin} tenderId={id} onChanged={load} />}
        {tab === "corrigenda" && <Corrigenda twin={twin} tenderId={id} onChanged={load} isDemo={isDemo} />}
        {tab === "graph" && <TwinGraph twin={twin} />}
        {tab === "memory" && <Memory twin={twin} />}
        {tab === "bids" && <BidsComparative tenderId={id} />}
        {tab === "queries" && <OfficerQueries tenderId={id} predicted={(twin.prebid || []).length} onChanged={load} />}
        {tab === "evaluation" && <EvaluationPanel tenderId={id} onChanged={load} />}
        {tab === "studio" && <StudioProvenance tenderId={id} />}
        {tab === "exports" && (
          <div className="space-y-6">
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {[
                ["Readiness report (PDF)", "A printable summary for file noting or the tender committee.", `/tenders/${id}/export/report.pdf`],
                ["Issues register (Excel)", "All issues, requirements and the checklist as spreadsheet sheets.", `/tenders/${id}/export/findings.xlsx`],
                ["Full tender data (JSON)", "Everything SpecSure extracted, with sources — for other software.", `/tenders/${id}/twin.json`],
                ["SARIF file (for developers)", "Standard format for automated check results; opens in VS Code or GitHub.", `/tenders/${id}/sarif`],
              ].map(([t, d, p]) => (
                <a key={p} href={fileUrl(p)} target="_blank" rel="noreferrer" className="glass-panel rounded-2xl p-4 hover:border-sky-500/50 border block">
                  <Download className="w-5 h-5 text-sky-400 mb-2" />
                  <div className="text-sm font-bold text-ink">{t}</div>
                  <div className="text-[0.8125rem] text-slate-400">{d}</div>
                </a>
              ))}
            </div>
            <AuditTrail tenderId={id} />
          </div>
        )}
      </div>
          <SectionPager all={all} tab={tab} onGo={setTab} />
        </section>
      </div>
      <Disclaimer />
    </div>
  );
}

/** "Previous / Next section" links at the bottom of each section, so the tender can be reviewed start to finish. */
function SectionPager({ all, tab, onGo }: { all: TabDef[]; tab: Tab; onGo: (t: Tab) => void }) {
  const i = all.findIndex((x) => x.id === tab);
  const prev = i > 0 ? all[i - 1] : null, next = i < all.length - 1 ? all[i + 1] : null;
  return (
    <div className="flex flex-wrap justify-between gap-3 pt-4 border-t border-[#d5deea]">
      {prev ? <button onClick={() => onGo(prev.id)} className="text-left rounded-md border border-[#d5deea] bg-white px-4 py-2.5 hover:border-[#1d4f93]">
        <div className="text-[0.8125rem] text-slate-500 flex items-center gap-1"><ArrowLeft className="w-3.5 h-3.5" />Previous</div>
        <div className="font-bold text-[#1d4f93]">{prev.label}</div></button> : <span />}
      {next && <button onClick={() => onGo(next.id)} className="text-right rounded-md border border-[#d5deea] bg-white px-4 py-2.5 hover:border-[#1d4f93] ml-auto">
        <div className="text-[0.8125rem] text-slate-500 flex items-center justify-end gap-1">Next<ArrowRight className="w-3.5 h-3.5" /></div>
        <div className="font-bold text-[#1d4f93]">{next.label}</div></button>}
    </div>
  );
}
