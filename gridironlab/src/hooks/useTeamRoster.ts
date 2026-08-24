import { fetchTeamRoster } from '../services/teamService'
import { useAsync } from './useAsync'

/** Roster with latest projections for one team. */
export function useTeamRoster(abbr: string) {
  return useAsync(() => fetchTeamRoster(abbr), [abbr])
}
