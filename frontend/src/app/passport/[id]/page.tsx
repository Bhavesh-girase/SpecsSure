"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { BadgeCheck, ShieldX, KeyRound, QrCode, FileJson } from "lucide-react";
import { Badge, Button, Card, ErrorBox, Loading } from "@/components/ui";
import { getPassport, verifyCredential } from "@/lib/api";
import { cn, STATUS_STYLE } from "@/lib/utils";

export default function PassportPage() {
  const { id } = useParams() as { id: string };
  const [p, setP] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const [paste, setPaste] = useState("");
  const [check, setCheck] = useState<any>(null);
  useEffect(() => { getPassport(id).then(setP).catch((e) => setErr(e.message)); }, [id]);
  if (err) return <div className="max-w-4xl mx-auto p-8"><ErrorBox error={err} /></div>;
  if (!p) return <Loading />;
  const vc = p.credential;
  const s = vc.credentialSubject;
  const ok = p.verification.verified && !p.verification.revoked;
  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      <Card glow className={cn("flex flex-wrap items-center gap-6", ok ? "border-emerald-500/40" : "border-rose-500/40")}>
        {ok ? <BadgeCheck className="w-12 h-12 text-emerald-400" /> : <ShieldX className="w-12 h-12 text-rose-400" />}
        <div className="flex-1 min-w-[260px]">
          <div className="text-[0.8125rem] uppercase tracking-widest text-emerald-400 font-bold">Product Compliance Passport · W3C Verifiable Credential 2.0</div>
          <h1 className="text-xl font-bold text-ink">{s.product?.name} — {s.product?.manufacturer}</h1>
          <div className="text-[0.8125rem] text-slate-400 font-mono break-all">{vc.id}</div>
          <div className="flex flex-wrap gap-2 mt-2">
            <Badge className={ok ? "border-emerald-500/50 text-emerald-300" : "border-rose-500/50 text-rose-300"}>{ok ? "signature verified" : "NOT verified"}</Badge>
            <Badge className="border-slate-700 text-slate-300"><KeyRound className="w-3 h-3" />{vc.proof.cryptosuite} · Ed25519</Badge>
            <Badge className="border-slate-700 text-slate-300">valid until {vc.validUntil?.slice(0, 10) || "—"}</Badge>
            {p.verification.expired && <Badge className="border-rose-500/50 text-rose-300">expired</Badge>}
          </div>
        </div>
        {p.qr && <div className="text-center"><img src={p.qr} alt="verification QR" className="w-32 h-32 rounded-lg bg-white p-1" /><div className="text-[0.75rem] text-slate-500 mt-1 flex items-center gap-1 justify-center"><QrCode className="w-3 h-3" />scan to verify</div></div>}
      </Card>
      <div className="grid lg:grid-cols-2 gap-6">
        <Card>
          <div className="text-sm font-bold text-ink mb-2">Identity, standards & certification</div>
          <div className="text-xs text-slate-300 space-y-1">
            <div>Applicable standards: <b className="font-mono text-emerald-300">{(s.applicableStandards || []).join(", ")}</b></div>
            <div>BIS licence: <b className="font-mono">{s.certification?.licenceNumber || "—"}</b> · grade {s.certification?.grade || "—"} · valid until {s.certification?.validUntil || "—"} · {s.certification?.status || ""}</div>
            <div className="text-[0.8125rem] text-slate-500">{s.certification?.verificationNote}</div>
            <div>Laboratory: {s.laboratory?.name || "—"} ({s.laboratory?.accreditation || "—"}) · report {s.laboratory?.reportNo} dated {s.laboratory?.reportDate}</div>
            <div>Issuer: <span className="font-mono text-[0.75rem] break-all">{vc.issuer.id}</span> — {vc.issuer.name}</div>
          </div>
          <div className="text-sm font-bold text-ink mt-4 mb-2">Evidence bundle (SHA-256)</div>
          {(s.evidenceBundle || []).map((e: any) => <div key={e.file} className="text-[0.8125rem] font-mono text-slate-400 truncate">{e.file} · {e.sha256}</div>)}
        </Card>
        <Card>
          <div className="text-sm font-bold text-ink mb-2">Test results & deviations</div>
          {(s.testResults || []).map((t: any, i: number) => (
            <div key={i} className="grid grid-cols-[1fr_90px_90px_130px] gap-2 text-[0.8125rem] py-1 border-b border-slate-800/60">
              <span className="text-slate-300">{t.parameter}</span><span className="font-mono text-ink">{t.value}</span><span className="font-mono text-slate-500">{t.requirement}</span>
              <span className={cn("px-1.5 rounded border text-[0.75rem] text-center", STATUS_STYLE[t.status])}>{t.status.replaceAll("_", " ")}</span>
            </div>
          ))}
          {(s.deviationHistory || []).length > 0 && <div className="mt-3 text-[0.8125rem] text-rose-300">{s.deviationHistory.map((d: any, i: number) => <div key={i}>⚠ Cl.{d.clause} {d.parameter}: {d.detail}</div>)}</div>}
          <div className="text-[0.8125rem] text-slate-400 mt-3">Tender linkage: {(s.tenderLinkage || []).map((t: any) => `${t.tender} (${t.verdict}, ${t.compliance_score}%)`).join("; ")}</div>
        </Card>
      </div>
      <Card>
        <div className="text-sm font-bold text-ink mb-2 flex items-center gap-2"><FileJson className="w-4 h-4 text-sky-400" />Verify any passport (paste credential JSON — try changing one value)</div>
        <textarea value={paste} onChange={(e) => setPaste(e.target.value)} placeholder="Paste a credential…" className="w-full h-28 bg-slate-950 border border-slate-700 rounded-lg p-2 text-[0.8125rem] font-mono" />
        <div className="flex gap-2 mt-2">
          <Button variant="ghost" onClick={() => setPaste(JSON.stringify(vc, null, 2))}>Load this credential</Button>
          <Button onClick={async () => { try { setCheck(await verifyCredential(JSON.parse(paste))); } catch (e: any) { setCheck({ verified: false, error: e.message }); } }}>Verify signature</Button>
          {check && <span className={cn("text-xs self-center", check.verified ? "text-emerald-300" : "text-rose-300")}>{check.verified ? "✓ valid Ed25519 Data Integrity proof" : `✗ ${check.error || "invalid"}`}</span>}
        </div>
        <details className="mt-3"><summary className="text-[0.8125rem] text-slate-400 cursor-pointer">Raw credential</summary><pre className="text-[0.75rem] text-slate-300 whitespace-pre-wrap mt-2">{JSON.stringify(vc, null, 2)}</pre></details>
      </Card>
    </div>
  );
}
