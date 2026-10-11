"use client";

import { useEffect, useState } from "react";
import { FlaskConical, Loader2, MapPin } from "lucide-react";
import { corpusLabs } from "@/lib/api";

/** Testing route: where the product can be tested for this standard (BIS LIMS snapshot), cheapest first. */
export function LabsPanel({ base, summary }: { base: string; summary?: any }) {
  const [open, setOpen] = useState(false);
  const [city, setCity] = useState("");
  const [d, setD] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (!open) return;
    setBusy(true);
    const t = setTimeout(() => corpusLabs(base, city || undefined).then(setD).catch(() => setD(null)).finally(() => setBusy(false)), city ? 300 : 0);
    return () => clearTimeout(t);
  }, [open, city, base]);
  if (!summary?.count) return null;
  return (
    <section>
      <h4 className="text-[0.875rem] font-bold uppercase tracking-wide text-slate-500 mb-1 flex items-center gap-1"><FlaskConical className="w-3.5 h-3.5" />Where to test</h4>
      <button onClick={() => setOpen(!open)} className="w-full text-left text-[0.875rem] border border-[#adc8ea] bg-[#eef4fb] rounded-md p-2 hover:bg-[#e3edf9]">
        <b className="text-[#13325d]">{summary.count} BIS / BIS-recognised labs</b> list test facilities for {base}
        {summary.min_charges ? <> · full test from <b>₹{Number(summary.min_charges).toLocaleString("en-IN")}</b></> : null}
        {summary.cities ? <> · {summary.cities} cities</> : null} <span className="text-[#1d4f93] underline">{open ? "hide" : "show labs"}</span>
      </button>
      {open && (
        <div className="mt-2 border border-[#e2e8f0] rounded-md">
          <div className="flex items-center gap-2 p-2 border-b border-[#eef2f7]">
            <MapPin className="w-3.5 h-3.5 text-slate-500" />
            <input value={city} onChange={(e) => setCity(e.target.value)} placeholder="Filter by city (e.g. Delhi, Chennai)" className="flex-1 border border-[#c9d5e6] rounded px-2 py-1 text-[0.875rem]" aria-label="Filter labs by city" />
            {busy && <Loader2 className="w-4 h-4 animate-spin text-slate-400" />}
          </div>
          <table className="w-full text-[0.875rem]">
            <thead><tr className="text-left text-slate-500"><th className="p-1.5">Laboratory</th><th className="p-1.5">City</th><th className="p-1.5 text-right">Charges*</th><th className="p-1.5 text-right">Clauses</th></tr></thead>
            <tbody>
              {(d?.labs || []).slice(0, 12).map((l: any, i: number) => (
                <tr key={i} className="border-t border-[#eef2f7]">
                  <td className="p-1.5"><b className="text-[#0f2748]">{l.lab}</b>{l.scope && <div className="text-[0.8125rem] text-slate-500">scope: {l.scope}</div>}</td>
                  <td className="p-1.5">{l.city || "—"}</td>
                  <td className="p-1.5 text-right font-mono">{l.charges_total ? `₹${Number(l.charges_total).toLocaleString("en-IN")}` : "—"}</td>
                  <td className="p-1.5 text-right font-mono">{l.clauses_tested ?? "—"}</td>
                </tr>))}
              {d && !d.labs?.length && <tr><td colSpan={4} className="p-2 text-slate-500">No lab in that city in our snapshot.</td></tr>}
            </tbody>
          </table>
          {d?.tests_seen?.length > 0 && <div className="p-2 text-[0.8125rem] text-slate-400 border-t border-[#eef2f7]"><b>Tests labs list for this standard:</b> {d.tests_seen.slice(0, 8).join(" · ")}</div>}
          <p className="p-2 text-[0.8125rem] text-slate-500 border-t border-[#eef2f7]">*Full-test charges excl. taxes as listed on <a className="underline" href="https://lims.bis.gov.in/home/search_is_number/" target="_blank" rel="noreferrer">BIS LIMS</a> ({d?.meta?.fetched}); confirm with the lab.</p>
        </div>
      )}
    </section>
  );
}
