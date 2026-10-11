"use client";

import { useState } from "react";
import Link from "next/link";
import { RecommendedStandard } from "@/types";
import { 
  ShieldCheck, AlertTriangle, ExternalLink, ChevronDown, ChevronUp, 
  Layers, FileText, CheckCircle2, Bookmark, Award
} from "lucide-react";
import { getStatusColor, formatScore } from "@/lib/utils";

interface RecommendationCardProps {
  standard: RecommendedStandard;
  onOpenEvidence?: (standard: RecommendedStandard) => void;
}

export function RecommendationCard({ standard, onOpenEvidence }: RecommendationCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const scorePercent = Math.round(standard.relevance_score * 100);

  return (
    <div className="glass-panel rounded-2xl p-6 border border-slate-800 transition-all hover:border-slate-700 shadow-xl space-y-4">
      
      {/* Header Row */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="font-mono text-base sm:text-lg font-bold text-sky-400">
              {standard.is_number}
            </span>
            <span className={`text-[0.8125rem] font-semibold px-2 py-0.5 rounded-full border ${getStatusColor(standard.status)}`}>
              {standard.status.toUpperCase()}
            </span>
            {standard.latest_edition && (
              <span className="text-[0.8125rem] text-slate-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-800 font-mono">
                {standard.latest_edition}
              </span>
            )}
          </div>
          <h3 className="text-sm sm:text-base font-semibold text-ink leading-snug">
            {standard.title}
          </h3>
        </div>

        {/* Relevance Score Pill */}
        <div className="flex items-center gap-3 bg-slate-900/90 border border-slate-800 px-3.5 py-1.5 rounded-xl">
          <div className="text-right">
            <div className="text-[0.75rem] uppercase font-bold text-slate-400 tracking-wider">
              Applicability
            </div>
            <div className="text-sm font-bold font-mono text-emerald-400">
              {scorePercent}%
            </div>
          </div>
          <div className="w-10 h-1.5 bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-sky-400 to-emerald-400"
              style={{ width: `${scorePercent}%` }}
            />
          </div>
        </div>
      </div>

      {/* Scope / Summary */}
      {standard.scope && (
        <p className="text-xs text-slate-300 leading-relaxed line-clamp-2">
          {standard.scope}
        </p>
      )}

      {/* Relevance Reason & AI Explainability Note */}
      <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 text-xs text-slate-300 space-y-1">
        <div className="flex items-center gap-1.5 text-sky-400 font-semibold">
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>Audit Provenance & Decision Logic</span>
        </div>
        <p className="text-slate-300 leading-relaxed font-sans">
          {standard.relevance_reason}
        </p>
      </div>

      {/* Active Amendments Banner if present */}
      {standard.amendments && standard.amendments.length > 0 && (
        <div className="flex items-center gap-2 p-2.5 rounded-lg bg-amber-950/20 border border-amber-500/30 text-xs text-amber-300">
          <Bookmark className="w-4 h-4 text-amber-400 flex-shrink-0" />
          <span>
            <strong>{standard.amendments.length} Active Amendment(s) in force</strong>: Always mandate latest revision compliance.
          </span>
        </div>
      )}

      {/* Expandable Details Section */}
      {isExpanded && (
        <div className="pt-4 border-t border-slate-800 space-y-4 animate-in fade-in duration-200 text-xs">
          
          {/* Mathematical Provenance Trace */}
          {standard.explanation && (
            <div className="space-y-2">
              <h4 className="font-semibold text-slate-200 uppercase tracking-wider text-[0.8125rem]">
                Deterministic Proof Trail (Trace)
              </h4>
              <ul className="space-y-1.5">
                {standard.explanation.auditable_trace.map((trace, i) => (
                  <li key={i} className="flex items-start gap-2 text-slate-300">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0 mt-0.5" />
                    <span>{trace}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Amendments List */}
          {standard.amendments && standard.amendments.length > 0 && (
            <div className="space-y-2">
              <h4 className="font-semibold text-slate-200 uppercase tracking-wider text-[0.8125rem]">
                Published Amendments Details
              </h4>
              <div className="space-y-2">
                {standard.amendments.map((amend) => (
                  <div key={amend.id} className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 space-y-1">
                    <div className="flex items-center justify-between font-mono font-bold text-slate-200">
                      <span>Amendment No. {amend.amendment_number}</span>
                      {amend.published_at && <span className="text-[0.75rem] text-slate-400">{amend.published_at.split("T")[0]}</span>}
                    </div>
                    {amend.summary && <p className="text-slate-400">{amend.summary}</p>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Card Actions Footer */}
      <div className="flex items-center justify-between pt-2">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-xs text-sky-400 hover:text-sky-300 flex items-center gap-1 font-medium transition-colors"
        >
          {isExpanded ? (
            <>
              <span>Hide Details</span>
              <ChevronUp className="w-3.5 h-3.5" />
            </>
          ) : (
            <>
              <span>View Audit Trace & Amendments ({standard.amendments?.length || 0})</span>
              <ChevronDown className="w-3.5 h-3.5" />
            </>
          )}
        </button>

        <div className="flex items-center gap-2">
          <Link
            href={`/standards/${encodeURIComponent(standard.is_number)}`}
            className="text-xs px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-ink border border-slate-800 transition-colors flex items-center gap-1"
          >
            <Layers className="w-3 h-3" />
            <span>Standard Graph</span>
          </Link>

          <a
            href={standard.evidence?.[0]?.direct_url || `https://standards.bis.gov.in`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs px-3 py-1.5 rounded-lg bg-sky-600/20 hover:bg-sky-600/30 text-sky-300 border border-sky-500/30 transition-colors flex items-center gap-1"
          >
            <span>BIS Source</span>
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>
    </div>
  );
}
