import { fetchPlayerDetail } from '../services/playerService'
import { useAsync } from './useAsync'

/** Weekly history and career summary for one player. */
export function usePlayerDetail(playerId: string) {
  return useAsync(() => fetchPlayerDetail(playerId), [playerId])
}
