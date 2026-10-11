"use client";

import { useState } from "react";
import { MessageCircleQuestion, History, Send, BookOpen } from "lucide-react";
import { Badge, Bar, Button, Card, Empty, SevBadge } from "@/components/ui";
import { prebidDecision, prebidPropagate } from "@/lib/api";

export function Prebid({ twin, tenderId, onChanged }: { twin: any; tenderId: string; onChanged: () => void }) {
  const [edit, setEdit] = useState<Record<string, string>>({});
  const [draft, setDraft] = useState<any>(null);
  const approved = (twin.prebid || []).filter((p: any) => ["approved", "published"].includes(p.status)).length;
  return (
    <div className="space-y-6">
      <Card glow className="flex flex-wrap items-center gap-4">
        <MessageCircleQuestion className="w-7 h-7 text-sky-300" />
        <div className="flex-1 min-w-[260px]">
          <div className="text-sm font-bold text-ink">Pre-bid question prediction</div>
          <p className="text-[0.8125rem] text-slate-400">Questions bidders are likely to ask — predicted before publication from the compiler’s findings and from institutional memory (how often similar wording drew queries in past tenders). Each draft answer is linked to evidence and needs committee approval.</p>
        </div>
        <Button variant="success" disabled={!approved} onClick={async () => setDraft((await prebidPropagate(tenderId, false)).draft)}><Send className="w-3.5 h-3.5" />Propagate {approved} approved → corrigendum</Button>
      </Card>
      {draft && (
        <Card>
          <div className="flex justify-between mb-2"><div className="text-sm font-bold text-ink">Draft corrigendum from approved clarifications</div>
            <div className="flex gap-2"><Button variant="ghost" onClick={() => setDraft(null)}>Close</Button><Button variant="success" onClick={async () => { await prebidPropagate(tenderId, true); setDraft(null); onChanged(); }}>Issue & re-compile</Button></div></div>
          <pre className="text-[0.8125rem] whitespace-pre-wrap bg-slate-950/70 border border-slate-800 rounded-lg p-3">{draft.text}</pre>
        </Card>
      )}
      {(twin.prebid || []).length === 0 ? <Empty>No likely questions — the tender is clear.</Empty> : (
        <div className="space-y-3">
          {twin.prebid.map((p: any) => (
            <Card key={p.id} className="p-4">
              <div className="flex flex-wrap items-center gap-2 mb-2">
                <SevBadge sev={p.severity} />
                <span className="font-mono text-[0.75rem] text-slate-400">{p.rule_id} · Cl. {p.clause_key ?? "—"}</span>
                <Badge className={p.status === "approved" ? "border-emerald-500/40 text-emerald-300" : p.status === "rejected" ? "border-slate-600 text-slate-400" : "border-sky-500/40 text-sky-300"}>{p.status}</Badge>
                <div className="ml-auto flex items-center gap-2 w-44"><span className="text-[0.75rem] text-slate-400">likelihood</span><Bar value={p.likelihood * 100} tone="bg-sky-500" /><span className="font-mono text-[0.8125rem] text-ink">{Math.round(p.likelihood * 100)}%</span></div>
              </div>
              <div className="text-sm text-ink">“{p.question}”</div>
              <div className="text-[0.8125rem] text-slate-500 mt-1">{p.rationale}</div>
              {p.precedents?.length > 0 && (
                <div className="mt-2 rounded-lg bg-violet-500/5 border border-violet-500/20 p-2 text-[0.8125rem]">
                  <div className="text-violet-300 flex items-center gap-1 mb-1"><History className="w-3 h-3" />Institutional memory</div>
                  {p.precedents.map((h: any, i: number) => (
                    <div key={i} className="text-slate-300">{h.tender_ref} Cl.{h.clause_key} (similarity {h.score}) asked: <i>“{h.prebid_questions[0]}”</i>{h.resolution ? <span className="text-slate-500"> → {h.resolution}</span> : null}</div>
                  ))}
                </div>
              )}
              <textarea value={edit[p.id] ?? p.final_response ?? p.draft_response} onChange={(e) => setEdit({ ...edit, [p.id]: e.target.value })}
                className="w-full mt-3 bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200 h-16" />
              <div className="flex gap-2 mt-2">
                <Button variant="success" onClick={async () => { await prebidDecision(tenderId, p.id, "approved", edit[p.id] ?? p.draft_response); onChanged(); }}>Approve response</Button>
                <Button variant="ghost" onClick={async () => { await prebidDecision(tenderId, p.id, "rejected"); onChanged(); }}>Reject</Button>
              </div>
            </Card>
          ))}
        </div>
      )}
      {(twin.prebid_received || []).length > 0 && (
        <Card>
          <div className="text-sm font-bold text-ink mb-2">Received pre-bid queries (parsed & linked to clauses)</div>
          {twin.prebid_received.map((q: any) => (
            <div key={q.id} className="text-xs border-b border-slate-800 py-2"><span className="font-mono text-sky-300 mr-2">Cl.{q.clause_key || "?"}</span>{q.question}{q.final_response && <div className="text-emerald-300 mt-0.5">↳ {q.final_response}</div>}</div>
          ))}
        </Card>
      )}
    </div>
  );
}

export function Memory({ twin }: { twin: any }) {
  const m = twin.memory || {};
  return (
    <div className="grid lg:grid-cols-2 gap-6">
      <Card>
        <div className="text-sm font-bold text-ink mb-3 flex items-center gap-2"><BookOpen className="w-4 h-4 text-violet-300" />Similar historical tenders</div>
        {(m.similar_tenders || []).map((t: any) => (
          <div key={t.ref} className="border-b border-slate-800 py-2 text-xs">
            <div className="flex justify-between"><span className="text-ink">{t.title}</span><span className="font-mono text-slate-500">{t.score}</span></div>
            <div className="text-slate-400">{t.ref} · {t.year} — {t.outcome}</div>
          </div>
        ))}
      </Card>
      <Card>
        <div className="text-sm font-bold text-ink mb-3">Recurring issue patterns across the department</div>
        {(m.recurring_patterns || []).map((p: any) => (
          <div key={p.rule_id} className="flex items-center gap-3 text-xs py-1">
            <span className="font-mono text-sky-300 w-24">{p.rule_id}</span>
            <Bar value={p.occurrences} max={Math.max(...m.recurring_patterns.map((x: any) => x.occurrences))} tone="bg-violet-500" />
            <span className="text-slate-400 w-40 text-right">{p.occurrences}× · {p.prebid_questions_generated} queries</span>
          </div>
        ))}
      </Card>
      <Card className="lg:col-span-2">
        <div className="text-sm font-bold text-ink mb-3">Clause precedents (flagged clauses that look like past problem clauses)</div>
        {Object.keys(m.clause_precedents || {}).length === 0 ? <p className="text-xs text-slate-400">No close precedents.</p> :
          Object.entries(m.clause_precedents).map(([k, hits]: any) => (
            <div key={k} className="mb-3">
              <div className="font-mono text-xs text-sky-300">Clause {k}</div>
              {hits.map((h: any, i: number) => (
                <div key={i} className="text-[0.8125rem] text-slate-300 ml-3">≈ {h.tender_ref} Cl.{h.clause_key} ({h.score}): “{h.text}” — issues {h.issues.join(", ") || "none"}{h.resolution ? ` — resolved by: ${h.resolution}` : ""}</div>
              ))}
            </div>
          ))}
      </Card>
    </div>
  );
}
