"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  ArrowRight, BadgeCheck, Briefcase, CalendarClock, Database, Eye, FileText,
  Gavel, Lock, Mic, Radar, Scale, Search, ShieldCheck, Sigma, UserCog, Wand2,
} from "lucide-react";
import { SearchBar } from "@/components/search-bar";
import { UploadZone } from "@/components/upload-zone";
import { corpusStats, demoIds, demoSeed, officerDashboard, portalStats, radarEvents } from "@/lib/api";
import { T, usePrefs } from "@/lib/prefs";
import { SectionHead, StagePill } from "@/components/gov-ui";

const FIND_EXAMPLES = [
  "PVC insulated copper wire for house wiring, 450/750 V",
  "portable fire extinguisher, dry powder type",
  "helmet for two-wheeler riders",
  "split air conditioner 1.5 ton inverter",
];
const DRAFT_EXAMPLES = [
  "need a tender of 500 light bulbs and 100 meters wire",
  "500 LED bulb 9 watt aur 100 meter 2.5 sq mm taar, 30 din mein",
  "400 bags 53 grade cement and 5 tonnes Fe 500D TMT bars",
];

const ROLES = [
  {
    id: "officer",
    Icon: UserCog,
    accent: "#1d4f93",
    bg: "#1d4f9322",
    iconColor: "#7aa4d8",
    css: "role-card-officer",
    titleEn: "I'm a Procurement Officer",
    titleHi: "मैं क्रय अधिकारी हूँ",
    tagEn: "Create and audit tenders, evaluate bids, award contracts",
    tagHi: "निविदा बनाएँ, जाँचें, मूल्यांकन करें व अनुबंध दें",
    ctaEn: "Open Officer Workspace",
    ctaHi: "अधिकारी कार्यक्षेत्र खोलें",
    href: "/officer",
    stepsEn: [
      "Type one sentence — get a complete, checked draft tender",
      "Check any tender for contradictions, outdated standards and unfair clauses",
      "Compare all bids clause by clause in one table",
      "Apply Make in India and MSE purchase rules, then record the award",
    ],
    stepsHi: [
      "एक वाक्य टाइप करें — सत्यापित निविदा प्रारूप",
      "निविदा जाँच: विरोधाभास, पुराने मानक, लिंटिंग",
      "खंड-दर-खंड बोली मूल्यांकन",
      "एमआईआई/एमएसई नियम व अनुबंध दर्ज करें",
    ],
  },
  {
    id: "contractor",
    Icon: Briefcase,
    accent: "#138808",
    bg: "#13880822",
    iconColor: "#138808",
    css: "role-card-contractor",
    titleEn: "I'm a Contractor / Bidder",
    titleHi: "मैं ठेकेदार / बोलीदाता हूँ",
    tagEn: "Find open tenders, check compliance, submit a bid",
    tagHi: "खुली निविदाएँ, अनुपालन जाँचें, बोली जमा करें",
    ctaEn: "Open Contractor Workspace",
    ctaHi: "ठेकेदार कार्यक्षेत्र खोलें",
    href: "/contractor",
    stepsEn: [
      "Find open tenders that match your products",
      "Upload a scanned test report — the bid form fills itself",
      "See your match score: what is covered and what is missing",
      "Submit a sealed bid and get a verifiable compliance certificate",
    ],
    stepsHi: [
      "अपने उत्पाद से संबंधित खुली निविदाएँ",
      "NABL रिपोर्ट स्कैन करें — फ़ॉर्म स्वतः भरता है",
      "मिलान सूचकांक: क्या है, क्या नहीं",
      "सीलबंद बोली व अनुपालन पासपोर्ट पाएँ",
    ],
  },
  {
    id: "citizen",
    Icon: Eye,
    accent: "#b7862b",
    bg: "#b7862b22",
    iconColor: "#b7862b",
    css: "role-card-citizen",
    titleEn: "I'm a Citizen / Auditor",
    titleHi: "मैं नागरिक / लेखा परीक्षक हूँ",
    tagEn: "Verify decisions, explore standards, read the audit trail",
    tagHi: "निर्णय सत्यापित करें, मानक देखें, लेखा बही पढ़ें",
    ctaEn: "View Audit Ledger",
    ctaHi: "लेखा बही देखें",
    href: "/ledger",
    stepsEn: [
      "Check the tamper-proof record of every decision",
      "Read published clarifications and award decisions",
      "Explore how standards, rules and tests connect",
      "Verify a product’s compliance certificate, even offline",
    ],
    stepsHi: [
      "हैश-श्रृंखलित लेखा बही स्वयं सत्यापित करें",
      "प्रकाशित स्पष्टीकरण व अनुबंध निर्णय पढ़ें",
      "मानक ज्ञान ग्राफ़ देखें",
      "उत्पाद अनुपालन पासपोर्ट ऑफ़लाइन सत्यापित करें",
    ],
  },
];

const LIFECYCLE = [
  { Icon: Mic,   n:"01", en:"Intent to Tender",   hi:"इरादा से निविदा",    d:"Type or speak one sentence — get a checked draft tender in seconds", href:"/studio" },
  { Icon: Lock,  n:"02", en:"Bids collected",      hi:"बोलियाँ एकत्र",      d:"Bids stay sealed; uploaded documents fill the form; a match score shows any gaps", href:"/contractor" },
  { Icon: Scale, n:"03", en:"Evaluate and award",  hi:"मूल्यांकन व अनुबंध", d:"Lowest price first, then Make in India and MSE preference; award letter with sources", href:"/officer" },
  { Icon: Gavel, n:"04", en:"Audit and verify",    hi:"लेखा परीक्षा",       d:"Every step kept in a tamper-proof log; certificates anyone can verify", href:"/ledger" },
];

const WHY = [
  { Icon: Sigma,         t: "Proves contradictions",  d: "Finds clauses that can never be met together — and proves it with the numbers, not just a warning." },
  { Icon: CalendarClock, t: "Time-aware standards",   d: "Checks each Indian Standard as it stood on the tender date, so withdrawn or amended editions are always caught." },
  { Icon: BadgeCheck,    t: "Verifiable compliance",  d: "Compliance certificates are digitally signed, so anyone can check them — even without internet." },
];

export default function HomePage() {
  const { t, lang } = usePrefs();
  const router = useRouter();
  const [q, setQ] = useState(DRAFT_EXAMPLES[0]);
  const [mode, setMode] = useState<"find" | "draft">("find");
  const [fq, setFq] = useState(FIND_EXAMPLES[0]);
  const [stats, setStats] = useState<any>(null);
  const [tenders, setTenders] = useState<any[]>([]);
  const [events, setEvents] = useState<any[]>([]);
  const [demo, setDemo] = useState<any>(null);
  const [seeding, setSeeding] = useState(false);

  const load = () => {
    portalStats().then((p: any) => {
      setStats(p);
      corpusStats().then((c: any) => setStats({ ...p, corpus: c })).catch(() => {});
    }).catch(() => {});
    officerDashboard().then((d: any) => setTenders(d.tenders || [])).catch(() => {});
    radarEvents().then((e: any) => setEvents(e || [])).catch(() => {});
    demoIds().then(setDemo).catch(() => {});
  };
  useEffect(load, []);

  const hi = lang === "hi";
  const news = events.length
    ? events.slice(0, 6).map((e: any) => `${e.event_type?.toUpperCase?.() || "UPDATE"}: ${e.title}`)
    : ["IS 16102 (Part 1):2026 supersedes 2012 edition for LED lamps — tenders citing 2012 are flagged automatically",
       "Make in India: Class-I purchase preference applied in evaluation above Rs 5 lakh",
       "MSE Policy: MSEs within L1 plus 15% may supply up to 25% by matching L1",
       "Quality Control Orders are checked against every generated tender on the publication date"];

  return (
    <div className="pb-4">

      {/* HERO */}
      <section className="gov-hero text-white">
        <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 py-10 lg:py-14 grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_minmax(0,34rem)] gap-8 lg:gap-12 items-center">
          <div className="max-w-3xl min-w-0">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-sm bg-[#ff9933] text-[#0f2748] text-[0.8125rem] font-extrabold uppercase tracking-wider mb-4">
              {t("home.kicker")}
            </div>
            <h1 className="text-3xl sm:text-[2.5rem] font-extrabold leading-[1.12] tracking-tight mb-3">
              Government tenders deserve <span className="text-[#fbbf24]">better than guesswork.</span>
            </h1>
            <p className="text-[1.0625rem] leading-relaxed text-[#dbe5f3] max-w-2xl">
              SpecSure reads procurement documents the way an auditor would, then <strong className="text-white">proves</strong> problems
              with mathematics. From one sentence, it drafts a verified tender in minutes.
            </p>
            <ul className="mt-6 grid sm:grid-cols-3 gap-3 text-[0.9375rem]">
              {[["Find the right Indian Standard", "सही भारतीय मानक खोजें"], ["Check a tender before publishing", "प्रकाशन से पहले निविदा जाँचें"], ["Prove a bid meets every clause", "सिद्ध करें कि बोली हर खंड पूरा करती है"]].map(([en, hv]) => (
                <li key={en} className="flex items-start gap-2 text-[#e6eef8]"><BadgeCheck className="w-5 h-5 text-[#8fd18a] shrink-0" /><T en={en} hi={hv} /></li>
              ))}
            </ul>
          </div>

          {/* QUICK SEARCH WIDGET */}
          <div className="w-full min-w-0">
            <form onSubmit={(e) => { e.preventDefault(); router.push(mode === "find" ? `/recommend?q=${encodeURIComponent(fq)}` : `/studio?q=${encodeURIComponent(q)}`); }}
              className="bg-white text-[#0f2748] rounded-xl shadow-xl overflow-hidden border-t-4 border-[#ff9933]">
              <div className="grid grid-cols-2 border-b border-[#e2e8f0]" role="tablist">
                {([["find", Search, "Find a Standard", "मानक खोजें"], ["draft", Wand2, "Draft a Tender", "निविदा बनाएँ"]] as const).map(([m, Icon, en, hv]) => (
                  <button type="button" key={m} role="tab" aria-selected={mode === m} onClick={() => setMode(m)}
                    className={`py-3 text-[0.9375rem] font-bold flex items-center justify-center gap-2 transition-colors ${mode === m ? "text-[#0f2748] border-b-2 border-[#ff9933] bg-white" : "text-slate-500 bg-[#f8fafc] hover:text-[#0f2748]"}`}>
                    <Icon className="w-4 h-4" /><T en={en} hi={hv} />
                  </button>
                ))}
              </div>
              <div className="p-4 space-y-3">
                <textarea value={mode === "find" ? fq : q} onChange={(e) => mode === "find" ? setFq(e.target.value) : setQ(e.target.value)}
                  rows={2} placeholder={mode === "find" ? "Describe a product or paste a specification…" : "Describe what your office needs…"}
                  className="w-full rounded-lg border border-[#c9d5e6] bg-[#f8fafc] p-3 text-[1rem] focus:border-[#1d4f93] outline-none resize-none" />
                <div className="flex flex-wrap gap-1.5">
                  {(mode === "find" ? FIND_EXAMPLES : DRAFT_EXAMPLES).map((x) => (
                    <button type="button" key={x} onClick={() => mode === "find" ? setFq(x) : setQ(x)}
                      className="text-[0.8125rem] px-2 py-1 rounded bg-[#eef4fb] text-[#1d4f93] hover:bg-[#d6e4f5] text-left truncate max-w-full" title={x}>
                      {x}
                    </button>
                  ))}
                </div>
                <button type="submit" className="w-full py-2.5 rounded-lg bg-[#0f2748] text-white font-bold text-[1rem] flex items-center justify-center gap-2 hover:bg-[#1d4f93] transition-colors">
                  <T en={mode === "find" ? "Find Standard" : "Generate Tender"} hi={mode === "find" ? "मानक खोजें" : "निविदा बनाएँ"} /><ArrowRight className="w-4 h-4" />
                </button>
                {!demo?.studio_tender_id && (
                  <button type="button" disabled={seeding}
                    onClick={async () => { setSeeding(true); try { await demoSeed(); load(); } finally { setSeeding(false); } }}
                    className="w-full py-2 rounded-lg border border-[#c9d5e6] text-[0.9375rem] font-semibold text-slate-400 hover:bg-[#f1f5f9] flex items-center justify-center gap-1.5 transition-colors">
                    <Database className="w-3.5 h-3.5" />{seeding ? "Loading…" : t("home.cta.demo")}
                  </button>
                )}
              </div>
            </form>
          </div>
        </div>
      </section>

      {/* TICKER */}
      <div className="bg-white border-b border-[#d5deea]">
        <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 flex items-stretch">
          <Link href="/radar" className="shrink-0 bg-[#c0262d] text-white text-[0.875rem] font-bold uppercase tracking-wide px-3 flex items-center gap-1.5">
            <Radar className="w-3.5 h-3.5" />{t("home.whatsnew")}
          </Link>
          <div className="overflow-hidden flex-1 py-2" aria-live="off">
            <div className="ticker flex gap-12 whitespace-nowrap w-max text-[0.9375rem] text-[#0f2748]">
              {[...news, ...news].map((n, i) => <span key={i} className="flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-[#ff9933]" />{n}</span>)}
            </div>
          </div>
        </div>
      </div>

      {/* WHO ARE YOU — role entry points on a light surface for easy reading */}
      <section aria-labelledby="who-h" className="bg-[#e8eef6] border-b border-[#d5deea]">
        <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-4">
          <SectionHead id="who-h" title={<T en="Start here — who are you?" hi="यहाँ से शुरू करें — आप कौन हैं?" />}
            sub={<T en="Pick your role to open a workspace with only the tools you need." hi="अपनी भूमिका चुनें — केवल आवश्यक उपकरणों वाला कार्यक्षेत्र खुलेगा।" />} />
          {/* ROLE ENTRY CARDS */}
          <div className="grid md:grid-cols-3 gap-4">
            {ROLES.map((role, i) => (
              <Link key={role.id} href={role.href}
                className={`group bg-white border border-[#d5deea] rounded-xl p-5 shadow-card transition-all hover:-translate-y-0.5 flex flex-col ${role.css} card-reveal card-reveal-d${(i + 1) as 1|2|3}`}>
                <div className="flex items-center gap-3 mb-3">
                  <span className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0" style={{ background: role.bg }}>
                    <role.Icon className="w-5 h-5" style={{ color: role.accent }} />
                  </span>
                  <div>
                    <div className="font-bold text-[1.0625rem] text-[#0f2748] leading-snug">{hi ? role.titleHi : role.titleEn}</div>
                    <div className="text-[0.875rem] text-[#475569] leading-snug mt-0.5">{hi ? role.tagHi : role.tagEn}</div>
                  </div>
                </div>
                <ul className="space-y-2 mb-4 flex-1">
                  {(hi ? role.stepsHi : role.stepsEn).map((s: string, j: number) => (
                    <li key={j} className="flex gap-2 text-[0.9375rem] text-[#334155]">
                      <span className="mt-2 w-1.5 h-1.5 rounded-full shrink-0" style={{ background: role.accent }} />
                      {s}
                    </li>
                  ))}
                </ul>
                <div className="flex items-center justify-center gap-1.5 text-[0.9375rem] font-bold text-white rounded-lg py-2.5 group-hover:gap-2.5 transition-all" style={{ background: role.accent }}>
                  {hi ? role.ctaHi : role.ctaEn}<ArrowRight className="w-4 h-4" />
                </div>
              </Link>
            ))}
          </div>

        </div>
      </section>

      <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 space-y-10 pt-8">

        {/* STATS */}
        <section aria-labelledby="stats-h">
          <h2 id="stats-h" className="sr-only">Portal at a glance</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { en: "Indian Standards", hi: "भारतीय मानक",       v: stats?.corpus?.designations?.toLocaleString("en-IN") ?? stats?.standards, tone: "text-[#0f2748]" },
              { en: "Standards links",  hi: "मानक संबंध",          v: stats?.corpus?.relations?.toLocaleString("en-IN"),                         tone: "text-[#1d4f93]" },
              { en: "Active tenders",  hi: "सक्रिय निविदाएँ",    v: stats?.tenders,                                                             tone: "text-[#138808]" },
              { en: "BIS labs linked", hi: "बीआईएस प्रयोगशालाएँ", v: "482",                                                                      tone: "text-[#b7862b]" },
            ].map(({ en, hv, v, tone }: any) => (
              <div key={en} className="bg-white border border-[#d5deea] rounded-xl p-4 shadow-card">
                <div className={`text-[1.75rem] font-extrabold font-mono leading-none ${tone}`}>{v ?? "—"}</div>
                <div className="text-[0.875rem] font-semibold text-slate-500 uppercase tracking-wide mt-1"><T en={en} hi={hv ?? en} /></div>
              </div>
            ))}
          </div>
        </section>

        {/* LIFECYCLE */}
        <section aria-labelledby="life-h" className="space-y-5">
          <SectionHead id="life-h"
            title={<T en="How a procurement flows through SpecSure" hi="SpecSure में खरीद प्रक्रिया" />}
            sub={<T en="One connected system from intent to award — every step has a source, a proof, and an audit record." hi="इरादे से अनुबंध तक — हर चरण में स्रोत, प्रमाण और लेखा परीक्षा।" />}
          />
          <ol className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {LIFECYCLE.map(({ Icon, n, en, hi: lhi, d, href }) => (
              <li key={n}>
                <Link href={href} className="group flex flex-col gap-3 bg-white border border-[#d5deea] rounded-xl p-5 hover:border-[#1d4f93] hover:shadow-lift transition-all h-full">
                  <div className="flex items-center justify-between">
                    <span className="w-10 h-10 rounded-lg bg-[#0f2748] text-white flex items-center justify-center"><Icon className="w-5 h-5" /></span>
                    <span className="text-[0.8125rem] font-mono font-extrabold text-[#ff9933]">{n}</span>
                  </div>
                  <div>
                    <div className="text-[1rem] font-bold text-[#0f2748] leading-snug"><T en={en} hi={lhi} /></div>
                    <div className="text-[0.875rem] text-slate-500 mt-1 leading-snug">{d}</div>
                  </div>
                  <div className="mt-auto text-[0.875rem] font-semibold text-[#1d4f93] flex items-center gap-1 group-hover:gap-2 transition-all">
                    Open <ArrowRight className="w-3.5 h-3.5" />
                  </div>
                </Link>
              </li>
            ))}
          </ol>
        </section>

        {/* LATEST TENDERS + UPDATES */}
        <section className="grid lg:grid-cols-3 gap-6">
          <div className="space-y-3 lg:col-span-2 min-w-0">
            <SectionHead title={<T en="Latest tenders" hi="नवीनतम निविदाएँ" />}
              right={<Link href="/market" className="text-[0.9375rem] font-semibold text-[#1d4f93] hover:underline flex items-center gap-1">View all <ArrowRight className="w-3.5 h-3.5" /></Link>} />
            <div className="bg-white border border-[#d5deea] rounded-xl overflow-hidden shadow-card">
              {tenders.length ? (
                <div className="divide-y divide-[#e2e8f0]">
                  {tenders.slice(0, 5).map((x) => (
                    <div key={x.id} className="p-4 flex items-center gap-4 hover:bg-[#f8fafc] transition-colors">
                      <div className="flex-1 min-w-0">
                        <Link href={x.stage === "published" ? `/market/${x.id}` : `/tenders/${x.id}`} className="font-semibold text-[1rem] text-[#1d4f93] hover:underline block truncate">{x.title}</Link>
                        <div className="text-[0.875rem] text-slate-500 flex items-center gap-2 mt-0.5">
                          <span className="font-mono">{x.reference_no || x.id?.slice(0, 8)}</span>
                          {x.organisation && <><span>·</span><span className="truncate">{x.organisation}</span></>}
                        </div>
                      </div>
                      <div className="flex items-center gap-3 shrink-0">
                        <StagePill stage={x.stage} />
                        {x.bid_due && <span className="text-[0.875rem] text-slate-500 whitespace-nowrap">{x.bid_due}</span>}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-8 text-center text-slate-500">
                  <p className="text-[1rem] mb-3">No tenders yet.</p>
                  <button disabled={seeding} onClick={async () => { setSeeding(true); try { await demoSeed(); load(); } finally { setSeeding(false); } }}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[#0f2748] text-white text-[0.9375rem] font-semibold hover:bg-[#1d4f93] transition-colors">
                    <Database className="w-4 h-4" />{seeding ? "Loading…" : "Load demo data"}
                  </button>
                </div>
              )}
            </div>
          </div>
          <div className="space-y-3 min-w-0">
            <SectionHead title={<T en="Regulatory updates" hi="नियामक अद्यतन" />} right={<Link href="/radar" className="text-[0.9375rem] font-semibold text-[#1d4f93] hover:underline flex items-center gap-1"><T en="Open radar" hi="रडार खोलें" /> <ArrowRight className="w-3.5 h-3.5" /></Link>} />
            <ul className="bg-white border border-[#d5deea] rounded-xl divide-y divide-[#e2e8f0] shadow-card">
              {news.slice(0, 4).map((n, i) => (
                <li key={i} className="p-3.5 flex gap-3 hover:bg-[#f8fafc] transition-colors">
                  <FileText className="w-4 h-4 text-[#1d4f93] shrink-0 mt-0.5" />
                  <span className="text-[0.9375rem] text-[#0f2748] leading-snug">{n}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* WHY DIFFERENT */}
        <section className="space-y-4">
          <SectionHead
            title={<T en="Why SpecSure is different" hi="SpecSure अलग क्यों है" />}
            sub={<T en="Rule-based engines make every finding; AI only helps with wording. Each finding shows its source document, clause and date." hi="निर्णय नियतात्मक इंजन करते हैं; एआई केवल शब्दांकन करता है।" />}
          />
          <div className="grid sm:grid-cols-3 gap-4">
            {WHY.map(({ Icon, t: tt, d }) => (
              <div key={tt} className="bg-white border border-[#d5deea] rounded-xl p-5 flex gap-4 shadow-card hover:shadow-lift hover:-translate-y-0.5 transition-all">
                <span className="w-11 h-11 rounded-lg bg-[#eef4fb] text-[#1d4f93] flex items-center justify-center shrink-0"><Icon className="w-5 h-5" /></span>
                <div>
                  <div className="font-bold text-[1rem] text-[#0f2748] mb-1">{tt}</div>
                  <p className="text-[0.9375rem] text-slate-400 leading-relaxed">{d}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* STANDARDS SEARCH */}
        <section className="space-y-4">
          <SectionHead
            title={<T en="Search 29,875 Indian Standards" hi="29,875 भारतीय मानक खोजें" />}
            sub={<T en="Type an IS number or describe a product in English or any Indian language." hi="अंग्रेज़ी या किसी भारतीय भाषा में उत्पाद का वर्णन करें।" />}
          />
          <SearchBar />
          <details className="bg-white border border-[#d5deea] rounded-xl p-4 group">
            <summary className="cursor-pointer font-semibold text-[1rem] text-[#0f2748] flex items-center gap-2 list-none">
              <span className="w-6 h-6 rounded-md bg-[#eef4fb] flex items-center justify-center text-[#1d4f93]">+</span>
              Analyse a specification document (PDF / DOCX / scan)
            </summary>
            <div className="pt-4"><UploadZone /></div>
          </details>
        </section>

        {/* DISCLAIMER */}
        <p className="text-[0.875rem] text-slate-500 flex items-start gap-2 bg-[#fff8ec] border border-[#f2d8a7] rounded-xl p-3.5">
          <ShieldCheck className="w-4 h-4 text-[#b7862b] shrink-0 mt-0.5" />
          Decision-support prototype. Standards shown carry a verification state; confirm on the official BIS, DPIIT and MSME portals before use.
          The competent authority takes every procurement decision.{" "}
          <Link href="/about#disclaimer" className="underline whitespace-nowrap">Read the disclaimer</Link>.
        </p>

      </div>
    </div>
  );
}
