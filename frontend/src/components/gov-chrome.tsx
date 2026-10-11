"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ArrowUp, Bell, BookOpen, ChevronDown, ChevronRight, Contrast, HelpCircle, Home, Landmark, Menu, Search, UserCog, Briefcase, Eye, X } from "lucide-react";
import { corpusStats, getSystemHealth, notifications } from "@/lib/api";
import { Role, usePrefs } from "@/lib/prefs";
import { Bi, DETAIL_LABEL, NAV_GROUPS, locate } from "@/lib/nav";
import { GLOSSARY } from "@/lib/glossary";

/** Portal seal — an original mark (document + verified tick inside a gear ring). Deliberately not a national emblem. */
export function PortalSeal({ size = 56 }: { size?: number }) {
  const teeth = Array.from({ length: 24 }, (_, i) => i * 15);
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" role="img" aria-label="SpecSure portal seal">
      <circle cx="32" cy="32" r="31" fill="#0f2748" />
      {teeth.map((a) => (
        <rect key={a} x="30.6" y="2.5" width="2.8" height="5" rx="0.8" fill="#b7862b" transform={`rotate(${a} 32 32)`} />
      ))}
      <circle cx="32" cy="32" r="24" fill="#fff" stroke="#b7862b" strokeWidth="1.5" />
      <circle cx="32" cy="32" r="20.5" fill="none" stroke="#0f2748" strokeWidth="0.8" strokeDasharray="1.5 1.5" />
      <path d="M23 18h13l6 6v20a2 2 0 0 1-2 2H23a2 2 0 0 1-2-2V20a2 2 0 0 1 2-2z" fill="#eef4fb" stroke="#1d4f93" strokeWidth="1.6" />
      <path d="M36 18v6h6" fill="none" stroke="#1d4f93" strokeWidth="1.6" />
      <path d="M25 27h10M25 31h12M25 35h7" stroke="#1d4f93" strokeWidth="1.4" strokeLinecap="round" />
      <circle cx="39" cy="40" r="7" fill="#138808" />
      <path d="M35.8 40.2l2.2 2.2 4.3-4.6" fill="none" stroke="#fff" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M21 50h22" stroke="#ff9933" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  );
}

function UtilityBar() {
  const { t, lang, setLang, fs, setFs, contrast, setContrast } = usePrefs();
  return (
    <div className="bg-[#0a1a31] text-[#dbe5f3] text-[0.8125rem] no-print">
      <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 min-h-[34px] flex items-center justify-between gap-x-4 py-1">
        <div className="flex items-center gap-2 min-w-0" title={t("proto.banner")}>
          <Landmark className="w-3.5 h-3.5 shrink-0 text-[#ff9933]" aria-hidden />
          <span className="truncate">{t("proto.banner")}</span>
          <span className="hidden 2xl:inline shrink-0 opacity-70">· PS SIH26108 · Team CodeNova</span>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <a href="#main" className="hidden md:inline hover:underline">{t("skip")}</a>
          <span className="hidden md:inline opacity-40">|</span>
          <div className="flex items-center gap-1" role="group" aria-label="Text size">
            {[["sm", "A-"], ["md", "A"], ["lg", "A+"], ["xl", "A++"]].map(([k, l]) => (
              <button key={k} onClick={() => setFs(k)} aria-pressed={fs === k}
                className={`px-1.5 rounded ${fs === k ? "bg-white text-[#0a1a31] font-bold" : "hover:bg-white/10"}`}>{l}</button>
            ))}
          </div>
          <button onClick={() => setContrast(!contrast)} aria-pressed={contrast} className="flex items-center gap-1 hover:underline" title={t("contrast")}>
            <Contrast className="w-3.5 h-3.5" /><span className="hidden md:inline">{t("contrast")}</span>
          </button>
          <span className="opacity-40">|</span>
          <div className="flex items-center gap-1" role="group" aria-label="Language">
            <button onClick={() => setLang("en")} aria-pressed={lang === "en"} className={`px-1.5 rounded ${lang === "en" ? "bg-white text-[#0a1a31] font-bold" : "hover:bg-white/10"}`}>English</button>
            <button onClick={() => setLang("hi")} aria-pressed={lang === "hi"} className={`px-1.5 rounded ${lang === "hi" ? "bg-white text-[#0a1a31] font-bold" : "hover:bg-white/10"}`}>हिन्दी</button>
          </div>
        </div>
      </div>
    </div>
  );
}

function RoleSwitch() {
  const { role, setRole, t } = usePrefs();
  const router = useRouter();
  const opts: [Role, string, any, string][] = [
    ["officer", t("role.officer"), UserCog, "/officer"],
    ["contractor", t("role.contractor"), Briefcase, "/contractor"],
    ["citizen", t("role.citizen"), Eye, "/market"],
  ];
  return (
    <div className="hidden md:flex items-center gap-2">
      <span className="hidden 2xl:inline text-[0.8125rem] font-semibold uppercase tracking-wider text-slate-500">{t("role.label")}</span>
      <div className="flex rounded-md border border-[#c9d5e6] overflow-hidden bg-white" role="radiogroup" aria-label="Role">
        {opts.map(([r, label, Icon, href]) => (
          <button key={r} role="radio" aria-checked={role === r} title={label} aria-label={label} onClick={() => { setRole(r); router.push(href); }}
            className={`px-2.5 py-1.5 text-[0.875rem] font-semibold flex items-center gap-1.5 border-r last:border-r-0 border-[#c9d5e6] ${role === r ? "bg-[#0f2748] text-white" : "text-[#0f2748] hover:bg-[#eef4fb]"}`}>
            <Icon className="w-4 h-4" /><span className="hidden xl:inline">{label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------------------------------------
   Main navigation — pages grouped by who uses them, each with a one-line description,
   so people can find a page without knowing its internal name.
   ------------------------------------------------------------------------------------------------ */
function MainNav({ mobileOpen, onNavigate }: { mobileOpen: boolean; onNavigate: () => void }) {
  const { lang } = usePrefs();
  const pathname = usePathname() || "/";
  const [open, setOpen] = useState<string | null>(null);
  const ref = useRef<HTMLDivElement>(null);
  const timer = useRef<any>(null);
  const L = (b: Bi) => (lang === "hi" ? b.hi : b.en);
  const here = locate(pathname);

  useEffect(() => { setOpen(null); }, [pathname]);
  useEffect(() => {
    const onDoc = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(null); };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(null); };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("mousedown", onDoc); document.removeEventListener("keydown", onKey); };
  }, []);
  const hoverOpen = (id: string) => { clearTimeout(timer.current); timer.current = setTimeout(() => setOpen(id), 80); };
  const hoverClose = () => { clearTimeout(timer.current); timer.current = setTimeout(() => setOpen(null), 180); };

  return (
    <nav className="gov-nav bg-[#0f2748] text-white shadow-md sticky top-0 z-50 print:hidden" aria-label="Main">
      <div ref={ref} className="max-w-[1400px] mx-auto px-2 sm:px-4 lg:px-6">
        {/* desktop */}
        <ul className="hidden lg:flex items-stretch">
          <li>
            <Link href="/" aria-current={pathname === "/" ? "page" : undefined} className="navtop flex items-center gap-1.5 px-3.5 py-3 text-[0.9375rem] font-semibold hover:bg-white/10" title={L({ en: "Home", hi: "मुखपृष्ठ" })}>
              <Home className="w-4 h-4" /><span className="sr-only">{L({ en: "Home", hi: "मुखपृष्ठ" })}</span>
            </Link>
          </li>
          {NAV_GROUPS.map((g) => {
            const active = here.group?.id === g.id;
            if (g.href) {
              return (
                <li key={g.id}>
                  <Link href={g.href} aria-current={active ? "page" : undefined} className="navtop flex items-center gap-2 px-4 py-3 text-[0.9375rem] font-semibold whitespace-nowrap hover:bg-white/10">
                    <g.icon className="w-4 h-4 opacity-80" />{L(g.label)}
                  </Link>
                </li>
              );
            }
            const isOpen = open === g.id;
            return (
              <li key={g.id} className="relative" onMouseEnter={() => hoverOpen(g.id)} onMouseLeave={hoverClose}>
                <button type="button" aria-expanded={isOpen} aria-haspopup="true" aria-current={active ? "page" : undefined}
                  onClick={() => setOpen(isOpen ? null : g.id)}
                  className={`navtop h-full flex items-center gap-2 px-4 py-3 text-[0.9375rem] font-semibold whitespace-nowrap hover:bg-white/10 ${isOpen ? "bg-white/10" : ""}`}>
                  <g.icon className="w-4 h-4 opacity-80" />{L(g.label)}
                  <ChevronDown className={`w-4 h-4 transition-transform ${isOpen ? "rotate-180" : ""}`} />
                </button>
                {isOpen && (
                  <div className="nav-panel absolute left-0 top-full mt-0 w-[440px] bg-white text-[#0f2748] rounded-b-lg shadow-2xl border border-[#d5deea] border-t-4 border-t-[#ff9933] p-2 z-50">
                    <ul>
                      {g.items.map((it) => {
                        const on = here.item?.href === it.href;
                        return (
                          <li key={it.href}>
                            <Link href={it.href} onClick={() => setOpen(null)} aria-current={on ? "page" : undefined}
                              className={`flex gap-3 rounded-md p-3 hover:bg-[#eef4fb] focus:bg-[#eef4fb] ${on ? "bg-[#eef4fb]" : ""}`}>
                              <span className={`w-9 h-9 rounded-md flex items-center justify-center shrink-0 ${on ? "bg-[#0f2748] text-white" : "bg-[#eef4fb] text-[#1d4f93]"}`}><it.icon className="w-[18px] h-[18px]" /></span>
                              <span className="min-w-0">
                                <span className="block font-bold text-[0.9375rem] leading-snug">{L(it.label)}</span>
                                <span className="block text-[0.8125rem] text-[#475569] leading-snug mt-0.5">{L(it.desc)}</span>
                              </span>
                            </Link>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                )}
              </li>
            );
          })}
        </ul>

        {/* mobile / tablet */}
        {mobileOpen && (
          <div className="lg:hidden py-2 max-h-[75vh] overflow-y-auto">
            <Link href="/" onClick={onNavigate} className="navmob flex items-center gap-2 px-3 py-2.5 font-semibold rounded hover:bg-white/10"><Home className="w-4 h-4" />{L({ en: "Home", hi: "मुखपृष्ठ" })}</Link>
            {NAV_GROUPS.map((g) => (
              <div key={g.id} className="mt-2">
                <div className="px-3 pt-2 pb-1 text-[0.75rem] font-bold uppercase tracking-wider text-[#ffb866]">{L(g.label)}</div>
                {g.items.map((it) => (
                  <Link key={it.href} href={it.href} onClick={onNavigate} aria-current={here.item?.href === it.href ? "page" : undefined}
                    className="navmob flex items-start gap-3 px-3 py-2.5 rounded hover:bg-white/10">
                    <it.icon className="w-4 h-4 mt-1 shrink-0 opacity-80" />
                    <span><span className="block font-semibold">{L(it.label)}</span><span className="block text-[0.8125rem] text-[#c9d5e6] leading-snug">{L(it.desc)}</span></span>
                  </Link>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>
    </nav>
  );
}

/* Glossary drawer — plain-language meaning of every acronym used in the portal. */
function GlossaryDrawer({ onClose }: { onClose: () => void }) {
  const { lang } = usePrefs();
  const [q, setQ] = useState("");
  const input = useRef<HTMLInputElement>(null);
  useEffect(() => {
    input.current?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);
  const list = GLOSSARY.filter((g) => !q || (g.term + " " + (g.full || "") + " " + g.en + " " + g.hi).toLowerCase().includes(q.toLowerCase()));
  return (
    <div className="fixed inset-0 z-[70] print:hidden" role="dialog" aria-modal="true" aria-labelledby="glossary-h">
      <div className="absolute inset-0 bg-[#0a1a31]/50" onClick={onClose} />
      <aside className="nav-panel absolute right-0 top-0 bottom-0 w-full max-w-md bg-white shadow-2xl flex flex-col">
        <div className="px-5 py-4 border-b border-[#d5deea] flex items-start justify-between gap-3">
          <div>
            <h2 id="glossary-h" className="text-lg font-extrabold text-[#0f2748] flex items-center gap-2"><BookOpen className="w-5 h-5" />{lang === "hi" ? "शब्दावली" : "Glossary — what the terms mean"}</h2>
            <p className="text-[0.875rem] text-[#475569] mt-0.5">{lang === "hi" ? "पोर्टल में प्रयुक्त शब्दों के सरल अर्थ।" : "Plain-language meanings of the abbreviations used on this portal."}</p>
          </div>
          <button onClick={onClose} className="p-2 rounded-md hover:bg-[#eef4fb]" aria-label="Close glossary"><X className="w-5 h-5" /></button>
        </div>
        <div className="px-5 py-3 border-b border-[#e2e8f0]">
          <label className="relative block">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#64748b]" />
            <input ref={input} value={q} onChange={(e) => setQ(e.target.value)} placeholder={lang === "hi" ? "शब्द खोजें, जैसे QCO" : "Search a term, e.g. QCO"}
              className="w-full pl-9 pr-3 py-2.5 rounded-md border border-[#c9d5e6] text-[0.9375rem] outline-none focus:border-[#1d4f93]" />
          </label>
        </div>
        <dl className="flex-1 overflow-y-auto px-5 py-2 divide-y divide-[#e2e8f0]">
          {list.map((g) => (
            <div key={g.term} className="py-3">
              <dt className="font-bold text-[#0f2748]">{g.term}{g.full && <span className="font-normal text-[#475569]"> — {g.full}</span>}</dt>
              <dd className="text-[0.9375rem] text-[#334155] mt-1 leading-relaxed">{lang === "hi" ? g.hi : g.en}</dd>
            </div>
          ))}
          {!list.length && <p className="py-8 text-center text-[#64748b]">{lang === "hi" ? "कोई शब्द नहीं मिला।" : "No matching term."}</p>}
        </dl>
      </aside>
    </div>
  );
}

function BackToTop() {
  const [show, setShow] = useState(false);
  useEffect(() => {
    const on = () => setShow(window.scrollY > 700);
    on();
    window.addEventListener("scroll", on, { passive: true });
    return () => window.removeEventListener("scroll", on);
  }, []);
  if (!show) return null;
  return (
    <button onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })} aria-label="Back to top"
      className="fixed bottom-5 right-5 z-40 w-11 h-11 rounded-full bg-[#0f2748] text-white shadow-lift flex items-center justify-center hover:bg-[#1d4f93] print:hidden">
      <ArrowUp className="w-5 h-5" />
    </button>
  );
}

export function GovHeader() {
  const { lang } = usePrefs();
  const pathname = usePathname() || "/";
  const [health, setHealth] = useState<any>(null);
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);
  const [help, setHelp] = useState(false);
  useEffect(() => {
    getSystemHealth().then((h: any) => {
      setHealth(h);
      corpusStats().then((c: any) => setHealth({ ...h, corpus: c.designations })).catch(() => {});
    }).catch(() => setHealth({ status: "offline" }));
    notifications().then((n) => setUnread(n.filter((x: any) => !x.read).length)).catch(() => {});
    setOpen(false);
  }, [pathname]);
  const { t } = usePrefs();
  return (
    <>
    <header className="print:hidden">
      <UtilityBar />
      <div className="tricolour h-[3px]" aria-hidden />
      <div className="bg-white border-b border-[#d5deea]">
        <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 py-3 flex items-center justify-between gap-4">
          <Link href="/" className="flex items-center gap-3 min-w-0" aria-label="SpecSure home">
            <span className="shrink-0 hidden sm:block"><PortalSeal size={54} /></span>
            <span className="shrink-0 sm:hidden"><PortalSeal size={40} /></span>
            <div className="min-w-0">
              <div className="flex items-baseline gap-2 flex-wrap">
                <span className="text-[1.375rem] leading-none font-extrabold tracking-tight text-[#0f2748]">SpecSure</span>
                <span className="hidden sm:inline text-[1.125rem] leading-none font-bold text-[#0f2748]/80">स्पेकश्योर</span>
              </div>
              <div className="hidden sm:block text-[0.875rem] font-semibold text-[#1d4f93] mt-1 truncate">{t("portal.tagline")}</div>
              <div className="text-[0.8125rem] text-slate-500 truncate hidden sm:block">{t("portal.sub")}</div>
            </div>
          </Link>
          <div className="flex items-center gap-2 sm:gap-3 shrink-0">
            <span className="hidden xl:flex items-center gap-1.5 text-[0.8125rem] text-slate-500 mr-1" title={health?.status === "ok" ? "All analysis engines are running" : undefined}>
              <span className={`w-2 h-2 rounded-full ${health?.status === "ok" ? "bg-[#138808]" : "bg-[#ff9933]"}`} aria-hidden />
              {health?.status === "ok" ? `Online · ${health?.corpus ? health.corpus.toLocaleString("en-IN") : health?.total_standards ?? "—"} standards` : health?.status === "offline" ? "Server offline" : "Connecting…"}
            </span>
            <RoleSwitch />
            <button onClick={() => setHelp(true)} className="flex items-center gap-1.5 px-2.5 py-2 rounded-md border border-[#c9d5e6] text-[#0f2748] hover:bg-[#eef4fb]" title="What do these terms mean?" aria-label="Open glossary">
              <HelpCircle className="w-4 h-4" /><span className="hidden md:inline text-[0.875rem] font-semibold">{lang === "hi" ? "शब्दावली" : "Glossary"}</span>
            </button>
            <Link href="/radar" className="relative p-2 rounded-md border border-[#c9d5e6] hover:bg-[#eef4fb]" title="Notifications" aria-label={`Notifications: ${unread} unread`}>
              <Bell className="w-4 h-4 text-[#0f2748]" />
              {unread > 0 && <span className="absolute -top-1.5 -right-1.5 min-w-[18px] h-[18px] px-1 rounded-full bg-[#c0262d] text-[0.6875rem] font-bold text-white flex items-center justify-center">{unread}</span>}
            </Link>
            <button className="lg:hidden flex items-center gap-1.5 px-2.5 py-2 rounded-md border border-[#c9d5e6] text-[#0f2748]" onClick={() => setOpen(!open)} aria-expanded={open} aria-label="Menu">
              {open ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}<span className="text-[0.875rem] font-semibold">{lang === "hi" ? "मेनू" : "Menu"}</span>
            </button>
          </div>
        </div>
      </div>
    </header>
      <MainNav mobileOpen={open} onNavigate={() => setOpen(false)} />
      <Breadcrumbs />
      {help && <GlossaryDrawer onClose={() => setHelp(false)} />}
      <BackToTop />
    </>
  );
}

function Breadcrumbs() {
  const pathname = usePathname() || "/";
  const { lang } = usePrefs();
  if (pathname === "/") return null;
  const L = (b: Bi) => (lang === "hi" ? b.hi : b.en);
  const parts = pathname.split("/").filter(Boolean);
  const top = parts[0];
  const { group, item } = locate(pathname);
  const detail = parts.length > 1 ? decodeURIComponent(parts.slice(1).join(" / ")) : null;
  const crumbs: { label: string; href?: string; mono?: boolean }[] = [];
  if (group && !group.href) crumbs.push({ label: L(group.label) });
  if (item) crumbs.push({ label: L(item.label), href: detail ? item.href : undefined });
  else crumbs.push({ label: top });
  if (detail) {
    const d = DETAIL_LABEL[top];
    crumbs.push({ label: top === "standards" ? detail : d ? `${L(d)} · ${detail}` : detail, mono: !d });
  }
  return (
    <div className="bg-[#e8eef6] border-b border-[#d5deea] print:hidden">
      <ol className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 py-2 flex flex-wrap items-center gap-1 text-[0.875rem] text-[#334155]" aria-label="Breadcrumb">
        <li><Link href="/" className="hover:underline text-[#1d4f93] font-semibold">{L({ en: "Home", hi: "मुखपृष्ठ" })}</Link></li>
        {crumbs.map((c, i) => (
          <li key={i} className="flex items-center gap-1 min-w-0">
            <ChevronRight className="w-3.5 h-3.5 shrink-0 text-[#64748b]" />
            {c.href ? <Link href={c.href} className="hover:underline text-[#1d4f93] font-semibold">{c.label}</Link>
                    : <span aria-current={i === crumbs.length - 1 ? "page" : undefined} className={`${i === crumbs.length - 1 ? "font-semibold text-[#0f2748]" : "text-[#475569]"} ${c.mono ? "font-mono" : ""} truncate`}>{c.label}</span>}
          </li>
        ))}
      </ol>
    </div>
  );
}

export function GovFooter() {
  const { t, lang } = usePrefs();
  const L = (b: Bi) => (lang === "hi" ? b.hi : b.en);
  const col = (title: string, links: [string, string][]) => (
    <div>
      <h3 className="text-[0.9375rem] font-bold text-white mb-2 pb-1 border-b border-white/15">{title}</h3>
      <ul className="space-y-1.5">
        {links.map(([l, h]) => <li key={h + l}><Link href={h} className="text-[0.875rem] text-[#c9d5e6] hover:text-white hover:underline">{l}</Link></li>)}
      </ul>
    </div>
  );
  return (
    <footer className="mt-16 print:hidden">
      <div className="tricolour h-[3px]" aria-hidden />
      <div className="bg-[#0f2748] text-[#c9d5e6]">
        <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 py-10 grid gap-8 sm:grid-cols-2 lg:grid-cols-5">
          <div className="lg:col-span-2 space-y-3">
            <div className="flex items-center gap-3">
              <PortalSeal size={44} />
              <div>
                <div className="text-white font-extrabold text-lg leading-none">SpecSure <span className="font-bold text-white/80">स्पेकश्योर</span></div>
                <div className="text-[0.875rem] mt-1">{t("portal.tagline")}</div>
              </div>
            </div>
            <p className="text-[0.875rem] leading-relaxed max-w-md">
              Decision-support prototype for public procurement: deterministic engines (parser, SMT solver, rule engine, temporal knowledge graph)
              produce every finding with its source; AI-generated text is labelled; the competent authority decides.
            </p>
          </div>
          {NAV_GROUPS.filter((g) => g.id !== "audit").slice(0, 3).map((g) => (
            <div key={g.id}>{col(L(g.label), g.items.map((it) => [L(it.label), it.href] as [string, string]))}</div>
          ))}
          <div className="sm:col-span-2 lg:col-span-5 flex flex-wrap gap-x-6 gap-y-2 pt-2 border-t border-white/10 text-[0.875rem]">
            {[...NAV_GROUPS.find((g) => g.id === "audit")!.items, ...NAV_GROUPS.find((g) => g.id === "about")!.items].map((it) => (
              <Link key={it.href} href={it.href} className="text-[#c9d5e6] hover:text-white hover:underline">{L(it.label)}</Link>
            ))}
            <Link href="/about#accessibility" className="text-[#c9d5e6] hover:text-white hover:underline">{lang === "hi" ? "सुलभता विवरण" : "Accessibility statement"}</Link>
            <Link href="/about#privacy" className="text-[#c9d5e6] hover:text-white hover:underline">{lang === "hi" ? "गोपनीयता व सुरक्षा" : "Privacy & security"}</Link>
          </div>
        </div>
        <div className="border-t border-white/10">
          <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 py-4 flex flex-col md:flex-row gap-2 md:items-center md:justify-between text-[0.8125rem]">
            <span>Prototype by Team CodeNova for Smart India Hackathon 2026 (PS SIH26108 · Smart Automation). <b className="text-white">Not an official Government of India website.</b> Demo organisations, bidders and certificates are fictional.</span>
            <span className="shrink-0">Designed to WCAG 2.1 AA / GIGW 3.0 guidelines · Verify standards on the official BIS portal</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
