// SpecSure extension — annotates bid listings (GeM "All bids" cards) with the Indian Standard each item names,
// its edition in force / withdrawal / amendments and compulsory certification, or a suggested standard.
(() => {
  const DONE = "data-specsure";
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  function itemTextOf(card) {
    const rows = card.querySelectorAll(".card-body .row, .card-body div");
    for (const r of rows) {
      const strong = r.querySelector("strong");
      if (strong && /Items\s*:/i.test(strong.textContent || "")) {
        const a = r.querySelector("a[data-content]");
        const full = a ? a.getAttribute("data-content") : (r.textContent || "").replace(/Items\s*:/i, "");
        return { row: r, text: (full || "").replace(/\s+/g, " ").trim() };
      }
    }
    return null;
  }

  function firstItem(text) {
    // multi-item bids repeat categories separated by commas: keep the first category (up to its IS designation, if any)
    const m = text.match(/^(.*?\bIS\s*[:/]?\s*\d{2,5}(?:\s*\([^)]*\))?)/i);
    return (m ? m[1] : text.split(/,(?=[A-Z])/)[0]).trim();
  }

  function badge(row) {
    const parts = [];
    for (const c of row.cited || []) {
      const lvl = c.status?.level || "info";
      const cls = lvl === "bad" ? "ss-bad" : lvl === "warn" ? "ss-warn" : "ss-ok";
      let label = c.status?.in_force && lvl !== "bad" ? c.status.in_force : c.base;
      let note = lvl === "bad" ? `withdrawn${c.status?.replacement ? " → " + c.status.replacement : ""}` : lvl === "warn" ? "newer edition in force" : "in force";
      const amd = (c.amendments || []).length ? ` · Amd ${c.amendments.length}` : "";
      const cert = (c.certification || []).length ? ` · ${c.certification[0].scheme.replace(/^Scheme-/, "BIS Scheme-")}` : "";
      parts.push(`<span class="ss-chip ${cls}" title="${esc(c.status?.text || "")}">${esc(label)} · ${esc(note)}${esc(amd)}${esc(cert)}</span>`);
    }
    if (!parts.length) {
      const s = row.suggestion;
      if (s) {
        const cls = s.confidence === "high" ? "ss-suggest" : "ss-maybe";
        parts.push(`<span class="ss-chip ${cls}" title="${esc(s.title)}">No IS named · SpecSure: ${esc(s.base)} (${s.confidence === "high" ? "recommended" : "possible — verify"})</span>`);
      } else {
        parts.push(`<span class="ss-chip ss-none" title="No confident match — SpecSure abstains rather than guess">No IS named · no confident match</span>`);
      }
    }
    return `<div class="ss-badges"><span class="ss-logo">SpecSure</span>${parts.join("")}<button class="ss-more" type="button">details</button></div>`;
  }

  let queue = [];
  let timer = null;

  function scan() {
    const cards = [...document.querySelectorAll(".card")].filter((c) => !c.hasAttribute(DONE));
    for (const card of cards) {
      const it = itemTextOf(card);
      if (!it || !it.text) continue;
      card.setAttribute(DONE, "pending");
      queue.push({ card, row: it.row, text: firstItem(it.text) });
    }
    if (queue.length && !timer) timer = setTimeout(flush, 250);
  }

  function flush() {
    timer = null;
    const batch = queue.splice(0, 40);
    if (!batch.length) return;
    chrome.runtime.sendMessage({ type: "annotate", texts: batch.map((b) => b.text) }, (resp) => {
      if (!resp?.ok) {
        batch.forEach((b) => b.card.setAttribute(DONE, "error"));
        return;
      }
      resp.data.results.forEach((r, i) => {
        const b = batch[i];
        const holder = document.createElement("div");
        holder.innerHTML = badge(r);
        const el = holder.firstElementChild;
        el.querySelector(".ss-more").addEventListener("click", (e) => {
          e.preventDefault();
          chrome.runtime.sendMessage({ type: "open-detail", row: r });
        });
        b.row.insertAdjacentElement("afterend", el);
        b.card.setAttribute(DONE, "done");
      });
      summarise();
      if (queue.length) flush();
    });
  }

  function summarise() {
    const done = document.querySelectorAll(`.card[${DONE}="done"] .ss-badges`);
    const s = { cards: done.length, named: 0, withdrawn: 0, newer: 0, suggested: 0, abstained: 0 };
    done.forEach((d) => {
      if (d.querySelector(".ss-ok,.ss-warn,.ss-bad")) s.named++;
      if (d.querySelector(".ss-bad")) s.withdrawn++;
      if (d.querySelector(".ss-warn")) s.newer++;
      if (d.querySelector(".ss-suggest,.ss-maybe")) s.suggested++;
      if (d.querySelector(".ss-none")) s.abstained++;
    });
    chrome.runtime.sendMessage({ type: "page-summary", summary: { ...s, url: location.href, at: Date.now() } });
  }

  new MutationObserver(() => scan()).observe(document.body, { childList: true, subtree: true });
  scan();
})();
