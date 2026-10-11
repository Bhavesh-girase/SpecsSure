"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, Briefcase, CalendarClock, CheckCircle2, Clock, FileCheck2, Gavel, IndianRupee, Lock, Search, Store, Trophy, XCircle } from "lucide-react";
import { ErrorBox, Loading } from "@/components/ui";
import { Kpi, Notice, PageHead, SectionHead, StagePill } from "@/components/gov-ui";
import { contractorDashboard } from "@/lib/api";
import { T, inr, usePrefs } from "@/lib/prefs";

const DEMO_BIDDERS = ["Gyan Jyoti Electricals (fictional)", "Harit Lighting Udyog (fictional)", "Chandni Lamps (fictional)"];

const TIER: Record<string, string> = {
  FULLY_RESPONSIVE: "bg-[#e7f5e9] text-[#0d6b06] border-[#9bd3a3]",
  RESPONSIVE_WITH_CLARIFICATIONS: "bg-[#fff4e0] text-[#8a5300] border-[#f2cf8c]",
  NON_RESPONSIVE: "bg-[#fdecec] text-[#8a1414] border-[#f1b0b0]",
};

export default function ContractorWorkspace() {
  const { t, setRole } = usePrefs();
  const [bidder, setBidder] = useState("");
  const [input, setInput] = useState("");
  const [d, setD] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const [q, setQ] = useState("");
  useEffect(() => {
    setRole("contractor");
    let b = "";
    try { b = localStorage.getItem("specsure.bidder") || ""; } catch {}
    b = b || DEMO_BIDDERS[1];
    setBidder(b); setInput(b);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!bidder) return;
    try { localStorage.setItem("specsure.bidder", bidder); } catch {}
    contractorDashboard(bidder).then(setD).catch((e) => setErr(e.message));
  }, [bidder]);
  if (err && !d) return <div className="max-w-4xl mx-auto p-8"><ErrorBox error={err} /></div>;
  if (!d) return <Loading label="Loading workspace…" />;
  const won = d.bids.filter((b: any) => b.result === "awarded");
  const wonValue = won.reduce((s: number, b: any) => s + b.awarded.reduce((x: number, a: any) => x + a.value, 0), 0);
  const avg = d.bids.length ? d.bids.reduce((s: number, b: any) => s + (b.match_index || 0), 0) / d.bids.length : null;
  const open = d.open.filter((x: any) => !q || (x.title + " " + x.organisation + " " + x.items.map((i: any) => i.label).join(" ")).toLowerCase().includes(q.toLowerCase()));
  return (
    <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      <PageHead icon={Briefcase} kicker={<T en="Supplier · Bidder" hi="आपूर्तिकर्ता · बोलीदाता" />} title={t("dash.contractor.title")}
        sub={<T en="Find tenders you can win, see exactly what each clause needs, fix gaps before the deadline and submit a sealed bid."
                hi="जीतने योग्य निविदाएँ खोजें, हर खंड की आवश्यकता देखें, समय से पहले कमियाँ दूर करें और सीलबंद बोली जमा करें।" />}
        right={
          <form className="flex flex-wrap items-end gap-2" onSubmit={(e) => { e.preventDefault(); if (input.trim()) setBidder(input.trim()); }}>
            <label className="text-[0.875rem] text-slate-400">
              <span className="block font-semibold text-[#0f2748] mb-1"><T en="Firm name" hi="फ़र्म का नाम" /></span>
              <input list="demo-bidders" value={input} onChange={(e) => setInput(e.target.value)}
                className="w-72 max-w-full rounded-md border border-[#c9d5e6] px-3 py-2 text-[0.9375rem] text-[#0f2748] focus:border-[#1d4f93] outline-none" />
              <datalist id="demo-bidders">{DEMO_BIDDERS.map((b) => <option key={b} value={b} />)}</datalist>
            </label>
            <button className="px-4 py-2 rounded-md bg-[#138808] text-white text-[0.9375rem] font-bold"><T en="Switch" hi="बदलें" /></button>
          </form>
        } />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Kpi label={t("dash.open")} value={d.open.length} tone="green" icon={Store} />
        <Kpi label={t("dash.mybids")} value={d.bids.length} tone="navy" icon={FileCheck2} />
        <Kpi label={<T en="Average match index" hi="औसत मिलान सूचकांक" />} value={avg === null ? "—" : avg.toFixed(1)} tone="blue" icon={CheckCircle2} />
        <Kpi label={<T en="Orders won" hi="प्राप्त आदेश" />} value={<span className="text-[1.375rem]">{inr(wonValue)}</span>} tone="saffron" icon={Trophy} hint={`${won.length} tender(s)`} />
      </div>

      <section className="space-y-3">
        <SectionHead title={t("dash.open")} right={
          <label className="relative">
            <Search className="w-4 h-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search item, organisation…" aria-label="Search open tenders"
              className="pl-8 pr-3 py-2 rounded-md border border-[#c9d5e6] text-[0.9375rem] w-64 outline-none focus:border-[#1d4f93]" />
          </label>} />
        <div className="grid md:grid-cols-2 gap-4">
          {open.map((x: any) => {
            const urgent = x.days_left !== null && x.days_left <= 7;
            const mine = d.bids.find((b: any) => b.tender_id === x.id);
            return (
              <article key={x.id} className="bg-white border border-[#d5deea] rounded-lg shadow-card flex flex-col">
                <div className="p-4 space-y-2 flex-1">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="text-[0.8125rem] font-mono text-slate-500">{x.reference_no}</div>
                      <h3 className="text-[1.0625rem] font-bold text-[#0f2748] leading-snug">{x.title}</h3>
                      <div className="text-[0.875rem] text-slate-500">{x.organisation}</div>
                    </div>
                    <div className={`shrink-0 text-center rounded-md border px-2.5 py-1.5 ${urgent ? "border-[#f1b0b0] bg-[#fdecec] text-[#8a1414]" : "border-[#9bd3a3] bg-[#e7f5e9] text-[#0d6b06]"}`}>
                      <div className="text-[1.25rem] font-extrabold font-mono leading-none">{x.days_left ?? "—"}</div>
                      <div className="text-[0.75rem] font-bold uppercase">{t("days.left")}</div>
                    </div>
                  </div>
                  {x.items?.length > 0 && (
                    <ul className="flex flex-wrap gap-1.5">
                      {x.items.map((i: any) => <li key={i.label} className="text-[0.8125rem] px-2 py-0.5 rounded-sm bg-[#eef4fb] text-[#13325d]"><b>{i.quantity.toLocaleString("en-IN")} {i.unit}</b> · {i.label}</li>)}
                    </ul>
                  )}
                  <div className="flex flex-wrap gap-x-4 text-[0.875rem] text-slate-400">
                    <span className="flex items-center gap-1"><CalendarClock className="w-3.5 h-3.5" /><T en="Bid due" hi="अंतिम तिथि" /> <b className="text-[#0f2748]">{x.bid_due || "—"}</b></span>
                    <span>{x.bids} <T en="bids so far" hi="बोलियाँ अब तक" /></span>
                  </div>
                </div>
                <div className="px-4 py-3 border-t border-[#e2e8f0] flex items-center gap-2">
                  {mine ? <span className="text-[0.875rem] font-bold text-[#0d6b06] flex items-center gap-1"><Lock className="w-3.5 h-3.5" /><T en="Sealed bid submitted" hi="सीलबंद बोली जमा" /></span>
                        : <span className="text-[0.875rem] text-slate-500"><T en="Not yet bid" hi="अभी बोली नहीं" /></span>}
                  <span className="flex-1" />
                  <Link href={`/market/${x.id}`} className="px-3.5 py-2 rounded-md bg-[#138808] text-white text-[0.875rem] font-bold flex items-center gap-1 hover:brightness-110">
                    {mine ? <T en="View / queries" hi="देखें / प्रश्न" /> : <T en="Prepare bid" hi="बोली तैयार करें" />}<ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </article>
            );
          })}
          {!open.length && <Notice tone="info"><T en="No tenders are open for bidding right now." hi="अभी कोई निविदा खुली नहीं है।" /></Notice>}
        </div>
      </section>

      <section className="space-y-3">
        <SectionHead title={t("dash.mybids")} sub={<T en={`Bids submitted as “${bidder}”. Prices stay sealed — only their SHA-256 commitment is public until the financial opening.`}
                                                   hi={`“${bidder}” के रूप में जमा बोलियाँ। वित्तीय बोली खुलने तक मूल्य सीलबंद रहते हैं।`} />} />
        <div className="bg-white border border-[#d5deea] rounded-lg overflow-x-auto shadow-card">
          <table className="gov-table">
            <thead><tr><th>Tender</th><th>Product</th><th>Match index</th><th>Sealed price</th><th>Stage</th><th>Result</th></tr></thead>
            <tbody>
              {d.bids.map((b: any) => (
                <tr key={b.bid_id}>
                  <td><Link href={`/market/${b.tender_id}`} className="font-semibold text-[#1d4f93] hover:underline">{b.tender_title}</Link><div className="text-[0.8125rem] font-mono text-slate-500">{b.reference_no}</div></td>
                  <td>{b.product_name || "—"}</td>
                  <td><span className="font-mono font-bold text-[#0f2748]">{b.match_index?.toFixed?.(1) ?? "—"}</span>{" "}
                    {b.tier && <span className={`ml-1 px-1.5 py-0.5 rounded-sm border text-[0.75rem] font-bold ${TIER[b.tier] || ""}`}>{b.tier.replaceAll("_", " ")}</span>}</td>
                  <td>{b.sealed ? <span className="font-mono text-[0.8125rem] flex items-center gap-1" title={b.commitment}><Lock className="w-3 h-3 text-[#138808]" />{b.commitment.slice(0, 12)}…</span> : "—"}</td>
                  <td><StagePill stage={b.stage} /></td>
                  <td>
                    {b.result === "awarded" && <span className="text-[#0d6b06] font-bold flex items-center gap-1"><Gavel className="w-3.5 h-3.5" />{b.awarded.map((a: any) => `${a.quantity.toLocaleString("en-IN")} × ${inr(a.unit_price, 2)}`).join(", ")}</span>}
                    {b.result === "not awarded" && <span className="text-[#8a1414] font-semibold flex items-center gap-1"><XCircle className="w-3.5 h-3.5" /><T en="Not awarded" hi="अनुबंध नहीं" /></span>}
                    {!b.result && <span className="text-slate-500 flex items-center gap-1"><Clock className="w-3.5 h-3.5" /><T en="Pending" hi="लंबित" /></span>}
                  </td>
                </tr>
              ))}
              {!d.bids.length && <tr><td colSpan={6} className="text-center text-slate-500 py-6"><T en="No bids yet from this firm." hi="इस फ़र्म की कोई बोली नहीं।" /></td></tr>}
            </tbody>
          </table>
        </div>
      </section>
      {d.closed?.length > 0 && (
        <section className="space-y-3">
          <SectionHead title={<T en="Closed & awarded tenders" hi="बंद व अनुबंधित निविदाएँ" />} />
          <div className="flex flex-wrap gap-2">
            {d.closed.map((x: any) => (
              <Link key={x.id} href={`/market/${x.id}`} className="bg-white border border-[#d5deea] rounded-md px-3 py-2 text-[0.875rem] flex items-center gap-2 hover:border-[#1d4f93]">
                <StagePill stage={x.stage} /><span className="font-semibold text-[#0f2748]">{x.title}</span>{x.contract_value ? <span className="text-slate-500">· {inr(x.contract_value)}</span> : null}
              </Link>
            ))}
          </div>
        </section>
      )}
      <Notice tone="info"><IndianRupee className="w-4 h-4 inline -mt-0.5 mr-1" />
        <T en="No login in this prototype — enter your firm name to see its bids. Demo firms are fictional." hi="इस प्रोटोटाइप में लॉगिन नहीं है — अपनी फ़र्म का नाम दर्ज करें। डेमो फ़र्में काल्पनिक हैं।" /></Notice>
    </div>
  );
}
