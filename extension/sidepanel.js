// SpecSure side panel: search, analyse the bid document open in the tab, details for annotated bid cards.
const DEFAULT_API = "http://localhost:8000/api/v1";
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const out = $("out");

async function api() {
  const { api } = await chrome.storage.local.get("api");
  return (api || DEFAULT_API).replace(/\/$/, "");
}
async function get(path) {
  const r = await fetch((await api()) + path);
  if (!r.ok) throw new Error(`API ${r.status}`);
  return r.json();
}
async function post(path, body) {
  const r = await fetch((await api()) + path, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error(`API ${r.status}`);
  return r.json();
}

const LEVEL = { ok: "ok", warn: "warn", bad: "bad", info: "info" };
const CONF = { high: ["ok", "Recommended"], medium: ["warn", "Possible — verify"], low: ["none", "No confident match"] };

function statusLine(st) {
  if (!st) return "";
  return `<div class="status"><span class="chip ${LEVEL[st.level] || "info"}">${st.level === "bad" ? "Withdrawn" : st.level === "warn" ? "Check edition" : st.level === "ok" ? "In force" : "Edition"}</span> ${esc(st.text)}</div>`;
}
function certLine(certs) {
  if (!certs?.length) return "";
  return `<div class="row">${certs.slice(0, 2).map((c) => `<span class="chip info" title="${esc(c.title || "")}">${esc(c.scheme || c.type)}</span>`).join("")}<span class="muted">compulsory certification</span></div>`;
}
function specButton(base, item) {
  return `<button class="btn copy" data-base="${esc(base)}" data-item="${esc(item || "")}">Copy spec clause</button>`;
}

out.addEventListener("click", async (e) => {
  const b = e.target.closest("button.copy");
  if (!b) return;
  b.disabled = true;
  const old = b.textContent;
  b.innerHTML = '<span class="spin"></span> drafting…';
  try {
    const q = new URLSearchParams({ base: b.dataset.base });
    if (b.dataset.item) q.set("item", b.dataset.item);
    const blk = await get(`/corpus/spec-block?${q}`);
    await navigator.clipboard.writeText(blk.text + "\n\nNote: " + blk.notes.join(" "));
    b.textContent = "Copied ✓";
  } catch (err) {
    b.textContent = "Failed: " + err.message;
  }
  setTimeout(() => { b.textContent = old; b.disabled = false; }, 1800);
});

async function search(q) {
  out.innerHTML = `<div class="res"><span class="spin"></span> Searching 29,000+ Indian Standards for “${esc(q)}”…</div>`;
  try {
    const d = await post("/corpus/recommend", { query: q, top_k: 5, expand: 1 });
    const lang = d.translated ? `<div class="muted">Read as: ${esc(d.query_en)} (${esc(d.language)})</div>` : "";
    out.innerHTML = lang + d.results.map((r) => {
      const [cls, label] = CONF[r.confidence] || CONF.low;
      const why = r.scope ? `<div class="why">Scope: ${esc(r.scope.slice(0, 180))}…</div>` : "";
      return `<div class="res"><h3>${esc(r.base)}</h3><div class="t">${esc(r.title)}</div>
        <div class="row"><span class="chip ${cls}">${label}</span>${r.origin === "bis_portal" ? '<span class="chip none">title only (no full text)</span>' : ""}</div>
        ${statusLine(r.status)}${certLine(r.certification)}${why}${specButton(r.base, q)}</div>`;
    }).join("") + `<div class="muted">${esc(d.disclaimer || "")}</div>`;
  } catch (err) {
    out.innerHTML = `<div class="res bad">Could not reach SpecSure (${esc(err.message)}). Check the API address in settings.</div>`;
  }
}

function detail(row) {
  const cited = (row.cited || []).map((c) => `<div class="res"><div class="kicker">Named in the bid</div><h3>${esc(c.base)}</h3><div class="t">${esc(c.title || "")}</div>
      ${statusLine(c.status)}${(c.amendments || []).length ? `<div class="why">Amendments: ${c.amendments.map((a) => `No. ${a.no} (${a.year})`).join(", ")}</div>` : ""}
      ${certLine(c.certification)}${specButton(c.status?.replacement || c.base, row.text.replace(/\(V\d+\)|ISI Marked.*$|Conforming.*$/gi, "").trim())}</div>`).join("");
  const s = row.suggestion;
  const sug = s ? `<div class="res"><div class="kicker">No IS named — SpecSure suggests</div><h3>${esc(s.base)}</h3><div class="t">${esc(s.title)}</div>
      <div class="row"><span class="chip ${(CONF[s.confidence] || CONF.low)[0]}">${(CONF[s.confidence] || CONF.low)[1]}</span></div>
      ${statusLine(s.status)}${certLine(s.certification)}
      ${(s.alternatives || []).length ? `<div class="why">Also consider: ${s.alternatives.map((a) => `${esc(a.base)} (${esc(a.title.slice(0, 50))})`).join("; ")}</div>` : ""}
      ${specButton(s.base, row.text)}</div>` : "";
  const none = !cited && !s ? `<div class="res"><span class="chip none">No confident match</span> SpecSure abstains rather than guess. Search with more specific words below.</div>` : "";
  out.innerHTML = `<div class="muted">Item: ${esc(row.text)}</div>` + cited + sug + none;
}

async function analyseTab(tab) {
  const btn = $("analyse");
  btn.disabled = true;
  out.innerHTML = `<div class="res"><span class="spin"></span> Downloading the document from this tab and finding the items being bought…</div>`;
  try {
    const r = await fetch(tab.url, { credentials: "include" });
    const blob = await r.blob();
    if (!/pdf|octet|word|text/.test(blob.type) && blob.size < 2000) throw new Error("this tab does not hold a document");
    const head = new TextDecoder().decode(await blob.slice(0, 5).arrayBuffer());
    const isPdf = head.startsWith("%PDF") || blob.type.includes("pdf");
    let name = (tab.url.split("?")[0].split("/").pop() || "bid");
    if (isPdf && !/\.pdf$/i.test(name)) name += ".pdf";
    const fd = new FormData();
    fd.append("file", blob, name);
    const res = await fetch((await api()) + "/corpus/recommend-document", { method: "POST", body: fd });
    if (!res.ok) throw new Error(`API ${res.status}`);
    const d = await res.json();
    const rows = d.items.map((it) => {
      const c = it.candidates[0];
      const st = { named: ["info", "Named in bid"], recommended: ["ok", "Recommended"], possible: ["warn", "Possible"], none: ["none", "No confident IS"], service: ["none", "Service"] }[it.status] || ["none", it.status];
      const ed = c?.edition;
      const edLine = ed?.status === "Withdrawn" ? `<div class="chip bad">withdrawn → ${esc(ed.replacement || ed.superseded_by || "?")}</div>`
        : ed?.edition_in_force ? `<div class="muted">in force: ${esc(ed.edition_in_force)}${(ed.amendments || []).length ? ` + Amd ${ed.amendments.length}` : ""}</div>` : "";
      return `<tr><td><b>${esc(it.text)}</b>${it.qty ? `<div class="muted">${esc(it.qty)}</div>` : ""}</td>
        <td><span class="chip ${st[0]}">${st[1]}</span>${c && it.status !== "none" && it.status !== "service" ? `<div><b>${esc(c.base)}</b> <span class="muted">${esc(c.title.slice(0, 60))}</span></div>
        ${edLine}${c.certification?.length ? `<div class="chip info">${esc(c.certification[0].scheme)}</div>` : ""}${c.already_cited && it.status !== "named" ? '<div class="muted">already cited in the bid</div>' : ""}
        ${specButton(c.base, it.text)}` : ""}</td></tr>`;
    }).join("");
    const cc = d.citation_check?.citations || [];
    const cites = cc.length ? `<div class="res"><div class="kicker">Standards cited in this document</div>${cc.map((x) =>
      `<div class="status"><b>${esc(x.citation || x.family)}</b> ${x.found ? "" : '<span class="chip bad">not found</span>'}${x.withdrawn ? `<span class="chip bad">withdrawn → ${esc(x.edition?.replacement || x.edition?.superseded_by || "")}</span>` : ""}${x.newer_edition_archived ? `<span class="chip warn">newer edition: ${esc(x.edition?.edition_in_force || "")}</span>` : ""}
       ${x.not_cited_dependencies?.length ? `<div class="why">Its test methods / references not cited: ${x.not_cited_dependencies.slice(0, 4).map((y) => esc(y.base)).join(", ")}</div>` : ""}</div>`).join("")}</div>` : `<div class="res"><span class="chip warn">No Indian Standard is cited in this document</span></div>`;
    out.innerHTML = `<div class="res"><div class="kicker">${esc(d.document?.filename || "Document")} · ${d.document?.pages || "?"} pages</div>
      <div class="sum"><div><b>${(d.counts.named || 0) + d.counts.recommended}</b>with an IS</div><div><b>${d.counts.possible}</b>possible</div><div><b>${d.counts.none}</b>abstained</div></div></div>
      ${cites}<table><thead><tr><th>Item</th><th>Indian Standard</th></tr></thead><tbody>${rows || '<tr><td colspan="2" class="muted">No items found.</td></tr>'}</tbody></table>`;
  } catch (err) {
    out.innerHTML = `<div class="res bad">Could not analyse: ${esc(err.message)}</div>`;
  }
  btn.disabled = false;
}

async function refreshTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) return;
  let host = "";
  try { host = new URL(tab.url).host; } catch { /* chrome:// pages */ }
  const isDoc = /showbidDocument|showdirectradocumentPdf|\.pdf(\?|$)|download/i.test(tab.url || "");
  $("pageInfo").innerHTML = host ? `${esc(host)}${isDoc ? " · bid document" : ""}` : "Open a bid listing or a bid document.";
  $("analyse").hidden = !isDoc;
  $("analyse").onclick = () => analyseTab(tab);
  const key = `summary:${tab.id}`;
  const s = (await chrome.storage.session.get(key))[key];
  $("pageSummary").innerHTML = s && s.cards ? `<div class="sum"><div><b>${s.cards}</b>bids annotated</div><div><b>${s.named}</b>name an IS</div><div><b>${s.suggested}</b>SpecSure suggests</div></div>
    ${s.withdrawn ? `<div class="status"><span class="chip bad">${s.withdrawn} name a withdrawn standard</span></div>` : ""}${s.newer ? `<div class="status"><span class="chip warn">${s.newer} with a newer edition in force</span></div>` : ""}` : "";
}

async function pending() {
  const { pending: p } = await chrome.storage.session.get("pending");
  if (!p || Date.now() - p.at > 60000) return;
  await chrome.storage.session.remove("pending");
  if (p.kind === "query") { $("q").value = p.text; search(p.text); }
  if (p.kind === "detail") detail(p.row);
}

$("searchForm").addEventListener("submit", (e) => { e.preventDefault(); const q = $("q").value.trim(); if (q) search(q); });
$("gear").addEventListener("click", async () => { $("settings").hidden = !$("settings").hidden; $("api").value = await api(); });
$("saveApi").addEventListener("click", async () => {
  await chrome.storage.local.set({ api: $("api").value.trim() || DEFAULT_API });
  try { const s = await get("/corpus/stats"); $("apiState").textContent = `Connected · ${s.designations.toLocaleString("en-IN")} standards`; }
  catch (err) { $("apiState").textContent = "Not reachable: " + err.message; }
});
chrome.storage.session.onChanged.addListener(() => { pending(); refreshTab(); });
chrome.tabs.onActivated.addListener(refreshTab);
chrome.tabs.onUpdated.addListener((id, info) => { if (info.status === "complete") refreshTab(); });
refreshTab();
pending();
