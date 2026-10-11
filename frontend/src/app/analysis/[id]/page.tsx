"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { AnalysisResponse, RecommendedStandard } from "@/types";
import { getPastAnalysis } from "@/lib/api";
import { 
  ShieldCheck, ArrowLeft, Layers, FileText, Activity, 
  Award, ListChecks, Download, Share2, Sparkles, Clock, AlertTriangle 
} from "lucide-react";
import Link from "next/link";
import { SpecHealthDashboard } from "@/components/spec-health";
import { RecommendationCard } from "@/components/recommendation-card";
import { StandardsGraph } from "@/components/standards-graph";
import { EvidencePanel } from "@/components/evidence-panel";

export default function AnalysisResultsPage() {
  const params = useParams();
  const router = useRouter();
  const analysisId = params?.id as string;

  const [data, setData] = useState<AnalysisResponse | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "standards" | "graph" | "health" | "certification" | "requirements">("overview");
  const [selectedEvidenceStd, setSelectedEvidenceStd] = useState<RecommendedStandard | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // 1. Try loading from sessionStorage
    if (typeof window !== "undefined") {
      const cached = sessionStorage.getItem(`analysis_${analysisId}`);
      if (cached) {
        try {
          setData(JSON.parse(cached));
          setIsLoading(false);
          return;
        } catch (e) {
          console.error("Cache parse error", e);
        }
      }
    }

    // 2. Fetch from backend API
    getPastAnalysis(analysisId)
      .then((res) => {
        setData(res);
        setIsLoading(false);
      })
      .catch((err) => {
        console.error("Failed to load past analysis:", err);
        setIsLoading(false);
      });
  }, [analysisId]);

  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-24 text-center space-y-4">
        <div className="w-12 h-12 rounded-full border-2 border-sky-500 border-t-transparent animate-spin mx-auto" />
        <p className="text-sm text-slate-400 font-mono">Hydrating SpecSure Analysis Results...</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-24 text-center space-y-4">
        <AlertTriangle className="w-12 h-12 text-amber-400 mx-auto" />
        <h2 className="text-xl font-bold text-ink">Analysis Record Not Found</h2>
        <p className="text-sm text-slate-400">The requested analysis ID could not be loaded.</p>
        <Link
          href="/"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Return to Analyzer</span>
        </Link>
      </div>
    );
  }

  const tabs = [
    { id: "overview", label: "Overview", icon: Activity },
    { id: "standards", label: `Recommended Standards (${data.recommended_standards?.length || 0})`, icon: ShieldCheck },
    { id: "graph", label: "Knowledge Graph", icon: Layers },
    { id: "health", label: `Spec Health & Gaps (${data.spec_health?.gaps?.length || 0})`, icon: AlertTriangle },
    { id: "certification", label: `QCO & Mandates (${data.certification_info?.length || 0})`, icon: Award },
    { id: "requirements", label: `Extracted Requirements (${data.extracted_requirements?.length || 0})`, icon: ListChecks },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      
      {/* Top Banner with Navigation and Metadata */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-xl">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-ink transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <span className="text-xs uppercase tracking-widest font-mono font-bold text-sky-400">
              Analysis Results
            </span>
            <span className="text-[0.8125rem] text-slate-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-800 font-mono">
              ID: {data.analysis_id?.slice(0, 8)}
            </span>
          </div>

          <h1 className="text-xl sm:text-2xl font-bold text-ink mt-1">
            {data.product_identity || "Procurement Technical Specification"}
          </h1>
          
          <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 pt-1">
            {data.application_context && (
              <span><strong>Application:</strong> {data.application_context}</span>
            )}
            <span><strong>Language:</strong> {data.detected_language?.toUpperCase()}</span>
            <span className="flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 text-slate-400" />
              <span>{data.processing_time_seconds}s</span>
            </span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => window.print()}
            className="px-3.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-ink text-xs font-semibold flex items-center gap-1.5 transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export Report</span>
          </button>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex items-center gap-1 border-b border-slate-800 overflow-x-auto pb-1">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-4 py-2.5 rounded-t-xl text-xs sm:text-sm font-semibold flex items-center gap-2 whitespace-nowrap transition-all border-b-2 -mb-[2px] ${
                isActive
                  ? "border-sky-500 bg-slate-900/80 text-sky-400 shadow-sm"
                  : "border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/40"
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? "text-sky-400" : "text-slate-500"}`} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab Contents */}
      <div className="space-y-6">
        
        {/* Tab 1: Overview */}
        {activeTab === "overview" && (
          <div className="space-y-8">
            <SpecHealthDashboard specHealth={data.spec_health} />

            {/* Top Recommended Standards Preview */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-bold text-ink flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-sky-400" />
                  <span>Primary Recommended Indian Standards</span>
                </h3>
                <button
                  onClick={() => setActiveTab("standards")}
                  className="text-xs text-sky-400 hover:underline"
                >
                  View all ({data.recommended_standards.length})
                </button>
              </div>

              <div className="grid grid-cols-1 gap-4">
                {data.recommended_standards.slice(0, 2).map((std) => (
                  <RecommendationCard
                    key={std.id}
                    standard={std}
                    onOpenEvidence={setSelectedEvidenceStd}
                  />
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Recommended Standards */}
        {activeTab === "standards" && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-ink">Recommended Indian Standards</h2>
                <p className="text-xs text-slate-400">
                  Ranked by applicability score with active amendments and auditable evidence traces.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-4">
              {data.recommended_standards.map((std) => (
                <RecommendationCard
                  key={std.id}
                  standard={std}
                  onOpenEvidence={setSelectedEvidenceStd}
                />
              ))}
            </div>
          </div>
        )}

        {/* Tab 3: Knowledge Graph */}
        {activeTab === "graph" && (
          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-bold text-ink">Standards Knowledge Graph</h2>
              <p className="text-xs text-slate-400">
                Interactive relationship network connecting primary product specifications, test method codes, safety requirements, and installation practices.
              </p>
            </div>
            <StandardsGraph graphData={data.graph_data} />
          </div>
        )}

        {/* Tab 4: Spec Health & Gaps */}
        {activeTab === "health" && (
          <SpecHealthDashboard specHealth={data.spec_health} />
        )}

        {/* Tab 5: Mandatory Certification & QCOs */}
        {activeTab === "certification" && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-bold text-ink">Mandatory Certification & Quality Control Orders (QCO)</h2>
              <p className="text-xs text-slate-400">
                Statutory regulatory requirements under Government of India Gazette notifications.
              </p>
            </div>

            <div className="glass-panel rounded-2xl overflow-hidden border border-slate-800 shadow-xl">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-900/90 border-b border-slate-800 text-slate-400 uppercase font-mono">
                    <tr>
                      <th className="p-4">Standard Code</th>
                      <th className="p-4">Mandatory?</th>
                      <th className="p-4">Scheme</th>
                      <th className="p-4">QCO Notification / Authority</th>
                      <th className="p-4">Compliance Note</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800 text-slate-300">
                    {data.certification_info.map((cert, i) => (
                      <tr key={i} className="hover:bg-slate-900/40 transition-colors">
                        <td className="p-4 font-mono font-bold text-sky-400 whitespace-nowrap">
                          {cert.is_number}
                        </td>
                        <td className="p-4">
                          <span className={`px-2 py-0.5 rounded-full font-bold text-[0.75rem] uppercase ${
                            cert.is_mandatory.toLowerCase() === "yes"
                              ? "bg-rose-500/20 text-rose-400 border border-rose-500/30"
                              : "bg-slate-800 text-slate-400"
                          }`}>
                            {cert.is_mandatory.toUpperCase()}
                          </span>
                        </td>
                        <td className="p-4 font-semibold text-ink">
                          {cert.scheme || "Standard BIS Scheme"}
                        </td>
                        <td className="p-4 text-slate-300">
                          <div>{cert.qco_reference || "Gazette Notification"}</div>
                          <div className="text-[0.75rem] text-slate-500">{cert.issuing_authority}</div>
                        </td>
                        <td className="p-4 text-slate-400 max-w-md">
                          {cert.note}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Tab 6: Extracted Requirements */}
        {activeTab === "requirements" && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-bold text-ink">Extracted Technical Parameters</h2>
              <p className="text-xs text-slate-400">
                Structured parameters and numerical bounds identified from the specification text.
              </p>
            </div>

            <div className="glass-panel rounded-2xl overflow-hidden border border-slate-800 shadow-xl">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-900/90 border-b border-slate-800 text-slate-400 uppercase font-mono">
                    <tr>
                      <th className="p-4">Category</th>
                      <th className="p-4">Parameter</th>
                      <th className="p-4">Operator</th>
                      <th className="p-4">Target Value</th>
                      <th className="p-4">Unit</th>
                      <th className="p-4">Confidence</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800 text-slate-300">
                    {data.extracted_requirements.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="p-8 text-center text-slate-500">
                          No explicit numerical parameter constraints were extracted from this query.
                        </td>
                      </tr>
                    ) : (
                      data.extracted_requirements.map((req, idx) => (
                        <tr key={idx} className="hover:bg-slate-900/40 transition-colors">
                          <td className="p-4">
                            <span className="px-2 py-0.5 rounded bg-slate-800 font-mono text-slate-300 uppercase text-[0.75rem]">
                              {req.category}
                            </span>
                          </td>
                          <td className="p-4 font-semibold text-ink">{req.parameter}</td>
                          <td className="p-4 font-mono text-sky-400">{req.operator || "="}</td>
                          <td className="p-4 font-mono font-bold text-emerald-400">{req.value}</td>
                          <td className="p-4 text-slate-400">{req.unit || "—"}</td>
                          <td className="p-4 font-mono text-slate-400">{Math.round(req.confidence * 100)}%</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

      </div>

      {/* Evidence Verification Modal */}
      {selectedEvidenceStd && (
        <EvidencePanel
          standard={selectedEvidenceStd}
          onClose={() => setSelectedEvidenceStd(null)}
        />
      )}
    </div>
  );
}
