import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent          # project root
SCRIPTS = ROOT / "scripts"

d = json.load(open(SCRIPTS / "dashboard_facts.json", encoding="utf-8"))
months = d["months"]

types = sorted({k.split("|")[1] for k in d["A"]} | {k.split("|")[3] for k in d["B"]})
states = sorted({k.split("|")[2] for k in d["A"]})
cats = sorted({k.split("|")[3] for k in d["A"]})
statuses = sorted({k.split("|")[1] for k in d["B"]})
channels = sorted({k.split("|")[2] for k in d["B"]})

dims = {"types": types, "states": states, "cats": cats, "statuses": statuses, "channels": channels}
ti = {v: i for i, v in enumerate(types)}
si = {v: i for i, v in enumerate(states)}
ci = {v: i for i, v in enumerate(cats)}
sti = {v: i for i, v in enumerate(statuses)}
chi = {v: i for i, v in enumerate(channels)}

A = [[int(k.split("|")[0]), ti[k.split("|")[1]], si[k.split("|")[2]], ci[k.split("|")[3]], int(k.split("|")[4]), v[0], round(v[1], 1)] for k, v in d["A"].items()]
B = [[int(k.split("|")[0]), sti[k.split("|")[1]], chi[k.split("|")[2]], ti[k.split("|")[3]], int(k.split("|")[4]), v[0], round(v[1], 1)] for k, v in d["B"].items()]
H = [[int(k.split("|")[0]), int(k.split("|")[1]), int(k.split("|")[2]), v] for k, v in d["H"].items()]

out = {"months": months, "dims": dims, "A": A, "B": B, "H": H,
       "custMonthly": d["custMonthly"], "statusByMonth": d["statusByMonth"],
       "directions": d["directions"], "dirVol": d["dirVol"],
       "topCustomers": d["topCustomers"], "loanTypes": d["loanTypes"], "loanPct": d["loanPct"],
       "totalVolume": d["totalVolume"], "uniqScores": d["uniqScores"],
       "quality": d["quality"], "totals": d["totals"]}

s = json.dumps(out, separators=(",", ":"))
with open(SCRIPTS / "dashboard_facts.json", "w", encoding="utf-8") as f:
    f.write(s)
print("new size MB:", round(len(s) / 1e6, 2), "| A:", len(A), "B:", len(B))


def _p(x): print(round(x * 1e-6, 2), 'MB')
