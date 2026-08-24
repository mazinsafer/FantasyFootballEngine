# Gridiron Lab — Frontend

React + TypeScript dashboard for the Fantasy Football ML Prediction Engine.
Displays weekly full-PPR projections, model insights, rankings, team rosters,
and actual weekly results served by the FastAPI backend in `../api`.

## Run

```bash
npm install
npm run dev
```

The app fetches from the FastAPI backend at `http://localhost:8000` by default
(override with `VITE_API_URL` in a `.env` file). When the API is unreachable,
it falls back to a bundled 2025 Week 17 sample slate — the sidebar shows
"Sample data" vs "Live data" accordingly.

The dashboard always displays the **latest** `(season, week)` in
`fantasy_football.gold.predictions`. Writing a new week (including 2026 Week 1)
updates the UI without a frontend code change — restart or wait out the API's
1-hour cache, then refresh the browser.

## Structure

```
src/
├── components/   reusable UI — Sidebar, TopBar, PlayerIdentity, InsightPanel, …
├── pages/        one file per route — HomePage, RankingsPage, PlayerDetailPage, …
├── types/        interfaces only — Player, Prediction, Team
├── services/     API calls + sample fallback, no UI logic
├── hooks/        usePredictions, usePlayerDetail, useTeamRoster
├── styles/       design tokens + global CSS — tokens.css
├── App.tsx       root component, handles routing
├── main.tsx      entry point
└── index.css     @import "tailwindcss" only
```

## Design system

Dark, data-dense analytics UI. Color is semantic, never decorative:

- **Lime** `#C6E36B` — projections and primary actions
- **Teal** `#56C4D4` — model insight only
- **Green** `#5FBF87` — positive outcomes
- **Red** `#E05C70` — negative outcomes / risk
- Everything else is neutral. Hairline dividers over boxes; tabular numerals
  (Inter) for statistics.
