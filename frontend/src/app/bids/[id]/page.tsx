"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Download, BadgeCheck, FileSearch, ListTodo, MessageCircleQuestion, ShieldAlert } from "lucide-react";
import { Badge, Button, Card, Disclaimer, ErrorBox, Loading, Stat } from "@/components/ui";
import { fileUrl, getBid, issuePassport, rerunBid } from "@/lib/api";
import { cn, STATUS_STYLE } from "@/lib/utils";
import { FileReadout, MatchPanel } from "@/components/market/match";

const ORDER = ["NON_COMPLIANT", "CONFLICTING_EVIDENCE", "MISSING_EVIDENCE", "NEEDS_CLARIFICATION", "CLAIMED_ONLY", "COMPLIANT", "DECLARATION"];

export default function BidPage() {
  const { id } = useParams() as { id: string };
  const router = useRouter();
  const [b, setB] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("all");
  const [open, setOpen] = useState<number | null>(null);
  useEffect(() => { getBid(id).then(setB).catch((e) => setErr(e.message)); }, [id]);
  if (err) return <div className="max-w-4xl mx-auto p-8"><ErrorBox error={err} /></div>;
  if (!b) return <Loading label="Mirroring bid…" />;
  const r = b.result;
  const rows = r.rows.filter((x: any) => filter === "all" || x.status === filter);
  const bad = r.verdict.includes("NON_RESPONSIVE");
  return (
    <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      <div className="flex flex-wrap items-start gap-4">
        <Link href="/bidder" className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-ink"><ArrowLeft className="w-4 h-4" /></Link>
        <div className="flex-1 min-w-[260px]">
          <div className="text-[0.8125rem] uppercase tracking-widest text-emerald-400 font-bold">Bid Mirror · evaluator's view</div>
          <h1 className="text-xl font-bold text-ink">{b.bidder} — {b.product_name || "offered product"}</h1>
          <div className="text-[0.8125rem] text-slate-400">Against: <Link className="underline" href={`/tenders/${b.tender_id}`}>{r.tender_title}</Link> · bid due {r.bid_due || "—"} · scope {r.scope_domains?.join(", ")} ({r.out_of_scope_requirements} out-of-scope requirements skipped)</div>
        </div>
        <Button variant="ghost" title="Re-evaluate the same evidence against the latest tender version (after corrigenda)" onClick={async () => setB(await rerunBid(id))}>Re-mirror vs latest tender</Button>
        <a href={fileUrl(`/bids/${id}/export/matrix.xlsx`)}><Button variant="ghost"><Download className="w-3.5 h-3.5" />Compliance matrix (.xlsx)</Button></a>
        <a href={fileUrl(`/bids/${id}/export/evidence-package.zip`)}><Button variant="ghost"><Download className="w-3.5 h-3.5" />Evidence package (.zip)</Button></a>
        <Button variant="success" onClick={async () => { const p = await issuePassport(id); router.push(`/passport/${p.id}`); }}><BadgeCheck className="w-3.5 h-3.5" />Issue Compliance Passport</Button>
      </div>

      <Card glow className={cn("flex flex-wrap items-center gap-6", bad ? "border-rose-500/40" : "border-emerald-500/40")}>
        <ShieldAlert className={cn("w-10 h-10", bad ? "text-rose-400" : "text-emerald-400")} />
        <div className="flex-1 min-w-[240px]">
          <div className={cn("text-lg font-extrabold tracking-wide", bad ? "text-rose-300" : "text-emerald-300")}>{r.verdict.replaceAll("_", " ")}</div>
          <p className="text-xs text-slate-400">Predicted outcome of technical evaluation if submitted as-is. Fix the items below before the bid due date.</p>
        </div>
        <Stat label="Compliance" value={`${Math.round(r.compliance_score)}%`} tone={r.compliance_score > 80 ? "good" : r.compliance_score > 50 ? "warn" : "bad"} />
        <Stat label="Non-compliant" value={r.counts.NON_COMPLIANT} tone={r.counts.NON_COMPLIANT ? "bad" : "good"} />
        <Stat label="Missing proof" value={r.counts.MISSING_EVIDENCE + r.counts.CLAIMED_ONLY} tone="warn" />
      </Card>
      {b.form?.score && (
        <div className="grid lg:grid-cols-[380px_1fr] gap-4">
          <MatchPanel score={b.form.score} compact />
          <Card className="p-4">
            <div className="text-sm font-bold text-ink mb-2">Submitted through the smart bid form</div>
            <p className="text-[0.8125rem] text-slate-400 mb-2">Typed answers + documents. The matrix below is the evaluator's evidence view of the same bid (datasheet claims vs licence vs NABL report).</p>
            <FileReadout files={b.form.files} />
          </Card>
        </div>
      )}
      {r.security_flags?.length > 0 && <ErrorBox error={`Suspicious embedded instructions detected in: ${r.security_flags.map((s: any) => s.file).join(", ")} — quarantined from AI processing.`} />}

      <div className="grid lg:grid-cols-[1fr_360px] gap-6">
        <Card className="p-0 overflow-hidden">
          <div className="flex flex-wrap gap-1.5 p-3 border-b border-slate-800">
            {["all", ...ORDER].map((s) => (
              <button key={s} onClick={() => setFilter(s)} className={cn("px-2 py-1 rounded-md text-[0.75rem] border font-semibold", filter === s ? "bg-sky-500/20 border-sky-500/50 text-sky-200" : "border-slate-700 text-slate-400")}>
                {s.replaceAll("_", " ")} {s !== "all" ? r.counts[s] : r.rows.length}
              </button>
            ))}
          </div>
          <div className="divide-y divide-slate-800 max-h-[70vh] overflow-auto">
            {rows.map((x: any, i: number) => {
              const best = (x.evidence || []).slice().sort((a: any, z: any) => (z.strength || 0) - (a.strength || 0))[0];
              return (
                <div key={i} className="p-3 hover:bg-slate-900/50 cursor-pointer" onClick={() => setOpen(open === i ? null : i)}>
                  <div className="grid grid-cols-[150px_60px_1fr_110px_1fr] gap-3 items-start text-xs">
                    <span className={cn("px-2 py-0.5 rounded border text-[0.75rem] font-bold text-center", STATUS_STYLE[x.status])}>{x.status.replaceAll("_", " ")}</span>
                    <span className="font-mono text-sky-300">Cl. {x.clause_key}</span>
                    <span className="text-slate-200">{x.parameter || x.requirement.slice(0, 70)}</span>
                    <span className="font-mono text-slate-400">{x.required || ""}</span>
                    <span className="text-slate-300">{best ? <>{best.raw_value || best.snippet?.slice(0, 50)} <span className="text-slate-500">· {best.doc_name} p.{best.page}</span></> : <span className="text-slate-400">—</span>}</span>
                  </div>
                  <div className="text-[0.8125rem] text-slate-400 mt-1 ml-[162px]">{x.explanation}</div>
                  {open === i && (
                    <div className="mt-2 ml-[162px] space-y-1">
                      <div className="text-[0.8125rem] text-slate-500">Tender text: “{x.requirement}”</div>
                      {(x.evidence || []).map((e: any, j: number) => (
                        <div key={j} className="text-[0.8125rem] rounded bg-slate-950/70 border border-slate-800 p-1.5"><FileSearch className="inline w-3 h-3 mr-1 text-sky-400" />{e.doc_name} · p.{e.page} · strength {e.strength} ({e.doc_type}) — <span className="font-mono text-slate-300">{e.snippet}</span></div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </Card>
        <div className="space-y-4">
          <Card>
            <div className="text-sm font-bold text-ink mb-2 flex items-center gap-2"><ListTodo className="w-4 h-4 text-amber-300" />Action items before submission</div>
            {r.action_items.map((a: string, i: number) => <div key={i} className="text-[0.8125rem] text-slate-300 py-1 border-b border-slate-800/60">☐ {a}</div>)}
          </Card>
          <Card>
            <div className="text-sm font-bold text-ink mb-2 flex items-center gap-2"><MessageCircleQuestion className="w-4 h-4 text-sky-300" />Raise at pre-bid meeting</div>
            {(r.suggested_prebid_questions || []).length === 0 ? <p className="text-[0.8125rem] text-slate-400">No clause-level ambiguities affecting your offer.</p> :
              r.suggested_prebid_questions.map((q: any) => <div key={q.id} className="text-[0.8125rem] text-slate-300 py-1">• Cl. {q.clause_key}: {q.question}</div>)}
          </Card>
          <Card>
            <div className="text-sm font-bold text-ink mb-2">Documents analysed</div>
            {r.documents.map((d: any) => (
              <div key={d.doc_name} className="text-[0.8125rem] py-1 border-b border-slate-800/60">
                <Badge className="border-slate-700 text-slate-300 mr-1">{d.doc_type}</Badge>{d.doc_name}
                <div className="text-slate-500 font-mono">{d.licence_no || d.lab || ""} {d.valid_to ? `valid to ${d.valid_to}` : ""} {d.report_date ? `report ${d.report_date}` : ""} · sha256 {d.sha256?.slice(0, 10)}</div>
              </div>
            ))}
          </Card>
          <Disclaimer>{r.disclaimer}</Disclaimer>
        </div>
      </div>
    </div>
  );
}
