import { Link, useNavigate } from 'react-router-dom'
import { usePredictions } from '../hooks/usePredictions'
import { PlayerIdentity } from '../components/PlayerIdentity'
import { InsightPanel } from '../components/InsightPanel'
import { Delta, Projection } from '../components/Num'
import { fmt1 } from '../components/format'
import { ErrorState, SkeletonRows } from '../components/States'
import { PosLabel } from '../components/PosLabel'

export function HomePage() {
  const { data, loading, error } = usePredictions()
  const navigate = useNavigate()

  if (loading) {
    return (
      <div className="mx-auto max-w-[1200px] px-4 py-9 lg:px-8">
        <SkeletonRows rows={8} />
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

  const items = data.items
  const top = items.slice(0, 10)
  const featured = items.find((p) => p.insight)
  const otherInsights = items.filter((p) => p.insight && p !== featured)
  const teams = new Set(items.map((p) => p.team))
  items.forEach((p) => teams.add(p.opponent))

  return (
    <div className="mx-auto max-w-[1200px] px-4 py-9 lg:px-8">
      <div className="text-[11px] font-semibold uppercase tracking-[0.09em] text-[var(--text-3)]">
        Week {data.week} · Full PPR
      </div>
      <h1 className="mt-2 text-[24px] font-semibold tracking-[-0.015em] text-[var(--text-1)]">
        The slate, at a glance.
      </h1>
      <p className="mt-2 text-[13px] text-[var(--text-2)]">
        {items.length} players projected across {Math.round(teams.size / 2)} games.
      </p>

      {/* stat strip — hairlines, not cards */}
      <div className="my-7 mb-11 flex flex-col border-y border-[var(--border-soft)] sm:flex-row">
        <div className="flex-1 border-b border-[var(--border-soft)] py-4 sm:border-b-0 sm:border-r sm:pr-6">
          <div className="mb-2 text-[10.5px] font-semibold uppercase tracking-[0.06em] text-[var(--text-3)]">
            Players projected
          </div>
          <div className="tnum text-[22px] font-medium text-[var(--text-1)]">
            {items.length}
          </div>
          <div className="mt-1.5 text-[11.5px] text-[var(--text-3)]">
            QB · RB · WR · TE, full-PPR scoring
          </div>
        </div>
        <div className="flex-1 border-b border-[var(--border-soft)] py-4 sm:border-b-0 sm:border-r sm:px-6">
          <div className="mb-2 text-[10.5px] font-semibold uppercase tracking-[0.06em] text-[var(--text-3)]">
            Top projection
          </div>
          <div className="tnum text-[22px] font-medium text-[var(--lime)]">
            {fmt1(top[0]?.projectedPpr ?? null)}
            <span className="ml-1 text-[12px] font-normal text-[var(--text-3)]">PPR</span>
          </div>
          <div className="mt-1.5 text-[11.5px] text-[var(--text-3)]">
            <b className="font-medium text-[var(--text-2)]">{top[0]?.playerName}</b> ·{' '}
            {top[0]?.position}, {top[0]?.team}
          </div>
        </div>
        <div className="flex-1 py-4 sm:pl-6">
          <div className="mb-2 text-[10.5px] font-semibold uppercase tracking-[0.06em] text-[var(--text-3)]">
            Model week
          </div>
          <div className="tnum text-[18px] font-medium leading-[30px] text-[var(--text-1)]">
            {data.season} W{data.week}
          </div>
          <div className="mt-1.5 text-[11.5px] text-[var(--text-3)]">
            Locked · scored postgame
          </div>
        </div>
      </div>

      <div className="grid items-start gap-12 xl:grid-cols-[1fr_320px]">
        {/* primary focal point: the projections table */}
        <div>
          <div className="mb-3.5 flex items-baseline justify-between">
            <h2 className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--text-3)]">
              Top projections
            </h2>
            <Link
              to="/rankings"
              className="text-[12px] font-medium text-[var(--text-2)] hover:text-[var(--text-1)]"
            >
              Full rankings →
            </Link>
          </div>
          <div className="overflow-x-auto xl:overflow-x-visible">
            <table className="tbl min-w-[560px]">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Player</th>
                  <th>Matchup</th>
                  <th className="num">Projection</th>
                  <th className="num">Actual</th>
                  <th className="num">Δ</th>
                  <th className="num">3-wk avg</th>
                </tr>
              </thead>
              <tbody>
                {top.map((p, i) => (
                  <tr
                    key={p.playerId}
                    className="row-link"
                    onClick={() => navigate(`/players/${p.playerId}`)}
                  >
                    <td className="tnum w-[26px] text-[12.5px] text-[var(--text-3)]">
                      {i + 1}
                    </td>
                    <td>
                      <PlayerIdentity name={p.playerName} position={p.position} team={p.team} />
                    </td>
                    <td className="text-[12.5px] text-[var(--text-3)]">
                      {p.isHome ? 'vs' : '@'} {p.opponent}
                    </td>
                    <td className="num">
                      <Projection
                        value={p.projectedPpr}
                        trend={
                          p.threeWkAvg == null
                            ? undefined
                            : p.projectedPpr >= p.threeWkAvg
                              ? 'up'
                              : 'down'
                        }
                        className="text-[15px]"
                      />
                    </td>
                    <td className="num text-[12.5px]">{fmt1(p.actualPpr)}</td>
                    <td className="num">
                      <Delta projected={p.projectedPpr} actual={p.actualPpr} />
                    </td>
                    <td className="num text-[12.5px] text-[var(--text-3)]">
                      {fmt1(p.threeWkAvg)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* secondary column: model insight */}
        <div>
          <h2 className="mb-3.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--text-3)]">
            Model insight
          </h2>
          {featured ? (
            <InsightPanel
              insight={featured.insight}
              playerName={featured.playerName}
              role={`· ${featured.position}${featured.depthRank ?? ''}`}
            />
          ) : (
            <InsightPanel insight={null} />
          )}

          {otherInsights.length > 0 && (
            <>
              <h2 className="mb-1.5 mt-8 text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--text-3)]">
                More insights this week
              </h2>
              <div className="flex flex-col">
                {otherInsights.map((p) => (
                  <Link
                    key={p.playerId}
                    to={`/players/${p.playerId}`}
                    className="group flex items-center justify-between border-t border-[var(--border-soft)] py-2.5"
                  >
                    <span className="flex items-center gap-2">
                      <span className="text-[12.5px] font-semibold text-[var(--text-1)] group-hover:text-[var(--teal)]">
                        {p.playerName}
                      </span>
                      <PosLabel position={p.position} />
                      <span className="text-[11px] text-[var(--text-3)]">{p.team}</span>
                    </span>
                    <span className="tnum text-[12.5px] font-semibold text-[var(--lime)]">
                      {fmt1(p.projectedPpr)}
                    </span>
                  </Link>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
