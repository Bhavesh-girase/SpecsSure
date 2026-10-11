"use client";

import { Chrome, Download, FileSearch, ListChecks, MousePointerClick, PanelRight } from "lucide-react";
import { Notice, PageHead, SectionHead } from "@/components/gov-ui";

const SHOTS = [
  { src: "/extension/ext_listing.png", title: "On the bid listing", text: "Every bid card gets a SpecSure strip: the standard it names and whether that edition is in force, superseded or withdrawn, amendments, the certification scheme — or SpecSure’s suggestion when the bid names none." },
  { src: "/extension/ext_panel_document.png", title: "On a bid document", text: "One click reads the bid PDF open in the tab: items being bought, the IS for each, cited standards checked against the BIS portal, and a copy-ready specification clause." },
  { src: "/extension/ext_panel_search.png", title: "Anywhere", text: "Select text → right-click → Find Indian Standards; or type in the side panel in English or an Indian language." },
];

export default function ExtensionPage() {
  return (
    <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-8">
      <PageHead icon={Chrome} kicker="Where procurement happens" title="SpecSure in the browser — on the e-procurement portal itself"
        sub="Officers draft and bidders read tenders on GeM and CPPP, not in a separate tool. The SpecSure extension puts the Indian Standards check next to the bid they already have open."
        right={<a href="/specsure-extension.zip" className="px-4 py-2 rounded-md bg-[#0f2748] text-white font-bold text-sm flex items-center gap-2"><Download className="w-4 h-4" />Download (zip)</a>} />

      <section className="grid lg:grid-cols-3 gap-5">
        {SHOTS.map((s) => (
          <figure key={s.src} className="bg-white border border-[#d5deea] rounded-lg shadow-card overflow-hidden">
            <div className="bg-[#f1f5f9] h-[340px] overflow-hidden border-b border-[#e2e8f0]">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={s.src} alt={s.title} className="w-full object-cover object-top" />
            </div>
            <figcaption className="p-4"><div className="font-extrabold text-[#0f2748]">{s.title}</div><p className="text-[0.9375rem] text-slate-400 mt-1">{s.text}</p></figcaption>
          </figure>
        ))}
      </section>

      <section className="grid md:grid-cols-2 gap-5">
        <div className="bg-white border border-[#d5deea] rounded-lg p-5 shadow-card space-y-3">
          <SectionHead title="Install in two minutes" />
          <ol className="list-decimal pl-5 space-y-1.5 text-[0.9375rem] text-[#334155]">
            <li>Run the SpecSure backend (port 8000) — the extension talks only to it.</li>
            <li>Chrome or Edge → <code>chrome://extensions</code> → turn on <b>Developer mode</b>.</li>
            <li><b>Load unpacked</b> → choose the unzipped <code>extension</code> folder.</li>
            <li>Pin SpecSure and open <code>bidplus.gem.gov.in/all-bids</code>, or any tender PDF, and click the icon.</li>
          </ol>
          <Notice tone="info">Prototype for SIH 2026 (PS SIH26108). Not affiliated with GeM, CPPP or BIS. It reads the page only to send item names or the open document to your own SpecSure server.</Notice>
        </div>
        <div className="bg-white border border-[#d5deea] rounded-lg p-5 shadow-card space-y-3">
          <SectionHead title="Why this matters" />
          <ul className="space-y-2 text-[0.9375rem] text-[#334155]">
            <li className="flex gap-2"><ListChecks className="w-4 h-4 mt-0.5 text-[#1d4f93] shrink-0" />GeM names many categories after a standard (“… ISI Marked to IS 15683”). SpecSure checks that edition against the BIS portal — e.g. road-lighting luminaires now carry IS 10322 (Part 5/Sec 3):<b>2026</b>.</li>
            <li className="flex gap-2"><FileSearch className="w-4 h-4 mt-0.5 text-[#1d4f93] shrink-0" />Bid documents are read item by item, with the standards the document forgets (test methods its own standard calls up).</li>
            <li className="flex gap-2"><PanelRight className="w-4 h-4 mt-0.5 text-[#1d4f93] shrink-0" />The side panel stays open while the officer drafts — the clause goes straight to the clipboard.</li>
            <li className="flex gap-2"><MousePointerClick className="w-4 h-4 mt-0.5 text-[#1d4f93] shrink-0" />Nothing to integrate on the portal side: works on any page today, and the same API is ready for a native GeM integration.</li>
          </ul>
        </div>
      </section>
    </div>
  );
}
