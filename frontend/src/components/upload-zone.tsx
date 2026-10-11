"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { 
  Upload, FileText, Sparkles, ArrowRight, CheckCircle2, 
  AlertCircle, Loader2, RefreshCw, X, ShieldAlert, Zap
} from "lucide-react";
import { analyzeSpecification } from "@/lib/api";
import { LanguageSelector } from "@/components/language-selector";

const SAMPLE_PRESETS = [
  {
    label: "🧱 OPC Cement 43 Grade",
    desc: "Civil Construction",
    text: "Supply of Ordinary Portland Cement 43 Grade conforming to BIS standards with minimum 28 days compressive strength of 43 MPa, initial setting time not less than 30 minutes, sound by Le Chatelier test max 10 mm, packaged in 50 kg moisture-proof bags for bridge foundation work."
  },
  {
    label: "🏗️ TMT Steel Bars Fe 500D",
    desc: "Reinforced Concrete",
    text: "Procurement of high strength thermo-mechanically treated (TMT) deformed steel rebar Grade Fe 500D in diameters 12mm, 16mm, and 25mm. Must have minimum 0.2% proof stress of 500 N/mm2, TS/YS ratio >= 1.10, elongation >= 16% for seismic ductile detailing in Zone IV."
  },
  {
    label: "⚡ PVC Cables 1100V",
    desc: "Electrotechnical",
    text: "Supply of 1100V grade single core electrolytic copper conductor PVC insulated unsheathed flexible electrical wires 2.5 sq mm and 4.0 sq mm flame retardant (FR) with high oxygen index for government hospital electrical wiring."
  },
  {
    label: "💧 Drinking Water Testing",
    desc: "Public Health",
    text: "Quality testing of packaged potable drinking water for public distribution. Parameters require pH between 6.5 to 8.5, TDS max 500 mg/L, Total Hardness max 200 mg/L, absence of E. coli and coliform bacteria."
  },
  {
    label: "🛣️ Geotextile Fabric",
    desc: "Highway Construction",
    text: "Non-woven needle punched polypropylene geotextile fabric for subgrade soil separation and drainage in flexible road pavement. Mass 200 g/m2, CBR static puncture resistance minimum 2000 N, apparent opening size 90 microns."
  },
  {
    label: "🇮🇳 हिन्दी निविदा (Hindi Spec)",
    desc: "Multilingual Spec",
    text: "आरसीसी भवन निर्माण कार्य के लिए 43 ग्रेड साधारण पोर्टलैंड सीमेंट एवं 500 एमपीए न्यूनतम यील्ड स्ट्रेंथ वाले भूकंप प्रतिरोधी टीएमटी स्टील सरिया की आपूर्ति।"
  }
];

export function UploadZone() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [inputMode, setInputMode] = useState<"text" | "file">("text");
  const [textInput, setTextInput] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [language, setLanguage] = useState("auto");
  const [maxDepth, setMaxDepth] = useState(2);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      setSelectedFile(file);
      setInputMode("file");
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleAnalyze = async () => {
    if (inputMode === "text" && !textInput.trim()) {
      setError("Please paste tender specification text or select a preset.");
      return;
    }
    if (inputMode === "file" && !selectedFile) {
      setError("Please select or drag-and-drop a PDF/DOCX/TXT file.");
      return;
    }

    setError(null);
    setIsLoading(true);

    try {
      setLoadingStep("1/5: Detecting language & extracting technical requirements...");
      await new Promise(r => setTimeout(r, 400));
      
      setLoadingStep("2/5: Executing Dense + BM25 Hybrid Retrieval with RRF...");
      await new Promise(r => setTimeout(r, 400));

      setLoadingStep("3/5: Cross-Encoder candidate rescoring & Knowledge Graph BFS traversal...");
      
      const response = await analyzeSpecification({
        text: inputMode === "text" ? textInput : undefined,
        file: inputMode === "file" && selectedFile ? selectedFile : undefined,
        language: language,
        maxDepth: maxDepth
      });

      setLoadingStep("4/5: Checking compulsory QCO regulations and certification mandates...");
      await new Promise(r => setTimeout(r, 300));

      setLoadingStep("5/5: Computing mathematical provenance scores and spec health...");
      await new Promise(r => setTimeout(r, 200));

      // Cache result in sessionStorage for rapid page hydration
      if (typeof window !== "undefined") {
        sessionStorage.setItem(`analysis_${response.analysis_id}`, JSON.stringify(response));
      }

      router.push(`/analysis/${response.analysis_id}`);
    } catch (err: any) {
      console.error("Analysis failed:", err);
      setError(err.message || "Analysis pipeline failed. Ensure backend service is running.");
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto">
      {/* Container with glowing border */}
      <div className="glass-panel-glow rounded-2xl p-6 sm:p-8 shadow-2xl relative overflow-hidden">
        
        {/* Header Options */}
        <div className="flex flex-wrap items-center justify-between gap-4 pb-6 border-b border-slate-800">
          <div className="flex items-center gap-2 p-1 bg-slate-900/90 rounded-xl border border-slate-800">
            <button
              onClick={() => setInputMode("text")}
              className={`px-4 py-2 rounded-lg text-xs sm:text-sm font-semibold transition-all flex items-center gap-2 ${
                inputMode === "text"
                  ? "bg-sky-600 text-white shadow-md shadow-sky-600/30"
                  : "text-slate-400 hover:text-ink"
              }`}
            >
              <FileText className="w-4 h-4" />
              Paste Specification
            </button>
            <button
              onClick={() => setInputMode("file")}
              className={`px-4 py-2 rounded-lg text-xs sm:text-sm font-semibold transition-all flex items-center gap-2 ${
                inputMode === "file"
                  ? "bg-sky-600 text-white shadow-md shadow-sky-600/30"
                  : "text-slate-400 hover:text-ink"
              }`}
            >
              <Upload className="w-4 h-4" />
              Upload Document (PDF/DOCX)
            </button>
          </div>

          <div className="flex items-center gap-3">
            <LanguageSelector value={language} onChange={setLanguage} />
            
            <div className="hidden sm:flex items-center gap-1.5 text-xs text-slate-400 bg-slate-900 px-2.5 py-1.5 rounded-lg border border-slate-800">
              <span>Graph Depth:</span>
              <select
                value={maxDepth}
                onChange={(e) => setMaxDepth(Number(e.target.value))}
                className="bg-transparent text-sky-400 font-bold focus:outline-none cursor-pointer"
              >
                <option value={1} className="bg-slate-900">1 Hop</option>
                <option value={2} className="bg-slate-900">2 Hops</option>
                <option value={3} className="bg-slate-900">3 Hops</option>
              </select>
            </div>
          </div>
        </div>

        {/* Input Area */}
        <div className="mt-6">
          {inputMode === "text" ? (
            <div className="relative">
              <textarea
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                placeholder="Paste tender technical specifications, product parameters, or procurement clauses in English or Hindi (e.g. 'Ordinary Portland Cement 43 Grade with min 43 MPa strength...')"
                rows={7}
                className="w-full bg-slate-950/70 border border-slate-800 rounded-xl p-4 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent resize-y transition-all font-sans leading-relaxed"
              />
              {textInput && (
                <button
                  onClick={() => setTextInput("")}
                  className="absolute top-3 right-3 p-1.5 rounded-lg bg-slate-800 text-slate-400 hover:text-ink transition-colors"
                  title="Clear text"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
          ) : (
            <div
              onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
              onDragLeave={() => setIsDragOver(false)}
              onDrop={handleFileDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
                isDragOver
                  ? "border-sky-400 bg-sky-950/20 scale-[0.99]"
                  : selectedFile
                  ? "border-emerald-500/50 bg-emerald-950/10"
                  : "border-slate-700 hover:border-sky-500/50 bg-slate-950/40 hover:bg-slate-900/40"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.txt,.csv"
                onChange={handleFileSelect}
                className="hidden"
              />
              
              {selectedFile ? (
                <div className="flex flex-col items-center gap-3">
                  <div className="w-14 h-14 rounded-2xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400">
                    <CheckCircle2 className="w-8 h-8" />
                  </div>
                  <div>
                    <p className="font-semibold text-ink">{selectedFile.name}</p>
                    <p className="text-xs text-slate-400 mt-1 font-mono">
                      {(selectedFile.size / 1024).toFixed(1)} KB • Click or drop to replace
                    </p>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-3">
                  <div className="w-14 h-14 rounded-2xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
                    <Upload className="w-7 h-7" />
                  </div>
                  <div>
                    <p className="font-semibold text-ink">
                      Drop tender document here, or <span className="text-sky-400 underline">browse</span>
                    </p>
                    <p className="text-xs text-slate-400 mt-1">
                      Supports PDF, DOCX, and plain text tender specifications
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Preset Quick-Buttons */}
        <div className="mt-6">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="w-3.5 h-3.5 text-sky-400" />
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Or test with a sample procurement scenario:
            </span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {SAMPLE_PRESETS.map((preset, idx) => (
              <button
                key={idx}
                onClick={() => {
                  setInputMode("text");
                  setTextInput(preset.text);
                }}
                className="text-left p-2.5 rounded-xl bg-slate-900/70 hover:bg-slate-800 border border-slate-800/80 hover:border-sky-500/40 transition-all group"
              >
                <div className="text-xs font-semibold text-slate-200 group-hover:text-sky-300 transition-colors truncate">
                  {preset.label}
                </div>
                <div className="text-[0.75rem] text-slate-400 mt-0.5">{preset.desc}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mt-5 p-4 rounded-xl bg-rose-950/40 border border-rose-800 text-rose-300 text-xs flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Submit Action */}
        <div className="mt-6 flex items-center justify-between pt-5 border-t border-slate-800/80">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <Zap className="w-4 h-4 text-amber-400" />
            <span>AI reasons over graph • PostgreSQL asserts ground truth</span>
          </div>

          <button
            onClick={handleAnalyze}
            disabled={isLoading}
            className="px-6 py-3 rounded-xl bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-white font-semibold text-sm shadow-lg shadow-sky-500/25 hover:shadow-sky-500/40 transition-all flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed group"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Analyzing Specification...</span>
              </>
            ) : (
              <>
                <span>Run SpecSure Analysis</span>
                <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
              </>
            )}
          </button>
        </div>

        {/* Loading Progress Banner */}
        {isLoading && (
          <div className="mt-4 p-3 rounded-xl bg-sky-950/30 border border-sky-500/30 text-sky-300 text-xs flex items-center gap-2.5 animate-pulse">
            <RefreshCw className="w-4 h-4 animate-spin flex-shrink-0 text-sky-400" />
            <span className="font-mono">{loadingStep}</span>
          </div>
        )}
      </div>
    </div>
  );
}
