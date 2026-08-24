import { getJson, type DataSource } from './api'
import type { PlayerCareer, PlayerWeekRow } from '../types/Player'
import { sampleCareer, sampleHistory } from './sampleData'

export interface PlayerDetailResult {
  history: PlayerWeekRow[]
  career: PlayerCareer | null
  source: DataSource
}

interface ApiPlayerWeek {
  season: number
  week: number
  opponent?: string | null
  snap_share?: number | null
  targets?: number | null
  air_yards_share?: number | null
  wopr?: number | null
  fantasy_points_ppr?: number | null
}

interface ApiPlayerDetail {
  career?: {
    games_played?: number | null
    career_ppg?: number | null
    career_high?: number | null
  } | null
}

function mapWeek(r: ApiPlayerWeek): PlayerWeekRow {
  return {
    season: r.season,
    week: r.week,
    opponent: r.opponent ?? '—',
    snapPct: r.snap_share != null ? Math.round(r.snap_share * 100) : null,
    targets: r.targets ?? null,
    airYardsShare: r.air_yards_share ?? null,
    wopr: r.wopr ?? null,
    ppr: r.fantasy_points_ppr ?? 0,
  }
}

export async function fetchPlayerDetail(playerId: string): Promise<PlayerDetailResult> {
  try {
    const [detail, history] = await Promise.all([
      getJson<ApiPlayerDetail>(`/api/players/${encodeURIComponent(playerId)}`),
      getJson<{ items: ApiPlayerWeek[] }>(
        `/api/players/${encodeURIComponent(playerId)}/history?limit=500`,
      ),
    ])
    const career: PlayerCareer | null =
      detail.career?.games_played != null
        ? {
            gamesPlayed: detail.career.games_played,
            careerPpg: detail.career.career_ppg ?? 0,
            careerHigh: detail.career.career_high ?? 0,
          }
        : null
    const rows = history.items
      .map(mapWeek)
      .sort((a, b) => a.season - b.season || a.week - b.week)
    return { history: rows, career, source: 'live' }
  } catch {
    return { history: sampleHistory, career: sampleCareer, source: 'sample' }
  }
}
