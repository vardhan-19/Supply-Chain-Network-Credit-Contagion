import React, { useState, useMemo, useCallback, memo } from 'react';
import Tooltip from './Tooltip';
import './RiskRankings.css';

// ── Simple debounce hook ──
function useDebounce(value, delay = 200) {
  const [debouncedValue, setDebouncedValue] = useState(value);
  React.useEffect(() => {
    const id = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(id);
  }, [value, delay]);
  return debouncedValue;
}

/**
 * RiskRankings — Left sidebar panel showing all companies ranked by PD.
 *
 * Props:
 *   nodes           – array of graph nodes (with pd, risk_tier, name, revenue)
 *   selectedCompany – currently selected node, or null
 *   onSelectCompany – callback(node) when a company row is clicked
 */
const RiskRankings = memo(function RiskRankings({ nodes = [], selectedCompany = null, onSelectCompany }) {
  const [searchQuery, setSearchQuery] = useState('');
  const debouncedQuery = useDebounce(searchQuery, 200);

  // ── Sort by PD descending, then filter by debounced search ──
  const sortedNodes = useMemo(() => {
    const sorted = [...nodes].sort((a, b) => (b.pd ?? 0) - (a.pd ?? 0));
    if (!debouncedQuery.trim()) return sorted;
    const q = debouncedQuery.trim().toLowerCase();
    return sorted.filter(n => (n.name || '').toLowerCase().includes(q));
  }, [nodes, debouncedQuery]);

  // ── Risk counts (memoized independently) ──
  const counts = useMemo(() => {
    let high = 0, medium = 0, low = 0;
    nodes.forEach(n => {
      const tier = getRiskTier(n);
      if (tier === 'High') high++;
      else if (tier === 'Medium') medium++;
      else low++;
    });
    return { total: nodes.length, high, medium, low };
  }, [nodes]);

  const handleSearchChange = useCallback((e) => {
    setSearchQuery(e.target.value);
  }, []);

  return (
    <>
      {/* ── Summary stats ── */}
      <div className="risk-summary">
        <div className="risk-summary__card">
          <span className="risk-summary__value" style={{ color: 'var(--text-primary)' }}>
            {counts.total}
          </span>
          <span className="risk-summary__label">Total</span>
        </div>
        <div className="risk-summary__card">
          <span className="risk-summary__value" style={{ color: '#FF6B6B' }}>{counts.high}</span>
          <Tooltip
            term="High Risk"
            text="Companies with >50% probability of defaulting on their debt. The AI model flags these as financially distressed."
          >
            <span className="risk-summary__label">High</span>
          </Tooltip>
        </div>
        <div className="risk-summary__card">
          <span className="risk-summary__value" style={{ color: '#FFB300' }}>{counts.medium}</span>
          <Tooltip
            term="Medium Risk"
            text="Companies with 20–50% probability of default. Elevated credit risk — worth monitoring closely."
          >
            <span className="risk-summary__label">Medium</span>
          </Tooltip>
        </div>
        <div className="risk-summary__card">
          <span className="risk-summary__value" style={{ color: '#00E676' }}>{counts.low}</span>
          <Tooltip
            term="Low Risk"
            text="Companies with <20% probability of default. Financially stable — unlikely to cause chain reactions."
          >
            <span className="risk-summary__label">Low</span>
          </Tooltip>
        </div>
      </div>


      {/* ── Search ── */}
      <div className="risk-search">
        <div className="risk-search__wrapper">
          <span className="risk-search__icon">🔍</span>
          <input
            type="text"
            className="risk-search__input"
            placeholder="Search Companies..."
            value={searchQuery}
            onChange={handleSearchChange}
          />
        </div>
      </div>

      {/* ── Company list ── */}
      {/* Column header — all definitions live here, once */}
      <div className="risk-list__header">
        <span className="risk-list__header-rank">#</span>
        <div className="risk-list__header-info">
          <span className="risk-list__header-company">Company</span>
          <div className="risk-list__header-meta">
            <Tooltip
              term="Revenue"
              text="Total annual income from sales. Larger = bigger company. '—' means data unavailable."
            >
              <span className="risk-list__header-revenue">Revenue ⓘ</span>
            </Tooltip>
            <Tooltip
              term="Risk Tier"
              text="High (>50% PD): financially distressed. Medium (20–50% PD): elevated risk. Low (<20% PD): financially stable."
            >
              <span className="risk-list__header-risk">Risk ⓘ</span>
            </Tooltip>
          </div>
        </div>
        <Tooltip
          term="Probability of Default (PD)"
          text="The AI model's estimate of how likely a company is to fail to repay its debts. 0% = completely safe, 100% = certain default."
        >
          <span className="risk-list__header-pd">PD ⓘ</span>
        </Tooltip>
      </div>

      {sortedNodes.length === 0 ? (
        <div className="risk-empty">
          <div className="risk-empty__icon">🔎</div>
          <div className="risk-empty__text">
            No companies match<br />"{debouncedQuery}"
          </div>
        </div>
      ) : (
        <ul className="risk-list">
          {sortedNodes.map((node, idx) => {
            const tier = getRiskTier(node);
            const isSelected = selectedCompany && node.id === selectedCompany.id;
            const pd = (node.pd ?? 0) * 100;

            return (
              <li
                key={node.id}
                className={`risk-list__item ${isSelected ? 'risk-list__item--selected' : ''}`}
                onClick={() => onSelectCompany && onSelectCompany(node)}
              >
                <span className="risk-list__rank">{idx + 1}</span>
                <div className="risk-list__info">
                  <span className="risk-list__name" title={node.name}>
                    {node.name || 'Unknown'}
                  </span>
                  <div className="risk-list__meta">
                    <span>{formatRevenue(node.revenue)}</span>
                    <span className={`risk-badge risk-badge--${tier.toLowerCase()}`}>
                      {tier}
                    </span>
                  </div>
                </div>
                <span
                  className="risk-list__pd"
                  style={{ color: tier === 'High' ? '#FF6B6B' : tier === 'Medium' ? '#FFB300' : '#00E676' }}
                >
                  {pd.toFixed(1)}%
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </>
  );
});

// ═══════════════ Helpers ═══════════════

function getRiskTier(node) {
  if (node.risk_tier) return node.risk_tier;
  const pd = node.pd ?? 0;
  if (pd >= 0.5) return 'High';
  if (pd >= 0.2) return 'Medium';
  return 'Low';
}

function formatRevenue(rev) {
  if (rev == null || isNaN(rev) || rev === 0) return '—';
  const abs = Math.abs(rev);
  if (abs >= 1e12) return `$${(rev / 1e12).toFixed(1)}T`;
  if (abs >= 1e9)  return `$${(rev / 1e9).toFixed(1)}B`;
  if (abs >= 1e6)  return `$${(rev / 1e6).toFixed(0)}M`;
  if (abs >= 1e3)  return `$${(rev / 1e3).toFixed(0)}K`;
  return `$${rev.toFixed(0)}`;
}

export default RiskRankings;
