import React from 'react';
import './EdgeInspector.css';

export const RELATIONSHIP_COLORS = {
  supply:                       '#00F5FF',
  tier1_supplier:               '#FFD500',
  raw_material_supplier:        '#4C6FFF',
  tier2_supplier_battery:       '#FF7A00',
  tier2_supplier_semiconductor: '#39FF14',
  trade_credit:                 '#B388FF',
  ownership:                    '#FF4FD8',
  unknown:                      '#78909C',
};

export const RELATIONSHIP_LABELS = {
  supply:                       'Supply',
  tier1_supplier:               'Tier-1 Supplier',
  tier2_supplier_battery:       'Tier-2 — Battery',
  tier2_supplier_semiconductor: 'Tier-2 — Semiconductor',
  ownership:                    'Ownership',
  trade_credit:                 'Trade Credit',
  raw_material_supplier:        'Raw Material Supplier',
  unknown:                      'Unknown',
};

export const REL_EXPLANATIONS = {
  supply:                       'General supply: one company provides goods or services to the other.',
  tier1_supplier:               'Tier-1 Supplier: directly feeds the main manufacturer — the closest link.',
  tier2_supplier_battery:       'Tier-2 Battery: supplies battery parts to a Tier-1 supplier (two steps from manufacturer).',
  tier2_supplier_semiconductor: 'Tier-2 Semiconductor: supplies chips to a Tier-1 supplier (two steps from manufacturer).',
  ownership:                    'Ownership: one company owns or controls the other (e.g. parent–subsidiary).',
  trade_credit:                 'Trade Credit: buyer receives goods now and pays later — a short-term financing arrangement.',
  raw_material_supplier:        'Raw Material Supplier: provides unprocessed inputs (metals, chemicals, etc.) at the base of the chain.',
  unknown:                      'Relationship type not classified in this dataset.',
};

export default function EdgeInspector({ link }) {
  if (!link) {
    return (
      <div className="edge-inspector edge-inspector--idle">
        <div className="edge-inspector__idle-content">
          <span className="edge-inspector__idle-icon">↗</span>
          <span className="edge-inspector__idle-text">
            Hover over any network connection to inspect counterparties &amp; credit weight
          </span>
        </div>
      </div>
    );
  }

  const srcName = link.source_name || link.source?.name || (typeof link.source === 'string' ? link.source : '?');
  const tgtName = link.target_name || link.target?.name || (typeof link.target === 'string' ? link.target : '?');
  const relType = link.relationship_type || 'unknown';
  const relColor = RELATIONSHIP_COLORS[relType] || RELATIONSHIP_COLORS.unknown;
  const relLabel = RELATIONSHIP_LABELS[relType] || relType;
  const relExplanation = REL_EXPLANATIONS[relType] || '';
  const weight = link.weight != null ? link.weight.toFixed(3) : '—';

  return (
    <div className="edge-inspector edge-inspector--active">
      <div className="edge-inspector__header">
        <span
          className="edge-inspector__badge"
          style={{
            backgroundColor: `${relColor}18`,
            color: relColor,
            borderColor: `${relColor}50`,
          }}
        >
          <span className="edge-inspector__dot" style={{ backgroundColor: relColor }} />
          {relLabel}
        </span>
        <span className="edge-inspector__weight-tag">
          <span className="edge-inspector__weight-label">Weight</span>
          <span className="edge-inspector__weight-val">{weight}</span>
        </span>
      </div>

      <div className="edge-inspector__content">
        {/* Source -> Target */}
        <div className="edge-inspector__route">
          <div className="edge-inspector__node-box">
            <span className="edge-inspector__node-role">Supplier / Source</span>
            <span className="edge-inspector__node-name" title={srcName}>{srcName}</span>
          </div>
          <div className="edge-inspector__arrow-box">
            <span className="edge-inspector__arrow">→</span>
          </div>
          <div className="edge-inspector__node-box">
            <span className="edge-inspector__node-role">Buyer / Target</span>
            <span className="edge-inspector__node-name" title={tgtName}>{tgtName}</span>
          </div>
        </div>

        {/* Explanation */}
        {relExplanation && (
          <div className="edge-inspector__desc">
            {relExplanation}
          </div>
        )}
      </div>
    </div>
  );
}
