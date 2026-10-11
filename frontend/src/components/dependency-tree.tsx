"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { corpusDependencyTree } from "@/lib/api";

const TONE: Record<string, string> = {
  root: "#0f2748", test_method: "#1d4f93", terminology: "#6d28d9", safety: "#c0262d", installation: "#b45309", sampling: "#0e7490",
  packaging_marking: "#64748b", material: "#047857", dimensions: "#7c3aed", allied_product: "#334155",
};
const LABEL: Record<string, string> = {
  test_method: "test method", terminology: "terminology", safety: "safety", installation: "installation", sampling: "sampling",
  packaging_marking: "packing / marking", material: "material", dimensions: "dimensions", allied_product: "normative reference",
};
const COL_W = 250, ROW_H = 30, MAX_PER_COL = 22;

/** Compliance tree: everything a tender pulls in by citing `base` — its normative references, their references, … */
export function DependencyTree({ base }: { base: string }) {
  const [depth, setDepth] = useState(2);
  const [d, setD] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    setBusy(true);
    corpusDependencyTree(base, depth).then(setD).catch(() => setD(null)).finally(() => setBusy(false));
  }, [base, depth]);

  const cols: any[][] = [];
  for (const n of d?.nodes || []) (cols[n.depth] ||= []).push(n);
  const shown = cols.map((c) => c.slice(0, MAX_PER_COL));
  const pos: Record<string, { x: number; y: number }> = {};
  const H = Math.max(3, ...shown.map((c) => c.length)) * ROW_H + 20;
  shown.forEach((c, i) => c.forEach((n, j) => {
    const off = (H - c.length * ROW_H) / 2;
    pos[n.base] = { x: 10 + i * COL_W, y: off + j * ROW_H + ROW_H / 2 };
  }));
  const W = Math.max(1, shown.length) * COL_W + 20;
  const kinds = Array.from(new Set((d?.nodes || []).filter((n: any) => n.depth > 0).map((n: any) => n.kind)));

  return (
    <figure className="bg-white border border-[#d5deea] rounded-lg p-3">
      <div className="flex flex-wrap items-center gap-2 mb-2">
        <span className="text-[0.875rem] font-bold text-[#0f2748]">Compliance tree</span>
        <span className="text-[0.8125rem] text-slate-500">what a supplier must satisfy when the tender cites {base}</span>
        <div className="ml-auto flex items-center gap-1 text-[0.875rem]">
          depth
          {[1, 2, 3].map((k) => (
            <button key={k} onClick={() => setDepth(k)} aria-pressed={depth === k}
              className={`w-7 h-7 rounded border font-bold ${depth === k ? "bg-[#0f2748] text-white border-[#0f2748]" : "border-[#c9d5e6] text-[#0f2748]"}`}>{k}</button>
          ))}
          {busy && <Loader2 className="w-4 h-4 animate-spin text-slate-400" />}
        </div>
      </div>
      {d && (
        <>
          <div className="flex flex-wrap gap-3 text-[0.8125rem] text-slate-400 mb-1">
            <span><b className="text-[#0f2748]">{d.counts.nodes}</b> standards pulled in</span>
            {Object.entries(d.counts.by_depth).filter(([k]) => k !== "0").map(([k, v]) => <span key={k}>level {k}: <b>{v as number}</b></span>)}
            {d.counts.withdrawn > 0 && <span className="text-[#8a1414] font-bold">{d.counts.withdrawn} withdrawn (replacement shown)</span>}
          </div>
          <div className="overflow-x-auto">
            <svg width={W} height={H} role="img" aria-label={`Compliance tree of ${base}`}>
              {d.edges.filter((e: any) => pos[e.from] && pos[e.to]).map((e: any, i: number) => {
                const a = pos[e.from], b = pos[e.to];
                const x1 = a.x + 200, x2 = b.x, mx = (x1 + x2) / 2;
                return <path key={i} d={`M${x1},${a.y} C${mx},${a.y} ${mx},${b.y} ${x2},${b.y}`} fill="none" stroke={TONE[e.kind] || "#94a3b8"} strokeOpacity={0.35} strokeWidth={1.2} />;
              })}
              {shown.flat().map((n: any) => {
                const p = pos[n.base];
                const tone = TONE[n.kind] || "#334155";
                const withdrawn = n.status === "Withdrawn";
                return (
                  <Link key={n.base} href={`/recommend?q=${encodeURIComponent(n.base + " " + (n.title || ""))}`}>
                    <g className="cursor-pointer">
                      <title>{`${n.base} — ${n.title || ""}${n.edition_in_force ? ` · in force: ${n.edition_in_force}` : ""}${withdrawn ? ` · WITHDRAWN → ${n.replacement || "?"}` : ""}`}</title>
                      <rect x={p.x} y={p.y - 11} width={200} height={22} rx={5} fill={n.depth === 0 ? "#0f2748" : withdrawn ? "#fdecec" : "#fff"}
                        stroke={withdrawn ? "#c0262d" : tone} strokeWidth={1.3} strokeDasharray={withdrawn ? "3 2" : undefined} />
                      <text x={p.x + 7} y={p.y + 4} fontSize="10.5" fontWeight="700" fill={n.depth === 0 ? "#fff" : tone} fontFamily="JetBrains Mono, monospace">
                        {n.base.length > 17 ? n.base.slice(0, 16) + "…" : n.base}
                      </text>
                      <text x={p.x + 118} y={p.y + 4} fontSize="9.5" fill={n.depth === 0 ? "#cbd5e1" : "#64748b"}>
                        {withdrawn ? "withdrawn" : (n.title || "").slice(0, 14)}
                      </text>
                    </g>
                  </Link>
                );
              })}
            </svg>
          </div>
          {cols.some((c) => c.length > MAX_PER_COL) && <p className="text-[0.8125rem] text-slate-500">Showing {MAX_PER_COL} per level; {d.counts.nodes} in total.</p>}
          <figcaption className="flex flex-wrap gap-x-3 gap-y-1 text-[0.8125rem] text-slate-400 mt-1">
            {kinds.map((k: any) => <span key={k} className="flex items-center gap-1"><span className="w-3 h-0.5" style={{ background: TONE[k] }} />{LABEL[k] || k}</span>)}
            <span className="text-slate-400">· every link is read from a clause of the citing standard</span>
          </figcaption>
        </>
      )}
    </figure>
  );
}
