import json, pathlib

root = pathlib.Path(__file__).resolve().parent          # scripts/
tpl = (root / "dashboard_template.html").read_text(encoding="utf-8")
data = (root / "dashboard_facts.json").read_text(encoding="utf-8")
chartjs = (root / "chart.umd.min.js").read_text(encoding="utf-8")
q = json.loads(data)["quality"]

maxm = json.loads(data)["months"][-1]
fraudpct = json.loads(data)["totals"]["fraudPct"]

out = (tpl.replace("{{CHARTJS}}", chartjs)
          .replace("{{DATA}}", data)
          .replace("{{MAXM}}", maxm)
          .replace("{{FRAUDPCT}}", f"{fraudpct:.2f}")
          .replace("{{OUTLIERS}}", f"{q['outliers']:,}")
          .replace("{{OUTPCT}}", f"{q['outlier_pct']}")
          .replace("{{AMTMAX}}", f"{q['amt_stats']['max']:,.0f}"))
dest = root.parent / "dashboard" / "indian_banking_dashboard.html"
dest.write_text(out, encoding="utf-8")
import os
print("written:", dest, round(dest.stat().st_size / 1e6, 2), "MB")
