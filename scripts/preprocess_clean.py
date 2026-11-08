# -*- coding: utf-8 -*-
"""
Preprocessing pipeline for the Indian Banking Transactions dataset.

Mirrors the cleaning + validation steps from
Indian_Banking_Transactions_Data_Preprocessing.ipynb :

  1. Load raw CSV
  2. Data profiling report (shape, dtypes, missing, unique, completeness)
  3. Drop exact duplicate rows
  4. Parse dates / times, convert numerics, ID columns to string
  5. Strip + uppercase all categorical text columns
  6. Validation checks (amounts, credit scores, hours, statuses, IDs...)
  7. IQR outlier analysis on transaction_amount
  8. Export cleaned CSV  -> clean_data/
  9. Export quality reports -> reports/

Folder layout (run from the project root):
    raw_data/    source CSV
    clean_data/  cleaned output
    reports/     profiling / missing / validation / outlier / summary CSVs
"""

import pathlib
import sys

import numpy as np
import pandas as pd

# Required so the rupee/garbled output doesn't crash on the cp1252 console
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw_data"
CLEAN_DIR = ROOT / "clean_data"
REPORTS_DIR = ROOT / "reports"

RAW_CSV = RAW_DIR / "indian_banking_transactions.csv"
CLEAN_CSV = CLEAN_DIR / "indian_banking_transactions_cleaned.csv"

pd.set_option("display.max_columns", None)
pd.set_option("display.float_format", "{:.2f}".format)

# ---------------------------------------------------------------- 1. Load
df_raw = pd.read_csv(RAW_CSV)
df_clean = df_raw.copy()

print("Raw dataset:", df_raw.shape)

# ------------------------------------------------------- 2. Profiling report
data_profile = pd.DataFrame({
    "Column_Name": df_raw.columns,
    "Data_Type": df_raw.dtypes.astype(str).values,
    "Total_Records": len(df_raw),
    "Missing_Values": df_raw.isnull().sum().values,
    "Unique_Values": df_raw.nunique().values,
})
data_profile["Completeness_Percentage"] = (
    (data_profile["Total_Records"] - data_profile["Missing_Values"])
    / data_profile["Total_Records"] * 100
)
data_profile.to_csv(REPORTS_DIR / "data_profiling_report.csv", index=False)

# --------------------------------------------------------------------------
# 3. Missing value report (on raw, before any row drops)
# --------------------------------------------------------------------------
missing_report = pd.DataFrame({
    "Missing_Count": df_clean.isnull().sum(),
    "Missing_Percentage": df_clean.isnull().sum() / len(df_clean) * 100,
})
missing_report = missing_report[missing_report["Missing_Count"] > 0]
missing_report = missing_report.sort_values("Missing_Percentage", ascending=False)
missing_report.to_csv(REPORTS_DIR / "missing_value_report.csv")

# ------------------------------------------------- 4. Drop exact duplicates
before_rows = len(df_clean)
df_clean = df_clean.drop_duplicates().copy()
removed_rows = before_rows - len(df_clean)
print("Duplicates removed:", removed_rows, f"({before_rows} -> {len(df_clean)})")

# --------------------------------------------------- 5. Type conversions
# Transaction date -> datetime
df_clean["transaction_date"] = pd.to_datetime(
    df_clean["transaction_date"], errors="coerce"
)

# Transaction time -> standardized HH:MM string
df_clean["transaction_time"] = (
    df_clean["transaction_time"].astype("string").str.strip()
)
df_clean["transaction_time"] = pd.to_datetime(
    df_clean["transaction_time"], format="%H:%M", errors="coerce"
).dt.strftime("%H:%M")

# Numeric columns
numeric_columns_to_convert = [
    "transaction_amount",
    "account_balance",
    "credit_score",
    "has_loan",
    "emi_amount",
    "is_fraud",
    "transaction_hour",
]
for col in numeric_columns_to_convert:
    df_clean[col] = pd.to_numeric(df_clean[col], errors="coerce")

# Identifier columns -> string
id_columns = ["transaction_id", "customer_id"]
for col in id_columns:
    df_clean[col] = df_clean[col].astype("string")

# ------------------------------------------------- 6. Text standardization
text_columns = [
    "account_type",
    "transaction_type",
    "transaction_direction",
    "merchant_category",
    "state",
    "loan_type",
    "transaction_status",
    "channel",
    "kyc_status",
]
for col in text_columns:
    df_clean[col] = df_clean[col].astype("string").str.strip()
for col in text_columns:
    df_clean[col] = df_clean[col].str.upper()
print("Categorical values stripped and uppercased.")

# ----------------------------------------------------- 7. Validation checks
VALID_STATUSES = ["SUCCESS", "FAILED", "REVERSED", "PENDING"]

invalid_amounts = df_clean["transaction_amount"] <= 0
missing_amounts = df_clean["transaction_amount"].isnull()
invalid_credit = (
    df_clean["credit_score"].lt(300)
    | df_clean["credit_score"].gt(900)
    | df_clean["credit_score"].isnull()
)
invalid_loan = ~df_clean["has_loan"].isin([0, 1])
invalid_fraud = ~df_clean["is_fraud"].isin([0, 1])
invalid_hours = (
    df_clean["transaction_hour"].lt(0)
    | df_clean["transaction_hour"].gt(23)
    | df_clean["transaction_hour"].isnull()
)
invalid_dates = df_clean["transaction_date"].isnull()
invalid_times = df_clean["transaction_time"].isnull()
invalid_statuses = ~df_clean["transaction_status"].isin(VALID_STATUSES)
loan_type_without_loan = (df_clean["has_loan"] == 0) & df_clean["loan_type"].notnull()
loan_type_missing_for_loan = (df_clean["has_loan"] == 1) & df_clean["loan_type"].isnull()

invalid_data_report = pd.DataFrame({
    "Issue": [
        "Zero or Negative Transaction Amount",
        "Missing Transaction Amount",
        "Invalid Credit Score",
        "Invalid Loan Indicator",
        "Invalid Fraud Indicator",
        "Invalid Transaction Hour",
        "Invalid Transaction Date",
        "Invalid Transaction Status",
        "Loan Type Present Without Loan",
        "Loan Type Missing For Loan",
    ],
    "Count": [
        int(invalid_amounts.sum()),
        int(missing_amounts.sum()),
        int(invalid_credit.sum()),
        int(invalid_loan.sum()),
        int(invalid_fraud.sum()),
        int(invalid_hours.sum()),
        int(invalid_dates.sum()),
        int(invalid_statuses.sum()),
        int(loan_type_without_loan.sum()),
        int(loan_type_missing_for_loan.sum()),
    ],
})
invalid_data_report.to_csv(REPORTS_DIR / "invalid_data_report.csv", index=False)

# -------------------------------------------------- 8. IQR outlier analysis
Q1 = df_clean["transaction_amount"].quantile(0.25)
Q3 = df_clean["transaction_amount"].quantile(0.75)
IQR = Q3 - Q1
lower_bound = Q1 - 1.5 * IQR
upper_bound = Q3 + 1.5 * IQR

outlier_mask = (
    df_clean["transaction_amount"] < lower_bound
) | (
    df_clean["transaction_amount"] > upper_bound
)
outlier_count = int(outlier_mask.sum())
outlier_percentage = outlier_count / len(df_clean) * 100
print(f"Outliers: {outlier_count} ({outlier_percentage:.2f}%)")

outlier_report = pd.DataFrame({
    "Metric": ["Q1", "Q3", "IQR", "Lower Bound", "Upper Bound",
               "Total Outliers", "Outlier Percentage"],
    "Value": [Q1, Q3, IQR, lower_bound, upper_bound,
              outlier_count, outlier_percentage],
})
outlier_report.to_csv(REPORTS_DIR / "outlier_analysis_report.csv", index=False)

# --------------------------------------------------- 9. Validation report
validation_report = pd.DataFrame({
    "Validation_Check": [
        "Transaction ID Uniqueness",
        "Exact Duplicate Records",
        "Missing Transaction Amounts",
        "Non-Positive Transaction Amounts",
        "Invalid Transaction Dates",
        "Invalid Transaction Times",
        "Invalid Transaction Statuses",
        "Invalid Credit Scores",
        "Invalid Loan Indicators",
        "Invalid Fraud Indicators",
        "Invalid Transaction Hours",
    ],
    "Issue_Count": [
        int(df_clean["transaction_id"].duplicated().sum()),
        int(df_clean.duplicated().sum()),
        int(missing_amounts.sum()),
        int(invalid_amounts.sum()),
        int(invalid_dates.sum()),
        int(invalid_times.sum()),
        int(invalid_statuses.sum()),
        int(invalid_credit.sum()),
        int(invalid_loan.sum()),
        int(invalid_fraud.sum()),
        int(invalid_hours.sum()),
    ],
})
validation_report["Status"] = np.where(
    validation_report["Issue_Count"] == 0, "PASS", "REVIEW"
)
validation_report.to_csv(REPORTS_DIR / "data_validation_report.csv", index=False)

# --------------------------------------------- 10. Final quality summary
quality_summary = pd.DataFrame({
    "Metric": [
        "Original Row Count",
        "Cleaned Row Count",
        "Original Column Count",
        "Exact Duplicates Removed",
        "Remaining Exact Duplicates",
        "Missing Values After Processing",
        "Transaction ID Duplicate Count",
        "Statistical Outlier Count",
    ],
    "Value": [
        len(df_raw),
        len(df_clean),
        df_raw.shape[1],
        removed_rows,
        int(df_clean.duplicated().sum()),
        int(df_clean.isnull().sum().sum()),
        int(df_clean["transaction_id"].duplicated().sum()),
        outlier_count,
    ],
})
quality_summary.to_csv(REPORTS_DIR / "final_data_quality_summary.csv", index=False)

# ------------------------------------------------------ 11. Export CSV
CLEAN_DIR.mkdir(exist_ok=True)
df_clean.to_csv(CLEAN_CSV, index=False)
print("Cleaned rows:", len(df_clean))
print("Saved:", CLEAN_CSV)
print("Reports saved to:", REPORTS_DIR)
print("\nQuality summary:")
print(quality_summary.to_string(index=False))
