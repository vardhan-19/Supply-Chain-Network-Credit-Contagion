import React, { memo } from 'react';
import Tooltip from './Tooltip';
import './SimulationResults.css';

/**
 * SimulationResults — Right slide-in panel content.
 * Shows all the cascade implications after a simulation runs.
 *
 * Props:
 *   results   – simulation result object from API
 *   nodes     – full nodes array (to resolve names)
 *   onClear   – callback to clear simulation & close panel
 */
const SimulationResults = memo(function SimulationResults({ results, nodes = [], onClear }) {
  if (!results) return null;

  const { shocked_company, total_systemic_loss_increase, affected_nodes = [] } = results;
  const sortedAffected = [...affected_nodes].sort((a, b) => b.delta_pd - a.delta_pd);

  const shockedNode = nodes.find(n => n.id === shocked_company);
  const shockedName = shockedNode?.name || 'Unknown';

  return (
    <div className="sr-content">

      {/* ── Header ── */}
      <div className="sr-header">
        <div className="sr-header__title">
          <span className="sr-header__icon">⚡</span>
          Systemic Impact Analysis
        </div>
        <button className="sr-header__clear" onClick={onClear} title="Clear simulation results">
          ✕ Clear
        </button>
      </div>

      {/* ── Shocked company card ── */}
      <div className="sr-origin-card">
        <div className="sr-origin-card__label">
          {results.shock_type === 'edge_removal' ? 'Target Company (Edge To)' : 'Shocked Company'}
        </div>
        <div className="sr-origin-card__name">{shockedName}</div>
        <div className="sr-origin-card__id">{shocked_company}</div>
      </div>

      {/* ── Edge removal: show source company ── */}
      {results.source_company && (() => {
        const sourceNode = nodes.find(n => n.id === results.source_company);
        const sourceName = sourceNode?.name || 'Unknown';
        return (
          <div className="sr-origin-card" style={{ marginTop: '8px', borderLeft: '3px solid #FFB300' }}>
            <div className="sr-origin-card__label">Source Company (Edge From)</div>
            <div className="sr-origin-card__name">{sourceName}</div>
            <div className="sr-origin-card__id" style={{ color: '#FFB300' }}>
              {sourceName} → {shockedName}
            </div>
          </div>
        );
      })()}

      {/* ── Total systemic loss ── */}
      <div className="sr-loss-card">
        <Tooltip
          term="Total Systemic Loss Increase"
          text="The extra financial loss that spreads across the entire supply chain network as a direct result of this one company defaulting. Think of it as the 'damage bill' to the whole system."
        >
          <div className="sr-loss-card__label">Total Systemic Loss Increase</div>
        </Tooltip>
        <div className="sr-loss-card__value">{formatCurrency(total_systemic_loss_increase)}</div>
      </div>

      {/* ── Affected companies ── */}
      {sortedAffected.length > 0 ? (
        <div className="sr-affected-section">
          <Tooltip
            term="Affected Downstream Companies"
            text="Companies that suffer financial damage if the shocked firm defaults. 'Downstream' means they receive goods or services from the defaulted company."
          >
            <div className="sr-affected-label">
              Affected Downstream Companies
              <span className="sr-affected-count">{sortedAffected.length}</span>
            </div>
          </Tooltip>

          {/* Table header */}
          <div className="sr-table">
            <div className="sr-table__head">
              <span>Company</span>
              <Tooltip term="Before" text="Probability of Default BEFORE the shock event.">
                <span>Before</span>
              </Tooltip>
              <Tooltip term="After" text="Probability of Default AFTER the shock — higher = more damaged.">
                <span>After</span>
              </Tooltip>
              <Tooltip term="Δ PD" text="Change in Probability of Default — how much more likely to fail after the shock.">
                <span>Δ PD</span>
              </Tooltip>
              <Tooltip term="EL ↑" text="Expected Loss increase — extra dollar amount this company is now expected to lose.">
                <span>EL ↑</span>
              </Tooltip>
            </div>

            {sortedAffected.map(a => {
              const node   = nodes.find(n => n.id === a.company_id);
              const name   = node?.name || a.company_id.split('-')[0];
              const before = (a.before_pd * 100).toFixed(1);
              const after  = (a.after_pd  * 100).toFixed(1);
              const delta  = (a.delta_pd  * 100).toFixed(1);
              const el     = formatCurrency(a.el_increase);

              const severity =
                a.delta_pd >= 0.10 ? 'high' :
                a.delta_pd >= 0.02 ? 'medium' : 'low';

              return (
                <div key={a.company_id} className="sr-table__row">
                  <span className="sr-table__name" title={name}>{name}</span>
                  <span className="sr-table__val">{before}%</span>
                  <span className="sr-table__val">{after}%</span>
                  <span className={`sr-table__delta sr-table__delta--${severity}`}>+{delta}%</span>
                  <span className={`sr-table__delta sr-table__delta--${severity}`}>{el}</span>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="sr-empty">
          <div className="sr-empty__icon">🛡️</div>
          <div className="sr-empty__text">
            No significant downstream defaults triggered by this shock.
          </div>
        </div>
      )}
    </div>
  );
});

// ═══ Helpers ═══

function formatCurrency(val) {
  if (val == null || isNaN(val)) return '$0';
  if (val === 0) return '$0';
  const abs  = Math.abs(val);
  const sign = val < 0 ? '-' : '';
  if (abs >= 1e12) return `${sign}$${(abs / 1e12).toFixed(2)}T`;
  if (abs >= 1e9)  return `${sign}$${(abs / 1e9).toFixed(2)}B`;
  if (abs >= 1e6)  return `${sign}$${(abs / 1e6).toFixed(2)}M`;
  if (abs >= 1e3)  return `${sign}$${(abs / 1e3).toFixed(0)}K`;
  return `${sign}$${abs.toFixed(0)}`;
}

export default SimulationResults;
