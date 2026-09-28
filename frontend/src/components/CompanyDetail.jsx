import React, { useMemo } from 'react';
import Tooltip from './Tooltip';
import './CompanyDetail.css';

/**
 * CompanyDetail — Pure content component showing all company metrics.
 * No backdrop, no bottom-sheet. Renders as a plain scrollable div
 * to be hosted inside any panel.
 *
 * Props:
 *   company    – selected node object
 *   links      – full links array
 *   nodes      – full nodes array
 *   onSimulate – callback(companyId, shockType)
 */
function CompanyDetail({ company, links, nodes, onSimulate }) {
  if (!company) return null;

  // ═══ Derived: ALL first-degree relationships, grouped by type ═══
  const { inbound, outbound } = useMemo(() => {
    // inbound[relType] = [{ node, link }]  — things feeding into this company
    // outbound[relType] = [{ node, link }] — things this company feeds into
    const inMap  = {};
    const outMap = {};

    links.forEach(link => {
      const srcId   = typeof link.source === 'object' ? link.source.id : link.source;
      const tgtId   = typeof link.target === 'object' ? link.target.id : link.target;
      const relType = link.relationship_type || 'unknown';

      if (tgtId === company.id) {
        // This company receives from srcId
        const node = nodes.find(n => n.id === srcId);
        if (node) {
          if (!inMap[relType]) inMap[relType] = [];
          inMap[relType].push({ node, link });
        }
      }
      if (srcId === company.id) {
        // This company sends to tgtId
        const node = nodes.find(n => n.id === tgtId);
        if (node) {
          if (!outMap[relType]) outMap[relType] = [];
          outMap[relType].push({ node, link });
        }
      }
    });
    return { inbound: inMap, outbound: outMap };
  }, [company.id, links, nodes]);

  // Totals for display
  const totalIn  = Object.values(inbound).reduce((s, arr) => s + arr.length, 0);
  const totalOut = Object.values(outbound).reduce((s, arr) => s + arr.length, 0);


  const pd      = company.pd ?? 0;
  const tier    = pd >= 0.5 ? 'High' : pd >= 0.2 ? 'Medium' : 'Low';
  const pdColor = tier === 'High' ? '#dc2626' : tier === 'Medium' ? '#d97706' : '#059669';

  const rawConf = company.data_confidence;
  const confText = rawConf && typeof rawConf === 'string'
    ? rawConf.charAt(0).toUpperCase() + rawConf.slice(1)
    : null;

  const confPct = useMemo(() => {
    if (!rawConf) return null;
    if (typeof rawConf === 'string') {
      const lower = rawConf.toLowerCase();
      if (lower === 'high') return 95;
      if (lower === 'medium') return 70;
      if (lower === 'low') return 40;
      const num = parseFloat(rawConf);
      return !isNaN(num) ? (num <= 1 ? num * 100 : num) : null;
    }
    if (typeof rawConf === 'number') {
      return rawConf <= 1 ? rawConf * 100 : rawConf;
    }
    return null;
  }, [rawConf]);

  return (
    <div className="cd-content">

      {/* ── Company Header ── */}
      <div className="cd-header-inline">
        <div className="cd-header-inline__top">
          {company.ticker && <span className="cd-header__ticker">{company.ticker}</span>}
          <Tooltip
            term={`${tier} Risk`}
            text={
              tier === 'High'
                ? 'High Risk: >50% probability of defaulting on its debts.'
                : tier === 'Medium'
                ? 'Medium Risk: 20–50% chance of default. Under financial stress.'
                : 'Low Risk: <20% chance of default. Financially stable.'
            }
          >
            <span className={`cd-badge cd-badge--${tier.toLowerCase()}`}>{tier} Risk</span>
          </Tooltip>
          {confText && (
            <Tooltip
              term="Data Confidence"
              text={`Data Confidence: ${confText}. Indicates whether balance sheet figures are directly SEC/audited verified (High), annual report derived (Medium), or sector imputed (Low).`}
            >
              <span className="cd-header__ticker" style={{ color: '#4b5563' }}>
                {confText} Conf.
              </span>
            </Tooltip>
          )}
          {company.is_subsidiary && (
            <Tooltip term="Subsidiary" text="Owned by a larger parent company. Its financial health may be tied to the parent.">
              <span className="cd-subsidiary-tag">SUBSIDIARY</span>
            </Tooltip>
          )}
        </div>
        <div className="cd-header-inline__name" title={company.name}>
          {company.name || 'Unknown Company'}
        </div>
        <Tooltip term="PD — Probability of Default" text="The AI model's estimate of how likely this company is to fail to repay its debts. 0% = safe, 100% = certain default.">
          <span className="cd-header-inline__pd" style={{ color: pdColor }}>
            PD: {(pd * 100).toFixed(1)}%
          </span>
        </Tooltip>
      </div>

      {/* ══ SECTION 1: Core Financials ══ */}
      <div className="cd-section-label">Financial Performance</div>
      <div className="cd-metrics-grid">
        <MetricCard label="Revenue" value={formatCurrency(company.revenue)}
          tone={company.revenue > 0 ? 'good' : company.revenue != null ? 'bad' : 'neutral'}
          tooltip="Total annual income from sales. Larger = bigger company." />
        <MetricCard label="Total Debt" value={formatCurrency(company.total_debt)}
          tone={company.total_debt == null ? 'neutral' : company.revenue && company.total_debt > company.revenue ? 'bad' : 'neutral'}
          tooltip="All money the company owes to banks and bondholders. High debt vs revenue is a warning sign." />
        <MetricCard label="Market Cap" value={formatCurrency(company.market_cap)}
          tone={company.market_cap > 0 ? 'good' : company.market_cap != null ? 'bad' : 'neutral'}
          tooltip="Total stock market value = share price × shares outstanding. A measure of company size." />
        <MetricCard label="Profit Margin" value={formatPercent(company.profit_margin)}
          tone={company.profit_margin == null ? 'neutral' : company.profit_margin > 0.1 ? 'good' : company.profit_margin > 0 ? 'neutral' : 'bad'}
          tooltip="% of revenue kept as profit after all costs. 15% means $0.15 kept per $1 earned. Negative = losing money." />
        <MetricCard label="Revenue Growth" value={formatPercent(company.revenue_growth)}
          tone={company.revenue_growth == null ? 'neutral' : company.revenue_growth > 0.05 ? 'good' : company.revenue_growth >= 0 ? 'neutral' : 'bad'}
          tooltip="How fast revenue grew vs last year. Positive = expanding. Negative = shrinking business." />
        <MetricCard label="Return on Assets" value={formatPercent(company.roa)}
          tone={company.roa == null ? 'neutral' : company.roa > 0.05 ? 'good' : company.roa >= 0 ? 'neutral' : 'bad'}
          tooltip="ROA: how efficiently the company converts assets into profit. Above 5% is healthy." />
        <MetricCard label="Current Ratio"
          value={company.current_ratio != null ? company.current_ratio.toFixed(2) : '—'}
          tone={company.current_ratio == null ? 'neutral' : company.current_ratio >= 1.5 ? 'good' : company.current_ratio >= 1.0 ? 'neutral' : 'bad'}
          tooltip="Short-term assets ÷ short-term debts. Above 1.5 = comfortable. Below 1.0 = can't pay near-term bills." />
        <MetricCard label="Debt / Equity"
          value={company.debt_to_equity != null ? company.debt_to_equity.toFixed(2) : '—'}
          tone={company.debt_to_equity == null ? 'neutral' : company.debt_to_equity < 1 ? 'good' : company.debt_to_equity < 2 ? 'neutral' : 'bad'}
          tooltip="Debt-to-Equity: borrowed money vs owner investment. Above 2.0 = heavily leveraged (risky)." />
      </div>

      {/* ══ SECTION 2: Solvency ══ */}
      <div className="cd-section-label">Solvency &amp; Credit</div>
      <div className="cd-metrics-grid--3col">
        <MetricCard label="Interest Coverage"
          value={company.interest_coverage != null ? company.interest_coverage.toFixed(1) + '×' : '—'}
          tone={company.interest_coverage == null ? 'neutral' : company.interest_coverage >= 3 ? 'good' : company.interest_coverage >= 1.5 ? 'neutral' : 'bad'}
          tooltip="Operating profit ÷ interest payments. Below 1.5× means the company can barely pay its debt interest." />
        <MetricCard label="GNN Credit Status"
          value={company.default_label === 1 ? '⚠ Distressed' : '✓ Healthy'}
          tone={company.default_label === 1 ? 'bad' : 'good'}
          tooltip="Machine-learning model prediction based on historical Altman Z-Score data. Distressed = near-bankrupt classification." />
        <MetricCard label="Probability of Default"
          value={`${(pd * 100).toFixed(2)}%`}
          tone={tier === 'High' ? 'bad' : tier === 'Medium' ? 'neutral' : 'good'}
          tooltip="GNN AI model estimate of default likelihood. Considers both the company's financials AND its position in the supply chain network." />
      </div>

      {/* Data confidence */}
      {confPct != null && (
        <div className="cd-confidence-wrap">
          <Tooltip term="Data Confidence" text="Quality score of available financial data (0–100%). Low = some figures estimated or missing, making predictions less certain.">
            <div className="cd-confidence-label">Data Confidence</div>
          </Tooltip>
          <div className="cd-confidence-bar">
            <div className="cd-confidence-bar__track">
              <div className="cd-confidence-bar__fill" style={{ width: `${confPct.toFixed(0)}%` }} />
            </div>
            <span className="cd-confidence-bar__label">{confPct.toFixed(0)}%</span>
          </div>
        </div>
      )}

      {/* ══ SECTION 3: Network Risk ══ */}
      <div className="cd-section-label">Network Risk Profile</div>
      <div className="cd-metrics-grid">
        <MetricCard label="Betweenness"
          value={company.betweenness != null ? `${(company.betweenness * 100).toFixed(2)}%` : '—'}
          tone="neutral"
          tooltip="How often this company sits on the shortest path between two others. High = a critical supply chain bottleneck." />
        <MetricCard label="PageRank"
          value={company.pagerank != null ? company.pagerank.toFixed(4) : '—'}
          tone="neutral"
          tooltip="Influence score. High = connected to other influential firms = more systemic risk." />
        <MetricCard label="In-Degree"
          value={company.in_degree != null ? company.in_degree : '—'}
          tone="neutral"
          tooltip="Number of direct suppliers feeding this company." />
        <MetricCard label="Out-Degree"
          value={company.out_degree != null ? company.out_degree : '—'}
          tone="neutral"
          tooltip="Number of direct customers buying from this company." />
        <MetricCard label="Eigenvector Centrality"
          value={company.eigenvector_centrality != null ? company.eigenvector_centrality.toFixed(4) : '—'}
          tone="neutral"
          tooltip="Connected to other highly-connected firms? High = risk amplifier at the heart of the network." />
        <MetricCard label="Clustering Coeff."
          value={company.clustering_coefficient != null ? company.clustering_coefficient.toFixed(3) : '—'}
          tone="neutral"
          tooltip="How tightly knit are this company's neighbours? High = contagion spreads rapidly within the local cluster." />
      </div>

      {/* ══ SECTION 4: All First-Degree Relationships ══ */}
      <div className="cd-section-label">First-Degree Relationships</div>

      {/* ── Inbound (things flowing IN to this company) ── */}
      <div className="cd-conn-header">
        <Tooltip term="Inbound Relationships"
          text="Other companies that supply to, own, or extend credit to this firm. Risk flows INTO this company from these sources.">
          <span className="cd-conn-direction cd-conn-direction--in">⬅ Inbound ({totalIn})</span>
        </Tooltip>
      </div>

      {totalIn === 0 ? (
        <div className="cd-conn-empty-full">No inbound relationships in dataset</div>
      ) : (
        Object.entries(inbound).map(([relType, items]) => (
          <RelGroup
            key={`in-${relType}`}
            relType={relType}
            items={items}
            direction="in"
          />
        ))
      )}

      {/* ── Outbound (things flowing OUT from this company) ── */}
      <div className="cd-conn-header" style={{ marginTop: 10 }}>
        <Tooltip term="Outbound Relationships"
          text="Companies this firm supplies to, owns, or extends credit to. If this firm fails, disruption flows OUT to these companies.">
          <span className="cd-conn-direction cd-conn-direction--out">Outbound ➡ ({totalOut})</span>
        </Tooltip>
      </div>

      {totalOut === 0 ? (
        <div className="cd-conn-empty-full">No outbound relationships in dataset</div>
      ) : (
        Object.entries(outbound).map(([relType, items]) => (
          <RelGroup
            key={`out-${relType}`}
            relType={relType}
            items={items}
            direction="out"
          />
        ))
      )}
    </div>
  );
}

// ═══ Sub-components ═══

function MetricCard({ label, value, tone = 'neutral', tooltip }) {
  return (
    <div className={`cd-metric-card cd-metric-card--${tone}`}>
      <Tooltip text={tooltip} delay={2000}>
        <span className="cd-metric__label">{label}</span>
      </Tooltip>
      <span className={`cd-metric__value cd-metric__value--${tone}`}>{value ?? '—'}</span>
    </div>
  );
}

// ─── RelGroup: shows one relationship type block with all its members ───
const REL_COLORS = {
  supply:                       '#00C8FF',
  tier1_supplier:               '#FFD500',
  tier2_supplier_battery:       '#FF7A00',
  tier2_supplier_semiconductor: '#39FF14',
  raw_material_supplier:        '#4C6FFF',
  trade_credit:                 '#B388FF',
  ownership:                    '#FF4FD8',
  unknown:                      '#9CA3AF',
};

const REL_FULL = {
  supply:                       'Supply',
  tier1_supplier:               'Tier-1 Supplier',
  tier2_supplier_battery:       'Tier-2 Battery',
  tier2_supplier_semiconductor: 'Tier-2 Semiconductor',
  raw_material_supplier:        'Raw Material Supplier',
  trade_credit:                 'Trade Credit',
  ownership:                    'Ownership',
  unknown:                      'Unknown',
};

function RelGroup({ relType, items, direction }) {
  const color = REL_COLORS[relType] || REL_COLORS.unknown;
  const label = REL_FULL[relType] || relType;
  return (
    <div className="cd-rel-group">
      <div className="cd-rel-group__header">
        <span className="cd-rel-group__dot" style={{ background: color }} />
        <Tooltip term={label} text={REL_DESCRIPTIONS[relType] || 'Supply chain relationship type.'}>
          <span className="cd-rel-group__label">{label}</span>
        </Tooltip>
        <span className="cd-rel-group__count">{items.length}</span>
      </div>
      <ul className="cd-conn-list">
        {items.map(({ node }) => (
          <ConnItem key={node.id} node={node} relType={relType} />
        ))}
      </ul>
    </div>
  );
}

function ConnItem({ node, relType }) {
  const pd      = node.pd ?? 0;
  const pdColor = pd >= 0.5 ? '#dc2626' : pd >= 0.2 ? '#d97706' : '#059669';
  return (
    <li className="cd-conn-item">
      <span className="cd-conn-item__name" title={node.name}>{node.name}</span>
      <div className="cd-conn-item__meta">
        <Tooltip term="PD" text="Probability of Default for this connected company.">
          <span className="cd-conn-item__pd" style={{ color: pdColor }}>{(pd * 100).toFixed(0)}%</span>
        </Tooltip>
      </div>
    </li>
  );
}


// ═══ Helpers ═══

const REL_SHORT = {
  supply: 'Supply', tier1_supplier: 'Tier-1',
  tier2_supplier_battery: 'Tier-2 Bat.', tier2_supplier_semiconductor: 'Tier-2 Semi.',
  ownership: 'Ownership', trade_credit: 'Trade Credit',
  raw_material_supplier: 'Raw Matl.', unknown: '?',
};

const REL_DESCRIPTIONS = {
  supply: 'General supply relationship — provides goods or services.',
  tier1_supplier: 'Tier-1: directly supplies the main manufacturer.',
  tier2_supplier_battery: 'Tier-2 Battery: supplies battery components to a Tier-1 supplier.',
  tier2_supplier_semiconductor: 'Tier-2 Semiconductor: supplies chips to a Tier-1 supplier.',
  ownership: 'Ownership: one company owns or controls the other.',
  trade_credit: 'Trade Credit: buyer receives goods now, pays later.',
  raw_material_supplier: 'Raw Material: provides unprocessed inputs at the base of the chain.',
  unknown: 'Relationship type not classified in this dataset.',
};

function formatCurrency(val) {
  if (val == null || isNaN(val)) return '—';
  if (val === 0) return '$0';
  const abs = Math.abs(val), sign = val < 0 ? '-$' : '$';
  if (abs >= 1e12) return `${sign}${(abs / 1e12).toFixed(2)}T`;
  if (abs >= 1e9)  return `${sign}${(abs / 1e9).toFixed(2)}B`;
  if (abs >= 1e6)  return `${sign}${(abs / 1e6).toFixed(0)}M`;
  return `${sign}${abs.toFixed(0)}`;
}

function formatPercent(val) {
  if (val == null || isNaN(val)) return '—';
  const pct = val * 100;
  return `${pct >= 0 ? '+' : ''}${pct.toFixed(1)}%`;
}

export default CompanyDetail;
