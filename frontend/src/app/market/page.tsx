"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Store, CalendarClock, Users, Wand2, ArrowRight, ShieldCheck } from "lucide-react";
import { Badge, Card, Empty, ErrorBox, Loading, Disclaimer } from "@/components/ui";
import { marketTenders } from "@/lib/api";
import { cn, gateStyle } from "@/lib/utils";
import { PageIntro } from "@/components/gov-ui";

export default function MarketPage() {
  const [rows, setRows] = useState<any[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { marketTenders().then(setRows).catch((e) => setErr(e.message)); }, []);
  return (
    <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      <PageIntro icon={Store} kicker="Open tenders · for bidders" title="Tenders open for bidding"
        sub="Pick a tender to open its bid form. The form is built from the latest version of the tender (corrigenda included). Upload your datasheet, BIS licence and test report — even a phone photo — and SpecSure fills in the values, checks each one against the clause, and shows your match score before you submit."
        steps={["Choose a tender below.", "Upload your documents — the form fills itself.", "Fix anything marked missing, then submit a sealed bid."]} />
      <ErrorBox error={err} />
      {!rows ? <Loading /> : rows.length === 0 ? <Empty>No published tenders yet — publish one from the <Link className="underline" href="/studio">Tender Studio</Link>.</Empty> : (
        <div className="grid md:grid-cols-2 gap-4">
          {rows.map((t) => (
            <Card key={t.id} className="flex flex-col gap-2 hover:border-emerald-500/40 transition-colors">
              <div className="flex items-start gap-2">
                <div className="flex-1">
                  <div className="text-[0.75rem] font-mono text-slate-500">{t.reference_no || t.id}</div>
                  <div className="text-sm font-bold text-ink leading-snug">{t.title}</div>
                  <div className="text-[0.8125rem] text-slate-400">{t.organisation}</div>
                </div>
                {t.generated && <Badge className="border-sky-500/40 text-sky-300"><Wand2 className="w-3 h-3" /> Studio</Badge>}
              </div>
              {t.items?.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {t.items.map((i: any, k: number) => <span key={k} className="text-[0.8125rem] px-2 py-0.5 rounded-full bg-slate-900 border border-slate-700 text-slate-300">{i.label.split("(")[0]} · {i.quantity} {i.unit}</span>)}
                </div>
              )}
              <div className="flex flex-wrap items-center gap-3 text-[0.8125rem] text-slate-400">
                <span className="flex items-center gap-1"><CalendarClock className="w-3.5 h-3.5" /> due {t.bid_due || "—"}</span>
                <span className="flex items-center gap-1"><Users className="w-3.5 h-3.5" /> {t.bids} bid(s)</span>
                <span>{t.requirements} requirements</span>
                <span className={cn("px-2 py-0.5 rounded-full border text-[0.75rem] font-bold", gateStyle(t.gate))}><ShieldCheck className="w-3 h-3 inline" /> tender quality {Math.round(t.readiness || 0)}</span>
              </div>
              <div className="flex gap-2 mt-1">
                <Link href={`/market/${t.id}`} className="flex-1 text-center px-3 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold flex items-center justify-center gap-1">Prepare bid <ArrowRight className="w-3.5 h-3.5" /></Link>
                <Link href={`/tenders/${t.id}?tab=bids`} className="px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-slate-300 text-xs">Buyer view</Link>
              </div>
            </Card>
          ))}
        </div>
      )}
      <Disclaimer />
    </div>
  );
}
