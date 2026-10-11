"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Search, Loader2, ArrowRight, ShieldCheck } from "lucide-react";
import { quickSearch } from "@/lib/api";
import { RecommendedStandard } from "@/types";
import { getStatusColor } from "@/lib/utils";

export function SearchBar() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<RecommendedStandard[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    if (query.trim().length < 2) {
      setResults([]);
      setIsOpen(false);
      return;
    }

    const timer = setTimeout(async () => {
      setIsLoading(true);
      try {
        const data = await quickSearch(query, 5);
        setResults(data.results);
        setIsOpen(true);
      } catch (err) {
        console.error("Search failed:", err);
      } finally {
        setIsLoading(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [query]);

  const handleSelect = (isNumber: string) => {
    setIsOpen(false);
    router.push(`/standards/${encodeURIComponent(isNumber)}`);
  };

  const handleFullSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      setIsOpen(false);
      router.push(`/search?q=${encodeURIComponent(query)}`);
    }
  };

  return (
    <div className="relative w-full max-w-2xl mx-auto">
      <form onSubmit={handleFullSearch} className="relative">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Instant search by IS Number or Product (e.g. 'IS 269', 'TMT steel', 'PVC cable')..."
          className="w-full bg-slate-900/90 border border-slate-700/80 rounded-2xl pl-12 pr-28 py-3.5 text-sm text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-500 shadow-xl backdrop-blur-md font-sans"
        />
        <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400">
          <Search className="w-5 h-5 text-sky-400" />
        </div>

        <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-2">
          {isLoading && <Loader2 className="w-4 h-4 text-sky-400 animate-spin" />}
          <button
            type="submit"
            className="px-3 py-1.5 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold flex items-center gap-1 transition-colors"
          >
            <span>Search</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </form>

      {/* Auto-complete Dropdown */}
      {isOpen && results.length > 0 && (
        <div className="absolute top-full mt-2 w-full bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden z-50 animate-in fade-in slide-in-from-top-2 duration-150">
          <div className="p-2 border-b border-slate-800 text-[0.8125rem] text-slate-400 px-3 uppercase font-semibold">
            Top Matched Standards
          </div>
          <div className="divide-y divide-slate-800/60 max-h-80 overflow-y-auto">
            {results.map((res) => (
              <button
                key={res.id}
                onClick={() => handleSelect(res.is_number)}
                className="w-full p-3 text-left hover:bg-slate-800/80 transition-colors flex items-center justify-between gap-3 group"
              >
                <div className="space-y-0.5 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-xs text-sky-400 group-hover:text-sky-300">
                      {res.is_number}
                    </span>
                    <span className={`text-[0.75rem] px-1.5 py-0.5 rounded border ${getStatusColor(res.status)}`}>
                      {res.status}
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 truncate">{res.title}</p>
                </div>
                <div className="text-right flex-shrink-0">
                  <span className="text-xs font-mono font-bold text-emerald-400">
                    {Math.round(res.relevance_score * 100)}%
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
