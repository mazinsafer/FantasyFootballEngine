import type { Position } from './Player'

export interface Prediction {
  playerId: string
  playerName: string
  position: Position
  team: string
  opponent: string
  isHome: boolean
  projectedPpr: number
  actualPpr: number | null
  threeWkAvg: number | null
  depthRank: number | null
  prevSeasonPpg: number | null
  impliedTotal: number | null
  spread: number | null
  winProb: number | null
  oppDefPprAllowed: number | null
  isDome: boolean
  isBadWeather: boolean
  insight: string | null
  season: number
  week: number
}
