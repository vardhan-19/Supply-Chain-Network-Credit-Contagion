import React, { useState, useMemo, useEffect, useRef, memo } from 'react';
import Tooltip from './Tooltip';
import './ShockSimulator.css';

/**
 * ShockSimulator — Right sidebar panel for triggering contagion simulations.
 *
 * Props:
 *   nodes             – array of graph nodes
 *   links             – array of graph edges (for edge removal source filtering)
 *   onSimulate        – callback(companyId, shockType, sourceCompanyId)
 *   simulationResults – results object from the API, or null
 *   isSimulating      – boolean loading state
 *   selectedCompany   – currently selected node in the dashboard
 *   onClear           – callback to clear simulation results
 */
const ShockSimulator = memo(function ShockSimulator({
  nodes = [],
  links = [],
  onSimulate,
  simulationResults,
  isSimulating,
  selectedCompany,
  onClear
}) {
  const [targetId, setTargetId] = useState('');
  const [shockType, setShockType] = useState('node_removal');
  
  // Custom dropdown state — target company
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const dropdownRef = useRef(null);

  // Source company state — for edge removal
  const [sourceId, setSourceId] = useState('');
  const [isSourceDropdownOpen, setIsSourceDropdownOpen] = useState(false);
  const [sourceSearchQuery, setSourceSearchQuery] = useState('');
  const sourceDropdownRef = useRef(null);

  // Sync with global selected company if it changes and we aren't simulating
  useEffect(() => {
    if (selectedCompany && !simulationResults) {
      setTargetId(selectedCompany.id);
    }
  }, [selectedCompany, simulationResults]);

  // Click outside to close dropdowns
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDropdownOpen(false);
      }
      if (sourceDropdownRef.current && !sourceDropdownRef.current.contains(event.target)) {
        setIsSourceDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Filter nodes for dropdown
  const filteredNodes = useMemo(() => {
    const sorted = [...nodes].sort((a, b) => (a.name || '').localeCompare(b.name || ''));
    if (!searchQuery.trim()) return sorted;
    const q = searchQuery.toLowerCase();
    return sorted.filter(n => (n.name || '').toLowerCase().includes(q));
  }, [nodes, searchQuery]);

  const targetNode = useMemo(() => nodes.find(n => n.id === targetId), [nodes, targetId]);

  // Source company options — only companies with a direct edge TO the target
  const sourceOptions = useMemo(() => {
    if (!targetId || shockType !== 'edge_removal') return [];
    const sourceIds = new Set(
      links
        .filter(link => {
          const linkTarget = typeof link.target === 'object' ? link.target.id : link.target;
          return linkTarget === targetId;
        })
        .map(link => typeof link.source === 'object' ? link.source.id : link.source)
    );
    return nodes
      .filter(n => sourceIds.has(n.id))
      .sort((a, b) => (a.name || '').localeCompare(b.name || ''));
  }, [targetId, shockType, links, nodes]);

  const filteredSourceOptions = useMemo(() => {
    if (!sourceSearchQuery.trim()) return sourceOptions;
    const q = sourceSearchQuery.toLowerCase();
    return sourceOptions.filter(n => (n.name || '').toLowerCase().includes(q));
  }, [sourceOptions, sourceSearchQuery]);

  const sourceNode = useMemo(() => nodes.find(n => n.id === sourceId), [nodes, sourceId]);

  // Reset sourceId when target or shock type changes
  useEffect(() => {
    setSourceId('');
    setSourceSearchQuery('');
  }, [targetId, shockType]);

  const handleSimulateClick = () => {
    if (targetId && onSimulate) {
      onSimulate(targetId, shockType, shockType === 'edge_removal' ? sourceId : null);
    }
  };

  // ═══════════════ Render: Results State ═══════════════
  if (simulationResults) {
    const { shocked_company, total_systemic_loss_increase, affected_nodes } = simulationResults;
    const sortedAffected = [...(affected_nodes || [])].sort((a, b) => b.delta_pd - a.delta_pd);
    
    // shocked_company from API is a UUID string
    const shockedNode = nodes.find(n => n.id === shocked_company);
    const shockedName = shockedNode?.name || 'Unknown';

    return (
      <div className="sim-results">
        <div className="sim-results__header">
          <span className="sim-results__title">Systemic Impact Analysis</span>
          <button className="sim-results__clear" onClick={onClear}>Clear Results</button>
        </div>

        <div className="sim-loss-card">
          <Tooltip
            term="Total Systemic Loss Increase"
            text="The extra financial loss that spreads across the entire supply chain network as a direct result of this one company defaulting. Think of it as the 'damage bill' to the whole system."
          >
            <div className="sim-loss-card__label">Total Systemic Loss Increase</div>
          </Tooltip>
          <div className="sim-loss-card__value">
            {formatCurrency(total_systemic_loss_increase)}
          </div>
          <div className="sim-loss-card__company">
            Origin: <strong>{shockedName}</strong>
            <div style={{ fontSize: '9px', color: 'var(--text-dim)', marginTop: '3px', fontFamily: 'monospace', wordBreak: 'break-all' }}>
              {shocked_company}
            </div>
          </div>
          {simulationResults.source_company && (
            <div className="sim-loss-card__company" style={{ marginTop: '8px', borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '8px' }}>
              Edge From: <strong>{nodes.find(n => n.id === simulationResults.source_company)?.name || 'Unknown'}</strong>
              <div style={{ fontSize: '9px', color: 'var(--text-dim)', marginTop: '3px' }}>
                → {shockedName}
              </div>
            </div>
          )}
        </div>

        {sortedAffected.length > 0 ? (
          <>
            <Tooltip
              term="Affected Downstream Companies"
              text="Companies that would suffer financial damage if the shocked firm defaults. 'Downstream' means they receive goods or services from the defaulted company — their supply chain is disrupted."
            >
              <div className="sim-affected-label">Affected Downstream Companies ({sortedAffected.length})</div>
            </Tooltip>
            <div className="sim-affected-list">
              <div className="sim-affected-row sim-affected-row--header">
                <span>Company</span>
                <Tooltip
                  term="Before"
                  text="The company's Probability of Default BEFORE the shock event. This is its normal credit risk level."
                >
                  <span style={{ textAlign: 'right' }}>Before</span>
                </Tooltip>
                <Tooltip
                  term="After"
                  text="The company's Probability of Default AFTER the shock. Higher = the default event has damaged this company's financial health."
                >
                  <span style={{ textAlign: 'right' }}>After</span>
                </Tooltip>
                <Tooltip
                  term="Δ PD (Delta PD)"
                  text="Change in Probability of Default. Shows how much more likely this company is to fail after the shock. E.g. +15% means 15 percentage points more likely to default."
                >
                  <span style={{ textAlign: 'right' }}>Δ PD</span>
                </Tooltip>
                <Tooltip
                  term="EL ↑ (Expected Loss Increase)"
                  text="Expected Loss increase — the extra dollar amount this company is now expected to lose due to the shock. Calculated as: Δ PD × LGD (45%) × EAD (15% of annual revenue)."
                >
                  <span style={{ textAlign: 'right' }}>EL ↑</span>
                </Tooltip>
              </div>
              {sortedAffected.map(a => {
                const node = nodes.find(n => n.id === a.company_id);
                const name = node?.name || a.company_id.split('-')[0];
                const before = (a.before_pd * 100).toFixed(1);
                const after  = (a.after_pd  * 100).toFixed(1);
                const delta  = (a.delta_pd  * 100).toFixed(1);
                const el     = formatCurrency(a.el_increase);

                let deltaClass = 'sim-affected-row__delta--low';
                if (a.delta_pd >= 0.10) deltaClass = 'sim-affected-row__delta--high';
                else if (a.delta_pd >= 0.02) deltaClass = 'sim-affected-row__delta--medium';

                return (
                  <div key={a.company_id} className="sim-affected-row">
                    <span className="sim-affected-row__name" title={a.company_id}>{name}</span>
                    <span className="sim-affected-row__value">{before}%</span>
                    <span className="sim-affected-row__value">{after}%</span>
                    <span className={`sim-affected-row__delta ${deltaClass}`}>+{delta}%</span>
                    <span className={`sim-affected-row__delta ${deltaClass}`}>{el}</span>
                  </div>
                );
              })}
            </div>
          </>
        ) : (
          <div className="sim-empty" style={{ padding: '20px' }}>
            <div className="sim-empty__icon">🛡️</div>
            <div className="sim-empty__text">No significant downstream defaults triggered by this shock.</div>
          </div>
        )}
      </div>
    );
  }

  // ═══════════════ Render: Setup State ═══════════════
  return (
    <>
      {/* ── Target Selection ── */}
      <div className="sim-section">
        <Tooltip
          term="Target Company"
          text="The company you want to 'shock' — i.e. simulate as if it suddenly went bankrupt. The model will then calculate how that failure ripples through the network."
        >
          <span className="sim-section__label">Target Company</span>
        </Tooltip>
        
        {targetNode && !isDropdownOpen ? (
          <div className="sim-selected">
            <span className="sim-selected__name" title={targetNode.name}>{targetNode.name}</span>
            <span className="sim-select__option-pd" style={{ color: getRiskColor(targetNode) }}>
              PD: {((targetNode.pd ?? 0) * 100).toFixed(1)}%
            </span>
            <button 
              className="sim-selected__clear" 
              onClick={() => { setTargetId(''); setIsDropdownOpen(true); }}
              title="Clear selection"
            >
              ×
            </button>
          </div>
        ) : (
          <div className="sim-select-wrapper" ref={dropdownRef}>
            <input
              type="text"
              className="sim-select__search"
              placeholder="Search to select a company..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              onFocus={() => setIsDropdownOpen(true)}
            />
            {isDropdownOpen && (
              <ul className="sim-select__dropdown">
                {filteredNodes.length === 0 ? (
                  <li className="sim-select__option" style={{ color: 'var(--text-dim)', justifyContent: 'center' }}>
                    No companies found
                  </li>
                ) : (
                  filteredNodes.map(node => (
                    <li 
                      key={node.id} 
                      className="sim-select__option"
                      onClick={() => {
                        setTargetId(node.id);
                        setSearchQuery('');
                        setIsDropdownOpen(false);
                      }}
                    >
                      <span className="sim-select__option-name">{node.name}</span>
                      <div className="sim-select__option-meta">
                        <span className={`risk-badge risk-badge--${getRiskTier(node).toLowerCase()}`}>
                          {getRiskTier(node)}
                        </span>
                        <span className="sim-select__option-pd" style={{ color: getRiskColor(node) }}>
                          {((node.pd ?? 0) * 100).toFixed(1)}%
                        </span>
                      </div>
                    </li>
                  ))
                )}
              </ul>
            )}
          </div>
        )}
      </div>

      {/* ── Shock Type ── */}
      <div className="sim-section">
        <Tooltip
          term="Shock Protocol"
          text="The type of financial stress event you want to simulate. Choose how the disruption enters the network."
        >
          <span className="sim-section__label">Shock Protocol</span>
        </Tooltip>
        <div className="sim-radio-group">
          {/* Node Default — radio label only, no Tooltip inside */}
          <label className={`sim-radio ${shockType === 'node_removal' ? 'sim-radio--active' : ''}`}>
            <div className="sim-radio__dot" />
            <input
              type="radio"
              name="shockType"
              value="node_removal"
              checked={shockType === 'node_removal'}
              onChange={() => setShockType('node_removal')}
              style={{ display: 'none' }}
            />
            <span className="sim-radio__label">Node Default (SCR-NR)</span>
          </label>
          {/* Info link outside the label so Tooltip click works correctly */}
          <div style={{ paddingLeft: 22, marginTop: -1, marginBottom: 5 }}>
            <Tooltip
              term="Node Default (SCR-NR)"
              text="Simulates the complete bankruptcy of the selected company. All its supply chain links are severed instantly, and the model measures how the financial damage spreads downstream."
            >
              <span style={{ fontSize: '10px', color: '#9ca3af' }}>What is this?</span>
            </Tooltip>
          </div>

          {/* Edge Severance — now enabled */}
          <label className={`sim-radio ${shockType === 'edge_removal' ? 'sim-radio--active' : ''}`}>
            <div className="sim-radio__dot" />
            <input
              type="radio"
              name="shockType"
              value="edge_removal"
              checked={shockType === 'edge_removal'}
              onChange={() => setShockType('edge_removal')}
              style={{ display: 'none' }}
            />
            <span className="sim-radio__label">Edge Severance (SCR-ER)</span>
          </label>
          {/* Info link outside the label */}
          <div style={{ paddingLeft: 22, marginTop: -1 }}>
            <Tooltip
              term="Edge Severance (SCR-ER)"
              text="Simulates cutting a single supply chain link between two companies — e.g. a supplier stops delivering to one customer. The supplier still exists; only the relationship is severed."
            >
              <span style={{ fontSize: '10px', color: '#9ca3af' }}>What is this?</span>
            </Tooltip>
          </div>
        </div>
      </div>

      {/* ── Source Company (Edge Removal only) ── */}
      {shockType === 'edge_removal' && targetId && (
        <div className="sim-section">
          <Tooltip
            term="Source Company"
            text="The company whose outgoing supply link to the target will be severed. Only companies with a direct edge to the target are shown."
          >
            <span className="sim-section__label">Source Company (Edge From)</span>
          </Tooltip>

          {sourceOptions.length === 0 ? (
            <div className="sim-empty" style={{ padding: '12px' }}>
              <div className="sim-empty__text" style={{ fontSize: '11px' }}>
                No incoming edges found for this target. Select a different target company.
              </div>
            </div>
          ) : sourceNode && !isSourceDropdownOpen ? (
            <div className="sim-selected">
              <span className="sim-selected__name" title={sourceNode.name}>{sourceNode.name}</span>
              <span className="sim-select__option-pd" style={{ color: getRiskColor(sourceNode) }}>
                PD: {((sourceNode.pd ?? 0) * 100).toFixed(1)}%
              </span>
              <button
                className="sim-selected__clear"
                onClick={() => { setSourceId(''); setIsSourceDropdownOpen(true); }}
                title="Clear selection"
              >
                ×
              </button>
            </div>
          ) : (
            <div className="sim-select-wrapper" ref={sourceDropdownRef}>
              <input
                type="text"
                className="sim-select__search"
                placeholder="Search source company..."
                value={sourceSearchQuery}
                onChange={e => setSourceSearchQuery(e.target.value)}
                onFocus={() => setIsSourceDropdownOpen(true)}
              />
              {isSourceDropdownOpen && (
                <ul className="sim-select__dropdown">
                  {filteredSourceOptions.length === 0 ? (
                    <li className="sim-select__option" style={{ color: 'var(--text-dim)', justifyContent: 'center' }}>
                      No matching companies
                    </li>
                  ) : (
                    filteredSourceOptions.map(node => (
                      <li
                        key={node.id}
                        className="sim-select__option"
                        onClick={() => {
                          setSourceId(node.id);
                          setSourceSearchQuery('');
                          setIsSourceDropdownOpen(false);
                        }}
                      >
                        <span className="sim-select__option-name">{node.name}</span>
                        <div className="sim-select__option-meta">
                          <span className={`risk-badge risk-badge--${getRiskTier(node).toLowerCase()}`}>
                            {getRiskTier(node)}
                          </span>
                          <span className="sim-select__option-pd" style={{ color: getRiskColor(node) }}>
                            {((node.pd ?? 0) * 100).toFixed(1)}%
                          </span>
                        </div>
                      </li>
                    ))
                  )}
                </ul>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Action Button ── */}
      <div className="sim-button-section">
        <button 
          className="sim-button"
          onClick={handleSimulateClick}
          disabled={!targetId || isSimulating || (shockType === 'edge_removal' && !sourceId)}
        >
          {isSimulating ? (
            <>
              <div className="sim-button__spinner" />
              <span>Simulating Cascade...</span>
            </>
          ) : (
            <span>{shockType === 'edge_removal' ? 'Simulate Edge Severance' : 'Simulate Default Cascade'}</span>
          )}
        </button>
      </div>
    </>
  );
});

// ═══════════════ Helpers ═══════════════

function getRiskColor(node) {
  const pd = node.pd ?? 0;
  if (pd >= 0.5) return '#FF6B6B';
  if (pd >= 0.2) return '#FFB300';
  return '#00E676';
}

function getRiskTier(node) {
  if (node.risk_tier) return node.risk_tier;
  const pd = node.pd ?? 0;
  if (pd >= 0.5) return 'High';
  if (pd >= 0.2) return 'Medium';
  return 'Low';
}

function formatCurrency(val) {
  if (val == null || isNaN(val)) return '$0';
  if (val === 0) return '$0';
  const abs = Math.abs(val);
  const sign = val < 0 ? '-' : '';
  if (abs >= 1e12) return `${sign}${(abs / 1e12).toFixed(2)}T`;
  if (abs >= 1e9)  return `${sign}${(abs / 1e9).toFixed(2)}B`;
  if (abs >= 1e6)  return `${sign}${(abs / 1e6).toFixed(2)}M`;
  if (abs >= 1e3)  return `${sign}${(abs / 1e3).toFixed(0)}K`;
  return `${sign}$${abs.toFixed(0)}`;
}

export default ShockSimulator;
