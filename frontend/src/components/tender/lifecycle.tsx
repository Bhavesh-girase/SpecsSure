"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Download, FileLock2, Gavel, Lock, LockOpen, MessageSquareText, Scale, ShieldCheck, ShieldX, TriangleAlert, Unlock, XCircle } from "lucide-react";
import { Button, ErrorBox, Loading } from "@/components/ui";
import { Notice } from "@/components/gov-ui";
import { answerQuery, closeBidding, evaluation, fileUrl, listQueries, openFinancial, recordAward } from "@/lib/api";
import { inr } from "@/lib/prefs";

const RULE_CHIP: Record<string, string> = {
  technical: "bg-[#fdecec] text-[#8a1414] border-[#f1b0b0]", L1: "bg-[#eef4fb] text-[#1d4f93] border-[#adc8ea]",
  MII: "bg-[#fff4e0] text-[#8a5300] border-[#f2cf8c]", MSE: "bg-[#e7f5e9] text-[#0d6b06] border-[#9bd3a3]",
};

export function EvaluationPanel({ tenderId, onChanged }: { tenderId: string; onChanged?: () => void }) {
  const [ev, setEv] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const [remarks, setRemarks] = useState("Approved as proposed by the Tender Evaluation Committee");
  const load = () => evaluation(tenderId).then(setEv).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, [tenderId]); // eslint-disable-line react-hooks/exhaustive-deps
  const act = async (fn: () => Promise<any>) => { setErr(null); try { setEv(await fn()); onChanged?.(); } catch (e: any) { setErr(e.message); } };
  if (!ev) return err ? <ErrorBox error={err} /> : <Loading label="Preparing evaluation…" />;
  const open = ev.financial_open;
  return (
    <div className="space-y-5">
      <div className="bg-white border border-[#d5deea] rounded-lg p-4 shadow-card space-y-4">
        <div className="flex flex-wrap items-center gap-3 justify-between">
          <div className="text-[0.9375rem] text-slate-400">
            <b className="text-[#0f2748]">{ev.bids_received}</b> bid(s) received · estimated value <b className="text-[#0f2748]">{inr(ev.estimated_value)}</b> ·
            Make in India preference <b className="text-[#0f2748]">{ev.mii_applicable ? "applicable" : "not applicable (< ₹5 lakh)"}</b>
          </div>
          <div className="flex flex-wrap gap-2">
            {ev.stage === "published" && <Button variant="ghost" onClick={() => act(() => closeBidding(tenderId))}><FileLock2 className="w-3.5 h-3.5" />Close bidding</Button>}
            {(ev.stage === "published" || ev.stage === "bids_closed") && <Button onClick={() => act(() => openFinancial(tenderId))}><Unlock className="w-3.5 h-3.5" />Open financial bids</Button>}
            {ev.stage === "financial_opened" && (
              <>
                <input value={remarks} onChange={(e) => setRemarks(e.target.value)} aria-label="Committee remarks" className="w-80 max-w-full rounded-md border border-[#c9d5e6] px-2 py-1.5 text-[0.875rem]" />
                <Button variant="success" onClick={() => act(() => recordAward(tenderId, remarks))}><Gavel className="w-3.5 h-3.5" />Record award</Button>
              </>
            )}
            {open && <a href={fileUrl(`/tenders/${tenderId}/evaluation/report.pdf`)} target="_blank" rel="noreferrer"><Button variant="ghost"><Download className="w-3.5 h-3.5" />Evaluation report (PDF)</Button></a>}
          </div>
        </div>
        {err && <ErrorBox error={err} />}
      </div>

      {/* integrity */}
      <section className="bg-white border border-[#d5deea] rounded-lg shadow-card overflow-hidden">
        <div className="px-4 py-2.5 bg-[#0f2748] text-white text-[0.9375rem] font-bold flex items-center gap-2"><ShieldCheck className="w-4 h-4" />Sealed-bid integrity</div>
        <table className="gov-table">
          <thead><tr><th>Bidder</th><th>Price bid</th><th>Commitment check</th></tr></thead>
          <tbody>
            {ev.integrity.map((i: any) => (
              <tr key={i.bid_id}>
                <td className="font-semibold">{i.bidder}</td>
                <td>{i.sealed ? <span className="flex items-center gap-1"><Lock className="w-3.5 h-3.5 text-[#138808]" />sealed at submission</span> : <span className="text-slate-500">no price bid</span>}</td>
                <td>{!i.sealed ? "—" : !open ? <span className="text-slate-500">verified at opening</span>
                  : i.verified ? <span className="text-[#0d6b06] font-bold flex items-center gap-1"><CheckCircle2 className="w-3.5 h-3.5" />SHA-256 matches ledger</span>
                  : <span className="text-[#8a1414] font-bold flex items-center gap-1"><ShieldX className="w-3.5 h-3.5" />MISMATCH — price altered after sealing</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {ev.lines.map((l: any) => (
        <section key={l.index} className="bg-white border border-[#d5deea] rounded-lg shadow-card overflow-hidden">
          <div className="px-4 py-3 border-b border-[#e2e8f0] flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="text-[0.8125rem] font-mono text-slate-500">Item {l.index}</div>
              <h3 className="font-extrabold text-[#0f2748]">{l.label} — {Number(l.quantity).toLocaleString("en-IN")} {l.unit}</h3>
            </div>
            <div className="text-[0.875rem] text-slate-400">estimate {l.estimate_unit ? inr(l.estimate_unit, 2) : "—"} / {l.unit} · {l.divisible ? "divisible" : "non-divisible"}
              {l.contract_value ? <> · <b className="text-[#0f2748]">contract {inr(l.contract_value, 2)}</b></> : null}</div>
          </div>
          <div className="overflow-x-auto">
            <table className="gov-table">
              <thead><tr><th>Rank</th><th>Bidder</th><th>Technical</th><th className="text-right">Match</th><th>MSE</th><th>MII class</th><th className="text-right">Unit rate</th></tr></thead>
              <tbody>
                {l.bids.map((b: any) => (
                  <tr key={b.bid_id}>
                    <td className="font-bold">{b.rank || (b.responsive ? "—" : "×")}</td>
                    <td className="font-semibold">{b.bidder}</td>
                    <td>{b.responsive ? <span className="text-[#0d6b06] font-semibold">Responsive</span>
                      : <span className="text-[#8a1414] font-semibold" title={b.reasons.join("\n")}>Non-responsive<div className="text-[0.8125rem] font-normal text-slate-400 max-w-md">{b.reasons[0]}</div></span>}</td>
                    <td className="text-right font-mono">{b.match_index?.toFixed?.(1) ?? "—"}</td>
                    <td>{b.mse ? "Yes" : "No"}</td>
                    <td>{b.mii_class === "non-local" ? "Non-local" : `Class-${b.mii_class}`}{b.local_content != null ? ` (${b.local_content} %)` : ""}</td>
                    <td className="text-right font-mono">{b.unit_price == null ? <span className="text-slate-500 inline-flex items-center gap-1"><Lock className="w-3 h-3" />sealed</span> : inr(b.unit_price, 2)}</td>
                  </tr>
                ))}
                {!l.bids.length && <tr><td colSpan={7} className="text-center text-slate-500 py-4">No bid received for this item.</td></tr>}
              </tbody>
            </table>
          </div>
          {(l.steps.length > 0 || l.flags.length > 0) && (
            <div className="p-4 grid lg:grid-cols-2 gap-4">
              <div>
                <div className="text-[0.875rem] font-bold text-[#0f2748] mb-2 flex items-center gap-1"><Scale className="w-3.5 h-3.5" />Evaluation steps</div>
                <ol className="space-y-1.5">
                  {l.steps.map((s: any, i: number) => (
                    <li key={i} className="flex gap-2 text-[0.875rem] text-[#334155]">
                      <span className={`shrink-0 h-fit px-1.5 py-0.5 rounded-sm border text-[0.75rem] font-bold ${RULE_CHIP[s.step] || RULE_CHIP.L1}`}>{s.step}</span><span>{s.text}</span>
                    </li>
                  ))}
                  {!open && l.bids.some((b: any) => b.responsive) && <li className="text-[0.875rem] text-slate-500 flex items-center gap-1"><LockOpen className="w-3.5 h-3.5" />L1, Make in India and MSE steps run when the financial bids are opened.</li>}
                </ol>
                {l.flags.map((f: any, i: number) => <div key={i} className="mt-2"><Notice tone={f.level === "warn" ? "warn" : "info"}><TriangleAlert className="w-3.5 h-3.5 inline -mt-0.5 mr-1" />{f.text}</Notice></div>)}
              </div>
              {l.allocation.length > 0 && (
                <div>
                  <div className="text-[0.875rem] font-bold text-[#0f2748] mb-2 flex items-center gap-1"><Gavel className="w-3.5 h-3.5" />Proposed allocation</div>
                  <div className="space-y-2">
                    {l.allocation.map((a: any) => {
                      const pct = (a.quantity / l.quantity) * 100;
                      return (
                        <div key={a.bid_id} className="rounded-md border border-[#e2e8f0] p-2.5">
                          <div className="flex justify-between text-[0.875rem]"><b className="text-[#0f2748]">{a.bidder}</b><span className="font-mono">{inr(a.value, 2)}</span></div>
                          <div className="h-2 bg-[#eef2f7] rounded-full mt-1.5 overflow-hidden"><div className="h-full rounded-full" style={{ width: `${pct}%`, background: a.basis === "L1" ? "#1d4f93" : "#ff9933" }} /></div>
                          <div className="text-[0.8125rem] text-slate-500 mt-1">{Number(a.quantity).toLocaleString("en-IN")} {l.unit} ({pct.toFixed(0)} %) at {inr(a.unit_price, 2)} · {a.basis}</div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}
        </section>
      ))}

      {open && (
        <div className="bg-[#0f2748] text-white rounded-lg p-4 flex flex-wrap items-center justify-between gap-3">
          <div className="text-[0.9375rem]">Recommended contract value</div>
          <div className="text-2xl font-extrabold font-mono">{inr(ev.recommended_contract_value, 2)}</div>
        </div>
      )}
      <p className="text-[0.8125rem] text-slate-500">{ev.note} Sources: {Object.values(ev.rules || {}).map((r: any, i: number) => (
        <a key={i} href={r.source_url} target="_blank" rel="noreferrer" className="underline mr-2">{r.title}</a>
      ))}</p>
    </div>
  );
}

export function OfficerQueries({ tenderId, predicted, onChanged }: { tenderId: string; predicted: number; onChanged?: () => void }) {
  const [list, setList] = useState<any[] | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const load = () => listQueries(tenderId).then((l) => {
    setList(l);
    setDrafts((d) => ({ ...Object.fromEntries(l.map((q: any) => [q.qid, (q.final_response || q.draft_response || "").replace(/^DRAFT:\s*/, "")])), ...d }));
  }).catch(() => setList([]));
  useEffect(() => { load(); }, [tenderId]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!list) return <Loading label="Loading queries…" />;
  const pending = list.filter((q) => q.status === "received");
  return (
    <div className="space-y-4">
      <Notice tone="info"><MessageSquareText className="w-4 h-4 inline -mt-0.5 mr-1" />
        {list.length} query(ies) from bidders · {pending.length} awaiting reply. Each query is located to its clause, checked against earlier queries for duplicates,
        and a reply is drafted from the compiler’s findings. The compiler predicted {predicted} question(s) before publication (Pre-bid tab). Replies are published without the bidder’s identity.
      </Notice>
      {list.map((q) => (
        <article key={q.qid} className={`bg-white border rounded-lg shadow-card p-4 space-y-2 ${q.status === "received" ? "border-[#f2cf8c]" : "border-[#d5deea]"}`}>
          <div className="flex flex-wrap items-center gap-2 text-[0.8125rem]">
            <span className="font-mono font-bold text-[#0f2748]">{q.qid}</span>
            {q.clause_key && <span className="px-1.5 py-0.5 rounded-sm bg-[#eef4fb] text-[#1d4f93] font-bold">Clause {q.clause_key}</span>}
            <span className="text-slate-500">from {q.from || "—"} · {q.raised_at?.replace("T", " ")}</span>
            {q.duplicate_of && <span className="px-1.5 py-0.5 rounded-sm bg-[#fff4e0] text-[#8a5300] font-bold">similar to {q.duplicate_of}</span>}
            {q.predicted_id && <span className="px-1.5 py-0.5 rounded-sm bg-[#e7f5e9] text-[#0d6b06] font-bold">predicted ({q.predicted_id})</span>}
            <span className="flex-1" />
            <span className={`px-2 py-0.5 rounded-sm font-bold uppercase text-[0.75rem] ${q.status === "received" ? "bg-[#fff4e0] text-[#8a5300]" : q.status === "rejected" ? "bg-[#fdecec] text-[#8a1414]" : "bg-[#e7f5e9] text-[#0d6b06]"}`}>{q.status}</span>
          </div>
          <p className="text-[1rem] font-semibold text-[#0f2748]">{q.question}</p>
          <textarea rows={2} value={drafts[q.qid] ?? ""} onChange={(e) => setDrafts({ ...drafts, [q.qid]: e.target.value })} aria-label={`Reply to ${q.qid}`}
            className="w-full rounded-md border border-[#c9d5e6] p-2 text-[0.9375rem] outline-none focus:border-[#1d4f93]" />
          {q.status === "received" && q.draft_response && <div className="text-[0.8125rem] text-slate-500">Draft generated from the tender compiler’s evidence — edit before publishing.</div>}
          <div className="flex gap-2">
            <Button variant="success" onClick={async () => { await answerQuery(tenderId, q.qid, drafts[q.qid] || "", "published"); load(); onChanged?.(); }}><CheckCircle2 className="w-3.5 h-3.5" />Publish reply</Button>
            <Button variant="ghost" onClick={async () => { await answerQuery(tenderId, q.qid, drafts[q.qid] || "Not relevant to the tender.", "rejected"); load(); onChanged?.(); }}><XCircle className="w-3.5 h-3.5" />Reject</Button>
          </div>
        </article>
      ))}
      {!list.length && <div className="text-center text-[0.9375rem] text-slate-500 py-8 bg-white border border-dashed border-[#c9d5e6] rounded-lg">No queries from bidders yet.</div>}
    </div>
  );
}
