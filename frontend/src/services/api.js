/**
 * services/api.js
 * ================
 * Centralized API service layer for all backend communication.
 * All URLs are relative — Vite proxy routes them to http://localhost:8001.
 */

/**
 * Fetch the full graph data (nodes + links) with GNN predictions attached.
 * @returns {Promise<{nodes: Array, links: Array}>}
 */
export async function fetchGraphData() {
  const res = await fetch('/graph');
  if (!res.ok) {
    throw new Error(`Failed to fetch graph data: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

/**
 * Run a contagion simulation by shocking a target company.
 * @param {string} companyId  - UUID of the company to shock
 * @param {string} shockType  - "node_removal" (default) or "edge_removal"
 * @param {string|null} sourceCompanyId - UUID of the source company (required for edge_removal)
 * @returns {Promise<{shocked_company: string, total_systemic_loss_increase: number, affected_nodes: Array}>}
 */
export async function runSimulation(companyId, shockType = 'node_removal', sourceCompanyId = null) {
  const res = await fetch('/simulate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      target_company_id: companyId,
      shock_type: shockType,
      ...(sourceCompanyId && { source_company_id: sourceCompanyId }),
    }),
  });
  if (!res.ok) {
    const errorBody = await res.text().catch(() => '');
    throw new Error(
      `Simulation failed: ${res.status} ${res.statusText}${errorBody ? ` — ${errorBody}` : ''}`
    );
  }
  const data = await res.json();
  if (data && data.error) {
    throw new Error(data.error);
  }
  return data;
}

/**
 * Fetch GNN default-probability predictions for every company.
 * @returns {Promise<Array<{company_id: string, company_name: string, pd: number, risk_tier: string}>>}
 */
export async function fetchPredictions() {
  const res = await fetch('/predict', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch predictions: ${res.status} ${res.statusText}`);
  }
  return res.json();
}
