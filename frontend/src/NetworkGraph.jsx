import React, { useState, useEffect, useLayoutEffect, useRef, useCallback, useMemo, forwardRef, useImperativeHandle } from 'react';
import ForceGraph2D from 'react-force-graph-2d';

// ══════════════════════════════════════════════════════════════
//  DESIGN SYSTEM — Graph colour palette (UNCHANGED)
// ══════════════════════════════════════════════════════════════

const RELATIONSHIP_COLORS = {
  supply:                       '#00F5FF',
  tier1_supplier:               '#FFD500',
  raw_material_supplier:        '#4C6FFF',
  tier2_supplier_battery:       '#FF7A00',
  tier2_supplier_semiconductor: '#39FF14',
  trade_credit:                 '#B388FF',
  ownership:                    '#FF4FD8',
  unknown:                      '#78909C',
};

const RELATIONSHIP_LABELS = {
  supply:                       'Supply',
  tier1_supplier:               'Tier-1 Supplier',
  tier2_supplier_battery:       'Tier-2 — Battery',
  tier2_supplier_semiconductor: 'Tier-2 — Semiconductor',
  ownership:                    'Ownership',
  trade_credit:                 'Trade Credit',
  raw_material_supplier:        'Raw Material Supplier',
  unknown:                      'Unknown',
};

const NODE_HEALTHY_COLOR  = '#D6E2FF';
const NODE_HEALTHY_BORDER = '#90AAFF';
const NODE_DEFAULT_COLOR  = '#FF4C4C';
const NODE_DEFAULT_BORDER = '#CC0000';

// ── Generate a short 3-4 char ticker label from the company name ──
function getNodeTicker(node) {
  // Use real ticker if available
  if (node.ticker && typeof node.ticker === 'string' && node.ticker.trim().length > 0
      && node.ticker.toLowerCase() !== 'nan' && node.ticker.toLowerCase() !== 'none') {
    return node.ticker.trim().toUpperCase().slice(0, 4);
  }
  // Auto-generate from company name
  const name = (node.name || node.id || '?').trim();
  // Remove common suffixes
  const cleaned = name.replace(/\b(Inc\.?|Corp\.?|Ltd\.?|LLC|Co\.?|Group|Holdings?|International|Technologies|Semiconductor|Automotive|Motors|Energy|Electronics|Chemical)\b/gi, '').trim();
  const words = cleaned.split(/[\s\-_&.]+/).filter(w => w.length > 0);
  if (words.length === 0) return '?';
  if (words.length === 1) {
    // Single word — take first 3-4 uppercase letters
    return words[0].toUpperCase().slice(0, 4);
  }
  // Multiple words — take first letter of each (up to 4)
  return words.slice(0, 4).map(w => w[0].toUpperCase()).join('');
}

// ── Draw the ticker label centred inside the node circle ──
// Smart fitting: text is guaranteed to stay inside the circle.
// Uses the inscribed rectangle of the circle (width = r×√2) as the
// bounding box, then measures the actual rendered text and shrinks
// the font until it fits.  Skips entirely for tiny nodes.
function drawNodeTicker(ctx, node, radius, fillColor) {
  // Don't attempt to draw text on very small nodes — it would be illegible
  if (radius < 4) return;

  const label = getNodeTicker(node);

  // The largest rectangle that fits inside a circle of radius r
  // has width = r * √2 ≈ r * 1.414.  We use 90% of that as our
  // max text width to add a small inner margin.
  const maxTextWidth = radius * 1.414 * 0.88;
  // Max text height is ~50% of the diameter (vertical margin)
  const maxTextHeight = radius * 0.9;

  // Start with an optimistic font size proportional to node radius,
  // then shrink until the measured text fits inside the circle.
  let fontSize = Math.min(maxTextHeight, radius * 0.7);
  const fontFamily = '"Inter", "Segoe UI", sans-serif';
  const MIN_FONT = 1.2;

  ctx.save();
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';

  // Iteratively shrink font size until text fits (max 6 iterations)
  for (let i = 0; i < 6; i++) {
    if (fontSize < MIN_FONT) { fontSize = MIN_FONT; break; }
    ctx.font = `bold ${fontSize}px ${fontFamily}`;
    const measured = ctx.measureText(label);
    if (measured.width <= maxTextWidth) break;
    // Shrink proportionally to how much we overflowed
    fontSize *= (maxTextWidth / measured.width) * 0.95;
  }

  if (fontSize < MIN_FONT) { ctx.restore(); return; }

  ctx.font = `bold ${fontSize}px ${fontFamily}`;
  ctx.fillStyle = fillColor;
  ctx.globalAlpha = 0.85;
  ctx.fillText(label, node.x, node.y);
  ctx.restore();
}

// ── Interpolate between two hex colours by factor t ∈ [0,1] ──
function lerpColor(hex1, hex2, t) {
  const parse = h => [
    parseInt(h.slice(1, 3), 16),
    parseInt(h.slice(3, 5), 16),
    parseInt(h.slice(5, 7), 16),
  ];
  const [r1, g1, b1] = parse(hex1);
  const [r2, g2, b2] = parse(hex2);
  return `rgb(${Math.round(r1+(r2-r1)*t)},${Math.round(g1+(g2-g1)*t)},${Math.round(b1+(b2-b1)*t)})`;
}

// ══════════════════════════════════════════════════════════════
//  ANIMATION CONSTANTS
// ══════════════════════════════════════════════════════════════

const ANIM_PHASE = {
  IDLE:      'idle',      // Before graph data loads
  NODES:     'nodes',     // Nodes bursting in, staggered by degree
  PAUSE:     'pause',     // All nodes visible, edges hidden
  EDGES:     'edges',     // Edges drawing like contagion spreading
  DONE:      'done',      // Normal interactive mode
};

const NODE_STAGGER_MS  = 12;   // ms between each node appearing
const PAUSE_DURATION   = 400;  // ms of stillness before edges draw
const EDGE_STAGGER_MS  = 6;    // ms between each edge batch appearing

/**
 * NetworkGraph — Force-directed 2D graph visualisation.
 *
 * Props:
 *   graphData        – { nodes: [], links: [] } from /graph API
 *   simulationResults – result from /simulate, or null
 *   selectedCompany  – currently selected company node, or null
 *   onNodeClick      – callback(node) when a node is clicked
 *
 * Ref methods:
 *   resetLayout()    – unpin all nodes, reheat simulation
 *   zoomToFit()      – fit entire graph into view
 *   centerOnNode(id) – animated zoom to a specific node
 */
const NetworkGraph = forwardRef(({
  graphData = { nodes: [], links: [] },
  simulationResults = null,
  selectedCompany = null,
  onNodeClick = null,
  onLinkHover = null,
}, ref) => {

  const [hoveredLink, setHoveredLink]       = useState(null);
  const [pulsePhase, setPulsePhase]         = useState(0);

  // ── Cinematic boot animation state ──
  const [animPhase, setAnimPhase]           = useState(ANIM_PHASE.IDLE);
  const [visibleNodeIds, setVisibleNodeIds] = useState(new Set());
  const [visibleEdgeCount, setVisibleEdgeCount] = useState(0);
  const sortedEdgesRef                      = useRef([]);  // Edges ordered by BFS distance
  const animTimers                          = useRef([]);

  // ── Edge-detail panel (static, top-right, no drag/resize) ──
  const containerRef     = useRef(null);
  const fgRef            = useRef();
  const pulseRaf         = useRef(null);
  // Tracks whether the first-load zoomToFit has fired via onEngineStop
  const hasInitialFitRef = useRef(false);
  const initialFitTimerRef = useRef(null);

  // ── Dynamic container dimensions (ensures graph stays strictly between panels) ──
  const [dimensions, setDimensions] = useState(() => ({
    width: typeof window !== 'undefined' ? Math.max(400, window.innerWidth - 760) : 800,
    height: typeof window !== 'undefined' ? Math.max(400, window.innerHeight - 80) : 600,
  }));

  useLayoutEffect(() => {
    if (!containerRef.current) return;
    const el = containerRef.current;
    const updateDimensions = () => {
      const rect = el.getBoundingClientRect();
      const w = Math.floor(rect.width);
      const h = Math.floor(rect.height);
      if (w > 0 && h > 0) {
        setDimensions(prev => (prev.width === w && prev.height === h ? prev : { width: w, height: h }));
      }
    };

    updateDimensions();

    const resizeObserver = new ResizeObserver(() => {
      updateDimensions();
    });
    resizeObserver.observe(el);

    return () => {
      resizeObserver.disconnect();
    };
  }, []);

  // ── Configure d3 force simulation to spread nodes gracefully across the canvas ──
  useEffect(() => {
    if (!fgRef.current || !graphData?.nodes?.length) return;
    const fg = fgRef.current;

    const charge = fg.d3Force('charge');
    if (charge) {
      charge.strength(-160).distanceMax(700);
    }

    const link = fg.d3Force('link');
    if (link) {
      link.distance(l => 45 + (1 - (l.weight || 0.5)) * 35);
    }
  }, [graphData]);

  // ═══════════════ Precompute simulation lookup maps ═══════════════
  const simMaps = useMemo(() => {
    if (!simulationResults) return null;
    const shockedId = simulationResults.shocked_company;
    const sourceId = simulationResults.source_company || null;
    const shockType = simulationResults.shock_type || 'node_removal';
    const affectedMap = {};
    (simulationResults.affected_nodes || []).forEach(a => {
      affectedMap[a.company_id] = a;
    });
    const maxDelta = Math.max(...Object.values(affectedMap).map(a => a.delta_pd), 0.001);
    return { shockedId, sourceId, shockType, affectedMap, maxDelta };
  }, [simulationResults]);

  // ═══════════════ Pulse animation for shocked node ═══════════════
  useEffect(() => {
    if (!simMaps) { cancelAnimationFrame(pulseRaf.current); return; }
    let start = null;
    const PERIOD = 900;
    const tick = (ts) => {
      if (!start) start = ts;
      setPulsePhase(Math.sin(((ts - start) % PERIOD) / PERIOD * Math.PI));
      pulseRaf.current = requestAnimationFrame(tick);
    };
    pulseRaf.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(pulseRaf.current);
  }, [simMaps]);

  // ═══════════════ Expose ref methods ═══════════════
  useImperativeHandle(ref, () => ({
    resetLayout() {
      if (!fgRef.current) return;
      graphData.nodes.forEach(n => { n.fx = undefined; n.fy = undefined; });
      fgRef.current.d3ReheatSimulation();
      setTimeout(() => fgRef.current.zoomToFit(1000, 60), 600);
    },
    zoomToFit() {
      // Use rAF so the DOM has the correct size before ForceGraph measures it
      requestAnimationFrame(() => fgRef.current?.zoomToFit(600, 70));
    },
    centerOnNode(nodeId) {
      if (!fgRef.current) return;
      const node = graphData.nodes.find(n => n.id === nodeId);
      if (node) {
        fgRef.current.centerAt(node.x, node.y, 800);
        fgRef.current.zoom(5, 800);
      }
    },
  }), [graphData]);

  // ═══════════════ CINEMATIC BOOT ANIMATION ═══════════════
  useEffect(() => {
    if (!fgRef.current || graphData.nodes.length === 0) return;

    // Cancel any running timers from previous data loads
    animTimers.current.forEach(t => clearTimeout(t));
    animTimers.current = [];

    // ── Step 1: Build degree map and sort nodes high-degree first ──
    const degreeMap = {};
    graphData.links.forEach(l => {
      const sId = typeof l.source === 'object' ? l.source.id : l.source;
      const tId = typeof l.target === 'object' ? l.target.id : l.target;
      degreeMap[sId] = (degreeMap[sId] || 0) + 1;
      degreeMap[tId] = (degreeMap[tId] || 0) + 1;
    });

    const nodesSorted = [...graphData.nodes].sort(
      (a, b) => (degreeMap[b.id] || 0) - (degreeMap[a.id] || 0)
    );

    // Hub = highest-degree node
    const hubId = nodesSorted[0]?.id;
    const hubNode = graphData.nodes.find(n => n.id === hubId);

    // ── Step 2: BFS from hub to order edges ──
    const adjacency = {};
    graphData.links.forEach(l => {
      const sId = typeof l.source === 'object' ? l.source.id : l.source;
      const tId = typeof l.target === 'object' ? l.target.id : l.target;
      if (!adjacency[sId]) adjacency[sId] = [];
      if (!adjacency[tId]) adjacency[tId] = [];
      adjacency[sId].push(tId);
      adjacency[tId].push(sId);
    });

    const bfsOrder = [];   // edge indices in BFS order
    const visited = new Set([hubId]);
    const queue = [hubId];
    const linksBySource = {};
    graphData.links.forEach((l, idx) => {
      const sId = typeof l.source === 'object' ? l.source.id : l.source;
      if (!linksBySource[sId]) linksBySource[sId] = [];
      linksBySource[sId].push(idx);
    });

    while (queue.length > 0) {
      const current = queue.shift();
      (linksBySource[current] || []).forEach(idx => bfsOrder.push(idx));
      (adjacency[current] || []).forEach(neighbor => {
        if (!visited.has(neighbor)) {
          visited.add(neighbor);
          queue.push(neighbor);
        }
      });
    }
    // Add any remaining edges not reached by BFS
    graphData.links.forEach((_, idx) => {
      if (!bfsOrder.includes(idx)) bfsOrder.push(idx);
    });
    sortedEdgesRef.current = bfsOrder;

    // ── Step 3: Reset initial-fit flag and begin animation ──
    setVisibleNodeIds(new Set());
    setVisibleEdgeCount(0);
    setAnimPhase(ANIM_PHASE.NODES);
    hasInitialFitRef.current = false;

    // Zoom out smoothly while nodes appear
    const t_zoomOut = setTimeout(() => fgRef.current?.zoomToFit(1400, 50), 700);
    animTimers.current.push(t_zoomOut);

    // ── Step 4: Burst nodes in staggered (fast) ──
    let accumulated = new Set();
    nodesSorted.forEach((node, i) => {
      const timer = setTimeout(() => {
        accumulated = new Set(accumulated);
        accumulated.add(node.id);
        setVisibleNodeIds(accumulated);
      }, i * NODE_STAGGER_MS);
      animTimers.current.push(timer);
    });

    // ── Step 5: Pause after all nodes appear ──
    const totalNodeTime = nodesSorted.length * NODE_STAGGER_MS;
    const t_pause = setTimeout(() => {
      setAnimPhase(ANIM_PHASE.PAUSE);
    }, totalNodeTime + 50);
    animTimers.current.push(t_pause);

    // ── Step 6: Begin drawing edges like contagion spreading ──
    const t_edgesStart = setTimeout(() => {
      setAnimPhase(ANIM_PHASE.EDGES);

      const totalEdges = sortedEdgesRef.current.length;
      const BATCH_SIZE = Math.max(1, Math.ceil(totalEdges / 80)); // ~80 batches

      for (let batch = 0; batch <= 80; batch++) {
        const edgeTimer = setTimeout(() => {
          setVisibleEdgeCount(Math.min((batch + 1) * BATCH_SIZE, totalEdges));
        }, batch * EDGE_STAGGER_MS);
        animTimers.current.push(edgeTimer);
      }
    }, totalNodeTime + PAUSE_DURATION);
    animTimers.current.push(t_edgesStart);

    // ── Step 7: Animation complete ──
    const totalEdgeTime = 80 * EDGE_STAGGER_MS;
    const t_done = setTimeout(() => {
      setAnimPhase(ANIM_PHASE.DONE);
      fgRef.current?.zoomToFit(800, 50);
    }, totalNodeTime + PAUSE_DURATION + totalEdgeTime + 100);
    animTimers.current.push(t_done);

    return () => animTimers.current.forEach(t => clearTimeout(t));
  }, [graphData]);

  // ═══════════════ Node drag — pin ═══════════════
  const handleNodeDragEnd = useCallback((node) => {
    node.fx = node.x; node.fy = node.y;
  }, []);

  // ═══════════════ Edge hover ═══════════════
  const handleLinkHover = useCallback((link) => {
    setHoveredLink(link || null);
    if (onLinkHover) onLinkHover(link || null);
  }, [onLinkHover]);

  const buildLinkLabel = useCallback((link) => {
    const srcName = link.source_name || link.source?.name || 'Unknown';
    const tgtName = link.target_name || link.target?.name || 'Unknown';
    const relType = RELATIONSHIP_LABELS[link.relationship_type] || link.relationship_type || 'Unknown';
    const relClr  = RELATIONSHIP_COLORS[link.relationship_type] || '#78909C';
    const weight  = link.weight ? link.weight.toFixed(3) : '—';
    return `<div style="background:rgba(10,10,30,0.96);color:#fff;padding:10px 14px;border-radius:8px;
      font-size:13px;line-height:1.6;box-shadow:0 4px 24px rgba(0,0,0,0.55);
      border-left:3px solid ${relClr};max-width:300px;">
      <div style="font-size:14px;font-weight:700;margin-bottom:4px;">
        ${srcName} <span style="color:#666;font-weight:400;">→</span> ${tgtName}
      </div>
      <div style="display:flex;align-items:center;gap:5px;">
        <span style="color:${relClr};font-size:16px;">●</span><span>${relType}</span>
      </div>
      <div style="color:#888;font-size:11px;margin-top:4px;">Weight: ${weight}</div>
    </div>`;
  }, []);

  // ── Edge colour ──
  const getLinkColor = useCallback((link) => {
    if (hoveredLink && link === hoveredLink) return '#FFFFFF';
    if (simMaps) {
      const srcId = typeof link.source === 'object' ? link.source.id : link.source;
      const tgtId = typeof link.target === 'object' ? link.target.id : link.target;

      // Edge removal: highlight the severed edge in red
      if (simMaps.shockType === 'edge_removal' && simMaps.sourceId) {
        if (srcId === simMaps.sourceId && tgtId === simMaps.shockedId) {
          return `rgba(255,76,76,${0.7 + pulsePhase * 0.3})`;
        }
      }

      // Node removal: edges from shocked node pulse red
      if (srcId === simMaps.shockedId || tgtId === simMaps.shockedId) {
        return `rgba(255,76,76,${0.5 + pulsePhase * 0.5})`;
      }
    }
    return RELATIONSHIP_COLORS[link.relationship_type] || RELATIONSHIP_COLORS.unknown;
  }, [hoveredLink, simMaps, pulsePhase]);

  const getLinkWidth = useCallback((link) => {
    const base = link.weight ? Math.max(0.5, link.weight * 2) : 1;
    if (hoveredLink && link === hoveredLink) return base + 2.5;
    if (simMaps) {
      const srcId = typeof link.source === 'object' ? link.source.id : link.source;
      const tgtId = typeof link.target === 'object' ? link.target.id : link.target;

      // Edge removal: thicken the severed edge
      if (simMaps.shockType === 'edge_removal' && simMaps.sourceId) {
        if (srcId === simMaps.sourceId && tgtId === simMaps.shockedId) return base + 2.5;
      }

      if (srcId === simMaps.shockedId || tgtId === simMaps.shockedId) return base + 1.5;
    }
    return base;
  }, [hoveredLink, simMaps]);

  // ── Link visibility: controlled during boot animation ──
  const getLinkVisibility = useCallback((link) => {
    if (animPhase === ANIM_PHASE.DONE || animPhase === ANIM_PHASE.IDLE) return true;
    if (animPhase === ANIM_PHASE.NODES || animPhase === ANIM_PHASE.PAUSE) return false;
    if (animPhase === ANIM_PHASE.EDGES) {
      const linkIdx = graphData.links.indexOf(link);
      const posInBFS = sortedEdgesRef.current.indexOf(linkIdx);
      return posInBFS !== -1 && posInBFS < visibleEdgeCount;
    }
    return true;
  }, [animPhase, graphData.links, visibleEdgeCount]);

  // ── Particle count ──
  const getLinkParticles = useCallback((link) => {
    if (animPhase !== ANIM_PHASE.DONE && animPhase !== ANIM_PHASE.IDLE) return 0;
    if (simMaps) {
      const srcId = typeof link.source === 'object' ? link.source.id : link.source;
      const tgtId = typeof link.target === 'object' ? link.target.id : link.target;

      // Edge removal: particles on the severed edge
      if (simMaps.shockType === 'edge_removal' && simMaps.sourceId) {
        if (srcId === simMaps.sourceId && tgtId === simMaps.shockedId) return 5;
      }

      if (srcId === simMaps.shockedId) return 4;
    }
    return 1;
  }, [simMaps, animPhase]);

  const getLinkParticleColor = useCallback((link) => {
    if (simMaps) {
      const srcId = typeof link.source === 'object' ? link.source.id : link.source;
      const tgtId = typeof link.target === 'object' ? link.target.id : link.target;

      // Edge removal: amber particles on the severed edge
      if (simMaps.shockType === 'edge_removal' && simMaps.sourceId) {
        if (srcId === simMaps.sourceId && tgtId === simMaps.shockedId) return '#FFB300';
      }

      if (srcId === simMaps.shockedId) return '#FF4C4C';
    }
    return RELATIONSHIP_COLORS[link.relationship_type] || '#78909C';
  }, [simMaps]);

  // ═══════════════ Custom node renderer ═══════════════
  const paintNode = useCallback((node, ctx) => {
    // During node-burst phase: only draw visible nodes
    if (animPhase === ANIM_PHASE.NODES || animPhase === ANIM_PHASE.PAUSE) {
      if (!visibleNodeIds.has(node.id)) return;
    }

    const baseR = 2 + (node.betweenness || 0) * 100;

    // ── SIMULATION MODE ──
    if (simMaps) {
      const isShocked  = node.id === simMaps.shockedId;
      const isSource   = simMaps.sourceId && node.id === simMaps.sourceId;
      const isEdgeRemoval = simMaps.shockType === 'edge_removal';
      const affData    = simMaps.affectedMap[node.id];
      const isAffected = !!affData;

      // ── SHOCKED NODE ──
      if (isShocked) {
        if (isEdgeRemoval) {
          // Edge removal target: dashed cyan ring (surgical, not explosive)
          const ringR = baseR + 4;
          ctx.beginPath();
          ctx.arc(node.x, node.y, ringR, 0, 2 * Math.PI);
          ctx.fillStyle = 'rgba(0, 200, 255, 0.08)';
          ctx.fill();

          ctx.beginPath();
          ctx.arc(node.x, node.y, baseR, 0, 2 * Math.PI);
          const isDefault = node.pd !== undefined ? node.pd >= 0.5 : node.default_label === 1;
          ctx.fillStyle = isDefault ? NODE_DEFAULT_COLOR : NODE_HEALTHY_COLOR;
          ctx.fill();

          // Dashed cyan border
          ctx.setLineDash([3, 3]);
          ctx.beginPath();
          ctx.arc(node.x, node.y, baseR + 1, 0, 2 * Math.PI);
          ctx.strokeStyle = `rgba(0, 200, 255, ${0.6 + pulsePhase * 0.4})`;
          ctx.lineWidth = 2;
          ctx.stroke();
          ctx.setLineDash([]);

          drawNodeTicker(ctx, node, baseR, '#00C8FF');
        } else {
          // Node removal: explosive pulsating red-to-black (existing behavior)
          const waveR = baseR * 2 + pulsePhase * baseR * 3;
          ctx.beginPath();
          ctx.arc(node.x, node.y, waveR, 0, 2 * Math.PI);
          ctx.strokeStyle = `rgba(255,76,76,${0.6 * (1 - pulsePhase)})`;
          ctx.lineWidth = 2;
          ctx.stroke();

          ctx.beginPath();
          ctx.arc(node.x, node.y, baseR * 2 + 3, 0, 2 * Math.PI);
          ctx.fillStyle = `rgba(255,76,76,${0.3 + pulsePhase * 0.3})`;
          ctx.fill();

          ctx.beginPath();
          ctx.arc(node.x, node.y, baseR * 2, 0, 2 * Math.PI);
          ctx.fillStyle = lerpColor('#FF0000', '#220000', pulsePhase);
          ctx.fill();
          ctx.strokeStyle = '#FF4C4C';
          ctx.lineWidth = 2;
          ctx.stroke();
          drawNodeTicker(ctx, node, baseR * 2, '#FF4C4C');
        }
        return;
      }

      // ── SOURCE NODE (edge removal only) ──
      if (isSource && isEdgeRemoval) {
        // Small pulsating amber indicator — this company still exists,
        // it just stopped supplying to the target
        const amberR = baseR + 2;
        ctx.beginPath();
        ctx.arc(node.x, node.y, amberR + 2, 0, 2 * Math.PI);
        ctx.fillStyle = `rgba(255, 179, 0, ${0.12 + pulsePhase * 0.15})`;
        ctx.fill();

        ctx.beginPath();
        ctx.arc(node.x, node.y, amberR, 0, 2 * Math.PI);
        const isDefault = node.pd !== undefined ? node.pd >= 0.5 : node.default_label === 1;
        ctx.fillStyle = isDefault ? NODE_DEFAULT_COLOR : NODE_HEALTHY_COLOR;
        ctx.fill();
        ctx.strokeStyle = `rgba(255, 179, 0, ${0.6 + pulsePhase * 0.4})`;
        ctx.lineWidth = 1.5;
        ctx.stroke();

        drawNodeTicker(ctx, node, amberR, '#FFB300');
        return;
      }

      if (isAffected) {
        const t = Math.min(affData.delta_pd / simMaps.maxDelta, 1);
        const fillColor = t < 0.5
          ? lerpColor('#D6E2FF', '#FFB300', t * 2)
          : lerpColor('#FFB300', '#FF4C4C', (t - 0.5) * 2);
        const haloAlpha = 0.15 + t * 0.5;
        const nodeR = baseR + t * baseR * 0.8;

        ctx.beginPath();
        ctx.arc(node.x, node.y, nodeR + 3, 0, 2 * Math.PI);
        ctx.fillStyle = t < 0.5 ? `rgba(255,179,0,${haloAlpha})` : `rgba(255,76,76,${haloAlpha})`;
        ctx.fill();

        ctx.beginPath();
        ctx.arc(node.x, node.y, nodeR, 0, 2 * Math.PI);
        ctx.fillStyle = fillColor;
        ctx.fill();
        ctx.strokeStyle = t < 0.5 ? '#FFB300' : '#FF4C4C';
        ctx.lineWidth = 0.8;
        ctx.stroke();
        drawNodeTicker(ctx, node, nodeR, t < 0.5 ? '#FFB300' : '#FF4C4C');
        return;
      }

      const isDefault = node.pd !== undefined ? node.pd >= 0.5 : node.default_label === 1;
      ctx.beginPath();
      ctx.arc(node.x, node.y, baseR, 0, 2 * Math.PI);
      ctx.fillStyle = isDefault ? 'rgba(255,76,76,0.18)' : 'rgba(160,180,220,0.18)';
      ctx.fill();
      drawNodeTicker(ctx, node, baseR, isDefault ? 'rgba(255,76,76,0.35)' : 'rgba(160,180,220,0.35)');
      return;
    }

    // ── NORMAL MODE ──
    const isDefault   = node.pd !== undefined ? node.pd >= 0.5 : node.default_label === 1;
    const fillColor   = isDefault ? NODE_DEFAULT_COLOR  : NODE_HEALTHY_COLOR;
    const borderColor = isDefault ? NODE_DEFAULT_BORDER : NODE_HEALTHY_BORDER;

    // Selected node highlight ring
    if (selectedCompany && node.id === selectedCompany.id) {
      ctx.beginPath();
      ctx.arc(node.x, node.y, baseR + 3.5, 0, 2 * Math.PI);
      ctx.strokeStyle = '#1a56db';
      ctx.lineWidth = 1.8;
      ctx.stroke();
    }

    // Outer glow
    ctx.beginPath();
    ctx.arc(node.x, node.y, baseR + 1.5, 0, 2 * Math.PI);
    ctx.fillStyle = isDefault ? 'rgba(255,82,82,0.25)' : 'rgba(0,230,118,0.18)';
    ctx.fill();

    // Main circle
    ctx.beginPath();
    ctx.arc(node.x, node.y, baseR, 0, 2 * Math.PI);
    ctx.fillStyle = fillColor;
    ctx.fill();
    ctx.strokeStyle = borderColor;
    ctx.lineWidth = 0.6;
    ctx.stroke();

    // Ticker label inside the node
    drawNodeTicker(ctx, node, baseR, borderColor);
  }, [simMaps, pulsePhase, selectedCompany, animPhase, visibleNodeIds]);

  // ═══════════════ Node click ═══════════════
  const handleNodeClick = useCallback((node) => {
    if (onNodeClick) onNodeClick(node);
  }, [onNodeClick]);

  // (Panel is now static — no drag or resize handlers needed)

  if (!graphData || graphData.nodes.length === 0) return null;

  const activeRelTypes = [...new Set(graphData.links.map(l => l.relationship_type))];
  const isAnimating = animPhase !== ANIM_PHASE.DONE && animPhase !== ANIM_PHASE.IDLE;

  return (
    <div
      ref={containerRef}
      style={{
        position: 'relative',
        height: '100%',
        width: '100%',
        overflow: 'hidden',
        background: '#F8F9FC',
        // Faint dot-grid for subtle texture / distinction
        backgroundImage: 'radial-gradient(circle, rgba(180,195,220,0.35) 1px, transparent 1px)',
        backgroundSize: '28px 28px',
      }}
    >
      {/* CSS for edge panel fade-in animation */}
      <style>{`
        @keyframes edgePanelIn {
          from { opacity: 0; transform: translateY(-4px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      {/* ── Simulation mode banner ── */}
      {simMaps && (
        <div style={{
          position: 'absolute', top: 12, left: '50%', transform: 'translateX(-50%)',
          zIndex: 15, pointerEvents: 'none',
          background: 'rgba(220,38,38,0.10)', border: '1px solid rgba(220,38,38,0.30)',
          borderRadius: 8, padding: '5px 16px', fontSize: 11, fontWeight: 700,
          color: '#dc2626', letterSpacing: '0.5px',
        }}>
          ⚡ SIMULATION ACTIVE — Contagion Cascade Visualisation
        </div>
      )}

      {/* ── Boot animation progress indicator ── */}
      {isAnimating && (
        <div style={{
          position: 'absolute', bottom: 14, left: '50%', transform: 'translateX(-50%)',
          zIndex: 15, pointerEvents: 'none',
          background: 'rgba(10,10,18,0.88)',
          border: '1px solid rgba(255,255,255,0.08)',
          borderRadius: 6, padding: '5px 14px', fontSize: 10, fontWeight: 600,
          color: 'rgba(255,255,255,0.5)', letterSpacing: '0.8px',
          textTransform: 'uppercase',
        }}>
          {animPhase === ANIM_PHASE.NODES && `◉ Mapping ${visibleNodeIds.size} / ${graphData.nodes.length} companies…`}
          {animPhase === ANIM_PHASE.PAUSE && '◉ Network topology loaded…'}
          {animPhase === ANIM_PHASE.EDGES && `◉ Tracing ${visibleEdgeCount} / ${graphData.links.length} supply chain links…`}
        </div>
      )}



      {/* ════════════ STATIC NODE STATUS + RELATIONSHIP LEGEND (bottom-LEFT, white) ════════════ */}
      <div
        style={{
          position: 'absolute',
          bottom: 10,
          left: 12,        /* ← bottom-LEFT: never overlaps with edge detail (top-right) */
          zIndex: 20,
          pointerEvents: 'none',
          background: '#ffffff',
          border: '1px solid #E2E8F0',
          borderRadius: '8px',
          padding: '9px 13px',
          fontSize: '11px',
          color: '#374151',
          lineHeight: '1.85',
          boxShadow: '0 2px 10px rgba(0,0,0,0.07)',
          minWidth: 155,
          opacity: isAnimating ? 0 : 1,
          transition: 'opacity 0.8s ease',
        }}
      >
        {/* ── Node Status ── */}
        <div style={{ fontWeight: 700, fontSize: '10px', color: '#6b7280',
                      letterSpacing: '0.7px', textTransform: 'uppercase', marginBottom: '5px' }}>
          {simMaps ? 'Simulation Key' : 'Node Status'}
        </div>
        {simMaps ? (
          <>
            <LegendDot color="#FF0000" glow label="Shocked (defaulted)" />
            <LegendDot color="#FF4C4C" label="High contagion impact" />
            <LegendDot color="#FFB300" label="Medium impact" />
            <LegendDot color="rgba(160,180,220,0.5)" label="Unaffected (dimmed)" />
          </>
        ) : (
          <>
            <LegendDot color={NODE_HEALTHY_COLOR} border={NODE_HEALTHY_BORDER} label="Healthy company" />
            <LegendDot color={NODE_DEFAULT_COLOR} border={NODE_DEFAULT_BORDER} label="Defaulted company" />
          </>
        )}

        {/* ── Separator ── */}
        <div style={{ borderTop: '1px solid #E2E8F0', margin: '7px 0 6px' }} />

        {/* ── Relationship Colour Legend ── */}
        <div style={{ fontWeight: 700, fontSize: '10px', color: '#6b7280',
                      letterSpacing: '0.7px', textTransform: 'uppercase', marginBottom: '5px' }}>
          Edge Types
        </div>
        {activeRelTypes.map(rt => (
          <div key={rt} style={{ display: 'flex', alignItems: 'center', gap: '7px', marginBottom: '2px' }}>
            <span style={{
              display: 'inline-block', width: 16, height: 3, borderRadius: '2px', flexShrink: 0,
              background: RELATIONSHIP_COLORS[rt] || RELATIONSHIP_COLORS.unknown,
            }} />
            <span style={{ fontSize: '10.5px', color: '#374151' }}>{RELATIONSHIP_LABELS[rt] || rt}</span>
          </div>
        ))}
      </div>

      {/* ════════════ GRAPH CANVAS ════════════ */}
      {dimensions.width > 0 && dimensions.height > 0 && (
        <ForceGraph2D
          ref={fgRef}
          width={dimensions.width}
          height={dimensions.height}
          graphData={graphData}
          nodeLabel="name"
          nodeCanvasObject={paintNode}
          nodePointerAreaPaint={(node, color, ctx) => {
            const r = 2 + (node.betweenness || 0) * 100;
            const hitR = (simMaps && node.id === simMaps.shockedId) ? r * 2 + 4 : r + 2;
            ctx.beginPath();
            ctx.arc(node.x, node.y, hitR, 0, 2 * Math.PI);
            ctx.fillStyle = color;
            ctx.fill();
          }}
          onNodeClick={handleNodeClick}
          linkColor={getLinkColor}
          linkWidth={getLinkWidth}
          linkVisibility={getLinkVisibility}
          linkHoverPrecision={4}
          onLinkHover={handleLinkHover}
          linkDirectionalArrowLength={4}
          linkDirectionalArrowRelPos={1}
          linkDirectionalParticles={getLinkParticles}
          linkDirectionalParticleWidth={2}
          linkDirectionalParticleSpeed={simMaps ? 0.008 : 0.004}
          linkDirectionalParticleColor={getLinkParticleColor}
          onNodeDragEnd={handleNodeDragEnd}
          enableNodeDrag={true}
          enableZoomPanInteraction={true}
          backgroundColor="#F8F9FC"
          d3AlphaDecay={0.02}
          d3VelocityDecay={0.3}
          warmupTicks={60}
          cooldownTicks={120}
          onEngineStop={() => {
            // Fire zoomToFit only on the very first engine-stop after data loads.
            // This guarantees the graph is centered once node positions are real.
            if (!hasInitialFitRef.current) {
              hasInitialFitRef.current = true;
              requestAnimationFrame(() => fgRef.current?.zoomToFit(600, 50));
            }
          }}
        />
      )}
    </div>
  );
});

NetworkGraph.displayName = 'NetworkGraph';

// ══════════════════════════════════════════════════════════════
//  EdgeDetailView — shown inside the multipurpose panel on hover
// ══════════════════════════════════════════════════════════════

const REL_EXPLANATIONS = {
  supply:                       'General supply: one company provides goods or services to the other.',
  tier1_supplier:               'Tier-1 Supplier: directly feeds the main manufacturer — the closest link.',
  tier2_supplier_battery:       'Tier-2 Battery: supplies battery parts to a Tier-1 supplier (two steps from manufacturer).',
  tier2_supplier_semiconductor: 'Tier-2 Semiconductor: supplies chips to a Tier-1 supplier (two steps from manufacturer).',
  ownership:                    'Ownership: one company owns or controls the other (e.g. parent–subsidiary).',
  trade_credit:                 'Trade Credit: buyer receives goods now and pays later — a short-term financing arrangement.',
  raw_material_supplier:        'Raw Material Supplier: provides unprocessed inputs (metals, chemicals, etc.) at the base of the chain.',
  unknown:                      'Relationship type not classified in this dataset.',
};

function EdgeDetailView({ link }) {
  const srcName = link.source_name || link.source?.name || (typeof link.source === 'string' ? link.source : '?');
  const tgtName = link.target_name || link.target?.name || (typeof link.target === 'string' ? link.target : '?');
  const relType = link.relationship_type || 'unknown';
  const relColor = RELATIONSHIP_COLORS[relType] || RELATIONSHIP_COLORS.unknown;
  const relLabel = RELATIONSHIP_LABELS[relType] || relType;
  const relExplanation = REL_EXPLANATIONS[relType] || '';
  const weight = link.weight != null ? link.weight.toFixed(3) : '—';

  return (
    <div style={{ fontSize: '11px', color: '#374151', lineHeight: 1.6 }}>

      {/* Source → Target */}
      <div style={{ marginBottom: 9 }}>
        <div style={{ fontSize: '9px', fontWeight: 700, textTransform: 'uppercase',
                      letterSpacing: '0.6px', color: '#94a3b8', marginBottom: 3 }}>Connection</div>
        <div style={{ fontWeight: 600, color: '#111827', fontSize: '11.5px',
                      wordBreak: 'break-word', lineHeight: 1.3 }}>{srcName}</div>
        <div style={{ color: '#94a3b8', fontSize: '10px', margin: '3px 0' }}>→</div>
        <div style={{ fontWeight: 600, color: '#111827', fontSize: '11.5px',
                      wordBreak: 'break-word', lineHeight: 1.3 }}>{tgtName}</div>
      </div>

      {/* Relationship type */}
      <div style={{ marginBottom: 9 }}>
        <div style={{ fontSize: '9px', fontWeight: 700, textTransform: 'uppercase',
                      letterSpacing: '0.6px', color: '#94a3b8', marginBottom: 4 }}>Relationship</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
          <span style={{
            display: 'inline-block', width: 10, height: 10, borderRadius: '50%',
            background: relColor, flexShrink: 0,
          }} />
          <span style={{ color: '#1e293b', fontWeight: 700, fontSize: '11px' }}>{relLabel}</span>
        </div>
        {relExplanation && (
          <div style={{ color: '#6b7280', fontSize: '10px', lineHeight: 1.45 }}>{relExplanation}</div>
        )}
      </div>

      {/* Weight */}
      <div>
        <div style={{ fontSize: '9px', fontWeight: 700, textTransform: 'uppercase',
                      letterSpacing: '0.6px', color: '#94a3b8', marginBottom: 2 }}>Weight</div>
        <div style={{ fontSize: '15px', fontWeight: 800, color: '#1a56db', letterSpacing: '-0.3px' }}>{weight}</div>
        <div style={{ color: '#9ca3af', fontSize: '9.5px', marginTop: 1 }}>0 = weak · 1 = critical</div>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════
//  LegendDot — compact coloured dot + label row
// ══════════════════════════════════════════════════════════════

function LegendDot({ color, border, glow, label }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 2 }}>
      <span style={{
        display: 'inline-block',
        width: 9, height: 9,
        borderRadius: '50%',
        background: color,
        border: border ? `1.5px solid ${border}` : 'none',
        boxShadow: glow ? `0 0 7px ${color}` : 'none',
        flexShrink: 0,
      }} />
      <span style={{ fontSize: '11px', color: '#374151' }}>{label}</span>
    </div>
  );
}

export default NetworkGraph;
