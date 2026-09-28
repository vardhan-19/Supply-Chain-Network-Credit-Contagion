import React from 'react';
import Tooltip from './Tooltip';
import './TopBar.css';

/**
 * TopBar — Fixed header bar with project title, stats, graph controls, and About button.
 *
 * Props:
 *   riskCounts       – { total, edges, high, medium, low }
 *   isSimulating     – boolean, shows pulse badge when true
 *   simulationResults – non-null when sim results are present
 *   onResetLayout    – callback to reset graph layout
 *   onFitToView      – callback to zoom-to-fit graph
 *   onAbout          – callback to open the About page
 */
function TopBar({
  riskCounts = { total: 0, edges: 0, high: 0, medium: 0, low: 0 },
  isSimulating = false,
  simulationResults = null,
  onResetLayout,
  onFitToView,
  onAbout,
}) {
  return (
    <header className="topbar">

      {/* ── Left: Brand + Title ── */}
      <div className="topbar__brand">
        <div className="topbar__brand-mark">◈</div>
        <div className="topbar__title-stack">
          <span className="topbar__title">Credit Contagion Dashboard</span>
          <span className="topbar__subtitle">Supply Chain Network Risk Intelligence</span>
        </div>
      </div>

      <div className="topbar__divider" />

      {/* ── Center: Stats Badges ── */}
      <div className="topbar__stats">
        <div className="topbar__badge">
          <Tooltip
            term="Companies"
            text="Total number of firms loaded in this supply chain network graph. Each dot on the map is one company."
          >
            <span>Companies</span>
          </Tooltip>
          {' '}<span className="topbar__badge__value">{riskCounts.total}</span>
        </div>

        <div className="topbar__badge">
          <Tooltip
            term="Edges"
            text="Supply chain connections between companies — e.g. a supplier sending goods to a manufacturer. Each line on the graph is one edge."
          >
            <span>Edges</span>
          </Tooltip>
          {' '}<span className="topbar__badge__value">{riskCounts.edges}</span>
        </div>

        <div className="topbar__badge topbar__badge--high">
          <span className="topbar__badge__dot" style={{ background: '#dc2626' }} />
          <Tooltip
            term="High Risk"
            text="Companies with more than a 50% chance of defaulting on (failing to repay) their debts. These are the most financially dangerous firms in the network."
          >
            <span>High Risk</span>
          </Tooltip>
          {' '}<span className="topbar__badge__value">{riskCounts.high}</span>
        </div>

        <div className="topbar__badge topbar__badge--medium">
          <span className="topbar__badge__dot" style={{ background: '#d97706' }} />
          <Tooltip
            term="Medium Risk"
            text="Companies with a 20–50% chance of defaulting. They are under financial stress but not yet in imminent danger."
          >
            <span>Medium</span>
          </Tooltip>
          {' '}<span className="topbar__badge__value">{riskCounts.medium}</span>
        </div>

        <div className="topbar__badge topbar__badge--low">
          <span className="topbar__badge__dot" style={{ background: '#059669' }} />
          <Tooltip
            term="Low Risk"
            text="Companies with less than a 20% chance of defaulting. These firms are financially stable and unlikely to cause problems in the network."
          >
            <span>Low Risk</span>
          </Tooltip>
          {' '}<span className="topbar__badge__value">{riskCounts.low}</span>
        </div>

        {/* Simulation-active pulse badge */}
        {(isSimulating || simulationResults) && (
          <div className="topbar__sim-badge">
            <span className="topbar__sim-dot" />
            {isSimulating ? 'Simulating…' : 'Simulation Active'}
          </div>
        )}
      </div>

      {/* ── Right: Graph Controls + About ── */}
      <div className="topbar__controls">
        <button
          className="topbar__btn"
          onClick={onResetLayout}
          title="Reset all pinned nodes and reheat the force simulation (R)"
        >
          ↻ Reset Layout
        </button>
        <button
          className="topbar__btn"
          onClick={onFitToView}
          title="Zoom to fit all nodes into view (F)"
        >
          ⊞ Fit to View
        </button>

        {/* About button — opens the full project about page */}
        <button
          className="topbar__btn topbar__btn--about"
          onClick={onAbout}
          title="Learn about this project, its methodology, and data sources"
        >
          ℹ About
        </button>
      </div>

    </header>
  );
}

export default TopBar;
