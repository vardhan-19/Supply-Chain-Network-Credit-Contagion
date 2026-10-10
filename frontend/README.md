# SCNCC Web Dashboard

Interactive 2D force-directed WebGL and Canvas dashboard for supply chain credit contagion visualization and stress testing.

## Tech Stack
- **Framework:** React 19 + Vite
- **Graph Engine:** `react-force-graph-2d` + D3-force
- **Styling:** CSS variables & responsive layout
- **Deployment:** GitHub Pages automated via GitHub Actions

## Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Structure
- `src/NetworkGraph.jsx`: Canvas force-directed graph renderer with live contagion wave propagation.
- `src/components/`: Modular cockpit components (ShockSimulator, RiskRankings, CompanyDetail, EdgeInspector, TopBar).
- `src/services/api.js`: Unified API service connecting to FastAPI backend with static cache fallback for offline/demo operation.

