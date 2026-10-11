import asyncio, os, glob, shutil
from playwright.async_api import async_playwright
EXT = "/home/claude/work/SpecsSure/extension"
CAP = """(t) => { let d = document.getElementById('__cap'); if (!d) { d = document.createElement('div'); d.id='__cap';
 d.style.cssText='position:fixed;left:50%;bottom:28px;transform:translateX(-50%);width:min(1080px,90vw);box-sizing:border-box;z-index:2147483647;background:rgba(15,39,72,.93);color:#fff;font:600 21px/1.35 system-ui,Segoe UI,sans-serif;padding:12px 22px;border-radius:10px;border-bottom:4px solid #ff9933;box-shadow:0 8px 30px rgba(0,0,0,.3);text-align:center';
 document.body.appendChild(d);} d.textContent=t; }"""
async def cap(pg, t, wait=3200):
    try: await pg.evaluate(CAP, t)
    except Exception: pass
    await pg.wait_for_timeout(wait)
async def main():
    async with async_playwright() as p:
        br = await p.chromium.launch()
        ctx = await br.new_context(viewport={"width": 1280, "height": 720}, record_video_dir="/tmp/claude-0/film/raw", record_video_size={"width": 1280, "height": 720})
        pg = await ctx.new_page()
        await pg.goto("http://localhost:3000/"); await pg.wait_for_timeout(2500)
        await cap(pg, "SpecSure — the right Indian Standard for everything you procure, with everything it depends on.", 3500)
        await pg.goto("http://localhost:3000/recommend"); await pg.wait_for_timeout(2500)
        await cap(pg, "29,875 Indian Standards · 80,834 links read from the standards themselves · editions & status from BIS.", 3800)
        ta = pg.locator("textarea").first
        await ta.fill(""); await ta.type("PVC insulated copper wire for house wiring, 450/750 V", delay=35)
        await pg.get_by_role("button", name="Recommend standards").click()
        await pg.wait_for_selector("article", timeout=120000); await pg.wait_for_timeout(1500)
        await pg.locator("article").first.scroll_into_view_if_needed(); await pg.mouse.wheel(0, 380)
        await cap(pg, "IS 694 first — matched on its Scope clause. Edition in force, every amendment, ISI mark compulsory.", 4200)
        btn = pg.locator("text=show labs").first
        if await btn.count():
            await btn.scroll_into_view_if_needed(); await btn.click(); await pg.wait_for_timeout(1500)
            await cap(pg, "Where to test: 52 BIS-recognised labs, cheapest full test ₹6,750 — live from BIS LIMS.", 4200)
        tree = pg.locator("text=Compliance tree").first
        if await tree.count():
            await tree.scroll_into_view_if_needed(); await pg.mouse.wheel(0, 200)
            await cap(pg, "Compliance tree: everything a supplier must satisfy — references, then the test methods they call up.", 4200)
        await pg.goto("http://localhost:3000/recommend?q=" + "स्प्लिट एयर कंडीशनर")
        await pg.wait_for_selector("article", timeout=120000); await pg.wait_for_timeout(800)
        await pg.locator("text=Detected").first.scroll_into_view_if_needed()
        await cap(pg, "Hindi, Tamil, Telugu, Bengali, Kannada — read offline: स्प्लिट → split, कंडीशनर → conditioner → IS 1391 (Part 2).", 4800)
        await pg.goto("http://localhost:3000/recommend?q=LED%20luminaire%20for%20road%20and%20street%20lights")
        await pg.wait_for_selector("article", timeout=120000); await pg.wait_for_timeout(800)
        await pg.locator("article").first.scroll_into_view_if_needed(); await pg.mouse.wheel(0, 300)
        await cap(pg, "The archive has the 2012 text — BIS now lists the 2026 edition. SpecSure flags it and drafts for 2026.", 4200)
        sb = pg.get_by_role("button", name="Spec block").first
        if await sb.count():
            await sb.click(); await pg.wait_for_timeout(7000)
            await cap(pg, "Ready-to-paste tender clause: edition, referred standards, tests, CRS registration — every line sourced.", 4500)
            await pg.keyboard.press("Escape")
        lp = pg
        await lp.goto("http://localhost:3000/extension")
        await lp.wait_for_timeout(2500)
        await cap(lp, "Browser extension for GeM / CPPP — the check happens where officers already work.", 3800)
        await lp.goto("http://localhost:3000/extension/ext_listing.png")
        await lp.evaluate("document.body.style.background='#f4f6f9'; const i=document.querySelector('img'); if(i){i.style.width='1100px';i.style.display='block';i.style.margin='0 auto'}")
        await lp.wait_for_timeout(1500)
        await cap(lp, "Browser extension on GeM bid listings: named standard, edition in force, certification — or an honest “no confident match”.", 5200)
        await lp.mouse.wheel(0, 700); await lp.wait_for_timeout(1500)
        await cap(lp, "Officers don't have to leave the portal they already use.", 2800)
        await pg.goto("http://localhost:3000/evidence"); await pg.wait_for_timeout(2500)
        await cap(pg, "Measured, not claimed: GeM's own category names — 80 % right first time, 91 % in the top 10, aliases off.", 4500)
        await pg.mouse.wheel(0, 1300); await pg.wait_for_timeout(1200)
        await cap(pg, "63 real tenders & GeM bids analysed · abstains on vague or service requests · every number reproducible.", 4500)
        await cap(pg, "SpecSure — deterministic, sourced, dated. AI assists; the officer decides.", 3500)
        await ctx.close(); await br.close()
asyncio.run(main())
