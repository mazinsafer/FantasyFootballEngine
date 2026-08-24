import type { Prediction } from '../types/Prediction'
import type { PlayerCareer, PlayerWeekRow } from '../types/Player'
import type { RosterEntry } from '../types/Team'

/** Bundled 2025 Week 17 sample slate, used when the API is unreachable. */

const S = 2025
const W = 17

export const samplePredictions: Prediction[] = [
  {
    playerId: 'puka-nacua', playerName: 'Puka Nacua', position: 'WR', team: 'LAR',
    opponent: 'ATL', isHome: true, projectedPpr: 21.5, actualPpr: 15.7,
    threeWkAvg: 36.7, depthRank: 1, prevSeasonPpg: 17.9, impliedTotal: 28.0,
    spread: 7.5, winProb: 0.79, oppDefPprAllowed: 33.3, isDome: true, isBadWeather: false,
    insight:
      "Atlanta's secondary is allowing 33.3 PPR/g to wide receivers, the widest exploit on the slate. The +7.5 road spread adds garbage-time risk to an otherwise elite volume profile — read 21.5 as a wide-outcome range, not a floor.",
    season: S, week: W,
  },
  {
    playerId: 'drake-maye', playerName: 'Drake Maye', position: 'QB', team: 'NE',
    opponent: 'NYJ', isHome: true, projectedPpr: 20.6, actualPpr: 32.4,
    threeWkAvg: 21.5, depthRank: 1, prevSeasonPpg: 16.2, impliedTotal: 22.4,
    spread: -3.0, winProb: 0.58, oppDefPprAllowed: 19.8, isDome: false, isBadWeather: true,
    insight:
      "New England's 22.4 implied total is modest, but the Jets are allowing 19.8 PPR/g to quarterbacks and Maye's 21.5 three-week average shows a stable rushing-supported floor. Freezing wind conditions are the primary risk to passing volume.",
    season: S, week: W,
  },
  {
    playerId: 'jahmyr-gibbs', playerName: 'Jahmyr Gibbs', position: 'RB', team: 'DET',
    opponent: 'MIN', isHome: true, projectedPpr: 20.2, actualPpr: 8.4,
    threeWkAvg: 24.1, depthRank: 1, prevSeasonPpg: 19.4, impliedTotal: 26.1,
    spread: -6.5, winProb: 0.74, oppDefPprAllowed: 21.0, isDome: true, isBadWeather: false,
    insight:
      "Detroit's 26.1 implied total is second-highest on the slate and Gibbs has averaged 24.1 PPR over his last three games. Minnesota is allowing 21.0 PPR/g to running backs, and a -6.5 home spread supports positive game script and goal-line volume.",
    season: S, week: W,
  },
  {
    playerId: 'matthew-stafford', playerName: 'Matthew Stafford', position: 'QB', team: 'LAR',
    opponent: 'ATL', isHome: true, projectedPpr: 20.2, actualPpr: 18.1,
    threeWkAvg: 19.0, depthRank: 1, prevSeasonPpg: 17.0, impliedTotal: 28.0,
    spread: 7.5, winProb: 0.79, oppDefPprAllowed: 15.4, isDome: true, isBadWeather: false,
    insight: null, season: S, week: W,
  },
  {
    playerId: 'trevor-lawrence', playerName: 'Trevor Lawrence', position: 'QB', team: 'JAX',
    opponent: 'IND', isHome: false, projectedPpr: 19.7, actualPpr: 14.2,
    threeWkAvg: 17.8, depthRank: 1, prevSeasonPpg: 15.5, impliedTotal: 20.9,
    spread: 2.5, winProb: 0.48, oppDefPprAllowed: 17.2, isDome: false, isBadWeather: false,
    insight: null, season: S, week: W,
  },
  {
    playerId: 'amon-ra-st-brown', playerName: 'Amon-Ra St. Brown', position: 'WR', team: 'DET',
    opponent: 'MIN', isHome: true, projectedPpr: 18.9, actualPpr: 16.3,
    threeWkAvg: 20.4, depthRank: 1, prevSeasonPpg: 18.7, impliedTotal: 26.1,
    spread: -6.5, winProb: 0.74, oppDefPprAllowed: 21.0, isDome: true, isBadWeather: false,
    insight: null, season: S, week: W,
  },
  {
    playerId: 'ceedee-lamb', playerName: 'CeeDee Lamb', position: 'WR', team: 'DAL',
    opponent: 'WAS', isHome: false, projectedPpr: 18.4, actualPpr: 11.9,
    threeWkAvg: 19.9, depthRank: 1, prevSeasonPpg: 16.6, impliedTotal: 23.5,
    spread: 3.5, winProb: 0.41, oppDefPprAllowed: 24.7, isDome: false, isBadWeather: false,
    insight: null, season: S, week: W,
  },
  {
    playerId: 'bijan-robinson', playerName: 'Bijan Robinson', position: 'RB', team: 'ATL',
    opponent: 'LAR', isHome: false, projectedPpr: 18.1, actualPpr: 9.6,
    threeWkAvg: 17.2, depthRank: 1, prevSeasonPpg: 14.9, impliedTotal: 20.5,
    spread: -7.5, winProb: 0.21, oppDefPprAllowed: 18.3, isDome: true, isBadWeather: false,
    insight: null, season: S, week: W,
  },
  {
    playerId: 'breece-hall', playerName: 'Breece Hall', position: 'RB', team: 'NYJ',
    opponent: 'NE', isHome: false, projectedPpr: 17.8, actualPpr: 6.1,
    threeWkAvg: 15.5, depthRank: 1, prevSeasonPpg: 13.8, impliedTotal: 16.9,
    spread: 3.0, winProb: 0.42, oppDefPprAllowed: 16.0, isDome: false, isBadWeather: true,
    insight: null, season: S, week: W,
  },
  {
    playerId: 'sam-laporta', playerName: 'Sam LaPorta', position: 'TE', team: 'DET',
    opponent: 'MIN', isHome: true, projectedPpr: 17.2, actualPpr: 13.0,
    threeWkAvg: 16.1, depthRank: 1, prevSeasonPpg: 12.4, impliedTotal: 26.1,
    spread: -6.5, winProb: 0.74, oppDefPprAllowed: 14.6, isDome: true, isBadWeather: false,
    insight: null, season: S, week: W,
  },
]

export const sampleHistory: PlayerWeekRow[] = [
  { season: S, week: 11, opponent: '@ SEA', snapPct: 52, targets: 11, airYardsShare: 0.34, wopr: 0.71, ppr: 19.4 },
  { season: S, week: 12, opponent: 'vs ARI', snapPct: 58, targets: 9, airYardsShare: 0.29, wopr: 0.64, ppr: 14.2 },
  { season: S, week: 13, opponent: 'vs NO', snapPct: 55, targets: 14, airYardsShare: 0.41, wopr: 0.79, ppr: 36.7 },
  { season: S, week: 14, opponent: '@ SF', snapPct: 49, targets: 8, airYardsShare: 0.25, wopr: 0.58, ppr: 11.6 },
  { season: S, week: 15, opponent: 'vs BUF', snapPct: 60, targets: 12, airYardsShare: 0.37, wopr: 0.73, ppr: 22.9 },
  { season: S, week: 16, opponent: '@ ARI', snapPct: 57, targets: 10, airYardsShare: 0.31, wopr: 0.66, ppr: 18.0 },
]

export const sampleCareer: PlayerCareer = {
  gamesPlayed: 38,
  careerPpg: 17.2,
  careerHigh: 36.7,
}

export const sampleRosterKC: RosterEntry[] = [
  { playerId: 'patrick-mahomes', playerName: 'Patrick Mahomes', position: 'QB', depthRank: 1, projectedPpr: 19.4, actualPpr: 21.0, opponent: 'vs LV' },
  { playerId: 'isiah-pacheco', playerName: 'Isiah Pacheco', position: 'RB', depthRank: 1, projectedPpr: 14.2, actualPpr: 9.8, opponent: 'vs LV' },
  { playerId: 'kareem-hunt', playerName: 'Kareem Hunt', position: 'RB', depthRank: 2, projectedPpr: 8.1, actualPpr: 6.4, opponent: 'vs LV' },
  { playerId: 'carson-steele', playerName: 'Carson Steele', position: 'RB', depthRank: 3, projectedPpr: null, actualPpr: null, opponent: 'vs LV' },
  { playerId: 'rashee-rice', playerName: 'Rashee Rice', position: 'WR', depthRank: 1, projectedPpr: 15.6, actualPpr: 12.1, opponent: 'vs LV' },
  { playerId: 'xavier-worthy', playerName: 'Xavier Worthy', position: 'WR', depthRank: 2, projectedPpr: 11.9, actualPpr: 17.8, opponent: 'vs LV' },
  { playerId: 'juju-smith-schuster', playerName: 'JuJu Smith-Schuster', position: 'WR', depthRank: 3, projectedPpr: 6.4, actualPpr: 3.2, opponent: 'vs LV' },
  { playerId: 'travis-kelce', playerName: 'Travis Kelce', position: 'TE', depthRank: 1, projectedPpr: 13.7, actualPpr: 15.9, opponent: 'vs LV' },
]
