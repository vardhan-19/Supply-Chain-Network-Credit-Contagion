# U_DeepResearch_Roadmap — Project Implementation Roadmap: Supply-Chain Network Credit Contagion

## Overview

Traditional credit-risk evaluation treats firms as isolated entities and misses systemic risk embedded in production and trade networks. This project constructs a heterogeneous, multi-relational supply-chain graph for the automotive manufacturing and parts sector and uses Graph Neural Networks (GNNs) with message passing to model credit contagion, predict network-adjusted Probability of Default (PD) and Expected Loss (EL), and deliver a GPU-accelerated interactive dashboard for risk managers.

---

## Phase 1: Data Engineering & Graph Construction

**Goal:** deterministically and probabilistically construct a multi-relational, heterogeneous supply-chain property graph `G = (V, E, X, W)` where:

* `V` — corporate entities (nodes)
* `E` — supply, trade-credit, and ownership linkages (edges)
* `X` — node feature matrix
* `W` — edge weight matrix (relationship intensities)

**Primary challenges:** aggregating, aligning, and entity resolving unstructured and semi-structured alternative data sources into a unified relational schema that supports deep graph learning at scale.

**Key data sources and methods**
s (SEC sources) are parsed and preprocessed (HTML → Markdown) for NLP/NER extraction of supplier–customer dyads. SEC
* High-frequency shippi
* Regulatory filingng data from Panjiva (transaction-level customs records) is parsed with ML to infer shipment volumes and map entities to corporate parents. Panjiva
* Entity resolution combines deterministic exact matches, probabilistic string distance metrics, and graph-based similarity to attach subsidiaries to parents and avoid fragmentation.
* Macroeconomic anchoring uses the World Input-Output Database for sectoral flows and to parameterize exogenous shocks. World Input-Output Database
* Cross-validation and enrichment leverage datasets such as the Federal Reserve Bank of New York’s Company/Crunchbase dataset and CSMAR supplier lists. Federal Reserve Bank of New York Crunchbase CSMAR
* Store resulting heterogeneous property graph in a distributed graph database capable of handling massive cardinality and property counts.

### Regulatory parsing / preprocessing

* Convert native HTML filings to Markdown to preserve headings/tables and reduce extraneous tokens.
* Apply NLP/NER to extract disclosed dependencies and produce structured edgelists.

### High-volume shipping / transaction mapping

* Parse Panjiva customs records with ML; aggregate volumes/frequencies to form weighted, directed edges.

### Entity resolution

* Combine deterministic matching + probabilistic string distances + graph similarity to build a master entity index with UUIDs.

### Macroeconomic alignment

* Map micro-level firm networks to macro sectoral flows to create exogenous risk features appended to node attributes.

### Table 1.1: Data Engineering and Graph Construction Specifications

| Component / Task            |                                     Data Sources | Processing Methodology & Algorithms                                                    | Expected Deliverable                                                     |
| --------------------------- | -----------------------------------------------: | -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| Regulatory Parsing          |            SEC 10-K/20-F filings, Annual Reports | HTML → Markdown pipelines; NLP NER for supplier–customer dyads                         | Structured edgelist of disclosed corporate dependencies (baseline graph) |
| Transaction & Trade Mapping | Panjiva shipment data, CSMAR auto supplier lists | ML parsing of unstructured customs data; aggregate volume & frequency for edge weights | Weighted, directed edges representing physical trade intensity           |
| Entity Resolution           |       SEC Metadata, Crunchbase, Panjiva entities | Probabilistic record linkage; graph-based entity alignment                             | Unified master entity index with UUIDs                                   |
| Macroeconomic Anchoring     |                      World Input-Output Database | Knowledge-graph alignment merging micro networks with macro flows                      | Exogenous risk features mapped to corporate nodes                        |
| Graph Schema Compilation    |                            All processed sources | Instantiate heterogeneous graph with multiple edge types                               | Queryable multi-relational property graph in distributed DB              |

---

## Phase 2: Feature Engineering & Network Analytics

**Goal:** compute intrinsic firm attributes and extrinsic network-derived topological features, and create time-aware edge encodings for the GNN.

### Intrinsic node features (`X ∈ ℝ^{|V| × d}`)

* Normalized accounting and market metrics:

  * Leverage (Debt-to-Equity), Liquidity (Current, Quick ratios)
  * Profitability margins, revenue growth, baseline PD / credit scores
* These define idiosyncratic vulnerability prior to network contagion.

### Extrinsic topological node features

* Degree centrality (separate in-degree / out-degree)
* Eigenvector centrality / PageRank (transitive influence)
* Clustering coefficients (local redundancy vs. bottleneck risk)

### Edge features (`W`)

* Transaction intensity: normalized shipment volumes
* Trade-credit volumes: monetary exposure inferred from disclosures
* Supplier dependency ratio: share of buyer’s COGS from a given supplier
* Directionality and temporal decay

### Temporal features

* Encode irregular, non-equidistant transaction time series using temporal convolutional feature extractors (tCNN) to distinguish active vs. dormant relationships and capture seasonality / lead times.

### Table 2.1: Feature Engineering and Analytics Specifications

| Feature Category          | Specific Metrics / Indicators                                | Mathematical Formulation & Algorithm                     | Purpose in Contagion Model                                     |
| ------------------------- | ------------------------------------------------------------ | -------------------------------------------------------- | -------------------------------------------------------------- |
| Intrinsic Node Attributes | Leverage, Liquidity, Revenue Growth, Baseline PD             | Matrix `X_i ∈ ℝ^d`; extracted from normalized financials | Idiosyncratic vulnerability prior to network shock             |
| Topological Node Features | Degree centrality, Eigenvector centrality, PageRank          | `CE(i)=λ_1 ∑_{j∈M(i)} CE(j)` where `M(i)` = neighbors    | Quantifies systemic importance & transmission potential        |
| Local Density Metrics     | Clustering coefficients                                      | `C_i = (2 e_i) / (k_i (k_i − 1))`                        | Identifies redundancy vs. critical single points of failure    |
| Edge Attributes           | Transaction intensity, trade credit volume, dependency ratio | Asymmetric `W_ij` normalized by total flows              | Conduit capacity and directional magnitude of risk propagation |
| Temporal Edge Features    | Irregular time series encoding                               | tCNN processing for non-equidistant observations         | Captures lead-time, seasonality, decay of relationships        |

---

## Phase 3: GNN Architecture & Training

**Analytical core:** hybrid GNN combining GCN, GAT, graph contrastive learning, heterophily handling, and physics-informed constraints.

### Architectural components

* **Message passing core:** Graph Convolutional Networks (GCN) for isotropic neighborhood aggregation using normalized adjacency / Laplacian matrices.
* **Attention:** Graph Attention Networks (GAT) multi-head layers to compute edge-wise attention coefficients (anisotropic weighting).
* **Heterophily handling:** Contrastive Unsupervised GNN (CuGNN) with adaptive convolution (balance of low-pass/high-pass filtering) to capture heterophilic financial links.
* **Contrastive learning:** instance-level and graph-level contrastive losses (pseudo-Siamese) to learn cluster-friendly latent embeddings for sparse or unlabeled regions.
* **Physics-informed constraints (PI-GNN):** add loss penalties enforcing conservation of material flow, production capacity limits, and lead-time constraints to prevent physically impossible predictions.

### Regularization & optimization to prevent representational collapse

* Address over-smoothing / over-squashing via structural dropout in aggregation (DropAGG) and Graph Random Aggregation Networks (GRANet).
* Sample/discretize features in high-entropy regions (SDE methods).
* Use linear control / state-space perspectives to ensure continuous gradient flow for deep message passing without excessive trainable parameters.

### Table 3.1: GNN Architecture and Training Specifications

| Architectural Component | Algorithm / Mechanism              | Implementation Details                                                | Expected Deliverable                                 |
| ----------------------- | ---------------------------------- | --------------------------------------------------------------------- | ---------------------------------------------------- |
| Message Passing Core    | Graph Convolutional Networks (GCN) | Spectral convolution using normalized adjacency                       | Baseline isotropic neighborhood aggregation          |
| Attention Mechanism     | Graph Attention Networks (GAT)     | Multi-head self-attention over node pairs                             | Anisotropic risk weighting; isolate critical paths   |
| Heterophily Handling    | CuGNN adaptive convolution         | High-pass & low-pass filtering for disparate profiles                 | Accurately model contrasting entities                |
| Cluster Representation  | Graph Contrastive Learning         | Instance & graph-level contrastive losses via pseudo-siamese networks | Unsupervised identification of high-risk communities |
| Domain Constraints      | Physics-Informed GNN (PI-GNN)      | Custom loss enforcing flow & capacity constraints                     | Physically viable contagion predictions              |

---

## Phase 4: Contagion Simulation & Stress Testing

**Goal:** introduce localized shocks and quantify systemic degradation through SIIS epidemic models, Cox-Copula joint default modeling, and targeted shock protocols.

### Contagion model

* Use an extended SIIS (Susceptible → Infected1 → Infected2 → Susceptible) to distinguish:

  * `Infected1` — idiosyncratic distress (internal failure)
  * `Infected2` — systemic distress (default caused by upstream/downstream collapse)
* Integrate a Cox–Copula framework to evaluate joint default probabilities under interacting macro and micro factors.

### Shock injection protocols

* **SCR-NR (Supply Chain Resilience — Node Removal):** remove or reduce capacity of high-centrality firms or geographic clusters (simulate bankruptcy, disaster, sanctions).
* **SCR-ER (Edge Removal):** sever critical supply routes or trade-credit lines (simulate port closures, strikes, frozen financing).

### Post-shock propagation

* Run GNN forward passes on perturbed graphs to compute network-adjusted PDs for every node.
* Recalculate portfolio metrics: EL, VaR, Expected Shortfall (ES).
* Compute Systemic Risk Contribution (SRC) per firm as expected losses induced by its idiosyncratic default plus cascading defaults.

**Empirical benchmarks:** prior microdata show SCN contagion can amplify EL by ~5.2×, VaR by ~6.7×, and ES by ~4.4× (these are example empirical multipliers for reference).

### Table 4.1: Contagion Simulation and Stress Testing Specifications

| Simulation Component              | Methodology / Protocol                       | Financial / Network Metrics Output                               | Strategic Purpose                                             |
| --------------------------------- | -------------------------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------- |
| Epidemic Contagion Modeling       | SIIS process                                 | Transition probabilities between idiosyncratic & systemic states | Separate internal risk from network-transmitted systemic risk |
| Joint Default Probability         | Cox-Copula integration                       | Dynamic joint default parameters                                 | Assess joint vulnerabilities on actual transaction paths      |
| Shock Injection Protocol          | SCR-NR & SCR-ER                              | Node/edge severing with probability `p`                          | Model multi-modal disruptions (geopolitical, cyber, natural)  |
| Risk Amplification Quantification | Network-adjusted PD, EL, VaR, ES integration | Recalculated portfolio metrics; amplification factors            | Provide true-cost estimates of cascading defaults             |
| Systemic Importance Scoring       | Systemic Risk Contribution (SRC)             | Aggregate primary + contagion-induced secondary losses           | Identify firms causing disproportionate systemic risk         |

---

## Phase 5: Dashboard Engineering & Deployment

**Goal:** translate GNN tensors, attention coefficients, and simulation outputs into an interpretable, low-latency GPU-accelerated visualization dashboard for non-technical risk managers.

### Front-end rendering

* Use GPU-accelerated WebGL force layouts and specialized rendering engines (e.g., Cosmograph) to offload many-body force computations to GPU for fluid interaction on multi-million node graphs. Cosmograph

### Data integration architecture

* Favor **zero-ETL** graph analytics to query data in place across data lakes/warehouses without heavy replication, ensuring real-time accuracy of customs, financial, and macro streams.

### UI features

* **Systemic Supplier Risk Rankings:** ranked by SRC.
* **Interactive scenario interface:** visual click-and-remove nodes/edges to trigger backend PI-GNN recalculations (on-the-fly SCR-NR / SCR-ER).
* **What-if visualization:** contagion radius, predicted downstream rating downgrades, EL amplification visual overlays.
* **Natural Language Generation (NLG):** synthesize numerical outcomes into concise, actionable recommendations (e.g., diversification or liquidity support suggestions).
* **APIs:** REST/GraphQL model endpoints for ERP and enterprise risk platform integration.

### Table 5.1: Dashboard Engineering and Deployment Specifications

| Infrastructure / UI Component | Technology / Technique              | Functional Capability                                       | Business Value                                                     |
| ----------------------------- | ----------------------------------- | ----------------------------------------------------------- | ------------------------------------------------------------------ |
| Large-Scale Rendering Engine  | GPU-accelerated WebGL force layouts | Offload many-body force sims to GPU for real-time rendering | Interactive exploration across multi-million node graphs           |
| Data Integration Architecture | Zero-ETL graph analytics            | Direct query translation over existing lakes/warehouses     | Real-time metrics; reduced maintenance & replication               |
| Scenario Command Interface    | Interactive UI/UX                   | Click/remove nodes/edges and trigger backend recalcs        | Democratize epidemiological stress-testing for non-technical users |
| Insight Translation Layer     | Natural Language Generation (NLG)   | Convert metrics into plain-language alerts                  | Bridge deep learning outputs to procurement decisions              |
| Enterprise Integration        | REST/GraphQL APIs & microservices   | Expose GNN inference & scenario endpoints                   | Embed contagion awareness into ERP / credit pipelines              |

---

## Risk Assessment & Mitigations

**Key algorithmic risks and programmatic mitigations**

### Over-smoothing & over-squashing

* **Problem:** deep message passing aggregates distant features, causing representation collapse and vanishing gradients.
* **Mitigations:** DropAGG structural aggregation dropout; GRANet; SDE sampling in high-entropy regions; state-space control formulations to preserve gradient flow without extra parameters.

### Data sparsity in deep tiers

* **Problem:** visibility drops sharply after tier-1; sparse bridges can skew attention in GAT layers and cause false negatives.
* **Mitigations:** Use CuGNN contrastive learning to infer latent dependencies; physics-informed bounds to prevent hallucinated supply flows or impossible capacities.

### Heterophily

* **Problem:** financial networks often join dissimilar nodes; standard homophilic GNNs fail.
* **Mitigations:** CuGNN adaptive filters (low/high pass) and specialized contrastive objectives to preserve signal for disparate node pairs.

---

## Deliverables (summary)

1. Distributed, queryable multi-relational property graph of the automotive supply chain with UUID master entity index.
2. Intrinsic + extrinsic node/edge feature matrices, including temporal encodings.
3. Trained hybrid GNN (GCN + GAT + CuGNN + PI-GNN) with contrastive pretraining and structural regularization.
4. Contagion simulation engine supporting SIIS dynamics, Cox-Copula joint defaults, SCR-NR / SCR-ER shock protocols, and portfolio-level integration (EL, VaR, ES).
5. GPU-accelerated interactive dashboard with zero-ETL integrations, scenario interface, NLG insights, and REST/GraphQL endpoints.

---

## Implementation Notes & Next Steps (technical checklist)

* Finalize master entity resolution pipeline and UUID schema.
* Choose distributed graph DB technology (scale, property support, query latency).
* Build HTML→Markdown parser templates for regulatory filings and design NER annotation schema.
* Instrument tCNN pipelines for irregular time series and validate temporal encodings on Panjiva data.
* Prototype GCN+GAT stack; integrate CuGNN contrastive pretraining and PI-GNN constraints.
* Implement DropAGG / GRANet modules and test for over-smoothing on synthetic deep-tier graphs.
* Develop SCR-NR/SCR-ER simulation harness and validate amplification multipliers on historical case studies.
* Implement GPU WebGL front-end (Cosmograph) prototype and zero-ETL query adapters.
* Define governance, explainability, and regulatory reporting requirements for model output consumption.

---

### Appendix: Notation & Acronyms

* `G = (V, E, X, W)` — property graph (nodes, edges, node features, edge weights)
* `PD` — Probability of Default
* `EL` — Expected Loss
* `VaR` — Value at Risk
* `ES` — Expected Shortfall
* `SRC` — Systemic Risk Contribution
* `SIIS` — Extended Susceptible-Infected1-Infected2-Susceptible epidemic process
* `GCN` — Graph Convolutional Network
* `GAT` — Graph Attention Network
* `CuGNN` — Contrastive Unsupervised GNN
* `PI-GNN` — Physics-Informed GNN
* `tCNN` — temporal Convolutional Neural Network
* `DropAGG` — structural aggregation dropout mechanism
* `GRANet` — Graph Random Aggregation Network

---
