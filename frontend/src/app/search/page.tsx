"use client";

import { Suspense, useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { Search, Filter, BookOpen, Layers, ExternalLink, ArrowRight, ShieldCheck } from "lucide-react";
import { searchStandards } from "@/lib/api";
import { RecommendedStandard } from "@/types";
import { getStatusColor } from "@/lib/utils";
import Link from "next/link";
import { PageIntro } from "@/components/gov-ui";
import { Library } from "lucide-react";

function SearchContent() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams?.get("q") || "";

  const [query, setQuery] = useState(initialQuery);
  const [results, setResults] = useState<RecommendedStandard[]>([]);
  const [selectedDivision, setSelectedDivision] = useState("all");
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    handleSearch(initialQuery || "IS");
  }, [initialQuery]);

  const handleSearch = async (searchTerm: string) => {
    if (!searchTerm.trim()) return;
    setIsLoading(true);
    try {
      const data = await searchStandards(searchTerm, 20);
      setResults(data.results);
    } catch (err) {
      console.error("Search failed:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const filteredResults = results.filter((r) => {
    if (selectedDivision === "all") return true;
    return (
      r.scope?.toLowerCase().includes(selectedDivision.toLowerCase()) || 
      r.title?.toLowerCase().includes(selectedDivision.toLowerCase())
    );
  });

  return (
    <div className="space-y-8">
      {/* Search Input and Filters */}
      <div className="glass-panel p-4 rounded-2xl border border-slate-800 space-y-4 shadow-xl">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSearch(query);
          }}
          className="relative"
        >
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search standards by IS number, product name, or testing scope..."
            className="w-full bg-slate-950/80 border border-slate-700/80 rounded-xl pl-12 pr-28 py-3.5 text-sm text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-500"
          />
          <Search className="w-5 h-5 text-sky-400 absolute left-4 top-1/2 -translate-y-1/2" />
          
          <button
            type="submit"
            className="absolute right-3 top-1/2 -translate-y-1/2 px-4 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-semibold text-xs transition-colors"
          >
            Search
          </button>
        </form>

        {/* Division Quick Filter Pills */}
        <div className="flex flex-wrap items-center gap-2 pt-1 text-xs">
          <span className="text-slate-500 font-semibold flex items-center gap-1">
            <Filter className="w-3.5 h-3.5" />
            Division:
          </span>
          {[
            { id: "all", label: "All Divisions" },
            { id: "cement", label: "Civil / Cement (CED)" },
            { id: "steel", label: "Metallurgy / Steel (MTD)" },
            { id: "cable", label: "Electrotechnical (ETD)" },
            { id: "water", label: "Food & Water (FAD)" },
            { id: "pipe", label: "Plastics / Petroleum (PCD)" },
          ].map((div) => (
            <button
              key={div.id}
              onClick={() => setSelectedDivision(div.id)}
              className={`px-3 py-1 rounded-lg transition-all ${
                selectedDivision === div.id
                  ? "bg-sky-600 text-white font-semibold shadow-md shadow-sky-600/30"
                  : "bg-slate-900 text-slate-400 hover:text-ink border border-slate-800"
              }`}
            >
              {div.label}
            </button>
          ))}
        </div>
      </div>

      {/* Results List */}
      <div className="space-y-4">
        <div className="flex items-center justify-between text-xs text-slate-400">
          <span>Found {filteredResults.length} standards</span>
        </div>

        {isLoading ? (
          <div className="p-16 text-center text-slate-400 font-mono">
            Searching standards registry...
          </div>
        ) : filteredResults.length === 0 ? (
          <div className="p-16 text-center text-slate-400 glass-panel rounded-2xl">
            No standards matched your search query. Try another keyword or IS number.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredResults.map((std) => (
              <div
                key={std.id}
                className="glass-panel p-5 rounded-2xl border border-slate-800 hover:border-slate-700 transition-all flex flex-col justify-between space-y-4 group"
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-base font-bold text-sky-400">
                      {std.is_number}
                    </span>
                    <span className={`text-[0.75rem] px-2 py-0.5 rounded-full border ${getStatusColor(std.status)}`}>
                      {std.status.toUpperCase()}
                    </span>
                  </div>
                  <h3 className="text-sm font-semibold text-ink leading-snug">
                    {std.title}
                  </h3>
                  {std.scope && (
                    <p className="text-xs text-slate-400 line-clamp-2">
                      {std.scope}
                    </p>
                  )}
                </div>

                <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs">
                  <span className="font-mono text-emerald-400 font-bold">
                    {Math.round(std.relevance_score * 100)}% Match
                  </span>

                  <Link
                    href={`/standards/${encodeURIComponent(std.is_number)}`}
                    className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-sky-400 hover:text-sky-300 font-medium border border-slate-800 transition-colors flex items-center gap-1"
                  >
                    <span>View Graph</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function SearchPage() {
  return (
    <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      <PageIntro icon={Library} kicker="Standards catalogue" title="Browse Indian Standards"
        sub="Search by IS number (e.g. IS 1786), product name or what is tested. Each result shows whether the standard is current, and opens its full details, amendments and related standards." />

      <Suspense fallback={<div className="p-16 text-center text-slate-400 font-mono">Loading Catalog...</div>}>
        <SearchContent />
      </Suspense>
    </div>
  );
}
