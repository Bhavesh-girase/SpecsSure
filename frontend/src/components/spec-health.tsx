"use client";

import { SpecHealth as ISpecHealth, SpecGap } from "@/types";
import { 
  AlertTriangle, CheckCircle, HelpCircle, ShieldAlert, 
  FileWarning, ArrowUpRight, Zap, Info, ShieldCheck
} from "lucide-react";
import { getSeverityColor } from "@/lib/utils";

interface SpecHealthProps {
  specHealth: ISpecHealth;
}

export function SpecHealthDashboard({ specHealth }: SpecHealthProps) {
  const score = specHealth.overall_score;

  const getScoreColor = (val: number) => {
    if (val >= 80) return "text-emerald-400 stroke-emerald-400";
    if (val >= 50) return "text-amber-400 stroke-amber-400";
    return "text-rose-400 stroke-rose-400";
  };

  const getScoreBadge = (val: number) => {
    if (val >= 80) return { label: "Robust Specification", bg: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" };
    if (val >= 50) return { label: "Moderate Risk", bg: "bg-amber-500/20 text-amber-400 border-amber-500/30" };
    return { label: "High Procurement Risk", bg: "bg-rose-500/20 text-rose-400 border-rose-500/30" };
  };

  const badge = getScoreBadge(score);

  // SVG Gauge math
  const radius = 60;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  return (
    <div className="space-y-6">
      
      {/* Top Health Overview Card */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800 flex flex-col md:flex-row items-center gap-8 shadow-xl">
        
        {/* Animated Circular Gauge */}
        <div className="relative w-40 h-40 flex-shrink-0 flex items-center justify-center">
          <svg className="w-full h-full transform -rotate-90" viewBox="0 0 140 140">
            <circle
              cx="70"
              cy="70"
              r={radius}
              className="stroke-slate-800"
              strokeWidth="10"
              fill="transparent"
            />
            <circle
              cx="70"
              cy="70"
              r={radius}
              className={`${getScoreColor(score)} transition-all duration-1000 ease-out`}
              strokeWidth="10"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              strokeLinecap="round"
              fill="transparent"
            />
          </svg>
          <div className="absolute flex flex-col items-center justify-center text-center">
            <span className={`text-3xl font-bold font-mono ${getScoreColor(score).split(" ")[0]}`}>
              {score}
            </span>
            <span className="text-[0.75rem] uppercase font-semibold text-slate-400 tracking-wider">
              / 100 Health
            </span>
          </div>
        </div>

        {/* Health Breakdown & Summary */}
        <div className="flex-1 space-y-4 text-center md:text-left">
          <div className="flex flex-wrap items-center justify-center md:justify-start gap-2">
            <span className={`text-xs px-2.5 py-1 rounded-full font-bold border ${badge.bg}`}>
              {badge.label}
            </span>
            <span className="text-xs text-slate-400">
              {specHealth.gaps.length} Actionable Items Identified
            </span>
          </div>

          <p className="text-sm text-slate-300 leading-relaxed">
            {specHealth.summary}
          </p>

          {/* Sub-scores */}
          <div className="grid grid-cols-3 gap-3 pt-2">
            <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-center">
              <div className="text-[0.8125rem] text-slate-400 font-medium">Completeness</div>
              <div className="text-lg font-bold font-mono text-sky-400 mt-0.5">
                {specHealth.completeness_score}%
              </div>
            </div>

            <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-center">
              <div className="text-[0.8125rem] text-slate-400 font-medium">Currency & Life</div>
              <div className="text-lg font-bold font-mono text-emerald-400 mt-0.5">
                {specHealth.currency_score}%
              </div>
            </div>

            <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-center">
              <div className="text-[0.8125rem] text-slate-400 font-medium">Clarity / Precision</div>
              <div className="text-lg font-bold font-mono text-amber-400 mt-0.5">
                {specHealth.clarity_score}%
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Detailed Gaps & Recommendations List */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-sky-400" />
          <span>Detailed Gap Analysis & Rectification Guidance</span>
        </h3>

        {specHealth.gaps.length === 0 ? (
          <div className="p-8 rounded-2xl glass-panel text-center text-slate-400 flex flex-col items-center gap-2">
            <ShieldCheck className="w-8 h-8 text-emerald-400" />
            <p className="text-sm font-medium text-slate-200">No specification vulnerabilities detected!</p>
            <p className="text-xs">All essential parameters, standards citations, and testing codes are well-formed.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3">
            {specHealth.gaps.map((gap, index) => (
              <div
                key={index}
                className={`p-4 rounded-xl border transition-all ${getSeverityColor(gap.severity)}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <span className="text-xs uppercase font-bold px-2 py-0.5 rounded bg-black/30">
                      {gap.severity}
                    </span>
                    <span className="text-xs font-mono font-semibold text-slate-200">
                      {gap.gap_type.replace(/_/g, " ").toUpperCase()}
                    </span>
                    {gap.affected_standard && (
                      <span className="text-[0.8125rem] font-mono text-sky-300">
                        ({gap.affected_standard})
                      </span>
                    )}
                  </div>
                  {gap.clause_reference && (
                    <span className="text-[0.75rem] text-slate-400 font-mono">
                      {gap.clause_reference}
                    </span>
                  )}
                </div>

                <p className="text-xs text-slate-200 mt-2 font-medium">
                  {gap.description}
                </p>

                <div className="mt-2.5 p-2.5 rounded-lg bg-black/20 border border-white/5 flex items-start gap-2 text-xs">
                  <ArrowUpRight className="w-3.5 h-3.5 text-sky-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold text-sky-300">Rectification: </span>
                    <span className="text-slate-300">{gap.suggestion}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
