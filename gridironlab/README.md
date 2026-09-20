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
`fantasy_football.gold.predictions`. Writing a new week updates the UI without
a frontend code change — restart the API (or wait out its 1-hour cache), then
refresh the browser.

## Deploy

Production is served from S3 + CloudFront at
`https://d1mkvupgst3eb9.cloudfront.net`. The same distribution proxies `/api/*`
to the ECS Fargate API, so live data is same-origin (no CORS).
`.env.production` sets `VITE_API_URL` to the CloudFront URL for production
builds. To ship a new build:

```bash
npm run build
aws s3 sync dist s3://gridiron-lab --delete
aws cloudfront create-invalidation --distribution-id E3PRKK3R468KYB --paths '/*'
```

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
