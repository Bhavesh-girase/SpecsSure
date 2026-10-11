"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  AlertOctagon, ArrowRight, Bell, ClipboardCheck, FilePlus2, FileSearch, Gavel, IndianRupee, Megaphone, MessageSquareText,
  Network, Radar, RefreshCw, Scale, ShieldCheck, UserCog, Link2, BookOpen,
} from "lucide-react";
import { ErrorBox, Loading } from "@/components/ui";
import { Kpi, Notice, PageHead, SectionHead, StagePill, StageTracker } from "@/components/gov-ui";
import { demoSeed, notifications, officerDashboard } from "@/lib/api";
import { T, inr, usePrefs } from "@/lib/prefs";

const ACTION: Record<string, { icon: any; tone: string; tab: string; cta: [string, string] }> = {
  fix: { icon: AlertOctagon, tone: "#c0262d", tab: "findings", cta: ["Fix issues", "समस्याएँ ठीक करें"] },
  publish: { icon: Megaphone, tone: "#138808", tab: "overview", cta: ["Review & publish", "जाँचें व प्रकाशित करें"] },
  queries: { icon: MessageSquareText, tone: "#1d4f93", tab: "queries", cta: ["Reply", "उत्तर दें"] },
  evaluate: { icon: ClipboardCheck, tone: "#c26a00", tab: "evaluation", cta: ["Evaluate", "मूल्यांकन करें"] },
  award: { icon: Gavel, tone: "#0f2748", tab: "evaluation", cta: ["Record award", "अनुबंध दर्ज करें"] },
};

export default function OfficerWorkspace() {
  const { t, setRole } = usePrefs();
  const [d, setD] = useState<any>(null);
  const [notes, setNotes] = useState<any[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const load = () => {
    officerDashboard().then(setD).catch((e) => setErr(e.message));
    notifications().then((n) => setNotes(n || [])).catch(() => {});
  };
  useEffect(() => { setRole("officer"); load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  if (err && !d) return <div className="max-w-4xl mx-auto p-8"><ErrorBox error={err} /></div>;
  if (!d) return <Loading label="Loading workspace…" />;
  const c = d.counts;
  return (
    <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      <PageHead icon={UserCog} kicker={<T en="Buyer · Tender Inviting Authority" hi="क्रेता · निविदा आमंत्रण प्राधिकारी" />} title={t("dash.officer.title")}
        sub={<T en="Draft, vet, publish, clarify, evaluate and award — every step recorded in the audit ledger."
                hi="प्रारूप, जाँच, प्रकाशन, स्पष्टीकरण, मूल्यांकन और अनुबंध — हर चरण लेखा बही में दर्ज।" />}
        right={
          <div className="flex flex-wrap gap-2">
            <Link href="/studio" className="px-4 py-2.5 rounded-md bg-[#0f2748] text-white text-[0.9375rem] font-bold flex items-center gap-2 hover:bg-[#1d4f93]"><FilePlus2 className="w-4 h-4" /><T en="New tender" hi="नई निविदा" /></Link>
            <Link href="/tenders" className="px-4 py-2.5 rounded-md border border-[#0f2748] text-[#0f2748] text-[0.9375rem] font-bold flex items-center gap-2 hover:bg-[#eef4fb]"><FileSearch className="w-4 h-4" /><T en="Vet an uploaded tender" hi="अपलोड निविदा जाँचें" /></Link>
            <button onClick={load} className="px-3 py-2.5 rounded-md border border-[#c9d5e6] text-[#0f2748] hover:bg-[#eef4fb]" aria-label="Refresh"><RefreshCw className="w-4 h-4" /></button>
          </div>
        } />

      {d.total === 0 && (
        <Notice tone="warn">No tenders yet. <button className="underline font-semibold" onClick={async () => { await demoSeed(); load(); }}>Load the demo data</button> or draft a new tender in Tender Studio.</Notice>
      )}

      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
        <Kpi label={t("stage.draft")} value={c.draft} tone="navy" icon={FileSearch} hint={<T en="under vetting" hi="जाँच में" />} />
        <Kpi label={t("stage.published")} value={c.published} tone="green" icon={Megaphone} hint={<T en="accepting bids" hi="बोलियाँ स्वीकार" />} />
        <Kpi label={<T en="In evaluation" hi="मूल्यांकन में" />} value={c.bids_closed + c.financial_opened} tone="saffron" icon={Scale} />
        <Kpi label={t("stage.awarded")} value={c.awarded} tone="blue" icon={Gavel} />
        <Kpi label={<T en="Contract value awarded" hi="अनुबंधित मूल्य" />} value={<span className="text-[1.375rem]">{inr(d.awarded_value)}</span>} tone="navy" icon={IndianRupee} />
        <Kpi label={<T en="Queries awaiting reply" hi="उत्तर प्रतीक्षित प्रश्न" />} value={d.queries_open} tone={d.queries_open ? "red" : "green"} icon={MessageSquareText} />
      </div>

      <div className="grid xl:grid-cols-[1fr_360px] gap-6">
        <div className="space-y-6 min-w-0">
          {/* pending actions */}
          <section className="space-y-3">
            <SectionHead title={t("dash.pending")} sub={<T en="Generated from each tender's stage, open blockers and unanswered queries." hi="प्रत्येक निविदा के चरण, अवरोधों और अनुत्तरित प्रश्नों से बनी सूची।" />} />
            <ul className="bg-white border border-[#d5deea] rounded-lg divide-y divide-[#e2e8f0] shadow-card">
              {d.actions.map((a: any, i: number) => {
                const m = ACTION[a.kind] || ACTION.publish;
                const Icon = m.icon;
                return (
                  <li key={i} className="p-3.5 flex items-center gap-3">
                    <span className="w-9 h-9 rounded-md flex items-center justify-center shrink-0 text-white" style={{ background: m.tone }}><Icon className="w-4 h-4" /></span>
                    <div className="min-w-0 flex-1">
                      <div className="text-[0.9375rem] font-bold text-[#0f2748]">{a.text}</div>
                      <div className="text-[0.875rem] text-slate-500 truncate">{a.title}</div>
                    </div>
                    <Link href={`/tenders/${a.tender_id}?tab=${m.tab}`} className="shrink-0 px-3 py-1.5 rounded-md text-[0.875rem] font-bold border hover:bg-[#eef4fb] flex items-center gap-1" style={{ color: m.tone, borderColor: m.tone }}>
                      <T en={m.cta[0]} hi={m.cta[1]} /><ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  </li>
                );
              })}
              {!d.actions.length && <li className="p-6 text-center text-[0.9375rem] text-slate-500"><T en="Nothing pending — all tenders are up to date." hi="कुछ भी लंबित नहीं।" /></li>}
            </ul>
          </section>

          {/* pipeline */}
          <section className="space-y-3">
            <SectionHead title={t("dash.pipeline")} />
            <div className="space-y-3">
              {d.tenders.map((x: any) => (
                <article key={x.id} className="bg-white border border-[#d5deea] rounded-lg shadow-card p-4 space-y-3">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="text-[0.8125rem] font-mono text-slate-500">{x.reference_no || x.id}</div>
                      <Link href={`/tenders/${x.id}`} className="text-[1.0625rem] font-bold text-[#1d4f93] hover:underline">{x.title}</Link>
                      <div className="text-[0.875rem] text-slate-500">{x.organisation || "—"}{x.items?.length ? " · " + x.items.map((i: any) => `${i.quantity.toLocaleString("en-IN")} ${i.unit} ${i.label}`).join(" · ") : ""}</div>
                    </div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <StagePill stage={x.stage} />
                      {x.gate && <span className={`px-2 py-0.5 rounded-sm text-[0.8125rem] font-bold border ${x.gate === "READY" ? "border-[#9bd3a3] text-[#0d6b06] bg-[#e7f5e9]" : x.gate === "BLOCKED" ? "border-[#f1b0b0] text-[#8a1414] bg-[#fdecec]" : "border-[#f2cf8c] text-[#8a5300] bg-[#fff4e0]"}`}>
                        {Math.round(x.readiness ?? 0)} · {x.gate}</span>}
                      {x.generated && <span className="px-2 py-0.5 rounded-sm text-[0.8125rem] font-bold border border-[#adc8ea] text-[#1d4f93] bg-[#eef4fb]">Studio</span>}
                    </div>
                  </div>
                  <StageTracker stage={x.stage} />
                  <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-[0.875rem] text-slate-400">
                    <span><b className="text-[#0f2748]">{x.bids}</b> <T en="bids" hi="बोलियाँ" /></span>
                    <span><b className="text-[#0f2748]">{x.queries_open}</b> <T en="open queries" hi="खुले प्रश्न" /></span>
                    <span><b className="text-[#0f2748]">{x.blockers}</b> <T en="blockers" hi="अवरोध" /></span>
                    <span><T en="Bid due" hi="अंतिम तिथि" /> <b className="text-[#0f2748]">{x.bid_due || "—"}</b>{x.days_left !== null && x.stage === "published" ? ` (${x.days_left} ${t("days.left")})` : ""}</span>
                    {x.contract_value ? <span><T en="Contract" hi="अनुबंध" /> <b className="text-[#0f2748]">{inr(x.contract_value)}</b></span> : null}
                    <span className="flex-1" />
                    <Link href={`/tenders/${x.id}?tab=${x.stage === "draft" ? "overview" : x.stage === "published" ? "queries" : "evaluation"}`} className="font-bold text-[#1d4f93] hover:underline flex items-center gap-1">
                      <T en="Open" hi="खोलें" /><ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                </article>
              ))}
            </div>
          </section>
        </div>

        <aside className="space-y-6">
          <section className="bg-white border border-[#d5deea] rounded-lg shadow-card">
            <div className="px-4 py-3 border-b border-[#e2e8f0] flex items-center justify-between">
              <h2 className="font-extrabold text-[#0f2748] flex items-center gap-2"><Bell className="w-4 h-4" /><T en="Regulatory alerts" hi="नियामक सूचनाएँ" /></h2>
              <Link href="/radar" className="text-[0.875rem] font-bold text-[#1d4f93] hover:underline">Radar</Link>
            </div>
            <ul className="divide-y divide-[#e2e8f0] max-h-[360px] overflow-y-auto">
              {notes.slice(0, 8).map((n: any) => (
                <li key={n.id} className="p-3 text-[0.875rem]">
                  <div className="font-semibold text-[#0f2748]">{n.title}</div>
                  {n.message && <div className="text-slate-500 line-clamp-2">{n.message}</div>}
                </li>
              ))}
              {!notes.length && <li className="p-4 text-[0.875rem] text-slate-500"><T en="No alerts. Simulate a new amendment or QCO in the Radar to see affected tenders re-validated." hi="कोई सूचना नहीं।" /></li>}
            </ul>
          </section>
          <section className="bg-white border border-[#d5deea] rounded-lg shadow-card p-4 space-y-2">
            <h2 className="font-extrabold text-[#0f2748] mb-1"><T en="Quick links" hi="त्वरित लिंक" /></h2>
            {[
              ["/studio", FilePlus2, "Tender Studio — one sentence to tender", "निविदा स्टूडियो"],
              ["/radar", Radar, "Regulatory & QCO radar", "नियामक रडार"],
              ["/kg", Network, "Procurement knowledge graph", "ज्ञान ग्राफ़"],
              ["/search", BookOpen, "Indian Standards search", "मानक खोज"],
              ["/ledger", Link2, "Audit ledger (verify chain)", "लेखा बही"],
            ].map(([h, Icon, en, hi]: any) => (
              <Link key={h} href={h} className="flex items-center gap-2 text-[0.9375rem] text-[#1d4f93] font-semibold hover:underline"><Icon className="w-4 h-4" /><T en={en} hi={hi} /></Link>
            ))}
          </section>
          <Notice tone="info"><ShieldCheck className="w-4 h-4 inline mr-1 -mt-0.5" />
            <T en="Authentication and role-based access are out of scope for this prototype; the role selector only changes the workspace view."
               hi="इस प्रोटोटाइप में प्रमाणीकरण शामिल नहीं है; भूमिका चयन केवल दृश्य बदलता है।" /></Notice>
        </aside>
      </div>
    </div>
  );
}
