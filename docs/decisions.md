# Technical Decisions and Architecture

This document formalizes the structural math, graph rules, and data sources for the Supply Chain Network Credit Contagion project. It serves as a localized reference to prevent assumption drifts in ML engineering.

## 1. Graph Schema Definition: `G = (V, E, X, W)`
The supply chain is modeled as a heterogeneous, directed, weighted, multi-relational property graph.

### 1.1 Node Features (`X` - 16 dimensions)
**Intrinsic Features (Financial, 10 types):**
1. `revenue`: Total annual revenue
2. `total_debt`: Total debt outstanding
3. `market_cap`: Share price × shares outstanding
4. `current_ratio`: Current Assets / Current Liabilities
5. `debt_to_equity`: Total Debt / Shareholder Equity
6. `profit_margin`: Net Income / Revenue
7. `revenue_growth`: YoY % change in revenue
8. `interest_coverage`: EBIT / Interest Expense
9. `altman_z_score`: Composite bankruptcy predictor
10. `roa`: EBIT / Total Assets

**Extrinsic Features (Topological, 6 types):**
11. `in_degree`: Number of suppliers feeding the company
12. `out_degree`: Number of customers depending on it
13. `betweenness_centrality`: Bridge/bottleneck indicator
14. `eigenvector_centrality`: Transitive influence
15. `pagerank`: Random-walk importance
16. `clustering_coefficient`: Local redundancy

### 1.2 Edge Types (`E` - 3 types)
- `supply`: Supplier → Customer (Disruption propagates upstream to downstream)
- `trade_credit`: Creditor → Debtor (Contagion limits accounts receivable)
- `ownership`: Parent → Subsidiary (Equity exposure contagion)

### 1.3 Edge Weight Formula (`W`)
`w_ij = purchase_volume_ij / total_COGS_j`
(Represents the fraction of Company B's total cost of goods sold that comes from Supplier A)

---

## 2. Data Source Evaluation Matrix Priorities

- **Critical:**
  - SEC EDGAR 10-K: Supplier/customer names from filings
  - yfinance: Financial metrics for public companies
  - Company annual reports: Financial data for private companies
- **Supplementary:**
  - Kaggle datasets: Pre-built supply chain networks
  - CSMAR: Auto supplier lists
- **Nice-to-have:** FactSet Revere
- **Later (Phase 5):** WIOD
- **Stretch goal:** Panjiva / ImportGenius

---

## 3. Default Labeling Strategy
Primary Strategy: **Altman Z-Score**

### Formula
`Z = 1.2·X₁ + 1.4·X₂ + 3.3·X₃ + 0.6·X₄ + 1.0·X₅`
- `X₁`: Working Capital / Total Assets
- `X₂`: Retained Earnings / Total Assets
- `X₃`: EBIT / Total Assets
- `X₄`: Market Cap / Total Liabilities
- `X₅`: Revenue / Total Assets

### Labeling Thresholds
- **Z > 2.99**: Safe Zone `0` (Low bankruptcy risk)
- **1.81 < Z ≤ 2.99**: Grey Zone `0` (Uncertain - monitor closely)
- **Z ≤ 1.81**: Distress Zone `1` (High bankruptcy risk - proxy for default)

---

## 4. Team Task Split & Weekly Sync Setup

### Role-Based Task Assignment (Phase 2)
- **ML Person:** 
  - Extract supplier names from SEC 10-K filings.
  - Pull financial data via yfinance.
  - Compute Altman Z-scores and assign default labels.
- **Developer:** 
  - Set up SQLite database schema.
  - Write CSV to SQLite loader script.
  - Set up FastAPI backend.
- **Both:** Research and expand company list from SEC filings.

### Weekly Sync Format
- **Frequency:** 30-minute weekly call.
- **Agenda:**
  1. **Progress Check (10 min):** Completed tasks, current blockers (ML / Dev).
  2. **Data Review (10 min):** Total companies/edges, entity resolution issues, data source status.
  3. **Next Week's Goals (5 min):** Top 3 tasks for each person.
  4. **Technical Decisions (5 min):** Schema changes, tool/library decisions.
