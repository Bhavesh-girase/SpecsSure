"use client";

import { useEffect, useMemo, useState } from "react";
import { ReactFlow, Background, Controls, MiniMap, MarkerType, Handle, Position } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Card } from "@/components/ui";
import { ledger } from "@/lib/api";

const LAYERS = ["tender", "clause", "finding", "requirement", "standard", "amendment", "test", "regulation", "certification"];
const COLORS: Record<string, string> = {
  tender: "#1d4f93", clause: "#475569", requirement: "#6d28d9", standard: "#047857", amendment: "#b45309",
  regulation: "#be123c", certification: "#be123c", test: "#0e7490", finding: "#ef4444",
};

function TwinNode({ data }: any) {
  const c = COLORS[data.type] || "#64748b";
  return (
    <div className="rounded-lg px-2.5 py-1.5 text-[0.75rem] max-w-[190px] border bg-white" style={{ borderColor: c, background: `${c}14`, color: "#0f2748" }}>
      <Handle type="target" position={Position.Left} style={{ background: c, width: 6, height: 6 }} />
      <div className="uppercase tracking-wider font-bold" style={{ color: c, fontSize: 8 }}>{data.type}{data.severity ? ` · ${data.severity}` : ""}{data.status && data.type === "standard" ? ` · ${data.status}` : ""}</div>
      <div className="font-semibold leading-snug line-clamp-2">{data.label}</div>
      <Handle type="source" position={Position.Right} style={{ background: c, width: 6, height: 6 }} />
    </div>
  );
}
const nodeTypes = { twin: TwinNode };

export function TwinGraph({ twin }: { twin: any }) {
  const [sel, setSel] = useState<any>(null);
  const [hidden, setHidden] = useState<Set<string>>(new Set(["amendment"]));
  const { nodes, edges } = useMemo(() => {
    const g = twin.graph;
    const keep = g.nodes.filter((n: any) => !hidden.has(n.type));
    const ids = new Set(keep.map((n: any) => n.id));
    const cols: Record<string, number> = {};
    const nodes = keep.map((n: any) => {
      const layer = LAYERS.indexOf(n.type) >= 0 ? LAYERS.indexOf(n.type) : LAYERS.length;
      const row = (cols[n.type] = (cols[n.type] ?? -1) + 1);
      return { id: n.id, type: "twin", position: { x: layer * 230, y: row * 62 }, data: n };
    });
    const edges = g.edges.filter((e: any) => ids.has(e.source) && ids.has(e.target)).map((e: any) => ({
      id: e.id, source: e.source, target: e.target, animated: e.relation === "flags",
      label: ["contains", "states", "flags"].includes(e.relation) ? undefined : e.relation.replaceAll("_", " "),
      style: { stroke: e.relation === "flags" ? "#ef4444" : e.relation === "superseded_by" ? "#b45309" : "#94a3b8" },
      labelStyle: { fill: "#475569", fontSize: 8 }, labelBgStyle: { fill: "#ffffff" }, labelBgPadding: [3, 1] as [number, number],
      markerEnd: { type: MarkerType.ArrowClosed, color: "#475569" },
    }));
    return { nodes, edges };
  }, [twin, hidden]);
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2 text-[0.8125rem]">
        {LAYERS.map((l) => (
          <button key={l} onClick={() => setHidden((h) => { const n = new Set(h); n.has(l) ? n.delete(l) : n.add(l); return n; })}
            className="px-2 py-1 rounded-full border capitalize" style={{ borderColor: COLORS[l], color: hidden.has(l) ? "#475569" : COLORS[l], opacity: hidden.has(l) ? 0.5 : 1 }}>{l}</button>
        ))}
        <span className="text-slate-500 ml-auto">{twin.graph.nodes.length} nodes · {twin.graph.edges.length} typed edges — Tender → Clause → Requirement → Standard → Amendment → QCO → Certification → Test</span>
      </div>
      <div className="grid lg:grid-cols-[1fr_300px] gap-4">
        <div className="h-[640px] rounded-2xl border border-slate-800 bg-slate-950/70 overflow-hidden">
          <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView minZoom={0.15} onNodeClick={(_, n) => setSel(n.data)} proOptions={{ hideAttribution: true }}>
            <Background color="#d5deea" gap={24} />
            <Controls />
            <MiniMap pannable zoomable nodeColor={(n: any) => COLORS[n.data?.type] || "#64748b"} maskColor="rgba(226,232,240,0.6)" style={{ background: "#f8fafc" }} />
          </ReactFlow>
        </div>
        <Card>
          <div className="text-sm font-bold text-ink mb-2">Node inspector</div>
          {!sel ? <p className="text-xs text-slate-400">Click a node.</p> : (
            <pre className="text-[0.75rem] text-slate-300 whitespace-pre-wrap break-words">{JSON.stringify(sel, null, 1)}</pre>
          )}
        </Card>
      </div>
    </div>
  );
}

export function AuditTrail({ tenderId }: { tenderId: string }) {
  const [rows, setRows] = useState<any[]>([]);
  useEffect(() => { ledger(tenderId).then(setRows).catch(() => setRows([])); }, [tenderId]);
  return (
    <Card>
      <div className="text-sm font-bold text-ink mb-2">Audit trail for this tender (hash-chained ledger)</div>
      <div className="space-y-1 max-h-96 overflow-auto">
        {rows.map((e) => (
          <div key={e.seq} className="grid grid-cols-[50px_150px_160px_1fr_120px] gap-2 text-[0.8125rem] border-b border-slate-800 py-1.5">
            <span className="font-mono text-slate-500">#{e.seq}</span>
            <span className="text-slate-400">{e.ts.slice(0, 19).replace("T", " ")}</span>
            <span className="text-sky-300">{e.action}</span>
            <span className="text-slate-300 truncate">{e.actor} · {JSON.stringify(e.payload).slice(0, 140)}</span>
            <span className="font-mono text-slate-500 truncate" title={e.entry_hash}>{e.entry_hash.slice(0, 14)}…</span>
          </div>
        ))}
      </div>
    </Card>
  );
}
