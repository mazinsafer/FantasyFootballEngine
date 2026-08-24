import { useNavigate } from 'react-router-dom'
import { usePredictions } from '../hooks/usePredictions'
import { PlayerIdentity } from '../components/PlayerIdentity'
import { Delta } from '../components/Num'
import { fmt1 } from '../components/format'
import { EmptyState, ErrorState, SkeletonRows } from '../components/States'

export function SlatePage() {
  const { data, loading, error } = usePredictions()
  const navigate = useNavigate()

  if (loading) {
    return (
      <div className="mx-auto max-w-[1200px] px-4 py-9 lg:px-8">
        <SkeletonRows rows={10} />
      </div>
    )
  }
  if (error || !data) {
    return (
      <ErrorState
        title="Warehouse unavailable — try again."
        desc="The Databricks connection timed out. Retry, or check API health."
      />
    )
  }

  const scored = data.items
    .filter((p) => p.actualPpr != null)
    .sort((a, b) => (b.actualPpr ?? 0) - (a.actualPpr ?? 0))

  return (
    <div className="mx-auto max-w-[1200px] px-4 py-9 lg:px-8">
      <div className="mb-6">
        <h1 className="text-[20px] font-semibold tracking-[-0.01em] text-[var(--text-1)]">
          Weekly results
        </h1>
        <p className="mt-1 text-[12.5px] text-[var(--text-3)]">
          {data.season} · Week {data.week} · actual PPR scoring, ranked by outcome
        </p>
      </div>

      {scored.length === 0 ? (
        <EmptyState
          title="No results yet for this week."
          desc="Actual scoring appears here after the games are played and the pipeline is re-run postgame."
        />
      ) : (
        <>
      <div className="mb-3.5 flex items-baseline justify-between">
        <h2 className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--text-3)]">
          Actual PPR leaderboard
        </h2>
        <span className="text-[11px] text-[var(--text-3)]">what actually happened</span>
      </div>

      <div className="overflow-x-auto xl:overflow-x-visible">
        <table className="tbl min-w-[560px]">
          <thead>
            <tr>
              <th>#</th>
              <th>Player</th>
              <th>Matchup</th>
              <th className="num">Actual PPR</th>
              <th className="num">Proj PPR</th>
              <th className="num">Δ vs proj</th>
            </tr>
          </thead>
          <tbody>
            {scored.map((p, i) => (
              <tr
                key={p.playerId}
                className="row-link"
                onClick={() => navigate(`/players/${p.playerId}`)}
              >
                <td className="tnum w-[26px] text-[12.5px] text-[var(--text-3)]">{i + 1}</td>
                <td>
                  <PlayerIdentity name={p.playerName} position={p.position} team={p.team} />
                </td>
                <td className="text-[12.5px] text-[var(--text-3)]">
                  {p.isHome ? 'vs' : '@'} {p.opponent}
                </td>
                <td className="num text-[15px] font-semibold text-[var(--text-1)]">
                  {fmt1(p.actualPpr)}
                </td>
                <td className="num text-[12.5px] text-[var(--text-3)]">
                  {fmt1(p.projectedPpr)}
                </td>
                <td className="num">
                  <Delta projected={p.projectedPpr} actual={p.actualPpr} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
        </>
      )}
    </div>
  )
}
