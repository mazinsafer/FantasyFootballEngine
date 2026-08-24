import { getJson, type DataSource } from './api'
import type { RosterEntry } from '../types/Team'
import type { Position } from '../types/Player'
import { sampleRosterKC, samplePredictions } from './sampleData'

export const TEAM_NAMES: Record<string, string> = {
  ARI: 'Arizona Cardinals', ATL: 'Atlanta Falcons', BAL: 'Baltimore Ravens',
  BUF: 'Buffalo Bills', CAR: 'Carolina Panthers', CHI: 'Chicago Bears',
  CIN: 'Cincinnati Bengals', CLE: 'Cleveland Browns', DAL: 'Dallas Cowboys',
  DEN: 'Denver Broncos', DET: 'Detroit Lions', GB: 'Green Bay Packers',
  HOU: 'Houston Texans', IND: 'Indianapolis Colts', JAX: 'Jacksonville Jaguars',
  KC: 'Kansas City Chiefs', LAC: 'Los Angeles Chargers', LAR: 'Los Angeles Rams',
  LV: 'Las Vegas Raiders', MIA: 'Miami Dolphins', MIN: 'Minnesota Vikings',
  NE: 'New England Patriots', NO: 'New Orleans Saints', NYG: 'New York Giants',
  NYJ: 'New York Jets', PHI: 'Philadelphia Eagles', PIT: 'Pittsburgh Steelers',
  SEA: 'Seattle Seahawks', SF: 'San Francisco 49ers', TB: 'Tampa Bay Buccaneers',
  TEN: 'Tennessee Titans', WAS: 'Washington Commanders',
}

export function teamName(abbr: string): string {
  return TEAM_NAMES[abbr] ?? abbr
}

export interface RosterResult {
  items: RosterEntry[]
  source: DataSource
}

interface ApiRosterRow {
  player_id: string
  player_name: string
  position: string
  depth_chart_rank?: number | null
  projected_ppr?: number | null
  actual_ppr?: number | null
  opponent?: string | null
}

const POSITIONS: Position[] = ['QB', 'RB', 'WR', 'TE']

export async function fetchTeamRoster(abbr: string): Promise<RosterResult> {
  try {
    const res = await getJson<{ players?: ApiRosterRow[]; items?: ApiRosterRow[] }>(
      `/api/teams/${encodeURIComponent(abbr)}`,
    )
    const rows = res.players ?? res.items ?? []
    const items: RosterEntry[] = rows
      .filter((r) => POSITIONS.includes(r.position as Position))
      .map((r) => ({
        playerId: r.player_id,
        playerName: r.player_name,
        position: r.position as Position,
        depthRank: r.depth_chart_rank ?? null,
        projectedPpr: r.projected_ppr ?? null,
        actualPpr: r.actual_ppr ?? null,
        opponent: r.opponent ?? null,
      }))
    if (items.length === 0) throw new Error('empty roster')
    return { items, source: 'live' }
  } catch {
    if (abbr === 'KC') return { items: sampleRosterKC, source: 'sample' }
    const items: RosterEntry[] = samplePredictions
      .filter((p) => p.team === abbr)
      .map((p) => ({
        playerId: p.playerId,
        playerName: p.playerName,
        position: p.position,
        depthRank: p.depthRank,
        projectedPpr: p.projectedPpr,
        actualPpr: p.actualPpr,
        opponent: `${p.isHome ? 'vs' : '@'} ${p.opponent}`,
      }))
    return { items, source: 'sample' }
  }
}
