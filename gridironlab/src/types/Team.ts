import type { Position } from './Player'

export interface RosterEntry {
  playerId: string
  playerName: string
  position: Position
  depthRank: number | null
  projectedPpr: number | null
  actualPpr: number | null
  opponent: string | null
}
