"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, CalendarClock, CheckCircle2, Compass, Gavel, HelpCircle, Lock, MessageSquareText, Send, Users, XCircle } from "lucide-react";
import { Button } from "@/components/ui";
import { Notice } from "@/components/gov-ui";
import { bidAdvice, listQueries, raiseQuery } from "@/lib/api";
import { T, inr } from "@/lib/prefs";

export type Decl = { mse: boolean; mii_class: "I" | "II" | "non-local"; local_content: number | "" };

/** Sealed price bid (per line item) + Make in India / MSE declarations. */
export function PriceBid({ lines, scope, prices, setPrices, decl, setDecl }: {
  lines: any[]; scope: string[] | null; prices: Record<string, string>; setPrices: (p: Record<string, string>) => void; decl: Decl; setDecl: (d: Decl) => void;
}) {
  const quoting = lines.filter((l) => !scope || !l.domain || scope.includes(l.domain));
  const total = quoting.reduce((s, l) => s + (Number(prices[String(l.index)]) || 0) * l.quantity, 0);
  return (
    <div className="space-y-4">
      <div className="bg-white border border-[#d5deea] rounded-lg overflow-x-auto">
        <table className="gov-table">
          <thead><tr><th>#</th><th>Item</th><th className="text-right">Quantity</th><th className="text-right">Unit rate (₹, incl. taxes)</th><th className="text-right">Amount (₹)</th></tr></thead>
          <tbody>
            {quoting.map((l) => {
              const p = prices[String(l.index)] ?? "";
              return (
                <tr key={l.index}>
                  <td className="font-mono">{l.index}</td>
                  <td className="font-semibold">{l.label}</td>
                  <td className="text-right font-mono whitespace-nowrap">{l.quantity.toLocaleString("en-IN")} {l.unit}</td>
                  <td className="text-right">
                    <input type="number" min="0" step="0.01" inputMode="decimal" aria-label={`Unit rate for ${l.label}`} value={p}
                      onChange={(e) => setPrices({ ...prices, [String(l.index)]: e.target.value })}
                      className="w-32 text-right rounded-md border border-[#c9d5e6] px-2 py-1.5 font-mono text-[0.9375rem] focus:border-[#1d4f93] outline-none" />
                  </td>
                  <td className="text-right font-mono">{p ? inr(Number(p) * l.quantity, 2) : "—"}</td>
                </tr>
              );
            })}
            <tr><td colSpan={4} className="text-right font-bold">Total quoted value</td><td className="text-right font-mono font-extrabold text-[#0f2748]">{inr(total, 2)}</td></tr>
          </tbody>
        </table>
      </div>
      <fieldset className="grid md:grid-cols-3 gap-3">
        <legend className="sr-only">Preference declarations</legend>
        <label className="bg-white border border-[#d5deea] rounded-md p-3 flex gap-2 text-[0.875rem] cursor-pointer">
          <input type="checkbox" checked={decl.mse} onChange={(e) => setDecl({ ...decl, mse: e.target.checked })} />
          <span><b className="text-[#0f2748]">Micro / Small Enterprise (Udyam)</b><br /><span className="text-slate-500">MSE Policy 2012: within L1 + 15 % you may be offered up to 25 % of the quantity at L1; EMD exempt.</span></span>
        </label>
        <label className="bg-white border border-[#d5deea] rounded-md p-3 text-[0.875rem]">
          <b className="text-[#0f2748]">Make in India class</b>
          <select value={decl.mii_class} onChange={(e) => setDecl({ ...decl, mii_class: e.target.value as any })}
            className="mt-1 w-full rounded-md border border-[#c9d5e6] px-2 py-1.5 text-[0.9375rem]">
            <option value="I">Class-I local supplier (local content ≥ 50 %)</option>
            <option value="II">Class-II local supplier (20 – 50 %)</option>
            <option value="non-local">Non-local supplier (&lt; 20 %)</option>
          </select>
          <span className="text-slate-500 block mt-1">PPP-MII Order 2017: Class-I within 20 % of L1 may be invited to match L1.</span>
        </label>
        <label className="bg-white border border-[#d5deea] rounded-md p-3 text-[0.875rem]">
          <b className="text-[#0f2748]">Local content (%)</b>
          <input type="number" min="0" max="100" value={decl.local_content} onChange={(e) => setDecl({ ...decl, local_content: e.target.value === "" ? "" : Number(e.target.value) })}
            className="mt-1 w-full rounded-md border border-[#c9d5e6] px-2 py-1.5 font-mono text-[0.9375rem]" />
          {decl.local_content !== "" && ((decl.mii_class === "I" && Number(decl.local_content) < 50) || (decl.mii_class === "II" && (Number(decl.local_content) < 20 || Number(decl.local_content) >= 50))) &&
            <span className="text-[#8a1414] block mt-1 font-semibold">Declared class does not match the local content.</span>}
        </label>
      </fieldset>
      <Notice tone="info"><Lock className="w-4 h-4 inline -mt-0.5 mr-1" />
        <T en="Your prices are sealed: at submission only a SHA-256 commitment (hash of prices + bid id + a random salt) is written to the public audit ledger. At the financial opening every price is re-hashed and must match — a price changed later is detected."
           hi="आपके मूल्य सीलबंद हैं: जमा करते समय केवल SHA-256 प्रतिबद्धता लेखा बही में दर्ज होती है। वित्तीय बोली खुलने पर हर मूल्य का पुनः हैश मिलाया जाता है।" /></Notice>
    </div>
  );
}

const TONE: Record<string, string> = {
  good: "border-[#9bd3a3] bg-[#e7f5e9] text-[#0d4f07]", ok: "border-[#adc8ea] bg-[#eef4fb] text-[#13325d]",
  warn: "border-[#f2cf8c] bg-[#fff8ec] text-[#6b4200]", bad: "border-[#f1b0b0] bg-[#fdecec] text-[#8a1414]",
};

/** Bid / No-Bid advisor with a back-scheduled plan. */
export function Advisor({ tenderId, answers, scope }: { tenderId: string; answers: any; scope: string[] | null }) {
  const [a, setA] = useState<any>(null);
  useEffect(() => {
    const t = setTimeout(() => bidAdvice(tenderId, answers, scope).then(setA).catch(() => {}), 450);
    return () => clearTimeout(t);
  }, [tenderId, answers, scope]);
  if (!a) return null;
  const Icon = a.tone === "good" ? CheckCircle2 : a.tone === "bad" ? XCircle : a.tone === "warn" ? AlertTriangle : Compass;
  return (
    <section className="bg-white border border-[#d5deea] rounded-lg shadow-card overflow-hidden" aria-live="polite">
      <div className="px-4 py-2.5 bg-[#0f2748] text-white text-[0.9375rem] font-bold flex items-center gap-2"><Compass className="w-4 h-4" /><T en="Bid / No-Bid advisor" hi="बोली / न-बोली सलाहकार" /></div>
      <div className="p-4 space-y-3">
        <div className={`border rounded-md p-3 ${TONE[a.tone]}`}>
          <div className="font-extrabold text-[1.0625rem] flex items-center gap-2"><Icon className="w-5 h-5" />{a.verdict}</div>
          <p className="text-[0.875rem] mt-1">{a.reason}</p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center">
          <div className="rounded-md bg-[#f8fafc] border border-[#e2e8f0] p-2"><div className="text-[1.125rem] font-extrabold font-mono text-[#0f2748]">{a.days_left ?? "—"}</div><div className="text-[0.75rem] uppercase font-bold text-slate-500">days left</div></div>
          <div className="rounded-md bg-[#f8fafc] border border-[#e2e8f0] p-2"><div className="text-[1.125rem] font-extrabold font-mono text-[#0f2748]">{a.critical_path_days}</div><div className="text-[0.75rem] uppercase font-bold text-slate-500">days needed</div></div>
          <div className="rounded-md bg-[#f8fafc] border border-[#e2e8f0] p-2"><div className="text-[1.125rem] font-extrabold font-mono text-[#0f2748]">{a.expected_competitors ?? "—"}</div><div className="text-[0.75rem] uppercase font-bold text-slate-500 flex items-center justify-center gap-1"><Users className="w-3 h-3" />eligible makers</div></div>
        </div>
        {a.substantive?.length > 0 && (
          <div>
            <div className="text-[0.875rem] font-bold text-[#8a1414] mb-1">Cannot be fixed with documents</div>
            <ul className="space-y-1">{a.substantive.map((s: any) => <li key={s.field_id} className="text-[0.875rem] text-[#334155]">Cl. {s.clause_key} {s.label}: {s.detail}</li>)}</ul>
          </div>
        )}
        {a.plan?.length > 0 && (
          <div>
            <div className="text-[0.875rem] font-bold text-[#0f2748] mb-1 flex items-center gap-1"><CalendarClock className="w-3.5 h-3.5" />Preparation plan (back-scheduled from the bid due date)</div>
            <ol className="space-y-1.5">
              {a.plan.map((p: any) => (
                <li key={p.group} className={`rounded-md border p-2 text-[0.875rem] ${p.late ? "border-[#f1b0b0] bg-[#fdecec]" : "border-[#e2e8f0] bg-[#f8fafc]"}`}>
                  <div className="flex justify-between gap-2 font-semibold text-[#0f2748]"><span className="capitalize">{p.group.replaceAll("_", " ")} · ~{p.days} d</span>
                    <span className={p.late ? "text-[#8a1414]" : "text-slate-400"}>{p.late ? "start date passed" : `start by ${p.start_by}`}</span></div>
                  <ul className="list-disc ml-4 text-slate-400">{p.tasks.slice(0, 3).map((t: string) => <li key={t}>{t}</li>)}</ul>
                </li>
              ))}
            </ol>
          </div>
        )}
        <p className="text-[0.8125rem] text-slate-500">{a.note}</p>
      </div>
    </section>
  );
}

/** Ask the buyer + published clarifications (bidder identity hidden in the public list). */
export function QueriesBox({ tenderId, bidder, open }: { tenderId: string; bidder: string; open: boolean }) {
  const [list, setList] = useState<any[]>([]);
  const [q, setQ] = useState("");
  const [res, setRes] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const load = () => listQueries(tenderId, true).then(setList).catch(() => {});
  useEffect(() => { load(); }, [tenderId]); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <section className="bg-white border border-[#d5deea] rounded-lg shadow-card overflow-hidden">
      <div className="px-4 py-2.5 bg-[#1d4f93] text-white text-[0.9375rem] font-bold flex items-center gap-2"><MessageSquareText className="w-4 h-4" /><T en="Clarifications" hi="स्पष्टीकरण" /></div>
      <div className="p-4 space-y-3">
        {open && (
          <div className="space-y-2">
            <label htmlFor="cq" className="text-[0.875rem] font-semibold text-[#0f2748] flex items-center gap-1"><HelpCircle className="w-3.5 h-3.5" /><T en="Ask the buyer a question" hi="क्रेता से प्रश्न पूछें" /></label>
            <textarea id="cq" rows={3} value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. Is a BEE 3-star label acceptable under clause 3.7?"
              className="w-full rounded-md border border-[#c9d5e6] p-2 text-[0.9375rem] outline-none focus:border-[#1d4f93]" />
            <Button onClick={async () => {
              setErr(null);
              try { const r = await raiseQuery(tenderId, bidder || "Anonymous bidder", q); setRes(r); setQ(""); load(); } catch (e: any) { setErr(e.message); }
            }} disabled={q.trim().length < 8}><Send className="w-3.5 h-3.5" /><T en="Submit query" hi="प्रश्न भेजें" /></Button>
            {err && <Notice tone="bad">{err}</Notice>}
            {res && (
              <Notice tone="good">
                Query <b>{res.qid}</b> recorded{res.clause_key ? <> and linked to <b>Clause {res.clause_key}</b></> : null}.
                {res.duplicate_of && <> A similar question (<b>{res.duplicate_of}</b>) is already with the buyer — both will get one reply.</>}
                {res.predicted && <> The tender compiler had predicted this question before publication.</>}
              </Notice>
            )}
          </div>
        )}
        <div>
          <div className="text-[0.875rem] font-bold text-[#0f2748] mb-1"><T en="Published replies" hi="प्रकाशित उत्तर" /> ({list.length})</div>
          <ul className="space-y-2 max-h-72 overflow-y-auto">
            {list.map((x) => (
              <li key={x.qid} className="rounded-md border border-[#e2e8f0] bg-[#f8fafc] p-2 text-[0.875rem]">
                <div className="text-slate-500 font-mono text-[0.8125rem]">{x.qid}{x.clause_key ? ` · Cl. ${x.clause_key}` : ""}</div>
                <div className="font-semibold text-[#0f2748]">Q: {x.question}</div>
                <div className="text-[#13325d] mt-0.5">A: {x.final_response}</div>
              </li>
            ))}
            {!list.length && <li className="text-[0.875rem] text-slate-500"><T en="No replies published yet." hi="अभी कोई उत्तर प्रकाशित नहीं।" /></li>}
          </ul>
        </div>
      </div>
    </section>
  );
}

/** Public result once a tender is awarded. */
export function AwardResult({ ev }: { ev: any }) {
  if (!ev?.award) return null;
  return (
    <section className="bg-white border-2 border-[#0f2748] rounded-lg shadow-card overflow-hidden">
      <div className="px-4 py-2.5 bg-[#0f2748] text-white font-bold flex items-center gap-2"><Gavel className="w-4 h-4" />Award notice — {inr(ev.award.contract_value, 2)}</div>
      <div className="overflow-x-auto">
        <table className="gov-table">
          <thead><tr><th>Item</th><th>Supplier</th><th className="text-right">Quantity</th><th className="text-right">Unit rate</th><th className="text-right">Value</th><th>Basis</th></tr></thead>
          <tbody>
            {ev.award.allocation.map((a: any, i: number) => (
              <tr key={i}><td>{a.label}</td><td className="font-semibold">{a.bidder}</td><td className="text-right font-mono">{a.quantity.toLocaleString("en-IN")}</td>
                <td className="text-right font-mono">{inr(a.unit_price, 2)}</td><td className="text-right font-mono">{inr(a.value, 2)}</td><td className="text-[0.8125rem]">{a.basis}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="px-4 py-2 text-[0.8125rem] text-slate-500">Decided by {ev.award.decided_by} on {ev.award.decided_at?.slice(0, 10)}{ev.award.remarks ? ` — ${ev.award.remarks}` : ""}. Recorded in the audit ledger.</div>
    </section>
  );
}
