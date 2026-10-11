# SpecSure browser extension (prototype)

Brings SpecSure to where procurement actually happens — the e-procurement portal page the officer or bidder already has
open. Chrome / Edge, Manifest V3. Not affiliated with GeM, CPPP or BIS.

## What it does

| Where | What you see |
|---|---|
| **GeM "All bids" listing** (bidplus.gem.gov.in) | Under every bid card, a SpecSure strip: the Indian Standard the item names, whether that edition is **in force**, **superseded by a newer edition** or **withdrawn** (with the replacement), the number of amendments, and the compulsory-certification scheme (ISI mark / CRS). When the item names no standard, SpecSure's suggestion with its confidence — or an explicit *no confident match* (it abstains rather than guess). |
| **A bid document tab** (GeM `showbidDocument/…`, any tender PDF) | Side-panel button *Analyse this bid document*: the items being bought, the IS for each (named / recommended / possible / none), the standards the document cites with their edition status and the test-method standards it forgets, and a *Copy spec clause* button per item. |
| **Any page** | Select text → right-click → *Find Indian Standards for "…"*; or type in the side panel (English, हिन्दी, தமிழ், తెలుగు, বাংলা, ಕನ್ನಡ). |

Everything comes from the SpecSure API (default `http://localhost:8000/api/v1`, changeable in the side panel ⚙). No page
content leaves the machine except to that API.

## Install (developer mode)

1. Start the SpecSure backend (`uvicorn app.main:app --port 8000` in `backend/`).
2. Chrome → `chrome://extensions` → enable **Developer mode** → **Load unpacked** → select this `extension/` folder.
3. Pin *SpecSure*; click the icon to open the side panel.
4. Open `https://bidplus.gem.gov.in/all-bids` — the strips appear under each bid within a second or two.

## Test without a portal

`test/fixture_listing.html` reproduces the bid-card markup with real GeM category names (27 Sep 2026) and
`test/showbidDocument/9885403` is a real GeM bid document. `python3 test/run_ext_test.py <outdir>` loads the extension in
Chromium (Playwright), serves nothing itself — run `python3 -m http.server 8765` inside `test/` first — and saves
screenshots of the annotated listing, a side-panel search and a document analysis.

## Files

- `manifest.json` — permissions: side panel, context menu, storage; hosts: GeM, CPPP/e-tenders, `*.gov.in`, `*.nic.in`, localhost.
- `content.js` / `content.css` — finds bid cards (`.card` → "Items:"), batches their item names to `POST /corpus/annotate`.
- `background.js` — API proxy for the content script (avoids page CORS), context menu, side-panel opening.
- `sidepanel.*` — search, document analysis (`POST /corpus/recommend-document`), details, spec-clause copy (`GET /corpus/spec-block`).
