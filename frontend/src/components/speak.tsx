"use client";

import { useEffect, useState } from "react";
import { Square, Volume2 } from "lucide-react";

/** Read-aloud with the browser's own speech synthesis (offline voices where the OS has them; no server, no cost). */
export function speak(text: string, lang = "en-IN", onEnd?: () => void) {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return false;
  const synth = window.speechSynthesis;
  synth.cancel();
  const u = new SpeechSynthesisUtterance(text);
  const voices = synth.getVoices();
  const base = lang.split("-")[0];
  const v = voices.find((x) => x.lang === lang) || voices.find((x) => x.lang.startsWith(base + "-")) ||
    voices.find((x) => x.lang === "en-IN") || voices.find((x) => x.lang.startsWith("en"));
  if (v) { u.voice = v; u.lang = v.lang; } else { u.lang = lang; }
  u.rate = 0.95;
  if (onEnd) { u.onend = onEnd; u.onerror = onEnd; }
  synth.speak(u);
  return true;
}

export function stopSpeaking() {
  if (typeof window !== "undefined" && "speechSynthesis" in window) window.speechSynthesis.cancel();
}

const LANG: Record<string, string> = { hi: "hi-IN", mr: "mr-IN", ta: "ta-IN", te: "te-IN", bn: "bn-IN", kn: "kn-IN", en: "en-IN" };

/** Spoken summary of a recommendation — Hindi template for Devanagari queries, English otherwise. */
export function recommendationSpeech(r: any, language = "en"): string {
  const num = String(r.base || "").replace(/^IS\s*/, "I S ").replace(/\(Part (\w+)\)/, "Part $1").replace(/\/Sec (\w+)/, " Section $1");
  const cert = (r.certification || []).length ? (r.certification[0].scheme || "") : "";
  const conf = r.confidence === "high" ? "" : language === "hi" ? " इसकी जाँच कर लें।" : " Please verify.";
  const edition = r.status?.in_force && r.status?.level !== "bad" ? String(r.status.in_force).split(":")[1] : "";
  if (language === "hi" || language === "mr") {
    return `सुझाया गया भारतीय मानक: ${num}. ${r.title}.` + (edition ? ` वर्तमान संस्करण ${edition}.` : "") +
      (cert ? ` ${cert.includes("II") ? "बी आई एस पंजीकरण" : "आई एस आई मार्क"} अनिवार्य है.` : "") + conf;
  }
  return `Recommended Indian Standard: ${num}. ${r.title}.` + (edition ? ` Edition in force: ${edition}.` : "") +
    (cert ? ` ${cert.includes("II") ? "BIS registration" : "The ISI mark"} is compulsory.` : "") + conf;
}

export function SpeakButton({ text, language = "en", label = "Read aloud", compact }: { text: string; language?: string; label?: string; compact?: boolean }) {
  const [on, setOn] = useState(false);
  const [ok, setOk] = useState(true);
  useEffect(() => { setOk(typeof window !== "undefined" && "speechSynthesis" in window); return () => stopSpeaking(); }, []);
  if (!ok) return null;
  return (
    <button type="button" aria-pressed={on} title={on ? "Stop" : label}
      onClick={(e) => { e.stopPropagation(); if (on) { stopSpeaking(); setOn(false); } else { setOn(true); speak(text, LANG[language] || language, () => setOn(false)); } }}
      className={`inline-flex items-center gap-1 rounded-md border font-bold ${on ? "bg-[#0f2748] text-white border-[#0f2748]" : "border-[#c9d5e6] text-[#0f2748] hover:bg-[#eef4fb]"} ${compact ? "px-2 py-1 text-[0.8125rem]" : "px-3 py-1.5 text-[0.875rem]"}`}>
      {on ? <Square className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}{compact ? null : on ? "Stop" : label}
    </button>
  );
}
