# Indian Banking Transactions — Data Preprocessing Project

An end-to-end analysis of 550,000 Indian banking transactions (Jan 2019 – Jan 2024, ~80,000 customers)
with an interactive, offline dashboard.

## Folder Guide

| Folder | What's inside |
|---|---|
| `raw_data/` | The original, untouched source file `indian_banking_transactions.csv` (550K rows, 20 columns). Never edit files here. |
| `clean_data/` | The cleaned dataset `indian_banking_transactions_cleaned.csv` produced by the preprocessing script — duplicates dropped, dates/numbers parsed, text standardized. |
| `reports/` | Data quality CSVs from the preprocessing run: profiling report, missing-value report, invalid-data report, outlier (IQR) analysis, validation report, and the final quality summary. Open them in Excel. |
| `dashboard/` | **The main deliverable** — `indian_banking_dashboard.html`. One self-contained file (works fully offline, opens in any browser, phone-friendly). The `preview_*.png` files are quick screenshots of how it looks. |
| `scripts/` | All the Python code + build assets. Run them in the order listed below. |
| `Indian_Banking_Transactions_Data_Preprocessing.ipynb` | The original step-by-step notebook that documents the analysis logic. |

## How to Use the Dashboard

Just double-click `dashboard\indian_banking_dashboard.html` — no internet, no server needed.
It has 4 tabs (Overview, Fraud, Data Quality, Top Customers), filters at the top (month / type / state / category),
KPI cards, and 12 charts.

## How to Rebuild (from scratch)

Run these from the project root, in order:

```bat
:: 1. Clean the raw data and produce the quality reports
python scripts\preprocess_clean.py

:: 2. Build the fact tables (reads raw_data\, writes scripts\dashboard_facts.json)
python scripts\build_facts_final.py
python scripts\compact_facts.py

:: 3. Assemble the final dashboard (writes dashboard\indian_banking_dashboard.html)
python scripts\build_html.py

:: 4. Verify: renders the dashboard headlessly and saves new previews to dashboard\
python scripts\verify_dashboard.py
```

## Key Findings (verified numbers)

- Total volume **₹16.45B** across **550,000** transactions; average ticket **₹29,907**
- Fraud rate **0.89%** of transactions — but fraud tickets average ₹119K vs ₹29K genuine
- **RTGS is the riskiest channel**: 1.85% of RTGS transactions are fraud (₹385M flagged volume)
- Data quality: 0 duplicates, 0 invalid IDs/dates/statuses; outlier share **16.18%** (88,976 rows)
  by IQR; `loan_type` is blank for 377K rows simply because those customers have no loan
