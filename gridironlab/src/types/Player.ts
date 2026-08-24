export type Position = 'QB' | 'RB' | 'WR' | 'TE'

export interface PlayerCareer {
  gamesPlayed: number
  careerPpg: number
  careerHigh: number
}

export interface PlayerWeekRow {
  season: number
  week: number
  opponent: string
  snapPct: number | null
  targets: number | null
  airYardsShare: number | null
  wopr: number | null
  ppr: number
}
