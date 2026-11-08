import asyncio, pathlib, sys
sys.stdout.reconfigure(encoding="utf-8")
from playwright.async_api import async_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent

# visible demo cursor overlay (a soft dot that glides to each control)
CURSOR_JS = """
() => {
  const cur = document.createElement("div");
  cur.id = "demoCursor";
  cur.style.cssText = [
    "position:fixed", "z-index:2147483647", "width:20px", "height:20px",
    "border-radius:50%", "background:rgba(13,148,136,.45)", "border:3px solid #ffffff",
    "box-shadow:0 0 0 2px rgba(15,23,42,.45), 0 4px 12px rgba(0,0,0,.35)",
    "pointer-events:none", "left:0", "top:0",
    "transform:translate(-60px,-60px)",
    "transition:transform .45s cubic-bezier(.4,0,.2,1)"
  ].join(";") + "";
  document.body.appendChild(cur);
  window.moveDemoCursor = (x, y) => { cur.style.transform = `translate(${x - 12}px,${y - 12}px)`; };
  return true;
}
"""

async def center_of(pg, selector):
    return await pg.evaluate(
        "s => { const r = document.querySelector(s).getBoundingClientRect(); return [r.x + r.width/2, r.y + r.height/2]; }",
        selector)

async def glide_to(pg, x, y, hold=520):
    await pg.evaluate("([x,y]) => window.moveDemoCursor(x, y)", [x, y])
    await pg.mouse.move(x, y, steps=6)
    await pg.wait_for_timeout(hold)

async def vis_click(pg, selector, pre=520, post=320):
    x, y = await center_of(pg, selector)
    await glide_to(pg, x, y, pre)
    await pg.mouse.click(x, y)
    await pg.wait_for_timeout(post)

async def smooth_to(pg, selector, ms=1100):
    await pg.evaluate("s => document.querySelector(s).scrollIntoView({behavior:'smooth', block:'start'})", selector)
    await pg.wait_for_timeout(ms)

async def main():
    raw_dir = ROOT / "video" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    for stale in raw_dir.glob("*.webm"):
        stale.unlink()
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1,
            record_video_dir=str(raw_dir),
            record_video_size={"width": 1920, "height": 1080},
        )
        pg = await ctx.new_page()
        url = (ROOT / "dashboard" / "indian_banking_dashboard.html").as_uri()

        # 1) Opening shot: KPIs in light mode
        await pg.goto(url)
        await pg.wait_for_timeout(4200)
        await pg.evaluate(CURSOR_JS)
        cx, cy = 960, 590
        await glide_to(pg, cx, cy, 700)

        # 2) Overview charts with the cursor floating along
        await smooth_to(pg, "canvas#cTrend", 2400)      # monthly trend + type share
        # hover the trend chart -> live tooltip
        tr = await pg.evaluate("""() => { const r = document.querySelector('canvas#cTrend').getBoundingClientRect();
            return [r.x + r.width*0.55, r.y + r.height*0.45]; }""")
        await glide_to(pg, tr[0], tr[1], 300)
        await pg.mouse.move(tr[0] + 40, tr[1] + 8, steps=8)
        await pg.wait_for_timeout(2000)                 # tooltip visible
        await smooth_to(pg, "canvas#cCat", 2200)
        await smooth_to(pg, "canvas#cChan", 2200)
        await smooth_to(pg, "#insights", 1900)

        # metric toggle (volume -> count -> volume)
        await pg.evaluate("window.scrollTo({top:0, behavior:'auto'})")
        await vis_click(pg, "#mtCount", 600, 900)
        await vis_click(pg, "#mtVol", 500, 1100)

        # 3) Fraud tab
        await vis_click(pg, 'a.tab[href="#fraud"]', 460, 300)
        await pg.evaluate("document.getElementById('fraud').scrollIntoView({behavior:'auto'})")
        await pg.wait_for_timeout(2200)
        await smooth_to(pg, "canvas#cHour", 2300)
        await smooth_to(pg, "canvas#cFraudTrend", 2300)
        await smooth_to(pg, "canvas#cFraudState", 2100)

        # 4) Data quality tab
        await vis_click(pg, 'a.tab[href="#quality"]', 460, 300)
        await pg.evaluate("document.getElementById('quality').scrollIntoView({behavior:'auto'})")
        await pg.wait_for_timeout(2300)
        await smooth_to(pg, "canvas#cKyc", 2300)

        # 5) Top customers tab
        await vis_click(pg, 'a.tab[href="#customers"]', 460, 300)
        await pg.evaluate("document.getElementById('customers').scrollIntoView({behavior:'auto'})")
        await pg.wait_for_timeout(1600)
        await pg.evaluate("window.scrollBy({top: 480, behavior:'smooth'})")
        await pg.wait_for_timeout(1600)

        # 6) LIVE FILTERING — visible: cursor clicks each dropdown, arrow keys step values
        await vis_click(pg, 'a.tab[href="#overview"]', 460, 200)
        await pg.evaluate("window.scrollTo({top:0, behavior:'auto'})")
        await pg.wait_for_timeout(500)

        # Type -> IMPS (alphabetical: ATM_W, Auto_D, Cheque, Credit_Card, IMPS = 5 arrow-downs)
        await vis_click(pg, "#fType", 560, 250)
        for i in range(5):
            await pg.keyboard.press("ArrowDown")
            await pg.wait_for_timeout(380)
        await pg.wait_for_timeout(1700)                 # KPIs & charts recompute for IMPS

        # State -> Maharashtra (jump-key "m")
        await vis_click(pg, "#fState", 560, 250)
        await pg.keyboard.press("m")
        await pg.wait_for_timeout(400)
        await pg.wait_for_timeout(1700)                 # Maharashtra + IMPS

        # Fraud -> FRAUD only
        await vis_click(pg, "#fFraud", 560, 250)
        await pg.keyboard.press("ArrowDown")
        await pg.wait_for_timeout(400)
        await pg.wait_for_timeout(2000)                 # fraud-only KPIs

        # hover state chart with filters applied
        st = await pg.evaluate("""() => { const r = document.querySelector('canvas#cState').getBoundingClientRect();
            if (r.bottom < 0 || r.top > innerHeight) { document.querySelector('canvas#cState').scrollIntoView({block:'center',behavior:'auto'}); }
            const r2 = document.querySelector('canvas#cState').getBoundingClientRect();
            return [r2.x + r2.width*0.5, r2.y + r2.height*0.4]; }""")
        await glide_to(pg, st[0], st[1], 300)
        await pg.mouse.move(st[0], st[1] + 30, steps=6)
        await pg.wait_for_timeout(1800)                 # tooltip with txn + fraud counts

        # 7) Reset (visible click)
        await vis_click(pg, "#clearBtn", 560, 1400)

        # 8) Night mode finale
        await vis_click(pg, "#themeBtn", 620, 3000)
        await smooth_to(pg, "canvas#cTrend", 2000)      # charts in the dark
        await smooth_to(pg, "canvas#cCat", 1700)
        await pg.evaluate("window.scrollTo({top: 0, behavior:'smooth'})")
        await pg.wait_for_timeout(2400)                 # dark KPIs closing shot

        await ctx.close()   # flushes the recorded .webm
        await b.close()

    webm = next(raw_dir.glob("*.webm"))
    out = raw_dir / "dashboard_demo_v2.webm"
    webm.replace(out)
    print("recorded:", out, round(out.stat().st_size / 1e6, 2), "MB")

asyncio.run(main())
