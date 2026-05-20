"""
scripts/surgical_prune.py
==========================
Step 13 (Post) — Surgical Data Pruning & Accuracy Maximization

Purpose
-------
1. Remove 5 identified off-domain / noise companies from ALL data files
   (raw and processed) that contribute nothing meaningful to credit contagion
   modeling and have zero financial data.

2. Apply a suite of accuracy-maximization measures to the processed data
   to maximize GNN model performance in Phase 3.

Companies removed and rationale
--------------------------------
| Company                              | Reason for removal                           |
|--------------------------------------|----------------------------------------------|
| GMC                                  | Brand division of GM, not an independent     |
|                                      | legal entity. Already captured via GM node.  |
| BPIfrance                            | French state investment bank — not an        |
|                                      | operating company in the auto supply chain.  |
| Bugatti Rimac                        | Ultra-niche luxury brand. Off-domain for     |
|                                      | automotive credit contagion at scale.        |
| Boston Dynamics                      | Robotics company. Off-domain entirely.       |
| Tenaciou3 Prospect Investment Limited| Investment SPV. Not an operating entity.     |

Accuracy-maximization measures applied
---------------------------------------
1. Industry-median imputation for missing financial features
   (better than global mean — automotive sector has distinct ratio profiles)
2. Feature_missing binary mask columns added for each imputed column
   (lets the GNN learn that "this value was imputed" vs "this is real data")
3. Robust clipping of extreme outliers in financial features
   (e.g. Nvidia's Z-Score of 224 is a statistical outlier that can distort scaling)
4. Standardised altman_z_score clipping to [-5, 30] range
   (prevents a handful of extreme values from dominating gradient updates)

Files modified
--------------
    data/raw/supply_chain_combined.csv         — remove edges involving pruned companies
    data/raw/company_financials_validated.csv  — remove rows for pruned companies
    data/processed/supply_chain_resolved.csv   — remove edges involving pruned UUIDs
    data/processed/company_financials_resolved.csv — remove rows + apply accuracy measures
    data/processed/entity_index.json           — remove pruned name entries

Usage
-----
    python scripts/surgical_prune.py
"""

import json
import sys
import logging
from pathlib import Path

import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s",
                    stream=sys.stdout)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_SC      = PROJECT_ROOT / "data" / "raw"       / "supply_chain_combined.csv"
RAW_FIN     = PROJECT_ROOT / "data" / "raw"       / "company_financials_validated.csv"
PROC_SC     = PROJECT_ROOT / "data" / "processed" / "supply_chain_resolved.csv"
PROC_FIN    = PROJECT_ROOT / "data" / "processed" / "company_financials_resolved.csv"
ENTITY_IDX  = PROJECT_ROOT / "data" / "processed" / "entity_index.json"

# ---------------------------------------------------------------------------
# Companies to remove — must match names EXACTLY as they appear in the data
# ---------------------------------------------------------------------------
PRUNE_NAMES = {
    "GMC",
    "BPIfrance",
    "Bugatti Rimac",
    "Boston Dynamics",
    "Tenaciou3 Prospect Investment Limited",
}

# Financial feature columns eligible for imputation
FINANCIAL_FEATURES = [
    "revenue", "total_debt", "market_cap", "current_ratio",
    "debt_to_equity", "profit_margin", "revenue_growth", "roa",
]

# Altman Z-Score clip bounds — prevents extreme outliers from dominating scaling
Z_SCORE_CLIP_LOW  = -5.0
Z_SCORE_CLIP_HIGH = 30.0


# ===========================================================================
# HELPER FUNCTIONS
# ===========================================================================

def prune_raw_supply_chain(prune_names: set) -> int:
    """
    Remove all edges from the RAW supply chain CSV where source OR target
    is one of the pruned company names.
    Returns the number of rows removed.
    """
    if not RAW_SC.exists():
        log.warning("Raw supply chain CSV not found — skipping.")
        return 0

    df = pd.read_csv(RAW_SC, dtype=str)
    before = len(df)
    mask = df["source"].str.strip().isin(prune_names) | \
           df["target"].str.strip().isin(prune_names)
    df = df[~mask]
    df.to_csv(RAW_SC, index=False, encoding="utf-8")
    removed = before - len(df)
    log.info("RAW supply_chain_combined.csv: removed %d row(s). Now %d rows.", removed, len(df))
    return removed


def prune_raw_financials(prune_names: set) -> int:
    """Remove rows from the RAW financials CSV for pruned companies."""
    if not RAW_FIN.exists():
        log.warning("Raw financials CSV not found — skipping.")
        return 0

    df = pd.read_csv(RAW_FIN, dtype=str)
    before = len(df)
    df = df[~df["company_name"].str.strip().isin(prune_names)]
    df.to_csv(RAW_FIN, index=False, encoding="utf-8")
    removed = before - len(df)
    log.info("RAW company_financials_validated.csv: removed %d row(s). Now %d rows.", removed, len(df))
    return removed


def prune_processed_supply_chain(prune_uuids: set) -> int:
    """
    Remove edges from PROCESSED supply chain CSV where source_id OR target_id
    is in the set of pruned UUIDs.
    """
    df = pd.read_csv(PROC_SC, dtype=str)
    before = len(df)
    mask = df["source_id"].str.strip().isin(prune_uuids) | \
           df["target_id"].str.strip().isin(prune_uuids)
    df = df[~mask]
    df.to_csv(PROC_SC, index=False, encoding="utf-8")
    removed = before - len(df)
    log.info("PROCESSED supply_chain_resolved.csv: removed %d edge(s). Now %d rows.", removed, len(df))
    return removed


def prune_entity_index(prune_names: set, idx: dict) -> dict:
    """Remove pruned company names from the entity index."""
    before = len(idx)
    idx = {k: v for k, v in idx.items() if k.strip() not in prune_names}
    removed = before - len(idx)
    log.info("entity_index.json: removed %d entry(ies). Now %d entries.", removed, len(idx))
    return idx


def apply_industry_median_imputation(fin: pd.DataFrame) -> pd.DataFrame:
    """
    ACCURACY MEASURE 1: Industry-median imputation for missing financial features.

    For each missing value, impute using the MEDIAN of the same column
    computed only over NON-subsidiary, NON-imputed companies in the dataset.
    This is more accurate than global mean because:
    - Automotive companies have similar ratio profiles
    - Subsidiaries would skew the reference pool
    - Median is robust to the extreme outliers present (e.g. Nvidia)

    A binary `{col}_imputed` flag column is added for each imputed column
    (accuracy measure 2 — lets GNN learn which features were imputed).
    """
    log.info("Applying industry-median imputation to missing financial features ...")

    # Reference pool: companies with real data (not subsidiaries with inherited financials)
    ref_mask = ~(
        (fin["is_subsidiary"].str.strip().str.lower().isin(["true", "1"])) &
        (fin["imputation_method"].str.strip().str.lower().isin(["parent_financials", "segment_reported"]))
    )
    ref_pool = fin[ref_mask].copy()

    imputation_log = []

    for col in FINANCIAL_FEATURES:
        if col not in fin.columns:
            continue

        # Convert to numeric
        fin[col] = pd.to_numeric(fin[col], errors="coerce")
        ref_pool[col] = pd.to_numeric(ref_pool[col], errors="coerce")

        missing_mask = fin[col].isna()
        n_missing = missing_mask.sum()

        if n_missing == 0:
            # No missing values — still add imputed flag (all False)
            fin[f"{col}_imputed"] = False
            continue

        # Compute industry median from reference pool
        col_median = ref_pool[col].median()

        if pd.isna(col_median):
            log.warning("Cannot compute median for '%s' — skipping imputation.", col)
            fin[f"{col}_imputed"] = missing_mask
            continue

        # Add binary flag BEFORE imputation (True = value was imputed)
        fin[f"{col}_imputed"] = missing_mask

        # Impute
        fin.loc[missing_mask, col] = col_median
        imputation_log.append(
            f"  {col:20s}: {n_missing:3d} missing -> imputed with median={col_median:.4g}"
        )

    log.info("Imputation summary:")
    for line in imputation_log:
        log.info(line)

    return fin


def apply_zscore_clipping(fin: pd.DataFrame) -> pd.DataFrame:
    """
    ACCURACY MEASURE 3: Clip Altman Z-Score to [-5, 30].

    Extremely high Z-Scores (e.g. Nvidia = 224) are valid mathematically
    but create massive variance in the feature distribution, which hurts
    gradient-based optimization in the GNN. Clipping to a sensible range:
    - Preserves the relative ordering (healthy vs distressed)
    - Prevents one outlier from dominating feature normalization
    - Does NOT change any default_label (labels were set before clipping)
    """
    if "altman_z_score" not in fin.columns:
        return fin

    z = pd.to_numeric(fin["altman_z_score"], errors="coerce")
    n_clipped_high = (z > Z_SCORE_CLIP_HIGH).sum()
    n_clipped_low  = (z < Z_SCORE_CLIP_LOW).sum()

    z_clipped = z.clip(lower=Z_SCORE_CLIP_LOW, upper=Z_SCORE_CLIP_HIGH)
    fin["altman_z_score"] = z_clipped

    log.info(
        "Z-Score clipping [%.1f, %.1f]: %d high values clipped, %d low values clipped.",
        Z_SCORE_CLIP_LOW, Z_SCORE_CLIP_HIGH, n_clipped_high, n_clipped_low
    )
    return fin


# ===========================================================================
# MAIN
# ===========================================================================

def main() -> int:

    log.info("=" * 60)
    log.info("SURGICAL PRUNE + ACCURACY MAXIMIZATION")
    log.info("=" * 60)

    # -----------------------------------------------------------------------
    # 1. Load entity index to get UUIDs for pruned companies
    # -----------------------------------------------------------------------
    with open(ENTITY_IDX, encoding="utf-8") as f:
        idx = json.load(f)

    # Collect UUIDs for all names that match any prune target
    prune_uuids: set = set()
    for name, uid in idx.items():
        if name.strip() in PRUNE_NAMES:
            prune_uuids.add(uid)
            log.info("Pruning: '%s'  ->  UUID %s", name.strip(), uid)

    if not prune_uuids:
        log.warning("None of the target company names were found in entity_index.json.")
        log.warning("Check that names match exactly.")
        return 1

    log.info("Total UUIDs to remove: %d", len(prune_uuids))

    # -----------------------------------------------------------------------
    # 2. Prune RAW files
    # -----------------------------------------------------------------------
    log.info("")
    log.info("--- RAW FILES ---")
    prune_raw_supply_chain(PRUNE_NAMES)
    prune_raw_financials(PRUNE_NAMES)

    # -----------------------------------------------------------------------
    # 3. Prune PROCESSED files
    # -----------------------------------------------------------------------
    log.info("")
    log.info("--- PROCESSED FILES ---")

    # 3a. Processed supply chain edges
    prune_processed_supply_chain(prune_uuids)

    # 3b. Processed financials — load, prune, then apply accuracy measures
    fin = pd.read_csv(PROC_FIN, dtype=str)
    before = len(fin)
    fin = fin[~fin["entity_id"].str.strip().isin(prune_uuids)].copy()
    removed = before - len(fin)
    log.info("PROCESSED company_financials_resolved.csv: removed %d row(s). Now %d rows.", removed, len(fin))

    # -----------------------------------------------------------------------
    # 4. Apply accuracy-maximization measures
    # -----------------------------------------------------------------------
    log.info("")
    log.info("--- ACCURACY MAXIMIZATION MEASURES ---")

    # Measure 1 + 2: Industry-median imputation + imputed flag columns
    fin = apply_industry_median_imputation(fin)

    # Measure 3: Z-Score outlier clipping
    fin = apply_zscore_clipping(fin)

    # Save processed financials
    fin.to_csv(PROC_FIN, index=False, encoding="utf-8")
    log.info("PROCESSED company_financials_resolved.csv saved: %d rows, %d columns.",
             len(fin), len(fin.columns))

    # 3c. Update entity index
    idx = prune_entity_index(PRUNE_NAMES, idx)
    with open(ENTITY_IDX, "w", encoding="utf-8") as f:
        json.dump(idx, f, indent=2, ensure_ascii=False, sort_keys=True)
    log.info("entity_index.json saved: %d entries.", len(idx))

    # -----------------------------------------------------------------------
    # 5. Final summary
    # -----------------------------------------------------------------------
    log.info("")
    log.info("=" * 60)
    log.info("PRUNING COMPLETE")
    log.info("  Companies removed             : %d", len(prune_uuids))
    log.info("  Remaining companies           : %d", len(fin))
    log.info("  New feature columns added     : %d imputed-flag columns", len(FINANCIAL_FEATURES))
    log.info("  Z-Score clipped to            : [%.1f, %.1f]", Z_SCORE_CLIP_LOW, Z_SCORE_CLIP_HIGH)
    log.info("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
