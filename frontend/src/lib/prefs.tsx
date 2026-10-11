"use client";

// Portal preferences: language (English / हिन्दी), active role, text size and contrast — persisted per browser.
import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from "react";

export type Lang = "en" | "hi";
export type Role = "officer" | "contractor" | "citizen";

const DICT: Record<string, { en: string; hi: string }> = {
  // chrome
  "portal.name": { en: "SpecSure", hi: "स्पेकश्योर" },
  "portal.tagline": { en: "Public Procurement Standards Compliance Portal", hi: "सार्वजनिक खरीद मानक अनुपालन पोर्टल" },
  "portal.sub": { en: "Tender intelligence · Indian Standards · QCO · Evidence-first evaluation", hi: "निविदा विश्लेषण · भारतीय मानक · गुणवत्ता नियंत्रण आदेश · साक्ष्य-आधारित मूल्यांकन" },
  "proto.banner": { en: "Prototype for Smart India Hackathon 2026 — not an official Government of India website. All demo data is fictional.",
                    hi: "स्मार्ट इंडिया हैकाथॉन 2026 हेतु प्रोटोटाइप — यह भारत सरकार की आधिकारिक वेबसाइट नहीं है। सभी डेमो डेटा काल्पनिक हैं।" },
  "skip": { en: "Skip to main content", hi: "मुख्य सामग्री पर जाएँ" },
  "contrast": { en: "High contrast", hi: "उच्च कंट्रास्ट" },
  "role.officer": { en: "Procurement Officer", hi: "क्रय अधिकारी" },
  "role.contractor": { en: "Contractor / Bidder", hi: "ठेकेदार / बोलीदाता" },
  "role.citizen": { en: "Citizen / Auditor", hi: "नागरिक / लेखा परीक्षक" },
  "role.label": { en: "I am a", hi: "मैं हूँ" },
  "nav.home": { en: "Home", hi: "मुखपृष्ठ" },
  "nav.recommend": { en: "Find Standards", hi: "मानक खोजें" },
  "nav.evidence": { en: "Evidence", hi: "प्रमाण" },
  "nav.officer": { en: "Officer Workspace", hi: "अधिकारी कार्यक्षेत्र" },
  "nav.studio": { en: "Tender Studio", hi: "निविदा स्टूडियो" },
  "nav.tenders": { en: "Tender Vetting", hi: "निविदा जाँच" },
  "nav.contractor": { en: "Contractor Workspace", hi: "ठेकेदार कार्यक्षेत्र" },
  "nav.market": { en: "Open Tenders", hi: "खुली निविदाएँ" },
  "nav.bidmirror": { en: "Bid Mirror", hi: "बोली दर्पण" },
  "nav.kg": { en: "Knowledge Graph", hi: "ज्ञान ग्राफ़" },
  "nav.standards": { en: "Standards", hi: "मानक" },
  "nav.radar": { en: "Regulatory Radar", hi: "नियामक रडार" },
  "nav.lab": { en: "Tools", hi: "उपकरण" },
  "nav.audit": { en: "Audit Ledger", hi: "लेखा परीक्षा बही" },
  "nav.about": { en: "About", hi: "परिचय" },
  // home
  "home.kicker": { en: "Smart Automation · Public Procurement", hi: "स्मार्ट ऑटोमेशन · सार्वजनिक खरीद" },
  "home.title": { en: "The right Indian Standard for everything you procure — with every standard it depends on.",
                  hi: "हर ख़रीद के लिए सही भारतीय मानक — और उससे जुड़े सभी मानक।" },
  "home.lead": { en: "SpecSure reads the full body of Indian Standards — their scope, normative references, test methods and terminology — to recommend the right standard for a product description, its allied standards, the latest edition and amendments, and the mandatory certification (ISI mark, CRS, hallmarking). The same knowledge then drafts and checks tenders, scores bids and records the award.",
                 hi: "स्पेकश्योर भारतीय मानकों के पूरे संग्रह — उनके स्कोप, मानक संदर्भ, परीक्षण विधियाँ और शब्दावली — को पढ़कर किसी उत्पाद विवरण के लिए सही मानक, उससे संबद्ध मानक, नवीनतम संस्करण व संशोधन और अनिवार्य प्रमाणन (आईएसआई चिह्न, सीआरएस, हॉलमार्किंग) सुझाता है। यही ज्ञान निविदा का प्रारूप बनाता व जाँचता है, बोलियों का मूल्यांकन करता है और अनुबंध दर्ज करता है।" },
  "home.cta.officer": { en: "Create a tender", hi: "निविदा बनाएँ" },
  "home.cta.contractor": { en: "Find tenders & bid", hi: "निविदा खोजें व बोली दें" },
  "home.cta.demo": { en: "Load demo data", hi: "डेमो डेटा लोड करें" },
  "home.who": { en: "Choose your workspace", hi: "अपना कार्यक्षेत्र चुनें" },
  "home.lifecycle": { en: "One connected lifecycle", hi: "एक जुड़ा हुआ जीवनचक्र" },
  "home.stats": { en: "Portal at a glance", hi: "पोर्टल एक नज़र में" },
  "home.latest": { en: "Latest tenders", hi: "नवीनतम निविदाएँ" },
  "home.whatsnew": { en: "Regulatory updates", hi: "नियामक अद्यतन" },
  "home.why": { en: "Why it is different", hi: "यह अलग क्यों है" },
  // dashboards
  "dash.officer.title": { en: "Procurement Officer Workspace", hi: "क्रय अधिकारी कार्यक्षेत्र" },
  "dash.contractor.title": { en: "Contractor Workspace", hi: "ठेकेदार कार्यक्षेत्र" },
  "dash.pending": { en: "Pending actions", hi: "लंबित कार्य" },
  "dash.pipeline": { en: "Tender pipeline", hi: "निविदा पाइपलाइन" },
  "dash.open": { en: "Open for bidding", hi: "बोली हेतु खुली" },
  "dash.mybids": { en: "My bids", hi: "मेरी बोलियाँ" },
  "stage.draft": { en: "Draft / vetting", hi: "प्रारूप / जाँच" },
  "stage.published": { en: "Bidding open", hi: "बोली खुली" },
  "stage.bids_closed": { en: "Technical evaluation", hi: "तकनीकी मूल्यांकन" },
  "stage.financial_opened": { en: "Financial opened", hi: "वित्तीय बोली खुली" },
  "stage.awarded": { en: "Awarded", hi: "अनुबंधित" },
  "days.left": { en: "days left", hi: "दिन शेष" },
};

type Prefs = {
  lang: Lang; role: Role; fs: string; contrast: boolean; ready: boolean;
  setLang: (l: Lang) => void; setRole: (r: Role) => void; setFs: (f: string) => void; setContrast: (c: boolean) => void;
  t: (key: string, fallback?: string) => string;
};

const Ctx = createContext<Prefs | null>(null);

function load(key: string, dflt: string) {
  try { return localStorage.getItem(`specsure.${key}`) || dflt; } catch { return dflt; }
}
function save(key: string, v: string) {
  try { localStorage.setItem(`specsure.${key}`, v); } catch {}
}

export function PrefsProvider({ children }: { children: ReactNode }) {
  const [lang, setLangS] = useState<Lang>("en");
  const [role, setRoleS] = useState<Role>("officer");
  const [fs, setFsS] = useState("md");
  const [contrast, setContrastS] = useState(false);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    setLangS(load("lang", "en") as Lang);
    setRoleS(load("role", "officer") as Role);
    setFsS(load("fs", "md"));
    setContrastS(load("contrast", "0") === "1");
    setReady(true);
  }, []);
  useEffect(() => {
    const h = document.documentElement;
    h.lang = lang === "hi" ? "hi" : "en";
    h.dataset.fs = fs;
    h.dataset.contrast = contrast ? "high" : "normal";
  }, [lang, fs, contrast]);
  const t = useCallback((key: string, fallback?: string) => DICT[key]?.[lang] ?? fallback ?? DICT[key]?.en ?? key, [lang]);
  return (
    <Ctx.Provider value={{
      lang, role, fs, contrast, ready, t,
      setLang: (l) => { setLangS(l); save("lang", l); },
      setRole: (r) => { setRoleS(r); save("role", r); },
      setFs: (f) => { setFsS(f); save("fs", f); },
      setContrast: (c) => { setContrastS(c); save("contrast", c ? "1" : "0"); },
    }}>
      {children}
    </Ctx.Provider>
  );
}

export function usePrefs(): Prefs {
  const c = useContext(Ctx);
  if (!c) throw new Error("usePrefs outside PrefsProvider");
  return c;
}

/** Bilingual inline text: <T en="…" hi="…" /> */
export function T({ en, hi }: { en: string; hi: string }) {
  const { lang } = usePrefs();
  return <>{lang === "hi" ? hi : en}</>;
}

export const inr = (v: number | null | undefined, digits = 0) =>
  v === null || v === undefined ? "—" : "₹" + Number(v).toLocaleString("en-IN", { maximumFractionDigits: digits, minimumFractionDigits: digits });
