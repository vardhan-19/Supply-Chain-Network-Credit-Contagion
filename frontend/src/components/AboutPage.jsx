import React from 'react';
import './AboutPage.css';

/**
 * AboutPage — Full in-app page (not a modal) rendered inside the app-shell.
 * Replaces the dashboard content when "About" is clicked in TopBar.
 *
 * Designed to give an ML / Finance interviewer a crisp, technical overview
 * of the project without overwhelming detail.
 *
 * Props:
 *   onClose  – callback to return to the dashboard
 */
function AboutPage({ onClose }) {
  return (
    <div className="about-page">

      {/* ── Page Header ── */}
      <div className="about-page__header">
        <div className="about-page__header-inner">
          <div className="about-page__logo">◈</div>
          <div>
            <h1 className="about-page__title">Supply Chain Network Credit Contagion</h1>
            <p className="about-page__tagline">
              Modelling systemic financial risk in the global automotive supply chain using Graph Neural Networks
            </p>
          </div>
          <button className="about-back-btn" onClick={onClose}>
            ← Back to Dashboard
          </button>
        </div>
      </div>

      {/* ── Page Body ── */}
      <div className="about-page__body">

        {/* ═══ ROW 1: What + Why ═══ */}
        <div className="about-row">

          <div className="about-card about-card--accent">
            <div className="about-card__eyebrow">The Problem</div>
            <h2 className="about-card__heading">What is Credit Contagion?</h2>
            <p className="about-card__text">
              When a supplier defaults, it doesn't just hurt itself — it delays payments to its own suppliers,
              starves its customers of components, and forces credit losses onto every counterparty.
              This <strong>cascade</strong> is credit contagion.
            </p>
            <p className="about-card__text">
              Traditional credit models score firms in isolation. This project models the <strong>network</strong>:
              a firm's risk is a function of both its own financials and its structural position in the supply chain graph.
            </p>
          </div>

          <div className="about-card">
            <div className="about-card__eyebrow">Scope</div>
            <h2 className="about-card__heading">Why Automotive?</h2>
            <p className="about-card__text">
              The automotive supply chain is one of the world's most complex multi-tier networks —
              a single OEM sources from thousands of Tier-1, Tier-2 and Tier-3 suppliers globally.
              A single semiconductor shortage (2021–22) cost the industry <strong>$210 billion</strong> in lost revenue.
            </p>
            <div className="about-stat-row">
              <div className="about-stat"><span className="about-stat__num">174</span><span className="about-stat__label">Firms modelled</span></div>
              <div className="about-stat"><span className="about-stat__num">3</span><span className="about-stat__label">Edge types</span></div>
              <div className="about-stat"><span className="about-stat__num">12</span><span className="about-stat__label">Node features</span></div>
              <div className="about-stat"><span className="about-stat__num">100+</span><span className="about-stat__label">Data sources</span></div>
            </div>
          </div>

        </div>

        {/* ═══ ROW 2: ML Pipeline ═══ */}
        <div className="about-section-title">
          <span className="about-section-title__pill">ML Pipeline</span>
          <div className="about-section-title__line" />
        </div>

        <div className="about-pipeline">
          {[
            {
              step: '01',
              icon: '📄',
              title: 'Data Extraction',
              points: [
                'SEC 10-K / 20-F filings (US listed)',
                'Annual reports (Toyota, BMW, Bosch …)',
                'ESG reports, earnings calls, press releases',
                'Keyword NLP + manual verification per edge',
              ],
            },
            {
              step: '02',
              icon: '🔗',
              title: 'Graph Construction',
              points: [
                'Nodes = companies (OEMs, Tier-1/2, raw material)',
                'Edge type 1: supply (goods flow)',
                'Edge type 2: trade_credit (payment terms, AR exposure)',
                'Edge type 3: ownership (equity stake, subsidiary)',
              ],
            },
            {
              step: '03',
              icon: '🧠',
              title: 'GNN Training',
              points: [
                'Architecture: Linear(12→64) → 2x GCNConv → Linear(32→2)',
                'Node features: 8 financial ratios + 4 graph centralities',
                'Zero leakage: Altman Z excluded from model training',
                'Output: Probability of Default (PD) per node',
              ],
            },
            {
              step: '04',
              icon: '⚡',
              title: 'Shock Simulation',
              points: [
                'SCR-NR (Node Default) & SCR-ER (Edge Severance)',
                'Topological shock → GNN re-predicts counterparty PDs',
                'Calculates Basel EAD & Systemic Loss Increase (Δ EL)',
                'Contagion depth & affected counterparties surfaced in UI',
              ],
            },
          ].map(({ step, icon, title, points }) => (
            <div className="about-pipeline-card" key={step}>
              <div className="about-pipeline-card__step">{step}</div>
              <div className="about-pipeline-card__icon">{icon}</div>
              <div className="about-pipeline-card__title">{title}</div>
              <ul className="about-pipeline-card__list">
                {points.map(p => <li key={p}>{p}</li>)}
              </ul>
            </div>
          ))}
        </div>

        {/* ═══ ROW 3: Finance Model + Risk ═══ */}
        <div className="about-section-title">
          <span className="about-section-title__pill">Financial Model</span>
          <div className="about-section-title__line" />
        </div>

        <div className="about-row">

          <div className="about-card">
            <div className="about-card__eyebrow">Credit Risk</div>
            <h2 className="about-card__heading">Node Features Used (12 Dimensions)</h2>
            <div className="about-feature-grid">
              {[
                { name: 'Annual Revenue', desc: 'Total annual operational turnover in USD (Basel EAD proxy base)' },
                { name: 'Total Debt', desc: 'Short-term and long-term financial debt obligations' },
                { name: 'Market Cap', desc: 'Equity market valuation reflecting investor solvency cushion' },
                { name: 'Current Ratio', desc: 'Current Assets / Current Liabilities — short-term liquidity' },
                { name: 'Debt-to-Equity', desc: 'Total Debt / Shareholder Equity — capital structure leverage' },
                { name: 'Profit Margin', desc: 'Net Income / Revenue — operational profitability' },
                { name: 'Revenue Growth', desc: 'Year-over-year percentage revenue trajectory' },
                { name: 'Return on Assets (ROA)', desc: 'EBIT / Total Assets — asset productivity ratio' },
                { name: 'PageRank', desc: 'Random-walk structural importance in the global network' },
                { name: 'Betweenness Centrality', desc: 'Bottleneck exposure and sole-source bridge proxy' },
                { name: 'Eigenvector Centrality', desc: 'Connectivity to other influential systemic hubs' },
                { name: 'Clustering Coefficient', desc: 'Local supply triangle density and structural redundancy' },
              ].map(({ name, desc }) => (
                <div className="about-feature-row" key={name}>
                  <span className="about-feature-row__name">{name}</span>
                  <span className="about-feature-row__desc">{desc}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="about-card">
            <div className="about-card__eyebrow">Risk Tiers</div>
            <h2 className="about-card__heading">Probability of Default</h2>
            <p className="about-card__text">
              The GNN outputs a PD score per node. Tiers follow Basel-inspired thresholds:
            </p>
            <div className="about-tier-list">
              <div className="about-tier about-tier--high">
                <div className="about-tier__dot" />
                <div>
                  <div className="about-tier__label">High Risk — PD ≥ 0.50</div>
                  <div className="about-tier__desc">Imminent default risk. These nodes are contagion flashpoints — simulating their failure causes the largest downstream cascade.</div>
                </div>
              </div>
              <div className="about-tier about-tier--medium">
                <div className="about-tier__dot" />
                <div>
                  <div className="about-tier__label">Medium Risk — PD 0.20–0.49</div>
                  <div className="about-tier__desc">Under financial stress. Vulnerable to a second-order shock from a High-Risk neighbour defaulting.</div>
                </div>
              </div>
              <div className="about-tier about-tier--low">
                <div className="about-tier__dot" />
                <div>
                  <div className="about-tier__label">Low Risk — PD &lt; 0.20</div>
                  <div className="about-tier__desc">Financially stable. May still be operationally impacted (supply disruption) even without credit loss.</div>
                </div>
              </div>
            </div>
          </div>

        </div>

        {/* ═══ ROW 4: Data Sources Summary ═══ */}
        <div className="about-section-title">
          <span className="about-section-title__pill">Data Sources</span>
          <div className="about-section-title__line" />
        </div>

        <div className="about-sources-grid">
          {[
            {
              badge: 'SEC 10-K',
              badgeClass: 'sec',
              title: 'US-Listed Companies',
              desc: 'Toyota, GM, Ford, Tesla, Aptiv, BorgWarner, Lear, Nucor, Alcoa, Gentex, Visteon, NXP, Flex, Amphenol, TE Connectivity, Qualcomm, NVIDIA, Goodyear, Albemarle, Noveli, Motherson and more.',
              count: '30+ filings',
            },
            {
              badge: 'SEC 20-F',
              badgeClass: 'sec',
              title: 'Foreign Private Issuers (SEC)',
              desc: 'NXP Semiconductors N.V. (FY 2025 + legacy FY 2018 for historical semiconductor supply links), Sociedad Química y Minera (SQM — lithium supply).',
              count: '3 filings',
            },
            {
              badge: 'Annual Report',
              badgeClass: 'annual',
              title: 'Non-US / Unlisted Companies',
              desc: 'BMW, Volkswagen, Stellantis, Renault, Mercedes, Porsche, Bosch, Continental, DENSO, Aisin, ZF, Magna, Panasonic, CATL, TSMC, Samsung, Geely, BASF, Valeo, Faurecia, Infineon, Renesas, STMicro, Mobileye, Mahindra, Tata, SAIC, Dongfeng, BAIC and more.',
              count: '55+ reports',
            },
            {
              badge: 'Other',
              badgeClass: 'other',
              title: 'Supplementary Disclosures',
              desc: 'ESG / Sustainability reports, Supplier Relationship Disclosures, Investor Presentations, Q1 2025 Earnings Call Supplements, Joint Venture and Strategic Partnership Press Releases.',
              count: '9 source types',
            },
          ].map(({ badge, badgeClass, title, desc, count }) => (
            <div className="about-source-card" key={title}>
              <div className="about-source-card__top">
                <span className={`about-src-badge about-src-badge--${badgeClass}`}>{badge}</span>
                <span className="about-source-card__count">{count}</span>
              </div>
              <div className="about-source-card__title">{title}</div>
              <div className="about-source-card__desc">{desc}</div>
            </div>
          ))}
        </div>

        {/* ═══ ROW 5: Academic Foundations & Citations ═══ */}
        <div className="about-section-title">
          <span className="about-section-title__pill">Academic Foundations & Citations</span>
          <div className="about-section-title__line" />
        </div>

        <div className="about-citations-grid">
          {[
            {
              badge: 'IEEE ACCESS 2025',
              badgeClass: 'ieee',
              title: 'A Novel Hybrid Model for Credit Risk Assessment of Supply Chain Finance Based on Topological Data Analysis and Graph Neural Network',
              authors: 'Kimia Fereydooni Mojdehi, Babak Amiri, and Alireza Haddadi',
              journal: 'IEEE Access, vol. 13, pp. 11094–11116 (2025)',
              framework: 'Formulation of hybrid 12-dimensional feature tensor combining corporate accounting ratios with 4 network centralities (betweenness, eigenvector, PageRank, clustering); empirical proof that topological metrics dominate distress prediction.',
              doi: '10.1109/ACCESS.2025.3528373',
              url: 'https://doi.org/10.1109/ACCESS.2025.3528373'
            },
            {
              badge: 'ACM AIDF 2025',
              badgeClass: 'acm',
              title: 'Construction of Enterprise Credit Risk Assessment Model Driven by Graph Neural Network',
              authors: 'Kuan Liu',
              journal: 'Proc. 2025 Int. Conf. on Artificial Intelligence and Digital Finance, ACM, pp. 1–6',
              framework: 'Multi-tier automotive industry relationship graph formulation (OEMs, Tier-1, Tier-2), multi-relational edges (supply flows, trade credit, equity ownership), and edge-weighted message passing.',
              doi: '10.1145/3764727.3764741',
              url: 'https://doi.org/10.1145/3764727.3764741'
            },
            {
              badge: 'PLOS ONE 2024',
              badgeClass: 'plos',
              title: 'Credit risk contagion of supply chain finance: An empirical analysis of supply chain listed companies',
              authors: 'Xinpeng Geng, Bing Han, Debao Yang, and Junren Zhao',
              journal: 'PLoS ONE, vol. 19, no. 7, p. e0306724 (2024)',
              framework: 'Dynamic credit contagion mechanics in listed supply chains, asymmetric operational vs liquidity transmission channels, and exponential temporal decay of disclosure weights.',
              doi: '10.1371/journal.pone.0306724',
              url: 'https://doi.org/10.1371/journal.pone.0306724'
            },
            {
              badge: 'BASEL III & J. FINANCE',
              badgeClass: 'basel',
              title: 'Basel III Regulatory Capital Framework & Altman Bankruptcy Discriminant Analysis',
              authors: 'Basel Committee on Banking Supervision (2017) & Edward I. Altman (1968)',
              journal: 'Bank for International Settlements (BIS) / The Journal of Finance, 23(4), 589–609',
              framework: 'Ground-truth default supervision threshold (Z ≤ 1.81), Basel III Foundation IRB expected loss metrics (EAD = 0.15 × Revenue, LGD = 0.45, EL = PD × LGD × EAD), and systemic risk contribution (ΔEL).',
              doi: '10.1111/j.1540-6261.1968.tb00843.x',
              url: 'https://doi.org/10.1111/j.1540-6261.1968.tb00843.x'
            }
          ].map(({ badge, badgeClass, title, authors, journal, framework, doi, url }) => (
            <div className="about-citation-card" key={badge}>
              <div className="about-citation-card__top">
                <span className={`about-cite-badge about-cite-badge--${badgeClass}`}>{badge}</span>
                <a className="about-citation-card__doi" href={url} target="_blank" rel="noopener noreferrer">
                  doi:{doi} ↗
                </a>
              </div>
              <h3 className="about-citation-card__title">{title}</h3>
              <div className="about-citation-card__authors">{authors}</div>
              <div className="about-citation-card__journal">{journal}</div>
              <div className="about-citation-card__framework">
                <strong>Framework Taken:</strong> {framework}
              </div>
            </div>
          ))}
        </div>

        {/* ═══ ROW 6: Tech Stack ═══ */}
        <div className="about-section-title">
          <span className="about-section-title__pill">Tech Stack</span>
          <div className="about-section-title__line" />
        </div>

        <div className="about-tech-strip">
          {[
            { layer: 'Graph ML',   items: ['PyTorch Geometric', 'GCNConv', 'NetworkX', 'scikit-learn'] },
            { layer: 'Backend',    items: ['FastAPI', 'Python 3.11', 'Uvicorn', 'Pydantic'] },
            { layer: 'Frontend',   items: ['React 18', 'D3-force', 'react-force-graph-2d', 'Vite'] },
            { layer: 'Data Layer', items: ['Pandas', 'CSV / JSON', 'SEC EDGAR API', 'NLP (spaCy)'] },
          ].map(({ layer, items }) => (
            <div className="about-tech-block" key={layer}>
              <div className="about-tech-block__layer">{layer}</div>
              <div className="about-tech-block__items">
                {items.map(i => <span className="about-tech-chip" key={i}>{i}</span>)}
              </div>
            </div>
          ))}
        </div>

        {/* ═══ Footer ═══ */}
        <div className="about-page__footer">
          <span>All data sourced from public financial disclosures · FY 2025 unless noted · No proprietary data used</span>
          <button className="about-back-btn about-back-btn--footer" onClick={onClose}>← Back to Dashboard</button>
        </div>

      </div>
    </div>
  );
}

export default AboutPage;
