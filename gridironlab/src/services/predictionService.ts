import { getJson, type DataSource } from './api'
import type { Prediction } from '../types/Prediction'
import type { Position } from '../types/Player'
import { samplePredictions } from './sampleData'

export interface PredictionsResult {
  items: Prediction[]
  source: DataSource
  season: number
  week: number
}

interface ApiPredictionRow {
  player_id: string
  player_name: string
  position: string
  recent_team?: string | null
  team?: string | null
  opponent?: string | null
  is_home?: boolean | number | null
  projected_ppr?: number | null
  actual_ppr?: number | null
  fantasy_points_3wk_avg?: number | null
  depth_chart_rank?: number | null
  prev_season_ppg?: number | null
  implied_total?: number | null
  team_spread?: number | null
  team_win_prob?: number | null
  opp_def_ppg_allowed?: number | null
  is_dome?: boolean | number | null
  is_bad_weather?: boolean | number | null
  insight?: string | null
  season?: number
  week?: number
}

const POSITIONS: Position[] = ['QB', 'RB', 'WR', 'TE']

function mapRow(r: ApiPredictionRow): Prediction {
  return {
    playerId: r.player_id,
    playerName: r.player_name,
    position: POSITIONS.includes(r.position as Position) ? (r.position as Position) : 'WR',
    team: r.recent_team ?? r.team ?? '—',
    opponent: r.opponent ?? '—',
    isHome: Boolean(r.is_home),
    projectedPpr: r.projected_ppr ?? 0,
    actualPpr: r.actual_ppr ?? null,
    threeWkAvg: r.fantasy_points_3wk_avg ?? null,
    depthRank: r.depth_chart_rank ?? null,
    prevSeasonPpg: r.prev_season_ppg ?? null,
    impliedTotal: r.implied_total ?? null,
    spread: r.team_spread ?? null,
    winProb: r.team_win_prob ?? null,
    oppDefPprAllowed: r.opp_def_ppg_allowed ?? null,
    isDome: Boolean(r.is_dome),
    isBadWeather: Boolean(r.is_bad_weather),
    insight: r.insight ?? null,
    season: r.season ?? 0,
    week: r.week ?? 0,
  }
}

let cached: Promise<PredictionsResult> | null = null

async function load(): Promise<PredictionsResult> {
  try {
    const res = await getJson<{ items: ApiPredictionRow[] }>('/api/predictions?limit=500')
    const items = res.items
      .map(mapRow)
      .sort((a, b) => b.projectedPpr - a.projectedPpr)
    if (items.length === 0) throw new Error('empty predictions')
    return { items, source: 'live', season: items[0].season, week: items[0].week }
  } catch {
    return { items: samplePredictions, source: 'sample', season: 2025, week: 17 }
  }
}

/** Predictions for the latest week. Live responses are cached for the tab;
 *  a sample fallback is not, so a later retry can still hit a warmed-up API. */
export function fetchPredictions(): Promise<PredictionsResult> {
  if (!cached) {
    cached = load().then((result) => {
      if (result.source !== 'live') cached = null
      return result
    })
  }
  return cached
}
