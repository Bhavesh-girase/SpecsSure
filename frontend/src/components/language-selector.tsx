"use client";

import { Globe } from "lucide-react";

interface LanguageSelectorProps {
  value: string;
  onChange: (lang: string) => void;
}

export function LanguageSelector({ value, onChange }: LanguageSelectorProps) {
  const languages = [
    { code: "auto", label: "Auto-detect (स्वचालित)" },
    { code: "en", label: "English" },
    { code: "hi", label: "हिन्दी (Hindi)" },
    { code: "ta", label: "தமிழ் (Tamil)" },
    { code: "te", label: "తెలుగు (Telugu)" },
    { code: "bn", label: "বাংলা (Bengali)" },
  ];

  return (
    <div className="flex items-center gap-2">
      <Globe className="w-4 h-4 text-sky-400" />
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="bg-slate-900 border border-slate-700 text-slate-200 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-sky-500 cursor-pointer"
      >
        {languages.map((l) => (
          <option key={l.code} value={l.code}>
            {l.label}
          </option>
        ))}
      </select>
    </div>
  );
}
