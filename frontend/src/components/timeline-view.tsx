"use client";

import { Amendment } from "@/types";
import { History, BookmarkCheck, Calendar, FileText } from "lucide-react";

interface TimelineViewProps {
  edition?: string;
  publicationDate?: string;
  amendments: Amendment[];
  supersededBy?: string;
}

export function TimelineView({ edition, publicationDate, amendments, supersededBy }: TimelineViewProps) {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <History className="w-4 h-4 text-sky-400" />
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
          Standard Revision History & Active Amendments Timeline
        </h3>
      </div>

      <div className="relative pl-6 border-l-2 border-slate-800 space-y-6">
        
        {/* Base Standard Published */}
        <div className="relative">
          <div className="absolute -left-[31px] top-0 w-4 h-4 rounded-full bg-sky-500 border-4 border-slate-950" />
          <div className="p-4 rounded-xl glass-panel space-y-1">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-ink text-xs">
                Base Edition Published ({edition || "Initial Release"})
              </span>
              {publicationDate && (
                <span className="text-[0.75rem] text-slate-400 font-mono flex items-center gap-1">
                  <Calendar className="w-3 h-3" />
                  {publicationDate}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400">
              Approved by BIS Sectional Committee and notified in Gazette of India.
            </p>
          </div>
        </div>

        {/* Amendments Timeline */}
        {amendments.map((amend, idx) => (
          <div key={amend.id || idx} className="relative">
            <div className="absolute -left-[31px] top-0 w-4 h-4 rounded-full bg-amber-500 border-4 border-slate-950" />
            <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-amber-300 text-xs font-mono flex items-center gap-1.5">
                  <BookmarkCheck className="w-3.5 h-3.5 text-amber-400" />
                  Amendment No. {amend.amendment_number}
                </span>
                {amend.published_at && (
                  <span className="text-[0.75rem] text-slate-400 font-mono">
                    {amend.published_at.split("T")[0]}
                  </span>
                )}
              </div>

              {amend.changed_clauses && (
                <div className="text-[0.8125rem] text-slate-300 bg-slate-950/70 p-2 rounded border border-slate-800/80 font-mono">
                  Clauses: {amend.changed_clauses}
                </div>
              )}

              {amend.summary && (
                <p className="text-xs text-slate-300">
                  {amend.summary}
                </p>
              )}
            </div>
          </div>
        ))}

        {/* Superseded Notice if applicable */}
        {supersededBy && (
          <div className="relative">
            <div className="absolute -left-[31px] top-0 w-4 h-4 rounded-full bg-rose-500 border-4 border-slate-950" />
            <div className="p-4 rounded-xl bg-rose-950/20 border border-rose-500/30 text-rose-300 space-y-1">
              <div className="font-bold text-xs">SUPERSEDED & REPLACED</div>
              <p className="text-xs">
                This edition is no longer active. All new tenders must mandate compliance with <strong>{supersededBy}</strong>.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
