// SpecSure extension — service worker: API proxy for content scripts, context menu, side panel.
const DEFAULT_API = "http://localhost:8000/api/v1";

async function apiBase() {
  const { api } = await chrome.storage.local.get("api");
  return (api || DEFAULT_API).replace(/\/$/, "");
}

async function callApi(path, body) {
  const res = await fetch((await apiBase()) + path, {
    method: body ? "POST" : "GET",
    headers: body ? { "content-type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`SpecSure API ${res.status}`);
  return res.json();
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({ id: "specsure-find", title: "Find Indian Standards for “%s”", contexts: ["selection"] });
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(() => {});
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== "specsure-find" || !info.selectionText) return;
  await chrome.storage.session.set({ pending: { kind: "query", text: info.selectionText.slice(0, 600), at: Date.now() } });
  if (tab?.id) chrome.sidePanel.open({ tabId: tab.id }).catch(() => {});
});

chrome.runtime.onMessage.addListener((msg, sender, reply) => {
  if (msg?.type === "annotate") {
    callApi("/corpus/annotate", { texts: msg.texts }).then((d) => reply({ ok: true, data: d })).catch((e) => reply({ ok: false, error: String(e) }));
    return true;
  }
  if (msg?.type === "open-detail") {
    chrome.storage.session.set({ pending: { kind: "detail", row: msg.row, at: Date.now() } }).then(() => {
      if (sender.tab?.id) chrome.sidePanel.open({ tabId: sender.tab.id }).catch(() => {});
    });
    reply({ ok: true });
    return false;
  }
  if (msg?.type === "page-summary") {
    chrome.storage.session.set({ [`summary:${sender.tab?.id}`]: msg.summary });
    return false;
  }
  return false;
});
