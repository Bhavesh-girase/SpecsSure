"use client";

import { useEffect, useState } from "react";
import { Link2, ShieldCheck, ShieldX } from "lucide-react";
import { Button, Card, SectionTitle } from "@/components/ui";
import { ledger, ledgerVerify } from "@/lib/api";

export default function LedgerPage() {
  const [rows, setRows] = useState<any[]>([]);
  const [v, setV] = useState<any>(null);
  useEffect(() => { ledger().then(setRows); ledgerVerify().then(setV); }, []);
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      <SectionTitle icon={<Link2 className="w-5 h-5 text-sky-400" />} title="Tamper-evident audit ledger"
        subtitle="Every compile (with document hashes, knowledge-base snapshot hash and engine version), review decision, clarification, corrigendum, regulatory event and passport is appended to a SHA-256 hash chain. Editing any past entry breaks every later hash."
        right={<Button onClick={async () => setV(await ledgerVerify())}>Verify chain</Button>} />
      {v && (
        <Card className={v.valid ? "border-emerald-500/40" : "border-rose-500/40"}>
          <div className="flex items-center gap-3 text-sm">
            {v.valid ? <ShieldCheck className="w-6 h-6 text-emerald-400" /> : <ShieldX className="w-6 h-6 text-rose-400" />}
            {v.valid ? <span className="text-emerald-300">Chain intact — {v.entries} entries. Head: <span className="font-mono text-xs">{v.head}</span></span>
              : <span className="text-rose-300">Chain BROKEN at #{v.broken_at}: {v.reason}</span>}
          </div>
        </Card>
      )}
      <Card className="p-0 overflow-hidden">
        <div className="divide-y divide-slate-800 max-h-[70vh] overflow-auto">
          {rows.map((e) => (
            <details key={e.seq} className="px-4 py-2">
              <summary className="grid grid-cols-[60px_170px_190px_1fr_150px] gap-3 text-xs cursor-pointer">
                <span className="font-mono text-slate-500">#{e.seq}</span><span className="text-slate-400">{e.ts.slice(0, 19).replace("T", " ")}</span>
                <span className="text-sky-300">{e.action}</span><span className="text-slate-300 truncate">{e.actor} → {e.subject_type}:{e.subject_id}</span>
                <span className="font-mono text-[0.75rem] text-slate-500 truncate">{e.entry_hash}</span>
              </summary>
              <pre className="text-[0.75rem] text-slate-400 mt-2 whitespace-pre-wrap">prev: {e.prev_hash}{"\n"}payload_hash: {e.payload_hash}{"\n"}{JSON.stringify(e.payload, null, 1)}</pre>
            </details>
          ))}
        </div>
      </Card>
    </div>
  );
}
