"use client";

import { RecommendedStandard } from "@/types";
import { ShieldCheck, CheckCircle2, FileCode, ExternalLink, X, Scale } from "lucide-react";

interface EvidencePanelProps {
  standard: RecommendedStandard | null;
  onClose: () => void;
}

export function EvidencePanel({ standard, onClose }: EvidencePanelProps) {
  if (!standard) return null;

  const expl = standard.explanation;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl max-h-[85vh] overflow-y-auto p-6 shadow-2xl space-y-6 animate-in zoom-in-95 duration-150">
        
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <Scale className="w-5 h-5 text-sky-400" />
            <div>
              <h3 className="text-base font-bold text-ink font-mono">
                {standard.is_number} — Verification Evidence & Provenance
              </h3>
              <p className="text-xs text-slate-400">Verifiable Decision-Support Audit Trail</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-ink transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Score Math Formula */}
        {expl && (
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
            <h4 className="text-xs uppercase font-bold text-sky-400 tracking-wider">
              Mathematical Score Breakdown
            </h4>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
              <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                <div className="text-[0.75rem] text-slate-400">Semantic (0.40)</div>
                <div className="text-sm font-bold font-mono text-ink mt-0.5">
                  {Math.round(expl.semantic_score * 100)}%
                </div>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                <div className="text-[0.75rem] text-slate-400">Keyword (0.25)</div>
                <div className="text-sm font-bold font-mono text-ink mt-0.5">
                  {Math.round(expl.keyword_score * 100)}%
                </div>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                <div className="text-[0.75rem] text-slate-400">Domain (0.20)</div>
                <div className="text-sm font-bold font-mono text-ink mt-0.5">
                  {Math.round(expl.domain_score * 100)}%
                </div>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                <div className="text-[0.75rem] text-slate-400">Graph (0.15)</div>
                <div className="text-sm font-bold font-mono text-ink mt-0.5">
                  {Math.round(expl.graph_score * 100)}%
                </div>
              </div>
            </div>
            <p className="text-[0.8125rem] text-slate-400 italic">
              {expl.score_formula_note}
            </p>
          </div>
        )}

        {/* Provenance Points */}
        {expl?.auditable_trace && (
          <div className="space-y-3">
            <h4 className="text-xs uppercase font-bold text-slate-300 tracking-wider">
              Auditable Evidence Steps
            </h4>
            <div className="space-y-2">
              {expl.auditable_trace.map((item, idx) => (
                <div key={idx} className="p-3 rounded-xl bg-slate-950/70 border border-slate-800 text-xs text-slate-200 flex items-start gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                  <span className="leading-relaxed">{item}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between pt-4 border-t border-slate-800">
          <span className="text-xs text-slate-500 font-mono">
            DB Assertion ID: #{standard.id}
          </span>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold"
          >
            Close Panel
          </button>
        </div>
      </div>
    </div>
  );
}
