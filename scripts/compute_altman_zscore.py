"""
scripts/compute_altman_zscore.py
=================================
Step 13 — Compute Altman Z-Score & Assign Default Labels

Purpose
-------
Compute the Altman Z-Score for each company in company_financials_resolved.csv
and append `altman_z_score` and `default_label` columns.

This step updates (overwrites) the processed financials CSV in-place, which is
explicitly required by the Step 13 output specification.

Formula
-------
    Z = 1.2·X1 + 1.4·X2 + 3.3·X3 + 0.6·X4 + 1.0·X5

    X1 = Working Capital / Total Assets
    X2 = Retained Earnings / Total Assets
    X3 = EBIT / Total Assets
    X4 = Market Cap / Total Liabilities
    X5 = Revenue / Total Assets

Threshold logic
---------------
    Z <= 1.81  →  default_label = 1  (distressed)
    Z >  1.81  →  default_label = 0  (healthy)
    Z = NaN    →  default_label = 0  (insufficient data — see note below)

Variable proxies
----------------
The processed dataset contains: revenue, total_debt, market_cap, current_ratio,
roa, profit_margin, debt_to_equity. Direct balance-sheet items (total_assets,
retained_earnings, ebit, working_capital) are not available from yfinance; the
following proxies are derived from available columns:

    Total Assets (TA):
        TA = total_debt + market_cap
        (book debt + market equity — standard Altman market-value variant)

    Working Capital (WC):
        current_ratio = CA / CL  →  WC = CA - CL = (current_ratio - 1) × CL
        CL_proxy = total_debt × 0.40  (40% of total debt assumed to be short-term)
        WC = (current_ratio - 1) × CL_proxy

    Retained Earnings (RE):
        RE_proxy = profit_margin × revenue × 0.50
        (assumes 50% of net income is retained; proxy when no balance-sheet data)
        Fallback: roa × TA × 0.50

    EBIT:
        EBIT_proxy = profit_margin × revenue / 0.65
        (de-taxes net income assuming 35% effective tax rate)
        Fallback: roa × TA / 0.65

    Total Liabilities (TL):
        TL = total_debt  (proxy; total_debt ~ financial liabilities)

    X4 = market_cap / total_debt  (market value of equity / book liabilities)

Minimum data requirement for computation
-----------------------------------------
    revenue, total_debt, market_cap, current_ratio, roa
    (all five must be non-NaN and total_assets > 0)

If any minimum field is missing → altman_z_score = NaN, default_label = 0.

Usage
-----
    python scripts/compute_altman_zscore.py
"""

import sys
import math
from pathlib import Path

import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------
PROJECT_ROOT    = Path(__file__).resolve().parent.parent
FINANCIALS_PATH = PROJECT_ROOT / "data" / "processed" / "company_financials_resolved.csv"

# Altman Z-Score distress threshold
DISTRESS_THRESHOLD = 1.81

# Fraction of total_debt assumed to be current (short-term) liabilities
SHORT_TERM_DEBT_FRACTION = 0.40

# Effective corporate tax rate proxy (for EBIT from net income)
EFFECTIVE_TAX_RATE = 0.35

# Earnings retention ratio proxy (for retained earnings from net income)
RETENTION_RATIO = 0.50

# Minimum required columns for Z-Score computation
REQUIRED_COLS = ["revenue", "total_debt", "market_cap", "current_ratio", "roa"]


# ===========================================================================
# PROXY DERIVATION FUNCTIONS
# Each function takes a single DataFrame row (as a Series) and returns a float
# or NaN. All return values are in the same units as revenue (USD).
# ===========================================================================

def derive_total_assets(row: pd.Series) -> float:
    """
    Total Assets proxy:
        TA = total_debt + market_cap
    This is the market-value Altman variant: book debt + market equity.
    Returns NaN if either component is missing or TA <= 0.
    """
    td = row["total_debt"]
    mc = row["market_cap"]
    if pd.isna(td) or pd.isna(mc):
        return float("nan")
    ta = td + mc
    return ta if ta > 0 else float("nan")


def derive_working_capital(row: pd.Series, ta: float) -> float:
    """
    Working Capital proxy:
        CL_proxy = total_debt × SHORT_TERM_DEBT_FRACTION
        WC = (current_ratio - 1) × CL_proxy
    Returns NaN if current_ratio or total_debt is missing.
    """
    cr = row["current_ratio"]
    td = row["total_debt"]
    if pd.isna(cr) or pd.isna(td):
        return float("nan")
    cl_proxy = td * SHORT_TERM_DEBT_FRACTION
    return (cr - 1.0) * cl_proxy


def derive_retained_earnings(row: pd.Series, ta: float) -> float:
    """
    Retained Earnings proxy:
        Primary  : profit_margin × revenue × RETENTION_RATIO
        Fallback : roa × TA × RETENTION_RATIO  (when profit_margin is NaN)
    Returns NaN if insufficient data.
    """
    rev = row["revenue"]
    pm  = row["profit_margin"]
    roa = row["roa"]

    if not pd.isna(pm) and not pd.isna(rev):
        net_income = pm * rev
        return net_income * RETENTION_RATIO

    # Fallback: use ROA
    if not pd.isna(roa) and not pd.isna(ta):
        net_income = roa * ta
        return net_income * RETENTION_RATIO

    return float("nan")


def derive_ebit(row: pd.Series, ta: float) -> float:
    """
    EBIT proxy:
        Primary  : profit_margin × revenue / (1 - EFFECTIVE_TAX_RATE)
        Fallback : roa × TA / (1 - EFFECTIVE_TAX_RATE)
    Returns NaN if insufficient data.
    """
    rev = row["revenue"]
    pm  = row["profit_margin"]
    roa = row["roa"]
    tax_divisor = 1.0 - EFFECTIVE_TAX_RATE  # 0.65

    if not pd.isna(pm) and not pd.isna(rev):
        net_income = pm * rev
        return net_income / tax_divisor

    # Fallback: use ROA
    if not pd.isna(roa) and not pd.isna(ta):
        net_income = roa * ta
        return net_income / tax_divisor

    return float("nan")


# ===========================================================================
# ALTMAN Z-SCORE COMPUTATION
# ===========================================================================

def compute_zscore(row: pd.Series) -> tuple:
    """
    Compute the Altman Z-Score for a single company row.

    Returns
    -------
    (z_score, default_label, note)
        z_score       : float or NaN
        default_label : int (0 or 1)
        note          : str explaining the result

    Subsidiary guard
    ----------------
    Subsidiaries whose `imputation_method` is 'parent_financials' or
    'segment_reported' do NOT have an independent balance sheet — their
    financials were copied from the parent. Computing a Z-Score on copied
    data would produce the same score as the parent and inflate the distress
    count. These entities are flagged as NaN / label=0 with an explanation.
    They remain valid graph nodes but receive no standalone risk label here;
    their contagion risk is modelled via the ownership edge to the parent.
    """
    # -----------------------------------------------------------------------
    # Subsidiary imputation guard
    # -----------------------------------------------------------------------
    imp_method = str(row.get("imputation_method", "none")).strip().lower()
    is_sub     = str(row.get("is_subsidiary", "False")).strip().lower()

    if is_sub in ("true", "1") and imp_method in ("parent_financials", "segment_reported"):
        return (
            float("nan"),
            0,
            "skipped: subsidiary with imputed parent financials — "
            "no independent balance sheet; contagion risk modelled via ownership edge"
        )

    # -----------------------------------------------------------------------
    # Minimum data check — all 5 required columns must be present
    # -----------------------------------------------------------------------
    for col in REQUIRED_COLS:
        val = row[col]
        if pd.isna(val):
            return (
                float("nan"),
                0,
                f"insufficient_data: missing '{col}'"
            )

    # -----------------------------------------------------------------------
    # Derive intermediate quantities
    # -----------------------------------------------------------------------
    ta = derive_total_assets(row)
    if pd.isna(ta):
        return (float("nan"), 0, "insufficient_data: total_assets proxy = 0 or NaN")

    wc = derive_working_capital(row, ta)
    re = derive_retained_earnings(row, ta)
    ebit = derive_ebit(row, ta)

    # X4 and X5 use direct columns
    mc = float(row["market_cap"])
    td = float(row["total_debt"])
    rev = float(row["revenue"])

    # -----------------------------------------------------------------------
    # Compute X1–X5
    # -----------------------------------------------------------------------
    # X1 = Working Capital / Total Assets
    if pd.isna(wc):
        return (float("nan"), 0, "insufficient_data: cannot derive working_capital")
    x1 = wc / ta

    # X2 = Retained Earnings / Total Assets
    if pd.isna(re):
        return (float("nan"), 0, "insufficient_data: cannot derive retained_earnings")
    x2 = re / ta

    # X3 = EBIT / Total Assets
    if pd.isna(ebit):
        return (float("nan"), 0, "insufficient_data: cannot derive ebit")
    x3 = ebit / ta

    # X4 = Market Cap / Total Liabilities (= total_debt proxy)
    if td <= 0:
        # No debt → X4 is theoretically infinite; cap at a high value
        x4 = 10.0
    else:
        x4 = mc / td

    # X5 = Revenue / Total Assets
    x5 = rev / ta

    # -----------------------------------------------------------------------
    # Compute Z-Score
    # -----------------------------------------------------------------------
    z = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5

    # Guard against NaN propagation (can occur if any component is NaN)
    if math.isnan(z) or math.isinf(z):
        return (float("nan"), 0, "computation_error: z-score is NaN or Inf after calculation")

    # -----------------------------------------------------------------------
    # Apply threshold logic
    # -----------------------------------------------------------------------
    label = 1 if z <= DISTRESS_THRESHOLD else 0
    note  = f"z={z:.4f}; {'distressed' if label == 1 else 'healthy'}; " \
            f"x1={x1:.4f} x2={x2:.4f} x3={x3:.4f} x4={x4:.4f} x5={x5:.4f}"

    return (round(z, 6), label, note)


# ===========================================================================
# MAIN
# ===========================================================================

def main() -> int:
    """
    Load company_financials_resolved.csv, compute Altman Z-Scores for all rows,
    append the two new columns, and overwrite the file.

    Returns 0 on success, 1 on failure.
    """

    # -----------------------------------------------------------------------
    # 1. Load input file
    # -----------------------------------------------------------------------
    if not FINANCIALS_PATH.exists():
        print(f"ERROR: Input file not found: {FINANCIALS_PATH}")
        return 1

    print(f"Loading: {FINANCIALS_PATH}")
    # Load all columns as string first — convert numerics explicitly below
    fin = pd.read_csv(FINANCIALS_PATH, dtype=str)
    fin.columns = fin.columns.str.strip()
    print(f"  -> {len(fin)} rows, {len(fin.columns)} columns")

    # -----------------------------------------------------------------------
    # 2. Guard: if columns already exist, skip computation
    # -----------------------------------------------------------------------
    if "altman_z_score" in fin.columns and "default_label" in fin.columns:
        print("INFO: altman_z_score and default_label already present. No update needed.")
        return 0

    # -----------------------------------------------------------------------
    # 3. Convert numeric columns for computation
    # -----------------------------------------------------------------------
    numeric_cols = [
        "revenue", "total_debt", "market_cap", "current_ratio",
        "roa", "profit_margin", "debt_to_equity",
    ]
    for col in numeric_cols:
        if col in fin.columns:
            fin[col] = pd.to_numeric(fin[col], errors="coerce")

    # -----------------------------------------------------------------------
    # 4. Apply compute_zscore row-by-row
    # -----------------------------------------------------------------------
    print("Computing Altman Z-Scores ...")

    z_scores:  list = []
    labels:    list = []
    notes:     list = []

    for idx, row in fin.iterrows():
        z, label, note = compute_zscore(row)
        z_scores.append(z)
        labels.append(label)
        notes.append(note)

    fin["altman_z_score"] = z_scores
    fin["default_label"]  = labels

    # -----------------------------------------------------------------------
    # 5. Validation before saving
    # -----------------------------------------------------------------------
    total   = len(fin)
    computed = fin["altman_z_score"].notna().sum()
    skipped  = total - computed
    distressed = int((fin["default_label"] == 1).sum())
    distress_rate = distressed / total

    print()
    print("=== COMPUTATION SUMMARY ===")
    print(f"  Total companies          : {total}")
    print(f"  Z-Score computed         : {computed}")
    print(f"  Insufficient data (NaN)  : {skipped}")
    print(f"  Distressed (label=1)     : {distressed} ({distress_rate:.1%})")
    print(f"  Healthy    (label=0)     : {total - distressed} ({1 - distress_rate:.1%})")

    # Validation check: no company labeled distressed without a Z-Score
    distressed_no_z = fin[
        (fin["default_label"] == 1) & (fin["altman_z_score"].isna())
    ]
    if not distressed_no_z.empty:
        print(f"ERROR: {len(distressed_no_z)} company(ies) labeled distressed but have no Z-Score:")
        print(distressed_no_z[["company_name", "altman_z_score", "default_label"]].to_string())
        return 1
    print("  Validation: No distressed company is missing a Z-Score — PASS")

    # Distress rate check (warn if outside 5-15% range)
    if distress_rate < 0.05 or distress_rate > 0.15:
        print(f"  WARNING: Distress rate {distress_rate:.1%} is outside the expected 5-15% range.")
        print("           Review the Z-Score proxy assumptions if this is unexpected.")
    else:
        print(f"  Distress rate {distress_rate:.1%} is within expected 5-15% range — PASS")

    # Print distressed company list
    print()
    print("=== DISTRESSED COMPANIES (default_label = 1) ===")
    dist_rows = fin[fin["default_label"] == 1][
        ["company_name", "altman_z_score", "is_subsidiary", "parent_company"]
    ].copy()
    dist_rows["altman_z_score"] = dist_rows["altman_z_score"].apply(
        lambda x: f"{x:.4f}" if pd.notna(x) else "NaN"
    )
    print(dist_rows.to_string(index=False))

    # -----------------------------------------------------------------------
    # 6. Write back to CSV (overwrite — explicitly required by Step 13 spec)
    # -----------------------------------------------------------------------
    # Restore original string types for all columns EXCEPT the two new ones
    # (keep altman_z_score and default_label as their computed types for clarity)
    fin.to_csv(FINANCIALS_PATH, index=False, encoding="utf-8")
    print()
    print(f"Updated file saved: {FINANCIALS_PATH}")
    print(f"  New columns added: altman_z_score, default_label")
    print(f"  Total columns now: {len(fin.columns)}")

    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())
