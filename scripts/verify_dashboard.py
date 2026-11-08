import asyncio, sys, os, pathlib
sys.stdout.reconfigure(encoding="utf-8")
from playwright.async_api import async_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent          # project root

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errors.append(str(e)))
        url = (ROOT / "dashboard" / "indian_banking_dashboard.html").as_uri()
        screenshots = ROOT / "dashboard"
        await pg.goto(url)
        await pg.wait_for_timeout(2500)
        # check KPIs populated
        kvol = await pg.text_content("#kVol")
        kavg = await pg.text_content("#kAvg")
        kfraud = await pg.text_content("#kFraud")
        print("kVol:", kvol, "| kAvg:", kavg, "| kFraud:", kfraud)
        # count canvases with charts
        n = await pg.evaluate("Object.keys(ch).length")
        print("charts rendered:", n)
        # apply a filter (state = Maharashtra)
        await pg.select_option("#fState", "Maharashtra")
        await pg.wait_for_timeout(600)
        print("after filter kVol:", await pg.text_content("#kVol"), "| count:", await pg.text_content("#kCount"))
        # reset
        await pg.click("#clearBtn")
        await pg.wait_for_timeout(400)
        print("after reset kVol:", await pg.text_content("#kVol"))
        # dark / night mode toggle
        label_light = await pg.text_content("#themeBtn")
        await pg.click("#themeBtn")
        await pg.wait_for_timeout(900)
        dark_on = await pg.evaluate("document.body.classList.contains('dark')")
        bg = await pg.evaluate("getComputedStyle(document.body).backgroundColor")
        label_dark = await pg.text_content("#themeBtn")
        print("dark mode on:", dark_on, "| bg:", bg, "| label:", label_dark.strip())
        await pg.evaluate("window.scrollTo(0, 0)")
        await pg.wait_for_timeout(300)
        await pg.screenshot(path=str(screenshots / "preview_dark.png"), clip={"x":0,"y":0,"width":1440,"height":1000})
        await pg.click("#themeBtn")
        await pg.wait_for_timeout(700)
        print("toggled back to light:", not await pg.evaluate("document.body.classList.contains('dark')"), "| label:", (await pg.text_content("#themeBtn")).strip())
        # screenshots
        await pg.screenshot(path=str(screenshots / "preview_overview.png"), clip={"x":0,"y":0,"width":1440,"height":1000})
        await pg.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.45)")
        await pg.wait_for_timeout(300)
        await pg.screenshot(path=str(screenshots / "preview_charts.png"))
        await pg.evaluate("window.scrollTo(0, document.getElementById('quality').offsetTop)")
        await pg.wait_for_timeout(300)
        await pg.screenshot(path=str(screenshots / "preview_quality.png"))
        m = await b.new_page(viewport={"width": 390, "height": 844})
        await m.goto(url)
        await m.wait_for_timeout(2200)
        await m.screenshot(path=str(screenshots / "preview_mobile.png"))
        await m.select_option("#fState", "Delhi")
        await m.wait_for_timeout(500)
        await m.screenshot(path=str(screenshots / "preview_mobile_filtered.png"))
        print("console errors:", len(errors))
        for e in errors[:8]:
            print(" -", e[:200])
        await b.close()

asyncio.run(main())
