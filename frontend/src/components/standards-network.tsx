"use client";

import Link from "next/link";

const TONE: Record<string, string> = {
  normative: "#0f2748", test_method: "#1d4f93", terminology: "#6d28d9", safety: "#c0262d", installation: "#b45309",
  sampling: "#0e7490", packaging_marking: "#64748b", material: "#047857", allied_product: "#334155", cited_by: "#94a3b8",
};
const LABEL: Record<string, string> = {
  normative: "normative reference", test_method: "test method", terminology: "terminology", safety: "safety", installation: "installation",
  sampling: "sampling", packaging_marking: "packing / marking", material: "material", allied_product: "related product", cited_by: "used by",
};

/** Radial map of one standard's dependencies (from its own clauses) and the standards that cite it. */
export function StandardsNetwork({ base, allied }: { base: string; allied: any }) {
  const seen = new Set<string>();
  const nodes: { base: string; title?: string; kind: string; normative: boolean }[] = [];
  for (const g of allied.groups) {
    for (const it of g.items) {
      if (seen.has(it.base)) continue;
      seen.add(it.base);
      const normative = it.clauses.includes("references");
      nodes.push({ base: it.base, title: it.title, kind: it.kind === "allied_product" && normative ? "normative" : it.kind, normative });
    }
  }
  const out = nodes.slice(0, 18);
  const cited = (allied.cited_by || []).filter((c: any) => !seen.has(c.base)).slice(0, 6);
  const W = 980, H = 560, cx = W / 2, cy = H / 2;
  const RX = 400, RY = 225;
  const all = [...out.map((n) => ({ ...n, ring: 1 })), ...cited.map((c: any) => ({ base: c.base, title: c.title, kind: "cited_by", normative: false, ring: 2 }))];
  const n = all.length || 1;
  const pos = all.map((node, i) => {
    const a = -Math.PI / 2 + (2 * Math.PI * i) / n;
    const k = node.ring === 2 ? 0.62 : 1;
    return { ...node, x: cx + Math.cos(a) * RX * k, y: cy + Math.sin(a) * RY * (node.ring === 2 ? 0.55 : 1) };
  });
  const kinds = Array.from(new Set(pos.map((p) => p.kind)));
  return (
    <figure className="bg-white border border-[#d5deea] rounded-lg p-3">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img" aria-label={`Dependency map of ${base}`}>
        {pos.map((p) => (
          <line key={"l" + p.base} x1={cx} y1={cy} x2={p.x} y2={p.y} stroke={TONE[p.kind] || "#94a3b8"} strokeWidth={p.normative ? 1.8 : 1}
            strokeDasharray={p.kind === "cited_by" ? "4 4" : undefined} opacity={0.7} />
        ))}
        <g>
          <rect x={cx - 70} y={cy - 20} width={140} height={40} rx={8} fill="#0f2748" />
          <text x={cx} y={cy + 5} textAnchor="middle" fontSize="14" fontWeight="800" fill="#fff" fontFamily="JetBrains Mono, monospace">{base}</text>
        </g>
        {pos.map((p) => (
          <Link key={"n" + p.base} href={`/recommend?q=${encodeURIComponent(p.base + " " + (p.title || ""))}`}>
            <g className="cursor-pointer">
              <title>{`${p.base} — ${p.title || ""} (${LABEL[p.kind] || p.kind})`}</title>
              <rect x={p.x - 58} y={p.y - 13} width={116} height={26} rx={6} fill="#fff" stroke={TONE[p.kind] || "#94a3b8"} strokeWidth={1.5} />
              <text x={p.x} y={p.y + 4} textAnchor="middle" fontSize="10.5" fontWeight="700" fill={TONE[p.kind] || "#334155"} fontFamily="JetBrains Mono, monospace">
                {p.base.length > 19 ? p.base.slice(0, 18) + "…" : p.base}
              </text>
            </g>
          </Link>
        ))}
      </svg>
      <figcaption className="flex flex-wrap gap-x-3 gap-y-1 text-[0.8125rem] text-slate-400 px-1">
        {kinds.map((k) => <span key={k} className="flex items-center gap-1"><span className="w-3 h-0.5" style={{ background: TONE[k] }} />{LABEL[k] || k}</span>)}
        <span className="text-slate-400">· solid = referenced by {base}; dashed = standards that cite {base}</span>
      </figcaption>
    </figure>
  );
}
