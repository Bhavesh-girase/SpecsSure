"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getStandardDetail, getStandardGraph } from "@/lib/api";
import { RecommendedStandard, GraphData } from "@/types";
import { 
  ShieldCheck, ArrowLeft, Layers, Bookmark, ExternalLink, 
  Clock, AlertTriangle, Activity 
} from "lucide-react";
import Link from "next/link";
import { StandardsGraph } from "@/components/standards-graph";
import { TimelineView } from "@/components/timeline-view";
import { getStatusColor } from "@/lib/utils";

export default function StandardDetailPage() {
  const params = useParams();
  const isNumberRaw = params?.is_number as string;
  const isNumber = decodeURIComponent(isNumberRaw || "");

  const [standard, setStandard] = useState<RecommendedStandard | null>(null);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!isNumber) return;

    Promise.all([
      getStandardDetail(isNumber).catch(() => null),
      getStandardGraph(isNumber, 2).catch(() => null),
    ])
      .then(([stdRes, graphRes]) => {
        if (stdRes) setStandard(stdRes);
        if (graphRes) setGraphData(graphRes);
      })
      .finally(() => setIsLoading(false));
  }, [isNumber]);

  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-24 text-center">
        <div className="w-12 h-12 rounded-full border-2 border-sky-500 border-t-transparent animate-spin mx-auto" />
        <p className="text-sm text-slate-400 font-mono mt-4">Loading Standard Details & Graph...</p>
      </div>
    );
  }

  if (!standard && !graphData) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-24 text-center space-y-4">
        <AlertTriangle className="w-12 h-12 text-amber-400 mx-auto" />
        <h2 className="text-xl font-bold text-ink">Standard Not Found</h2>
        <p className="text-sm text-slate-400">Could not find {isNumber} in the BIS database.</p>
        <Link
          href="/search"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Return to Catalog</span>
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      
      {/* Top Standard Card */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4 shadow-xl">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <Link
                href="/search"
                className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-ink transition-colors"
              >
                <ArrowLeft className="w-4 h-4" />
              </Link>
              <span className="font-mono text-xl font-bold text-sky-400">
                {standard?.is_number || isNumber}
              </span>
              <span className={`text-xs px-2.5 py-0.5 rounded-full border ${getStatusColor(standard?.status || "current")}`}>
                {(standard?.status || "current").toUpperCase()}
              </span>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold text-ink leading-tight">
              {standard?.title}
            </h1>
          </div>

          <a
            href={`https://standards.bis.gov.in`}
            target="_blank"
            rel="noopener noreferrer"
            className="px-4 py-2 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-lg shadow-sky-600/20"
          >
            <span>Verify on BIS Portal</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>

        {standard?.scope && (
          <p className="text-sm text-slate-300 leading-relaxed max-w-4xl">
            {standard.scope}
          </p>
        )}
      </div>

      {/* Interactive Standards Knowledge Graph */}
      {graphData && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-ink flex items-center gap-2">
              <Layers className="w-5 h-5 text-sky-400" />
              <span>Standards Knowledge Graph ({graphData.nodes?.length || 0} Nodes)</span>
            </h2>
          </div>
          <StandardsGraph graphData={graphData} />
        </div>
      )}

      {/* Timeline & Active Amendments */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 shadow-xl">
        <TimelineView
          edition={standard?.latest_edition}
          amendments={standard?.amendments || []}
          supersededBy={standard?.superseded_by}
        />
      </div>

    </div>
  );
}
