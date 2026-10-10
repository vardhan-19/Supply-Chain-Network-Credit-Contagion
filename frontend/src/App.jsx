import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import NetworkGraph from './NetworkGraph';
import TopBar from './components/TopBar';
import RiskRankings from './components/RiskRankings';
import CompanyDetail from './components/CompanyDetail';
import ShockSimulator from './components/ShockSimulator';
import Tooltip from './components/Tooltip';
import AboutPage from './components/AboutPage';
import ErrorBoundary from './components/ErrorBoundary';
import EdgeInspector from './components/EdgeInspector';
import { fetchGraphData, runSimulation } from './services/api';
import './App.css';

/**
 * App.jsx — Supply Chain Network Credit Contagion main dashboard.
 */
function App() {
  // ═══ Core state ═══
  const [graphData, setGraphData]                 = useState(null);
  const [simulationResults, setSimulationResults] = useState(null);
  const [selectedCompany, setSelectedCompany]     = useState(null);
  const [isSimulating, setIsSimulating]           = useState(false);
  const [loading, setLoading]                     = useState(true);
  const [error, setError]                         = useState(null);
  const [retryStatus, setRetryStatus]             = useState('Connecting to backend…');

  // Left panel view: 'list' | 'detail'
  const [leftView, setLeftView] = useState('list');

  // About page — replaces dashboard when true
  const [showAbout, setShowAbout] = useState(false);

  // Shock type
  const [shockType, setShockType] = useState('node_removal');

  // Currently hovered network link/line
  const [hoveredLink, setHoveredLink] = useState(null);

  // ═══ Resizable panels state ═══
  const DEFAULT_LEFT_WIDTH  = 400;
  const DEFAULT_RIGHT_WIDTH = 360;
  const MIN_LEFT_WIDTH      = 260;
  const MIN_RIGHT_WIDTH     = 260;

  const [leftPanelWidth, setLeftPanelWidth] = useState(() => {
    try {
      const saved = localStorage.getItem('sc_left_panel_w');
      if (saved) {
        const val = parseInt(saved, 10);
        if (!isNaN(val) && val >= MIN_LEFT_WIDTH && val <= 700) return val;
      }
    } catch (_) {}
    return DEFAULT_LEFT_WIDTH;
  });

  const [rightPanelWidth, setRightPanelWidth] = useState(() => {
    try {
      const saved = localStorage.getItem('sc_right_panel_w');
      if (saved) {
        const val = parseInt(saved, 10);
        if (!isNaN(val) && val >= MIN_RIGHT_WIDTH && val <= 650) return val;
      }
    } catch (_) {}
    return DEFAULT_RIGHT_WIDTH;
  });

  const [isResizing, setIsResizing] = useState(false);
  const [activeHandle, setActiveHandle] = useState(null); // 'left' | 'right' | null

  const graphRef      = useRef(null);
  const listScrollRef = useRef(0);
  const listBodyRef   = useRef(null);

  // ═══ Data fetching — silent retry until backend is ready ═══
  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    setRetryStatus('Connecting to backend…');

    const MAX_RETRIES  = 10;                                   // up to ~30s total wait
    const BASE_DELAY   = 800;                                  // start at 800ms
    const MAX_DELAY    = 4000;                                 // cap at 4s per retry

    for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
      try {
        const data = await fetchGraphData();
        if (data?.error) throw new Error(data.error);
        const formatted = { nodes: data.nodes || [], links: data.links || data.edges || [] };
        if (formatted.nodes.length === 0) throw new Error('No nodes returned from API.');
        setGraphData(formatted);
        setLoading(false);
        setRetryStatus('');
        return;
      } catch (err) {
        if (attempt === MAX_RETRIES) {
          // Only show the error screen after ALL retries are exhausted
          setError(err.message);
          setLoading(false);
          return;
        }
        // Exponential backoff, capped at MAX_DELAY
        const delay = Math.min(BASE_DELAY * Math.pow(1.5, attempt), MAX_DELAY);
        setRetryStatus(`Backend starting up… (${attempt + 1}/${MAX_RETRIES})`);
        await new Promise(r => setTimeout(r, delay));
      }
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  // ═══ Callbacks ═══
  const handleNodeClick = useCallback((node) => {
    setSelectedCompany(node);
    setLeftView('detail');
  }, []);

  const handleSelectCompany = useCallback((node) => {
    if (listBodyRef.current) listScrollRef.current = listBodyRef.current.scrollTop;
    setSelectedCompany(node);
    setLeftView('detail');
    graphRef.current?.centerOnNode(node.id);
  }, []);

  const handleBackToList = useCallback(() => {
    setLeftView('list');
    requestAnimationFrame(() => {
      if (listBodyRef.current) listBodyRef.current.scrollTop = listScrollRef.current;
    });
  }, []);

  const handleSimulate = useCallback(async (companyId, type, sourceCompanyId = null) => {
    setIsSimulating(true);
    try {
      const results = await runSimulation(companyId, type, sourceCompanyId);
      setSimulationResults(results);
    } catch (err) {
      console.error('Simulation failed:', err);
      alert(`Simulation failed: ${err.message}`);
    } finally {
      setIsSimulating(false);
    }
  }, []);

  const clearSimulation = useCallback(() => {
    setSimulationResults(null);
  }, []);

  const handleResetLayout = useCallback(() => graphRef.current?.resetLayout(), []);
  const handleFitToView   = useCallback(() => graphRef.current?.zoomToFit(), []);

  // Re-center graph when right panel opens/closes
  useEffect(() => {
    const t = setTimeout(() => graphRef.current?.zoomToFit(), 350);
    return () => clearTimeout(t);
  }, [!!simulationResults]);

  // ═══ Resizing drag listeners ═══
  const handleMouseDownLeft = useCallback((e) => {
    e.preventDefault();
    setIsResizing(true);
    setActiveHandle('left');

    const startX = e.clientX;
    const startW = leftPanelWidth;

    const onMouseMove = (moveEvent) => {
      const delta = moveEvent.clientX - startX;
      const maxW = Math.min(650, window.innerWidth - rightPanelWidth - 280);
      const newW = Math.max(MIN_LEFT_WIDTH, Math.min(maxW, startW + delta));
      setLeftPanelWidth(newW);
    };

    const onMouseUp = (upEvent) => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      setIsResizing(false);
      setActiveHandle(null);

      const delta = upEvent.clientX - startX;
      const maxW = Math.min(650, window.innerWidth - rightPanelWidth - 280);
      const finalW = Math.max(MIN_LEFT_WIDTH, Math.min(maxW, startW + delta));
      try { localStorage.setItem('sc_left_panel_w', String(finalW)); } catch (_) {}
    };

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
  }, [leftPanelWidth, rightPanelWidth]);

  const handleMouseDownRight = useCallback((e) => {
    e.preventDefault();
    setIsResizing(true);
    setActiveHandle('right');

    const startX = e.clientX;
    const startW = rightPanelWidth;

    const onMouseMove = (moveEvent) => {
      // Dragging left increases right panel width
      const delta = startX - moveEvent.clientX;
      const maxW = Math.min(600, window.innerWidth - leftPanelWidth - 280);
      const newW = Math.max(MIN_RIGHT_WIDTH, Math.min(maxW, startW + delta));
      setRightPanelWidth(newW);
    };

    const onMouseUp = (upEvent) => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      setIsResizing(false);
      setActiveHandle(null);

      const delta = startX - upEvent.clientX;
      const maxW = Math.min(600, window.innerWidth - leftPanelWidth - 280);
      const finalW = Math.max(MIN_RIGHT_WIDTH, Math.min(maxW, startW + delta));
      try { localStorage.setItem('sc_right_panel_w', String(finalW)); } catch (_) {}
    };

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
  }, [leftPanelWidth, rightPanelWidth]);

  const handleResetLeftWidth = useCallback(() => {
    setLeftPanelWidth(DEFAULT_LEFT_WIDTH);
    try { localStorage.setItem('sc_left_panel_w', String(DEFAULT_LEFT_WIDTH)); } catch (_) {}
  }, []);

  const handleResetRightWidth = useCallback(() => {
    setRightPanelWidth(DEFAULT_RIGHT_WIDTH);
    try { localStorage.setItem('sc_right_panel_w', String(DEFAULT_RIGHT_WIDTH)); } catch (_) {}
  }, []);

  // ═══ Keyboard shortcuts ═══
  useEffect(() => {
    const onKey = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
      switch (e.key) {
        case 'Escape':
          if (showAbout)               { setShowAbout(false); break; }
          if (leftView === 'detail')   { setLeftView('list'); break; }
          if (simulationResults)       { clearSimulation(); break; }
          break;
        case 'r': case 'R': if (!showAbout) graphRef.current?.resetLayout(); break;
        case 'f': case 'F': if (!showAbout) graphRef.current?.zoomToFit();   break;
        default: break;
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [leftView, simulationResults, clearSimulation, showAbout]);

  // ═══ Derived stats ═══
  const riskCounts = useMemo(() => {
    if (!graphData) return { total: 0, high: 0, medium: 0, low: 0, edges: 0 };
    let high = 0, medium = 0, low = 0;
    graphData.nodes.forEach(n => {
      const pd   = n.pd ?? 0;
      const tier = n.risk_tier || (pd >= 0.5 ? 'High' : pd >= 0.2 ? 'Medium' : 'Low');
      if (tier === 'High') high++;
      else if (tier === 'Medium') medium++;
      else low++;
    });
    return { total: graphData.nodes.length, high, medium, low, edges: graphData.links.length };
  }, [graphData]);

  // ─── Loading screen (shown while backend warms up) ───
  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-skeleton">
          <div className="skeleton-bar skeleton-bar--title" />
          <div className="skeleton-row">
            <div className="skeleton-panel" />
            <div className="skeleton-graph" />
          </div>
        </div>
        <div className="loading-spinner" />
        <span className="loading-text">{retryStatus || 'Loading supply chain network…'}</span>
      </div>
    );
  }

  // ─── Error screen (only shown after all retries fail) ───
  if (error) {
    return (
      <div className="error-screen">
        <div className="error-screen__icon">⚠</div>
        <div className="error-screen__message">{error}</div>
        <div className="error-screen__hint">
          Make sure the backend server is running:<br />
          <code>uvicorn api.main:app --reload --port 8001</code>
        </div>
        <button className="btn" onClick={loadData}>↺ Retry</button>
      </div>
    );
  }

  const rightPanelOpen = true;  // Always show right panel for Shock Simulator

  // ─── Main app shell ───
  return (
    <div className="app-shell">

      {/* ═══ TOP BAR — always visible ═══ */}
      <TopBar
        riskCounts={riskCounts}
        isSimulating={isSimulating}
        simulationResults={simulationResults}
        onResetLayout={handleResetLayout}
        onFitToView={handleFitToView}
        onAbout={() => setShowAbout(true)}
      />

      {/* ═══ ABOUT PAGE — overlays dashboard (does NOT unmount the graph) ═══
           Keeping the dashboard always mounted means the NetworkGraph is never
           destroyed, so its boot animation never replays when navigating back.
      */}
      {showAbout && (
        <AboutPage onClose={() => setShowAbout(false)} />
      )}

      {/* ═══ DASHBOARD — always mounted so the graph stays alive ═══ */}
      <div
        className="dashboard-shell"
        style={showAbout ? { visibility: 'hidden', pointerEvents: 'none' } : undefined}
        aria-hidden={showAbout ? 'true' : undefined}
      >

          {/* ── MAIN CONTENT ROW ── */}
          <div
            className={`main-content ${isResizing ? 'main-content--resizing' : ''}`}
            style={{
              '--left-panel-w': `${leftPanelWidth}px`,
              '--right-panel-w': `${rightPanelWidth}px`,
            }}
          >

            {/* ── LEFT PANEL ── */}
            <aside
              className="left-panel"
              style={{ width: `${leftPanelWidth}px`, minWidth: `${leftPanelWidth}px`, maxWidth: `${leftPanelWidth}px` }}
            >

              <div className="left-panel__header">
                {leftView === 'detail' ? (
                  <>
                    <button className="left-panel__back-btn" onClick={handleBackToList}>
                      ← Back
                    </button>
                    <span className="left-panel__header-title">Company Detail</span>
                  </>
                ) : (
                  <span className="left-panel__header-title">Risk Rankings</span>
                )}
              </div>

              <div className="left-panel__body" ref={listBodyRef}>
                <ErrorBoundary title="Company View Error" onReset={handleBackToList}>
                  {leftView === 'list' ? (
                    <RiskRankings
                      nodes={graphData?.nodes || []}
                      selectedCompany={selectedCompany}
                      onSelectCompany={handleSelectCompany}
                    />
                  ) : (
                    selectedCompany && (
                      <CompanyDetail
                        company={selectedCompany}
                        links={graphData?.links || []}
                        nodes={graphData?.nodes || []}
                      />
                    )
                  )}
                </ErrorBoundary>
              </div>

              {/* Simulate section — pinned to bottom in detail view */}
              {leftView === 'detail' && selectedCompany && (
                <div className="left-panel__simulate">

                  <Tooltip
                    term="Shock Protocol"
                    text="The type of financial stress event to simulate. Choose how the disruption enters the supply chain network."
                  >
                    <div className="simulate-protocol-label">Shock Protocol</div>
                  </Tooltip>

                  <div className="simulate-radio-group">

                    <label
                      className={`simulate-radio ${shockType === 'node_removal' ? 'simulate-radio--active' : ''}`}
                      onClick={() => setShockType('node_removal')}
                    >
                      <div className="simulate-radio__dot" />
                      <div className="simulate-radio__text">
                        <span className="simulate-radio__label">Node Default</span>
                        <span className="simulate-radio__sublabel">SCR-NR — Full bankruptcy</span>
                      </div>
                    </label>
                    <div style={{ paddingLeft: 12, marginTop: -2, marginBottom: 4 }}>
                      <Tooltip
                        term="Node Default (SCR-NR)"
                        text="Simulates complete bankruptcy of the selected company. All supply chain links are severed instantly. The model measures how financial damage spreads downstream."
                      >
                        <span style={{ fontSize: '10px', color: '#9ca3af' }}>What is this?</span>
                      </Tooltip>
                    </div>

                    <label
                      className={`simulate-radio ${shockType === 'edge_removal' ? 'simulate-radio--active' : ''}`}
                      onClick={() => setShockType('edge_removal')}
                    >
                      <div className="simulate-radio__dot" />
                      <div className="simulate-radio__text">
                        <span className="simulate-radio__label">Edge Severance</span>
                        <span className="simulate-radio__sublabel">SCR-ER — Link cut</span>
                      </div>
                    </label>
                    <div style={{ paddingLeft: 12, marginTop: -2 }}>
                      <Tooltip
                        term="Edge Severance (SCR-ER)"
                        text="Simulates cutting a single supply chain link — e.g. a supplier stops delivering to one customer. The supplier still exists; only the relationship is severed."
                      >
                        <span style={{ fontSize: '10px', color: '#9ca3af' }}>What is this?</span>
                      </Tooltip>
                    </div>

                  </div>

                  <button
                    className="simulate-btn"
                    onClick={() => handleSimulate(selectedCompany.id, shockType)}
                    disabled={isSimulating || shockType === 'edge_removal'}
                    title={shockType === 'edge_removal' ? 'Use the right-panel Shock Simulator for edge removal (requires source company selection)' : undefined}
                  >
                    {isSimulating ? (
                      <><div className="simulate-btn__spinner" /><span>Simulating…</span></>
                    ) : (
                      <><span>⚡</span><span>{shockType === 'edge_removal' ? 'Use Shock Simulator →' : 'Simulate Default Cascade'}</span></>
                    )}
                  </button>
                  {shockType === 'edge_removal' && (
                    <div style={{ fontSize: '10px', color: '#9ca3af', textAlign: 'center', marginTop: '6px' }}>
                      Edge removal requires selecting a source company. Use the Shock Simulator panel in the right sidebar.
                    </div>
                  )}

                </div>
              )}
            </aside>

            {/* ── RESIZE HANDLE LEFT ── */}
            <div
              className={`resize-handle resize-handle--left ${activeHandle === 'left' ? 'resize-handle--active' : ''}`}
              onMouseDown={handleMouseDownLeft}
              onDoubleClick={handleResetLeftWidth}
              title="Drag to resize panel · Double-click to reset"
              role="separator"
              aria-orientation="vertical"
              aria-label="Resize left panel"
            >
              <div className="resize-handle__indicator" />
            </div>

            {/* ── GRAPH ── */}
            <div className="graph-area">
              {graphData && (
                <NetworkGraph
                  ref={graphRef}
                  graphData={graphData}
                  simulationResults={simulationResults}
                  selectedCompany={selectedCompany}
                  onNodeClick={handleNodeClick}
                  onLinkHover={setHoveredLink}
                />
              )}
            </div>

            {/* ── RESIZE HANDLE RIGHT ── */}
            <div
              className={`resize-handle resize-handle--right ${activeHandle === 'right' ? 'resize-handle--active' : ''}`}
              onMouseDown={handleMouseDownRight}
              onDoubleClick={handleResetRightWidth}
              title="Drag to resize panel · Double-click to reset"
              role="separator"
              aria-orientation="vertical"
              aria-label="Resize right panel"
            >
              <div className="resize-handle__indicator" />
            </div>

            {/* ── RIGHT PANEL: Shock Simulator + Results + Edge Inspector ── */}
            <aside
              className="right-panel"
              style={{ width: `${rightPanelWidth}px`, minWidth: `${rightPanelWidth}px`, maxWidth: `${rightPanelWidth}px` }}
            >
              <div className="right-panel__header">
                <span className="right-panel__header-title">⚡ Shock Simulator</span>
              </div>
              <div className="right-panel__body">
                <ErrorBoundary title="Shock Simulator Error" onReset={clearSimulation}>
                  <ShockSimulator
                    nodes={graphData?.nodes || []}
                    links={graphData?.links || []}
                    onSimulate={handleSimulate}
                    simulationResults={simulationResults}
                    isSimulating={isSimulating}
                    selectedCompany={selectedCompany}
                    onClear={clearSimulation}
                  />
                </ErrorBoundary>
              </div>

              {/* ── CONNECTION INSPECTOR: Pinned at bottom of right panel ── */}
              <EdgeInspector link={hoveredLink} />
            </aside>

          </div>{/* /main-content */}

          {/* ═══ STATUS BAR ═══ */}
          <footer className="status-bar">
            <div className="status-bar__left">
              <div className="status-bar__item">
                <span className="status-dot" />
                Connected
              </div>
              <div className="status-bar__item">
                GNN Model: GCNConv(12→64→64→32→2)
              </div>
            </div>
            <div className="status-bar__right">
              <div className="status-bar__item" style={{ color: 'var(--text-dim)', fontSize: '10px' }}>
                Click company to view detail · R reset · F fit · Esc back
              </div>
              <div className="status-bar__item">
                {isSimulating ? '⏳ Simulating…' : simulationResults ? '✓ Simulation complete' : 'Ready'}
              </div>
            </div>
          </footer>

      </div> {/* /dashboard-shell */}

    </div>
  );
}

export default App;
