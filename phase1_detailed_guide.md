# Phase 1 — Detailed Actionable Guide (Week 1)

> **Goal:** Get fully organized — environment, repo, graph schema, anchor companies, data strategy — before writing a single line of project code.

---

## Day 1–2: Environment & Repository Setup

### Step 1: Install & Verify Tools

Ensure the following are installed on your machine. Open a terminal and verify each:

| Tool | Install From | Verify Command |
|------|-------------|----------------|
| **Python 3.10+** | [python.org](https://www.python.org/downloads/) or Anaconda | `python --version` → must show 3.10+ |
| **Git** | [git-scm.com](https://git-scm.com/downloads) | `git --version` |
| **VS Code** | [code.visualstudio.com](https://code.visualstudio.com/) | Open it, install Python + Jupyter extensions |
| **Node.js 18+** | [nodejs.org](https://nodejs.org/) (LTS) | `node --version` |

> [!TIP]
> You already have a conda environment set up (from a previous conversation). Activate it with `conda activate scncc` before proceeding.

### Step 2: Create the Shared GitHub Repository

1. Go to [github.com/new](https://github.com/new)
2. **Repository name:** `supply-chain-credit-contagion`
3. **Visibility:** Private (you can make it public later)
4. Check "Add a README file"
5. Add `.gitignore` → select **Python**
6. License → **MIT** (standard for academic projects)
7. Click **Create repository**
8. Clone it locally:
   ```
   git clone https://github.com/<your-username>/supply-chain-credit-contagion.git
   cd supply-chain-credit-contagion
   ```
9. Add your teammate as a collaborator: **Settings → Collaborators → Add people**

### Step 3: Create the Folder Structure

Your repo should have this exact structure. Create every folder now (even if empty — add a `.gitkeep` file in empty folders so Git tracks them):

```
supply-chain-credit-contagion/
├── data/
│   ├── raw/                ← unprocessed CSVs, SEC filings, Kaggle downloads
│   ├── processed/          ← cleaned, normalized, merged datasets
│   └── external/           ← WIOD tables, Crunchbase data, macro indicators
├── graph/
│   ├── build_graph.py      ← (create later) graph construction script
│   ├── entity_resolution.py
│   └── network_metrics.py
├── model/
│   ├── baseline/           ← logistic regression, random forest
│   ├── gnn/                ← GCN, GAT, GraphSAGE, PI-GNN code
│   └── evaluation/         ← metrics, confusion matrices, ROC plots
├── simulation/
│   ├── siis_model.py       ← SIIS epidemic contagion
│   ├── shock.py            ← SCR-NR / SCR-ER protocols
│   └── stress_test.py
├── api/                    ← FastAPI backend
├── frontend/               ← React dashboard
├── notebooks/              ← Jupyter experiments & EDA
├── tests/                  ← unit tests & integration tests
├── docs/                   ← project documentation
├── environment.yml         ← conda environment spec
└── README.md
```

To create all folders at once (run from repo root in PowerShell):

```powershell
$folders = @(
    "data/raw", "data/processed", "data/external",
    "graph", "model/baseline", "model/gnn", "model/evaluation",
    "simulation", "api", "frontend", "notebooks", "tests", "docs"
)
foreach ($f in $folders) {
    New-Item -ItemType Directory -Path $f -Force
    if (-not (Test-Path "$f/.gitkeep")) { New-Item -ItemType File -Path "$f/.gitkeep" -Force }
}
```

Then commit:
```
git add -A
git commit -m "chore: initialize project folder structure"
git push origin main
```

### Step 4: Set Up Branch Strategy

Agree on a simple branching model for two people:

| Branch | Purpose |
|--------|---------|
| `main` | Always stable, working code |
| `dev` | Integration branch — merge features here first |
| `feature/<name>` | Individual task branches (e.g., `feature/data-collection`, `feature/api-setup`) |

Create the `dev` branch now:
```
git checkout -b dev
git push origin dev
```

---

## Day 2–3: Define the Graph Schema

This is the **most important technical decision** of Phase 1. Your entire project builds on this.

### Your Graph: `G = (V, E, X, W)`

#### Nodes `V` — Corporate Entities

Each node represents **one company**. Every node gets a **UUID** (assigned during entity resolution in Phase 2).

| Node Attribute | Type | Description | Source |
|---------------|------|-------------|--------|
| `entity_id` | `UUID` | Unique identifier across all data sources | Generated |
| `name` | `string` | Canonical company name | Entity resolution |
| `ticker` | `string` | Stock ticker (if publicly traded) | yfinance |
| `sector` | `string` | Industry sector (e.g., "Automotive OEM") | Manual / SIC code |
| `tier` | `enum` | `OEM`, `Tier1`, `Tier2`, `Tier3`, `RawMaterial` | Manual classification |
| `country` | `string` | HQ country (ISO 3166-1 alpha-2) | yfinance / manual |
| `is_public` | `bool` | Whether the company is publicly traded | Manual |

#### Node Features `X ∈ ℝ^{|V| × d}` — Financial + Topological

These are the **features your GNN will actually learn from**. Split into two categories:

**Intrinsic Features (from financial data — 10 dimensions):**

| # | Feature | Formula / Source | Why It Matters |
|---|---------|-----------------|----------------|
| 1 | `revenue` | Total annual revenue | Company scale |
| 2 | `total_debt` | Total debt outstanding | Leverage exposure |
| 3 | `market_cap` | Share price × shares outstanding | Market's valuation |
| 4 | `current_ratio` | Current Assets / Current Liabilities | Short-term liquidity |
| 5 | `debt_to_equity` | Total Debt / Shareholder Equity | Leverage ratio |
| 6 | `profit_margin` | Net Income / Revenue | Profitability |
| 7 | `revenue_growth` | YoY % change in revenue | Growth trajectory |
| 8 | `interest_coverage` | EBIT / Interest Expense | Debt servicing ability |
| 9 | `altman_z_score` | Composite bankruptcy predictor (see below) | Default proxy |
| 10 | `roa` | EBIT / Total Assets | Asset efficiency |

**Extrinsic Features (from network topology — 6 dimensions):**

| # | Feature | NetworkX Function | Why It Matters |
|---|---------|-------------------|----------------|
| 11 | `in_degree` | `G.in_degree(node)` | How many suppliers feed this company |
| 12 | `out_degree` | `G.out_degree(node)` | How many customers depend on it |
| 13 | `betweenness_centrality` | `nx.betweenness_centrality(G)` | Bridge / bottleneck importance |
| 14 | `eigenvector_centrality` | `nx.eigenvector_centrality(G)` | Transitive influence |
| 15 | `pagerank` | `nx.pagerank(G)` | Random-walk importance |
| 16 | `clustering_coefficient` | `nx.clustering(G.to_undirected())` | Local redundancy |

> **Total feature dimension: `d = 16` per node** (you can add more later, but start with these)

#### Edges `E` — Relationship Types

Your graph is a **heterogeneous multi-relational directed graph**. Three edge types:

| Edge Type | Direction | Meaning | Example |
|-----------|-----------|---------|---------|
| `supply` | Supplier → Customer | A supplies parts/materials to B | Denso → Toyota |
| `trade_credit` | Creditor → Debtor | A extends payment terms to B | Bosch → BMW (net-60 terms) |
| `ownership` | Parent → Subsidiary | A owns equity in B | Toyota → Denso (24.7% stake) |

> [!IMPORTANT]
> **Edge direction matters.** For `supply` edges, the arrow goes **Supplier → Customer** (A supplies B). This means risk propagates in the **reverse** direction — if Supplier A fails, Customer B suffers. Your GNN's message passing will naturally handle this.

#### Edge Weights `W` — Relationship Intensity

| Edge Attribute | Type | Description | How to Estimate |
|---------------|------|-------------|-----------------|
| `weight` | `float [0,1]` | Normalized relationship intensity | See formula below |
| `relationship_type` | `enum` | `supply`, `trade_credit`, `ownership` | Manual / NLP extraction |
| `data_source` | `string` | Where this edge came from | `sec_10k`, `kaggle`, `manual` |
| `confidence` | `float [0,1]` | How sure you are this edge exists | 1.0 for verified, 0.7 for NLP-extracted |
| `last_verified` | `date` | When this relationship was last confirmed | Filing date |

**Weight formula (for supply edges):**
```
w_ij = purchase_volume_ij / total_COGS_j
```
If you don't have exact volumes (likely), start with `weight = 1.0` for all edges and refine later.

#### Schema Summary Diagram

```
[Company A] ——supply(w=0.3)——→ [Company B]
   │                              │
   ├── entity_id: uuid            ├── entity_id: uuid
   ├── name: "Denso Corp"         ├── name: "Toyota Motor"
   ├── ticker: "6902.T"           ├── ticker: "TM"
   ├── tier: Tier1                ├── tier: OEM
   ├── X = [rev, debt, ...]       ├── X = [rev, debt, ...]
   └── default_label: 0           └── default_label: 0
```

---

## Day 3–4: Choose Anchor Companies (The Starting 30)

### Why Automotive Manufacturing?

| Factor | Automotive | Electronics | Pharma |
|--------|-----------|-------------|--------|
| **SEC filing availability** | ⭐⭐⭐ Excellent | ⭐⭐⭐ Excellent | ⭐⭐ Good |
| **Clear tiered structure** | ⭐⭐⭐ Very clear | ⭐⭐ Moderate | ⭐ Weak |
| **Public supply chain data** | ⭐⭐⭐ Best in class | ⭐⭐ Good | ⭐ Limited |
| **Historical disruptions** | ⭐⭐⭐ (COVID, chips, Suez) | ⭐⭐ | ⭐⭐ |
| **Academic precedent** | ⭐⭐⭐ Most studied | ⭐⭐ | ⭐ |

**Verdict:** Automotive is the best choice. Stick with it.

### Your 30 Anchor Companies

> [!NOTE]
> These are your **seed nodes**. In Phase 2, you will expand to ~300 by exploring 10-K filings of these anchors and discovering their suppliers/customers.

#### OEMs (Original Equipment Manufacturers) — 10 companies

| # | Company | Ticker | Country | Why Include |
|---|---------|--------|---------|-------------|
| 1 | Toyota Motor | `TM` | Japan | World's largest automaker by volume |
| 2 | Volkswagen Group | `VWAGY` | Germany | Europe's largest; owns Audi, Porsche, etc. |
| 3 | General Motors | `GM` | USA | Major US OEM; heavy domestic supply chain |
| 4 | Ford Motor | `F` | USA | Major US OEM; detailed 10-K disclosures |
| 5 | Stellantis | `STLA` | Netherlands | Owns Chrysler, Fiat, Peugeot, Jeep |
| 6 | Honda Motor | `HMC` | Japan | Major global OEM |
| 7 | BMW Group | `BMWYY` | Germany | Premium segment; vertical integration |
| 8 | Hyundai Motor | `HYMTF` | South Korea | Fast-growing; EV transition |
| 9 | Tesla | `TSLA` | USA | EV leader; unique supply chain (vertically integrated) |
| 10 | Nissan Motor | `NSANY` | Japan | Alliance with Renault; supply chain disruption history |

#### Tier 1 Suppliers — 12 companies

| # | Company | Ticker | Country | What They Supply |
|---|---------|--------|---------|------------------|
| 11 | Robert Bosch* | Private | Germany | Automotive electronics, braking, powertrain |
| 12 | Denso Corp | `DNZOY` | Japan | Thermal, powertrain, electronics; 24.7% Toyota-owned |
| 13 | ZF Friedrichshafen* | Private | Germany | Transmissions, chassis, safety systems |
| 14 | Magna International | `MGA` | Canada | Contract manufacturing, mirrors, closures |
| 15 | Continental AG | `CTTAY` | Germany | Tires, braking, electronics, ADAS |
| 16 | Aisin Corp | `ASEKY` | Japan | Drivetrain, body, electronics |
| 17 | Lear Corporation | `LEA` | USA | Seating, e-systems |
| 18 | Aptiv | `APTV` | Ireland (HQ) | Vehicle wiring, connectors, ADAS |
| 19 | BorgWarner | `BWA` | USA | Turbochargers, drivetrain, electrification |
| 20 | Yazaki* | Private | Japan | Wire harnesses, instrumentation |
| 21 | Hyundai Mobis | `HYUMY` (OTC) | South Korea | Modules, chassis, infotainment |
| 22 | Faurecia / Forvia | `FURCF` (OTC) | France | Interiors, seating, clean mobility |

> \*Companies marked with * are **private** — no ticker. You will need to manually enter financial data from public sources (annual reports, press releases).

#### Tier 2 / Raw Materials / Adjacent — 8 companies

| # | Company | Ticker | Country | Role in Supply Chain |
|---|---------|--------|---------|---------------------|
| 23 | CATL | `300750.SZ` | China | Largest EV battery manufacturer |
| 24 | Panasonic Holdings | `PCRFY` | Japan | Tesla battery partner; electronics |
| 25 | Nucor Steel | `NUE` | USA | Major automotive-grade steel supplier |
| 26 | Alcoa Corp | `AA` | USA | Aluminum (lightweighting) |
| 27 | TSMC | `TSM` | Taiwan | Automotive chip fabrication |
| 28 | NXP Semiconductors | `NXPI` | Netherlands | Automotive-specific chips |
| 29 | Flex Ltd | `FLEX` | Singapore | Contract electronics manufacturing |
| 30 | BASF | `BASFY` | Germany | Automotive coatings, catalysts, plastics |

### How to Record This

Create a spreadsheet or CSV called `data/raw/anchor_companies.csv`:

```csv
entity_id,name,ticker,country,tier,sector,is_public
,Toyota Motor,TM,JP,OEM,Automotive,TRUE
,Volkswagen Group,VWAGY,DE,OEM,Automotive,TRUE
,General Motors,GM,US,OEM,Automotive,TRUE
...
```

Leave `entity_id` blank for now — you'll assign UUIDs during entity resolution in Phase 2.

---

## Day 4–5: Evaluate & Plan Your Data Sources

Before collecting data, know **exactly** what you'll use and what each source gives you.

### Data Source Evaluation Matrix

| Source | What It Gives You | Cost | Difficulty | Priority |
|--------|------------------|------|-----------|----------|
| **SEC EDGAR 10-K** | Supplier/customer names from filings (Item 1, 1A, 7) | Free | Medium (NLP needed) | 🔴 Critical |
| **yfinance** | Financial metrics (revenue, debt, ratios) for public companies | Free | Easy (Python API) | 🔴 Critical |
| **Kaggle datasets** | Pre-built supply chain networks (search "supply chain") | Free | Easy | 🟡 Supplementary |
| **FactSet Revere** | Curated supplier-customer relationships | Paid (trial available) | Easy | 🟡 Nice-to-have |
| **WIOD** | Macro-level inter-sector trade flows for shock parameters | Free | Medium | 🟢 Later (Phase 5) |
| **Panjiva / ImportGenius** | Customs/shipment records → infer volumes | Paid | Hard | 🟢 Stretch goal |
| **Company annual reports** | Financial data for private companies (Bosch, ZF, Yazaki) | Free | Manual | 🔴 Critical |

### SEC EDGAR — How to Actually Use It

This is your **primary** source for building edges. Here's the exact process:

1. **Go to:** [efts.sec.gov/LATEST/search-index](https://efts.sec.gov/LATEST/search-index?q=%22major+supplier%22&dateRange=custom&startdt=2023-01-01&enddt=2025-01-01&forms=10-K)
   - This is the full-text search endpoint for EDGAR filings
2. **Search for each anchor company** by name or CIK number
3. **Open their latest 10-K filing** (annual report)
4. **Ctrl+F** search within the filing for these keywords:
   - `"major supplier"`, `"significant supplier"`, `"key supplier"`
   - `"principal customer"`, `"major customer"`, `"significant customer"`
   - `"supply agreement"`, `"supply chain"`, `"sole source"`
   - `"purchase commitment"`, `"raw material"`
5. **For each supplier/customer named**, add a row to your edge list CSV

> [!TIP]
> **Start manual, automate later.** For Week 1, just manually extract suppliers from 5–10 of your anchor companies' 10-K filings. In Phase 2, you'll write NLP scripts to scale this.

### yfinance — Quick Financial Data Check

To verify tickers work, open a Python shell and test:

```python
import yfinance as yf
stock = yf.Ticker("TM")  # Toyota
print(stock.info.get("shortName"))      # "Toyota Motor Corporation"
print(stock.info.get("totalRevenue"))    # should be ~$280B
print(stock.info.get("debtToEquity"))    # leverage
print(stock.info.get("currentRatio"))    # liquidity
```

If a ticker returns `None` for key fields, you may need an alternate ticker (e.g., some Japanese companies use Tokyo Stock Exchange tickers like `7203.T` instead of ADR tickers).

---

## Day 5–6: Default Labeling Strategy

Your GNN needs a **target variable** — which companies have defaulted or are at high risk?

### The Problem

Actual corporate defaults are **rare events** (< 2% per year). You won't have enough real defaults for 300 companies.

### The Solution: Multi-Strategy Labeling

Use **three complementary approaches** to label your `default_label` column:

#### Strategy 1: Altman Z-Score (Primary — compute from yfinance data)

The Altman Z-score is a well-established bankruptcy predictor. You can compute it entirely from data available via yfinance:

```
Z = 1.2·X₁ + 1.4·X₂ + 3.3·X₃ + 0.6·X₄ + 1.0·X₅
```

Where:
- **X₁** = Working Capital / Total Assets (liquidity)
- **X₂** = Retained Earnings / Total Assets (cumulative profitability)
- **X₃** = EBIT / Total Assets (operating efficiency)
- **X₄** = Market Cap / Total Liabilities (solvency)
- **X₅** = Revenue / Total Assets (asset turnover)

**Labeling thresholds:**

| Z-Score Range | Zone | Default Label |
|:---:|:---:|:---:|
| Z > 2.99 | Safe Zone | `0` (healthy) |
| 1.81 < Z ≤ 2.99 | Grey Zone | `0` (healthy, but flagged) |
| Z ≤ 1.81 | Distress Zone | `1` (default proxy) |

#### Strategy 2: Credit Rating Downgrade Proxy

If a company's credit rating has been downgraded to **BB+ or below** (non-investment grade / "junk"), label it as `1`. Sources:
- S&P ratings (search `"<company name> credit rating"`)
- Moody's (search `"<company name> Moody's rating"`)
- Free lookup at [tradingeconomics.com/bonds](https://tradingeconomics.com/)

#### Strategy 3: Market-Implied Distress

Use **Merton Distance-to-Default (DtD)** as a continuous risk score (you'll implement this in Phase 4, but plan for it now):
- DtD < 1.5 → high distress → `default_label = 1`
- DtD > 3.0 → healthy → `default_label = 0`

> [!IMPORTANT]
> **For Phase 1, just use Strategy 1 (Altman Z-Score).** It's computable from free data. You'll add Strategies 2 and 3 later.

---

## Day 6–7: Task Split & Weekly Sync Setup

### Role-Based Task Assignment for Week 2+

| Phase 2 Task | Who | Deliverable |
|-------------|-----|-------------|
| Extract supplier names from SEC 10-K filings (manual first, then NLP) | ML Person | `data/raw/supply_chain.csv` |
| Pull financial data via yfinance for all 30 anchors | ML Person | `data/raw/company_financials.csv` |
| Compute Altman Z-Scores and assign default labels | ML Person | `default_label` column in financials CSV |
| Set up SQLite database schema | Developer | `data/scncc.db` with tables |
| Write CSV → SQLite loader script | Developer | `api/load_data.py` |
| Set up FastAPI with health-check endpoint | Developer | `api/main.py` with `/` endpoint |
| Research and list additional companies from SEC filings | Both | Expand from 30 → 100+ companies |

### Weekly Sync Meeting Template

Set a recurring **30-minute weekly call**. Use this agenda:

```
SCNCC Weekly Sync — [Date]
───────────────────────────
1. Progress Check (10 min)
   - ML Person: What did you finish? What's blocked?
   - Developer: What did you finish? What's blocked?

2. Data Review (10 min)
   - How many companies/edges do we have now?
   - Any entity resolution issues?
   - Any data sources that aren't working?

3. Next Week's Goals (5 min)
   - ML Person's top 3 tasks for next week
   - Developer's top 3 tasks for next week

4. Technical Decisions (5 min)
   - Any schema changes needed?
   - Any tool/library decisions to make?
```

---

## Phase 1 Completion Checklist

By end of Week 1, you should have **all** of these done:

- [ ] Python 3.10+, Git, VS Code, Node.js installed and verified
- [ ] GitHub repository created with correct folder structure
- [ ] Branching strategy agreed on (`main` → `dev` → `feature/*`)
- [ ] Graph schema `G = (V, E, X, W)` fully defined (as documented above)
- [ ] 30 anchor companies identified with tickers in `data/raw/anchor_companies.csv`
- [ ] Automotive sector selected with justification documented
- [ ] Data source evaluation completed (know what you'll use for edges vs. features)
- [ ] Default labeling strategy decided (Altman Z-Score primary)
- [ ] Quick yfinance test — verified tickers work for at least 10 companies
- [ ] SEC EDGAR — read at least 2–3 10-K filings manually, found supplier names
- [ ] Task split for Phase 2 written down
- [ ] Weekly sync meeting scheduled (calendar invite sent)
- [ ] [environment.yml](file:///d:/Supply%20Chain%20Network%20Credit%20Contagion/environment.yml) or `requirements.txt` updated if new packages are needed
- [ ] All decisions committed to `docs/decisions.md` in the repo

> [!CAUTION]
> **Don't skip the manual SEC filing review.** Reading even 2–3 real 10-K filings yourself gives you intuition for what the NLP pipeline needs to extract in Phase 2. This cannot be skipped.
