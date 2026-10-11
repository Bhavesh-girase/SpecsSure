"""End-to-end test of the extension against a local fixture: listing annotation + side panel search + document analysis."""
import asyncio, os, sys
from playwright.async_api import async_playwright
EXT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp"

async def main():
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context("/tmp/claude-0/extprofile", headless=True, channel="chromium",
              args=[f"--disable-extensions-except={EXT}", f"--load-extension={EXT}"], viewport={"width": 1100, "height": 900})
        sw = ctx.service_workers[0] if ctx.service_workers else await ctx.wait_for_event("serviceworker", timeout=20000)
        ext_id = sw.url.split("/")[2]
        print("extension id", ext_id)
        page = await ctx.new_page()
        await page.goto("http://localhost:8765/fixture_listing.html")
        await page.wait_for_selector(".ss-badges", timeout=180000)
        await page.wait_for_function("document.querySelectorAll('.card[data-specsure=done]').length >= document.querySelectorAll('.card').length", timeout=240000)
        badges = await page.eval_on_selector_all(".ss-badges", "els => els.map(e => e.innerText.replace(/\\s+/g,' '))")
        for b in badges: print("BADGE", b)
        await page.screenshot(path=f"{OUT}/ext_listing.png", full_page=True)
        panel = await ctx.new_page()
        await panel.set_viewport_size({"width": 420, "height": 1000})
        await panel.goto(f"chrome-extension://{ext_id}/sidepanel.html")
        await panel.fill("#q", "LED street light 90 W")
        await panel.click("#searchForm button")
        await panel.wait_for_selector(".res h3", timeout=120000)
        await panel.screenshot(path=f"{OUT}/ext_panel_search.png", full_page=True)
        print("SEARCH", (await panel.inner_text("#out"))[:500].replace("\n", " | "))
        # document analysis: open the bid document in a tab, then trigger analysis from the panel for that tab
        doc = await ctx.new_page()
        await doc.goto("http://localhost:8765/fixture_listing.html")
        tab_id = await panel.evaluate("chrome.tabs.query({url: 'http://localhost:8765/fixture_listing.html'}).then(t => t[t.length-1].id)")
        await panel.evaluate("(async (id) => { const t = await chrome.tabs.get(id); await analyseTab({...t, url: 'http://localhost:8765/showbidDocument/9885403'}); })(%d)" % tab_id)
        await panel.wait_for_selector("table", timeout=240000)
        await panel.screenshot(path=f"{OUT}/ext_panel_document.png", full_page=True)
        print("DOC", (await panel.inner_text("#out"))[:700].replace("\n", " | "))
        await ctx.close()

asyncio.run(main())
