import { fetchPredictions } from '../services/predictionService'
import { useAsync } from './useAsync'

/** Latest-week predictions, cached at the service level for the session. */
export function usePredictions() {
  return useAsync(fetchPredictions, [])
}
