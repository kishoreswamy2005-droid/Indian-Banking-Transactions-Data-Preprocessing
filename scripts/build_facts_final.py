import pandas as pd, json, numpy as np, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent          # project root
SCRIPTS = ROOT / "scripts"
CSV = ROOT / "raw_data" / "indian_banking_transactions.csv"
df = pd.read_csv(CSV, parse_dates=["transaction_date"])
df["ym"] = df.transaction_date.dt.to_period("M").astype(str)
df["fraud"] = df.is_fraud.astype(int)
df["month_i"] = df.transaction_date.dt.to_period("M").astype(str).map(lambda s: s)

months = sorted(df.ym.unique().tolist())
midx = {m: i for i, m in enumerate(months)}

def pack(g, dims):
    """dims list of column names; returns rows [idx..., count, volume]"""
    rows = []
    for _, r in g.iterrows():
        row = [r.iloc[-2]] if False else None
        pass
    return rows

def fact_rows(groupcols):
    g = df.groupby(groupcols).agg(count=("transaction_amount", "size"),
                                  volume=("transaction_amount", "sum")).reset_index()
    out = []
    for rec in g.itertuples(index=False):
        d = rec._asdict()
        out.append(d)
    return out

# FACT A: time, type, state, category, fraud
a = df.groupby(["ym", "transaction_type", "state", "merchant_category", "fraud"]).agg(
    count=("transaction_amount", "size"), volume=("transaction_amount", "sum")).reset_index()
A = {}
for rec in a.itertuples(index=False):
    k = f"{midx[rec.ym]}|{rec.transaction_type}|{rec.state}|{rec.merchant_category}|{int(rec.fraud)}"
    A[k] = [int(rec.count), round(float(rec.volume), 2)]

# FACT B: time, status, channel, type, fraud
b = df.groupby(["ym", "transaction_status", "channel", "transaction_type", "fraud"]).agg(
    count=("transaction_amount", "size"), volume=("transaction_amount", "sum")).reset_index()
B = {}
for rec in b.itertuples(index=False):
    k = f"{midx[rec.ym]}|{rec.transaction_status}|{rec.channel}|{rec.transaction_type}|{int(rec.fraud)}"
    B[k] = [int(rec.count), round(float(rec.volume), 2)]

# hourly: time, hour, fraud
h = df.groupby(["ym", "transaction_hour", "fraud"]).agg(count=("transaction_amount", "size")).reset_index()
H = {}
for rec in h.itertuples(index=False):
    H[f"{midx[rec.ym]}|{int(rec.transaction_hour)}|{int(rec.fraud)}"] = int(rec.count)

# monthly customers / status / direction
cust_monthly = df.groupby("ym").customer_id.nunique().reindex(months).astype(int).tolist()
status_monthly = {y: s.count for y, s in [(y, v) for y, v in df.groupby(["ym","transaction_status"]).size().reset_index(name="c").iterrows() for k in ['name'] ]} if False else None
st = df.groupby(["ym","transaction_status"]).size().reset_index(name="count")
statusByMonth = {}
for rec in st.itertuples(index=False):
    statusByMonth.setdefault(midx[rec.ym], {})[rec.transaction_status] = int(rec.count)
di = df.groupby(["ym","transaction_direction"]).agg(count=("transaction_amount","size"), volume=("transaction_amount","sum")).reset_index()
directionByMonth = {}
for rec in di.itertuples(index=False):
    directionByMonth.setdefault(midx[rec.ym], {})[rec.transaction_direction] = [int(rec.count), round(float(rec.volume),2)]
directionByMonth = {"total": sum(v["Debit"][0]+v["Credit"][0] for v in directionByMonth.values())}
directions_tot = df.transaction_direction.value_counts().to_dict()
dir_vol_tot = df.groupby("transaction_direction").transaction_amount.sum().round(2).to_dict()

# top customers
top = (df.groupby(["customer_id","state"]).agg(volume=("transaction_amount","sum"),
     count=("transaction_id","size"), fraud=("is_fraud","max"),
     has_loan=("has_loan","max"), credit_score=("credit_score","mean")).round(2)
     .sort_values("volume", ascending=False).head(20).reset_index())
top["share"] = (top.volume / df.transaction_amount.sum() * 100).round(2)
top["credit_score"] = top.credit_score.round(0).astype(int)

# ================= QUALITY / VALIDATION (as in notebook) =================
q = {}
q["rows"] = len(df)
q["cols"] = df_raw_cols = len(df.columns) - 4
q["dup_rows"] = int(df.duplicated(subset=["transaction_id","customer_id","transaction_date","transaction_time","account_type","transaction_type","transaction_amount","transaction_direction","account_balance","merchant_category","state","credit_score","has_loan","loan_type","emi_amount","transaction_status","channel","kyc_status","is_fraud","transaction_hour"]).sum())
q["dup_txn_ids"] = int(df.transaction_id.duplicated(keep=False).sum())
q["txn_ids_unique"] = bool(df.transaction_id.is_unique)
q["zero_neg_amounts"] = int((df.transaction_amount <= 0).sum())
q["missing"] = df.isnull().sum().astype(int).to_dict()
for k in ("ym", "fraud", "month_i"):
    q["missing"].pop(k, None)
q["invalid_cs"] = int(((df.credit_score < 300) | (df.credit_score > 900)).sum())
q["invalid_has_loan"] = int((~df.has_loan.isin([0, 1])).sum())
q["invalid_is_fraud"] = int((~df.is_fraud.isin([0, 1])).sum())
q["invalid_hours"] = int(((df.transaction_hour < 0) | (df.transaction_hour > 23)).sum())
q["invalid_dates"] = int(df.transaction_date.isnull().sum())
allowed_status = {"SUCCESS","FAILED","REVERSED","PENDING"}
q["invalid_status"] = int((~df.transaction_status.str.upper().isin(allowed_status)).sum())
q["loan_without_type"] = int(((df.has_loan == 1) & df.loan_type.isna()).sum())
q["loan_type_no_loan"] = int(((df.has_loan == 0) & df.loan_type.notna()).sum())
q["missing_loan_type"] = int(df.loan_type.isnull().sum())
q["kyc_mix"] = {k[1:]: int(v["count"]) for k, v in (lambda g: {k: v for k, v in g.items()})(dict(df.kyc_status.value_counts()))} if False else dict(df.kyc_status.value_counts())
q["kyc_mix"] = {str(k): int(v) for k, v in df.kyc_status.value_counts().items()}
amt = df.transaction_amount
Q1, Q3 = amt.quantile(0.25), amt.quantile(0.75)
IQR = Q3 - Q1
q["iqr_lower"] = round(float(Q1 - 1.5 * IQR), 2)
q["iqr_upper"] = round(float(Q3 + 1.5 * IQR), 2)
q["outliers"] = int(((amt < q["iqr_lower"]) | (amt > q["iqr_upper"])).sum())
q["outlier_pct"] = round(q["outliers"] / len(df) * 100, 2)
q["amt_stats"] = {k: round(float(v), 2) for k, v in amt.describe().items()}
uniq_scores = int(df.credit_score.nunique())

loan_types_full = df[df.loan_type.notna()].loan_type.value_counts().to_dict()
loan_pct = float((df.has_loan == 1).mean() * 100)
total_volume = float(amt.sum())

data = {
    "months": months,
    "A": A, "B": B, "H": H,
    "custMonthly": cust_monthly,
    "statusByMonth": statusByMonth,
    "directions": directions_tot, "dirVol": dir_vol_tot,
    "topCustomers": top.to_dict("records"),
    "loanTypes": loan_types_full, "loanPct": loan_pct,
    "totalVolume": total_volume, "uniqScores": uniq_scores,
    "quality": q,
    "totals": {
        "nRows": int(len(df)), "nCustomers": int(df.customer_id.nunique()),
        "nTxnTypes": int(df.transaction_type.nunique()), "nStates": int(df.state.nunique()),
        "nCategories": int(df.merchant_category.nunique()), "nChannels": int(df.channel.nunique()),
        "fraudPct": round(float(df.is_fraud.mean() * 100), 3),
        "avgAmt": round(float(amt.mean()), 2), "medAmt": round(float(amt.median()), 2),
        "dateMin": str(df.transaction_date.min().date()), "dateMax": str(df.transaction_date.max().date()),
        "avgBalance": round(float(df.account_balance.mean()), 2), "totalEMI": float(df.emi_amount.sum()),
    }
}

# compact fact re-encode: use arrays keyed by month index? keep dict; check size
fig = json.dumps(data, separators=(",", ":"))
import os
print("data json size MB:", round(len(fig) / 1e6, 2))
print("facts A:", len(A), "| facts B:", len(B), "| hourly:", len(H))
with open(SCRIPTS / "dashboard_facts.json", "w", encoding="utf-8") as f:
    f.write(fig)
