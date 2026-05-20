"""
graph/entity_resolution.py
===========================
Step 11 — Entity Name Resolution & ID Injection

Purpose
-------
Resolve all raw company name variants (from supply chain edges and financial
records) into canonical UUIDs, then inject those UUIDs back into processed
output CSVs that Phase 3 graph construction will consume directly.

Three output files are produced:
    data/processed/entity_index.json          – master raw-name → UUID mapping
    data/processed/supply_chain_resolved.csv  – edge list with source_id / target_id
    data/processed/company_financials_resolved.csv – financials with entity_id

Resolution strategy (applied in this order):
    1. Deterministic normalisation — UPPERCASE + strip legal suffixes
       (Corp, Inc, AG, GmbH, Ltd, LLC, NV, SE, PLC, SA, SpA, …)
    2. Ticker alignment — rows that share the same non-empty ticker are merged
       into one canonical entity regardless of name variation
    3. Fuzzy matching — fuzz.token_sort_ratio ≥ 85 → auto-merge;
       80–84 → flag for manual review (logged, not merged automatically)

Subsidiary safety rule
-----------------------
A row where is_subsidiary == True AND parent_company is set receives its OWN
UUID that is distinct from its parent's UUID.  They are separate graph nodes.

Usage
-----
    python graph/entity_resolution.py

Dependencies
------------
    pip install pandas fuzzywuzzy python-Levenshtein
"""

import uuid
import json
import logging
import sys
from pathlib import Path

import pandas as pd
from fuzzywuzzy import fuzz  # fuzzy string matching library

# ---------------------------------------------------------------------------
# Logging setup — INFO to stdout so every major decision is visible
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path constants — all relative to project root
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent  # …/Supply Chain Network Credit Contagion

RAW_SUPPLY_CHAIN   = PROJECT_ROOT / "data" / "raw"       / "supply_chain_combined.csv"
RAW_FINANCIALS     = PROJECT_ROOT / "data" / "raw"       / "company_financials_validated.csv"

OUT_ENTITY_INDEX   = PROJECT_ROOT / "data" / "processed" / "entity_index.json"
OUT_SUPPLY_CHAIN   = PROJECT_ROOT / "data" / "processed" / "supply_chain_resolved.csv"
OUT_FINANCIALS     = PROJECT_ROOT / "data" / "processed" / "company_financials_resolved.csv"

# ---------------------------------------------------------------------------
# Legal suffix patterns to strip during normalisation
# Order matters: strip compound suffixes (e.g. "CO LTD") before simple ones
# ---------------------------------------------------------------------------
LEGAL_SUFFIXES = [
    # Multi-word suffixes first
    "HOLDING CO",
    "CO LTD",
    "CO INC",
    "PTE LTD",
    # Single-word suffixes
    "CORPORATION", "CORP",
    "INCORPORATED", "INC",
    "LIMITED", "LTD",
    "AKTIENGESELLSCHAFT", "AG",
    "GESELLSCHAFT MIT BESCHRÄNKTER HAFTUNG", "GMBH",
    "SOCIÉTÉ ANONYME", "SA",
    "SOCIEDAD ANÓNIMA",
    "SOCIETE ANONYME",
    "NV",       # Naamloze Vennootschap (Netherlands)
    "SE",       # Societas Europaea
    "PLC", "P.L.C.",
    "SPA", "S.P.A.",  # Società per Azioni (Italy)
    "LLC",
    "LP", "L.P.",
    "GROUP", "GROUP CO",
    "HOLDINGS", "HOLDING",
    "COMPANY", "CO",
    "INDUSTRIES", "INDUSTRY",
    "INTERNATIONAL", "INTL",
    "MANUFACTURING", "MFG",
    "AUTOMOTIVE",
    "SYSTEMS",
    "TECHNOLOGIES", "TECHNOLOGY", "TECH",
    "SOLUTIONS",
    "GLOBAL",
    "MOTORS", "MOTOR",   # keep short so "Motor Corp" → strip both
    "AUTO",
]

# Fuzzy thresholds (inclusive boundaries)
FUZZY_AUTO_MERGE   = 85   # score ≥ 85 → automatic same-entity
FUZZY_REVIEW       = 80   # 80 ≤ score < 85 → flag for manual review


# ===========================================================================
# NORMALISATION HELPERS
# ===========================================================================

def _strip_legal_suffix(name: str) -> str:
    """
    Strip recognised legal-entity suffixes from a company name.
    Iterates through the suffix list and removes trailing suffix tokens.
    Multiple passes handle stacked suffixes (e.g. 'Bosch GmbH Corp').
    """
    changed = True
    while changed:
        changed = False
        for suffix in LEGAL_SUFFIXES:
            # Match suffix at end of name, with optional trailing punctuation
            if name.endswith(suffix):
                candidate = name[: -len(suffix)].rstrip(" ,./")
                if candidate:            # do not reduce to empty string
                    name = candidate
                    changed = True
                    break                # restart outer loop
    return name


def normalise(raw_name: str) -> str:
    """
    Produce a normalised canonical key for comparison purposes.
    Steps:
        1. Strip whitespace
        2. UPPERCASE
        3. Remove common punctuation (dots, commas, hyphens, apostrophes)
        4. Collapse extra whitespace
        5. Strip legal suffixes
    The result is used ONLY for matching; the original raw_name is preserved
    in the entity index and in the output CSVs.
    """
    name = raw_name.strip().upper()
    # Remove punctuation that commonly differs between sources
    for char in [".", ",", "'", "\u2019", "-", "\u2013", "\u2014", "/"]:
        name = name.replace(char, " ")
    name = " ".join(name.split())   # collapse multiple spaces
    name = _strip_legal_suffix(name)
    name = " ".join(name.split())   # collapse again after suffix strip
    return name


# ===========================================================================
# ENTITY INDEX BUILDER
# ===========================================================================

def build_entity_index(
    sc_df: pd.DataFrame,
    fin_df: pd.DataFrame,
) -> dict:
    """
    Build the master entity index: a dict mapping every raw company name
    (exactly as it appears in the source files) to a canonical UUID string.

    Parameters
    ----------
    sc_df  : supply_chain_combined.csv DataFrame (source, target columns used)
    fin_df : company_financials_validated.csv DataFrame

    Returns
    -------
    entity_index : dict  {raw_name: uuid_string}

    Resolution order:
        Step A — Collect all unique raw names from both files
        Step B — Build ticker → canonical-uuid mapping (ticker alignment)
        Step C — Normalise + fuzzy-match remaining names
        Step D — Protect subsidiaries (they always get distinct UUIDs)
    """

    # -----------------------------------------------------------------------
    # Step A: Collect all unique raw names
    # -----------------------------------------------------------------------
    sc_sources = set(sc_df["source"].dropna().str.strip())
    sc_targets = set(sc_df["target"].dropna().str.strip())
    fin_names  = set(fin_df["company_name"].dropna().str.strip())

    # Union of ALL names from both files — every name must appear in the index
    all_raw_names: set = sc_sources | sc_targets | fin_names
    log.info("Unique raw names collected — %d total", len(all_raw_names))

    # -----------------------------------------------------------------------
    # Step B: Ticker alignment
    # Pre-assign UUIDs for names that share a known non-empty ticker.
    # All names with the same ticker map to one shared UUID.
    # -----------------------------------------------------------------------
    # ticker → uuid  (built from financials which carries ticker column)
    ticker_to_uuid: dict = {}

    # Build name → ticker lookup from financials
    name_to_ticker: dict = {}
    for _, row in fin_df.iterrows():
        raw_name = str(row["company_name"]).strip()
        ticker   = str(row.get("ticker", "")).strip()
        if ticker and ticker.lower() not in ("nan", "none", ""):
            name_to_ticker[raw_name] = ticker

    # Pre-create UUIDs keyed by ticker
    for ticker in set(name_to_ticker.values()):
        ticker_to_uuid[ticker] = str(uuid.uuid4())

    log.info("Ticker alignment pre-assigned %d tickers -> %d UUIDs",
             len(name_to_ticker), len(ticker_to_uuid))

    # -----------------------------------------------------------------------
    # Step C: Build subsidiary protection set
    # Any row where is_subsidiary is True AND parent_company is filled
    # must receive its own UUID (never merged with parent).
    # We record these raw names in a set; later they skip fuzzy merge even if
    # their normalised form would match their parent.
    # -----------------------------------------------------------------------
    subsidiary_names: set = set()
    for _, row in fin_df.iterrows():
        is_sub = str(row.get("is_subsidiary", "False")).strip()
        parent = str(row.get("parent_company", "")).strip()
        if is_sub.lower() in ("true", "1", "yes") and parent and parent.lower() not in ("nan", "none", ""):
            subsidiary_names.add(str(row["company_name"]).strip())

    log.info("Subsidiary-protected names: %d", len(subsidiary_names))

    # -----------------------------------------------------------------------
    # Step D: Main resolution loop
    # Data structures:
    #   entity_index   : raw_name → uuid_string   (the final output)
    #   canonical_pool : list of (normalised_form, uuid_string)
    #                    used for fuzzy comparison against new names
    # -----------------------------------------------------------------------
    entity_index: dict       = {}     # raw_name → uuid
    canonical_pool: list     = []     # [(norm_key, uuid), …]
    review_candidates: list  = []     # pairs flagged for manual review

    def _assign_new_uuid(raw_name: str, norm_key: str) -> str:
        """Create a fresh UUID, register it, and return it."""
        new_id = str(uuid.uuid4())
        entity_index[raw_name] = new_id
        canonical_pool.append((norm_key, new_id))
        return new_id

    def _assign_existing_uuid(raw_name: str, existing_uuid: str) -> None:
        """Map raw_name to an already-existing UUID (merge)."""
        entity_index[raw_name] = existing_uuid

    # Process names in a stable sorted order for reproducibility
    for raw_name in sorted(all_raw_names):

        if raw_name in entity_index:
            # Already resolved (e.g. via ticker alignment pre-pass below)
            continue

        norm_key = normalise(raw_name)
        is_subsidiary = raw_name in subsidiary_names

        # -- Ticker alignment check ------------------------------------------
        # If this name has a known ticker, use the pre-assigned ticker UUID
        # (unless it is a subsidiary — subsidiaries always get their own UUID)
        if not is_subsidiary and raw_name in name_to_ticker:
            ticker = name_to_ticker[raw_name]
            ticker_uuid = ticker_to_uuid[ticker]
            entity_index[raw_name] = ticker_uuid
            # Also register the normalised key in the pool if not already present
            if not any(k == norm_key for k, _ in canonical_pool):
                canonical_pool.append((norm_key, ticker_uuid))
            continue

        # -- Fuzzy matching against canonical pool ---------------------------
        best_score  = 0
        best_uuid   = None
        best_norm   = None

        for (pool_norm, pool_uuid) in canonical_pool:
            score = fuzz.token_sort_ratio(norm_key, pool_norm)
            if score > best_score:
                best_score = score
                best_uuid  = pool_uuid
                best_norm  = pool_norm

        if best_score >= FUZZY_AUTO_MERGE and not is_subsidiary:
            # Auto-merge: this name is the same entity as best_norm
            log.debug("AUTO-MERGE | '%s' → '%s' (score=%d, uuid=%s)",
                      raw_name, best_norm, best_score, best_uuid)
            _assign_existing_uuid(raw_name, best_uuid)

        elif FUZZY_REVIEW <= best_score < FUZZY_AUTO_MERGE and not is_subsidiary:
            # Score in grey zone — flag for review but DO NOT merge (safe default)
            review_candidates.append({
                "raw_name"   : raw_name,
                "norm_key"   : norm_key,
                "matched_to" : best_norm,
                "score"      : best_score,
                "matched_uuid": best_uuid,
            })
            log.warning("REVIEW NEEDED | '%s' ↔ '%s' (score=%d) — assigned new UUID",
                        raw_name, best_norm, best_score)
            _assign_new_uuid(raw_name, norm_key)

        else:
            # No match (or subsidiary) — new entity, new UUID
            if is_subsidiary:
                log.debug("SUBSIDIARY   | '%s' — assigning independent UUID", raw_name)
            _assign_new_uuid(raw_name, norm_key)

    # -----------------------------------------------------------------------
    # Step E: Verify every raw name from both files has an entry
    # -----------------------------------------------------------------------
    missing = [n for n in all_raw_names if n not in entity_index]
    if missing:
        log.error("BUG: %d names have no UUID entry — %s", len(missing), missing[:5])
        raise RuntimeError("Entity index is incomplete. See error log above.")

    log.info("Entity index built: %d entries total", len(entity_index))

    # Log manual-review candidates summary
    if review_candidates:
        log.warning("=== MANUAL REVIEW REQUIRED for %d name pairs ===",
                    len(review_candidates))
        for item in review_candidates:
            log.warning("  '%s'  ↔  '%s'  (score=%d)",
                        item["raw_name"], item["matched_to"], item["score"])
        log.warning("Each was given a SEPARATE UUID (conservative default).")

    return entity_index


# ===========================================================================
# VALIDATION HELPERS
# ===========================================================================

def validate_no_parent_subsidiary_merge(
    entity_index: dict,
    fin_df: pd.DataFrame,
) -> None:
    """
    Validate that no subsidiary shares a UUID with its parent company.
    Raises AssertionError if a violation is found.
    """
    violations = []
    for _, row in fin_df.iterrows():
        is_sub = str(row.get("is_subsidiary", "False")).strip()
        parent = str(row.get("parent_company", "")).strip()
        if is_sub.lower() in ("true", "1", "yes") and parent and parent.lower() not in ("nan", "none", ""):
            child_name  = str(row["company_name"]).strip()
            parent_name = parent

            child_uuid  = entity_index.get(child_name)
            parent_uuid = entity_index.get(parent_name)

            if child_uuid and parent_uuid and child_uuid == parent_uuid:
                violations.append(
                    f"SUBSIDIARY MERGE VIOLATION: '{child_name}' shares UUID "
                    f"{child_uuid} with parent '{parent_name}'"
                )

    if violations:
        for v in violations:
            log.error(v)
        raise AssertionError(
            f"{len(violations)} subsidiary–parent UUID collision(s) found. "
            "See error log above."
        )

    log.info("Validation PASS — no subsidiary merged with its parent")


def validate_no_blank_ids(
    sc_resolved: pd.DataFrame,
    fin_resolved: pd.DataFrame,
) -> None:
    """
    Validate that the resolved output CSVs have zero blank / NaN UUID columns.
    """
    sc_blanks  = sc_resolved["source_id"].isna().sum() + sc_resolved["target_id"].isna().sum()
    fin_blanks = fin_resolved["entity_id"].isna().sum()

    if sc_blanks > 0:
        log.error("supply_chain_resolved.csv: %d blank source_id/target_id values", sc_blanks)
    if fin_blanks > 0:
        log.error("company_financials_resolved.csv: %d blank entity_id values", fin_blanks)

    if sc_blanks + fin_blanks > 0:
        raise AssertionError("Blank UUID values found in resolved CSVs. See error log.")

    log.info("Validation PASS — zero blank IDs in both resolved CSVs")


def validate_ticker_uniqueness(entity_index: dict, fin_df: pd.DataFrame) -> None:
    """
    Validate that no two entities with DIFFERENT tickers share the same UUID.
    """
    uuid_to_tickers: dict = {}
    for _, row in fin_df.iterrows():
        raw_name = str(row["company_name"]).strip()
        ticker   = str(row.get("ticker", "")).strip()
        if ticker.lower() in ("nan", "none", ""):
            continue
        assigned_uuid = entity_index.get(raw_name)
        if assigned_uuid:
            uuid_to_tickers.setdefault(assigned_uuid, set()).add(ticker)

    violations = {
        uid: tickers
        for uid, tickers in uuid_to_tickers.items()
        if len(tickers) > 1
    }
    if violations:
        for uid, tickers in violations.items():
            log.error("UUID %s mapped to multiple tickers: %s", uid, tickers)
        raise AssertionError(
            f"{len(violations)} UUID(s) mapped to multiple distinct tickers. "
            "See error log."
        )
    log.info("Validation PASS — no UUID shared by distinct tickers")


# ===========================================================================
# MAIN PIPELINE
# ===========================================================================

def main() -> None:
    """
    Orchestrates the full entity resolution pipeline:
        1. Load raw CSVs
        2. Build entity index
        3. Run validations
        4. Inject UUIDs into processed CSVs
        5. Write outputs
    """

    # -----------------------------------------------------------------------
    # 1. Load raw input files
    # -----------------------------------------------------------------------
    log.info("Loading raw supply chain CSV: %s", RAW_SUPPLY_CHAIN)
    if not RAW_SUPPLY_CHAIN.exists():
        log.error("MISSING FILE: %s", RAW_SUPPLY_CHAIN)
        sys.exit(1)
    sc_df = pd.read_csv(RAW_SUPPLY_CHAIN, dtype=str)
    sc_df.columns = sc_df.columns.str.strip()
    sc_df["source"] = sc_df["source"].str.strip()
    sc_df["target"] = sc_df["target"].str.strip()
    log.info("  -> %d rows, %d unique sources, %d unique targets",
             len(sc_df),
             sc_df["source"].nunique(),
             sc_df["target"].nunique())

    log.info("Loading raw financials CSV: %s", RAW_FINANCIALS)
    if not RAW_FINANCIALS.exists():
        log.error("MISSING FILE: %s", RAW_FINANCIALS)
        sys.exit(1)
    fin_df = pd.read_csv(RAW_FINANCIALS, dtype=str)
    fin_df.columns = fin_df.columns.str.strip()
    fin_df["company_name"] = fin_df["company_name"].str.strip()
    log.info("  -> %d rows", len(fin_df))

    # Drop trailing empty rows (the financials CSV ends with one blank line)
    fin_df = fin_df.dropna(subset=["company_name"])
    fin_df = fin_df[fin_df["company_name"].str.strip() != ""]

    # -----------------------------------------------------------------------
    # 2. Build entity index
    # -----------------------------------------------------------------------
    log.info("Building entity index …")
    entity_index = build_entity_index(sc_df, fin_df)

    # -----------------------------------------------------------------------
    # 3. Validations — run BEFORE writing output
    # -----------------------------------------------------------------------
    log.info("Running validations …")
    validate_no_parent_subsidiary_merge(entity_index, fin_df)
    validate_ticker_uniqueness(entity_index, fin_df)

    # -----------------------------------------------------------------------
    # 4a. Inject UUIDs into supply chain CSV
    # -----------------------------------------------------------------------
    sc_resolved = sc_df.copy()
    sc_resolved["source_id"] = sc_resolved["source"].map(entity_index)
    sc_resolved["target_id"] = sc_resolved["target"].map(entity_index)

    # -----------------------------------------------------------------------
    # 4b. Inject UUIDs into financials CSV
    # -----------------------------------------------------------------------
    fin_resolved = fin_df.copy()
    fin_resolved["entity_id"] = fin_resolved["company_name"].map(entity_index)

    # -----------------------------------------------------------------------
    # 4c. Validate zero blanks in both resolved CSVs
    # -----------------------------------------------------------------------
    validate_no_blank_ids(sc_resolved, fin_resolved)

    # -----------------------------------------------------------------------
    # 5. Write outputs
    # -----------------------------------------------------------------------
    # Ensure the processed directory exists
    OUT_ENTITY_INDEX.parent.mkdir(parents=True, exist_ok=True)

    # 5a. entity_index.json
    with open(OUT_ENTITY_INDEX, "w", encoding="utf-8") as f:
        json.dump(entity_index, f, indent=2, ensure_ascii=False, sort_keys=True)
    log.info("Written: %s  (%d entries)", OUT_ENTITY_INDEX, len(entity_index))

    # 5b. supply_chain_resolved.csv
    # Column order: preserve all originals, then append source_id, target_id
    original_cols = list(sc_df.columns)
    sc_resolved = sc_resolved[original_cols + ["source_id", "target_id"]]
    sc_resolved.to_csv(OUT_SUPPLY_CHAIN, index=False, encoding="utf-8")
    log.info("Written: %s  (%d rows)", OUT_SUPPLY_CHAIN, len(sc_resolved))

    # 5c. company_financials_resolved.csv
    # Column order: preserve all originals, then append entity_id
    original_fin_cols = list(fin_df.columns)
    fin_resolved = fin_resolved[original_fin_cols + ["entity_id"]]
    fin_resolved.to_csv(OUT_FINANCIALS, index=False, encoding="utf-8")
    log.info("Written: %s  (%d rows)", OUT_FINANCIALS, len(fin_resolved))

    # -----------------------------------------------------------------------
    # 6. Final summary
    # -----------------------------------------------------------------------
    log.info("=" * 60)
    log.info("ENTITY RESOLUTION COMPLETE")
    log.info("  Entity index entries  : %d", len(entity_index))
    log.info("  Supply chain rows     : %d", len(sc_resolved))
    log.info("  Financials rows       : %d", len(fin_resolved))
    log.info("  Blank source_id       : %d", sc_resolved["source_id"].isna().sum())
    log.info("  Blank target_id       : %d", sc_resolved["target_id"].isna().sum())
    log.info("  Blank entity_id       : %d", fin_resolved["entity_id"].isna().sum())
    log.info("=" * 60)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()
