"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Briefcase, FileUp, ArrowRight, Sparkles } from "lucide-react";
import { Button, Card, ErrorBox, SectionTitle, Badge } from "@/components/ui";
import { PageIntro } from "@/components/gov-ui";
import { createBid, listBids, listTenders, demoIds, fileUrl } from "@/lib/api";

function BidderInner() {
  const router = useRouter();
  const qs = useSearchParams();
  const [tenders, setTenders] = useState<any[]>([]);
  const [bids, setBids] = useState<any[]>([]);
  const [tenderId, setTenderId] = useState(qs.get("tender") || "");
  const [tenderFile, setTenderFile] = useState<File | null>(null);
  const [bidder, setBidder] = useState("");
  const [product, setProduct] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [demo, setDemo] = useState<any>(null);
  useEffect(() => {
    listTenders().then((t) => { setTenders(t); if (!tenderId && t[0]) setTenderId(t[0].id); }).catch(() => {});
    listBids().then(setBids).catch(() => {});
    demoIds().then(setDemo).catch(() => {});
  }, []);
  const submit = async () => {
    setErr(null);
    const fd = new FormData();
    fd.append("bidder", bidder || "My company");
    if (product) fd.append("product_name", product);
    if (tenderFile) fd.append("tender_file", tenderFile); else fd.append("tender_id", tenderId);
    files.forEach((f) => fd.append("files", f));
    try { const r = await createBid(fd); router.push(`/bids/${r.id}`); } catch (e: any) { setErr(e.message); }
  };
  return (
    <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-8">
      <PageIntro icon={Briefcase} kicker="Bid Mirror · for bidders" title="Check your documents against a tender — before you bid"
        sub="See your bid the way the evaluator will. SpecSure reads your datasheets, BIS licence and NABL test reports and shows, for every tender requirement, the document and page that proves it — or tells you what is missing, what does not comply, and what to ask at the pre-bid meeting."
        steps={["Enter your firm name and product.", "Choose the tender (or upload your copy of it).", "Upload your datasheets, licences and test reports.", "Press “Mirror my bid” and review the requirement-by-requirement result."]} />
      <ErrorBox error={err} />
      <div className="grid lg:grid-cols-[1fr_420px] gap-6">
        <div className="space-y-3">
          <div className="text-xs uppercase tracking-widest text-slate-500 font-bold">Recent bid mirrors</div>
          {bids.length === 0 && <Card className="text-sm text-slate-400">No bids yet.</Card>}
          {bids.map((b) => (
            <Link key={b.id} href={`/bids/${b.id}`} className="block">
              <Card className="hover:border-emerald-500/40 flex items-center gap-3">
                <div className="flex-1"><div className="text-sm font-bold text-ink">{b.bidder} — {b.product_name || "product"}</div><div className="text-[0.8125rem] text-slate-400">tender {b.tender_id} · {b.created_at?.slice(0, 16).replace("T", " ")}</div></div>
                <Badge className="border-slate-700 text-slate-300">{b.verdict?.replaceAll("_", " ")}</Badge>
                <div className="text-xl font-mono text-ink w-16 text-right">{Math.round(b.compliance_score)}%</div>
                <ArrowRight className="w-4 h-4 text-slate-500" />
              </Card>
            </Link>
          ))}
          {demo && (
            <Card className="border-violet-500/30">
              <div className="text-sm font-bold text-ink flex items-center gap-2"><Sparkles className="w-4 h-4 text-violet-300" />Try with the demo evidence set</div>
              <p className="text-[0.8125rem] text-slate-400 mb-2">Download the fictional bidder documents and upload them against the demo tender:</p>
              <div className="flex flex-wrap gap-2">
                {["bidder/datasheet_arya_tmt.txt", "bidder/licence_arya_tmt.txt", "bidder/test_report_arya_tmt.txt", "tender_phc_building.txt", "corrigendum_1.txt", "corrigendum_2.txt"].map((f) => (
                  <a key={f} className="text-[0.8125rem] text-sky-300 underline" href={fileUrl(`/demo/files/${f}`)}>{f.split("/").pop()}</a>
                ))}
              </div>
            </Card>
          )}
        </div>
        <Card glow className="h-fit space-y-3">
          <div className="text-sm font-bold text-ink">New Bid Mirror</div>
          <label className="block text-[0.875rem] font-semibold text-ink">Your firm name
            <input value={bidder} onChange={(e) => setBidder(e.target.value)} placeholder="e.g. Arya Rebar Ltd" className="mt-1 w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm font-normal" />
          </label>
          <label className="block text-[0.875rem] font-semibold text-ink">Product you are offering
            <input value={product} onChange={(e) => setProduct(e.target.value)} placeholder="e.g. TMT Fe 500D" className="mt-1 w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm font-normal" />
          </label>
          <div className="text-[0.8125rem] text-slate-400">Tender</div>
          <select value={tenderId} onChange={(e) => setTenderId(e.target.value)} disabled={!!tenderFile} className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2 py-2 text-xs">
            {tenders.map((t) => <option key={t.id} value={t.id}>{t.title}</option>)}
          </select>
          <label className="text-[0.8125rem] text-slate-400 block">…or upload your copy of the tender <input type="file" className="block mt-1 text-xs" onChange={(e) => setTenderFile(e.target.files?.[0] || null)} /></label>
          <label className="block rounded-xl border border-dashed border-slate-700 p-4 text-center cursor-pointer hover:border-emerald-500/50">
            <FileUp className="w-5 h-5 text-emerald-400 mx-auto mb-1" />
            <span className="text-xs text-slate-300">Datasheets, BIS licence, NABL test reports, certificates (PDF / DOCX / image / TXT)</span>
            <input type="file" multiple className="hidden" onChange={(e) => setFiles(Array.from(e.target.files || []))} />
          </label>
          {files.map((f) => <div key={f.name} className="text-[0.8125rem] text-slate-300">· {f.name}</div>)}
          <Button className="w-full" variant="success" disabled={!files.length || (!tenderId && !tenderFile)} onClick={submit}>Mirror my bid</Button>
        </Card>
      </div>
    </div>
  );
}

export default function BidderPage() {
  return <Suspense><BidderInner /></Suspense>;
}
