import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { usePredictions } from '../hooks/usePredictions'
import { usePlayerDetail } from '../hooks/usePlayerDetail'
import { InsightPanel } from '../components/InsightPanel'
import { Sparkline } from '../components/Sparkline'
import { PosLabel } from '../components/PosLabel'
import { fmt1, fmtPct, fmtSigned } from '../components/format'
import { EmptyState, ErrorState, SkeletonRows } from '../components/States'

function initials(name: string): string {
  return name
    .split(' ')
    .map((w) => w[0])
    .filter(Boolean)
    .slice(0, 2)
    .join('')
    .toUpperCase()
}

export function PlayerDetailPage() {
  const { playerId = '' } = useParams()
  const { data: predictions, loading: predsLoading, error } = usePredictions()
  const { data: detail, loading: detailLoading } = usePlayerDetail(playerId)

  const player = predictions?.items.find((p) => p.playerId === playerId)

  const seasons = useMemo(
    () => [...new Set(detail?.history.map((h) => h.season) ?? [])].sort(),
    [detail],
  )
  const [seasonOverride, setSeasonOverride] = useState<number | null>(null)
  const season = seasonOverride ?? seasons[seasons.length - 1] ?? null
  const seasonRows = detail?.history.filter((h) => h.season === season) ?? []

  if (predsLoading || detailLoading) {
    return (
      <div className="mx-auto max-w-[1200px] px-4 py-9 lg:px-8">
        <SkeletonRows rows={8} />
      </div>
    )
  }
  if (error) {
    return (
      <ErrorState
        title="Warehouse unavailable — try again."
        desc="The Databricks connection timed out. Retry, or check API health."
      />
    )
  }
  if (!player) {
    return (
      <EmptyState
        title="Player not found in this week's slate."
        desc="They may not have a projection this week. Browse the full rankings instead."
      />
    )
  }

  const contextCells: { label: string; value: string; tone?: 'risk' }[] = [
    { label: 'Implied total', value: fmt1(player.impliedTotal) },
    {
      label: 'Spread',
      value: fmtSigned(player.spread),
      tone: player.spread != null && player.spread > 0 ? 'risk' : undefined,
    },
    {
      label: 'Win prob',
      value: fmtPct(player.winProb),
      tone: player.winProb != null && player.winProb < 0.4 ? 'risk' : undefined,
    },
    {
      label: 'Venue',
      value: player.isDome ? 'Dome' : player.isBadWeather ? 'Bad weather' : 'Outdoor',
      tone: player.isBadWeather ? 'risk' : undefined,
    },
    {
      label: `Opp vs ${player.position}`,
      value: player.oppDefPprAllowed != null ? `${fmt1(player.oppDefPprAllowed)} PPR/g` : '—',
    },
    { label: '3-wk avg', value: fmt1(player.threeWkAvg) },
    { label: 'Prev-season PPG', value: fmt1(player.prevSeasonPpg) },
  ]

  return (
    <div className="mx-auto max-w-[1200px] px-4 py-9 lg:px-8">
      <Link
        to="/rankings"
        className="text-[12px] text-[var(--text-3)] hover:text-[var(--text-1)]"
      >
        ← Rankings
      </Link>

      {/* profile header — the projection is the focal point of the page */}
      <div className="mt-4 flex flex-wrap items-start justify-between gap-5 border-b border-[var(--border-soft)] pb-6">
        <div className="flex items-center gap-4">
          <div className="flex h-[52px] w-[52px] items-center justify-center rounded-full border border-[var(--border)] bg-[var(--raised)] text-[16px] font-semibold text-[var(--text-3)]">
            {initials(player.playerName)}
          </div>
          <div>
            <h1 className="text-[23px] font-semibold tracking-[-0.015em] text-[var(--text-1)]">
              {player.playerName}
            </h1>
            <div className="mt-1.5 flex items-center gap-2 text-[12.5px] text-[var(--text-2)]">
              <PosLabel position={player.position} />
              <span>·</span>
              <span>
                {player.team} {player.isHome ? 'vs' : '@'} {player.opponent}
              </span>
              {player.depthRank != null && (
                <span className="tnum text-[11px] text-[var(--text-3)]">
                  {player.position}
                  {player.depthRank}
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="flex gap-9">
          <div className="text-right">
            <div className="mb-1 text-[10.5px] font-semibold uppercase tracking-[0.05em] text-[var(--text-3)]">
              Projected
            </div>
            <div className="tnum text-[30px] font-medium tracking-[-0.015em] text-[var(--lime)]">
              {fmt1(player.projectedPpr)}
            </div>
          </div>
          <div className="text-right">
            <div className="mb-1 text-[10.5px] font-semibold uppercase tracking-[0.05em] text-[var(--text-3)]">
              Actual
            </div>
            <div className="tnum text-[30px] font-medium tracking-[-0.015em] text-[var(--text-2)]">
              {fmt1(player.actualPpr)}
            </div>
          </div>
        </div>
      </div>

      {/* matchup context — hairline-divided strip, not cards */}
      <div className="my-5 mb-8 flex flex-col sm:flex-row sm:flex-wrap">
        {contextCells.map((c) => (
          <div
            key={c.label}
            className="flex items-center justify-between border-b border-[var(--border-soft)] py-2 sm:mr-5 sm:flex-col sm:items-start sm:justify-start sm:gap-1.5 sm:border-b-0 sm:border-r sm:py-0 sm:pr-5 sm:last:border-r-0"
          >
            <span className="text-[10.5px] uppercase tracking-[0.04em] text-[var(--text-3)]">
              {c.label}
            </span>
            <span
              className={`tnum text-[13.5px] font-medium ${
                c.tone === 'risk' ? 'text-[var(--red)]' : 'text-[var(--text-1)]'
              }`}
            >
              {c.value}
            </span>
          </div>
        ))}
      </div>

      <div className="grid items-start gap-12 lg:grid-cols-[1fr_280px]">
        <div>
          <h2 className="mb-3.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--text-3)]">
            Recent performance
          </h2>
          {seasons.length > 1 && (
            <div className="mb-4 flex gap-3.5">
              {seasons.map((s) => (
                <button
                  key={s}
                  onClick={() => setSeasonOverride(s)}
                  className={`border-b-[1.5px] pb-1 text-[12px] ${
                    s === season
                      ? 'border-[var(--lime)] font-semibold text-[var(--text-1)]'
                      : 'border-transparent font-medium text-[var(--text-3)] hover:text-[var(--text-2)]'
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>
          )}
          {seasonRows.length > 0 ? (
            <>
              <div className="mb-4">
                <Sparkline values={seasonRows.map((h) => h.ppr)} />
              </div>
              <div className="overflow-x-auto xl:overflow-x-visible">
                <table className="tbl min-w-[520px]">
                  <thead>
                    <tr>
                      <th>Week</th>
                      <th>Opp</th>
                      <th className="num">Snap%</th>
                      <th className="num">Targets</th>
                      <th className="num">Air-yds share</th>
                      <th className="num">WOPR</th>
                      <th className="num">PPR</th>
                    </tr>
                  </thead>
                  <tbody>
                    {seasonRows.map((h) => (
                      <tr key={`${h.season}-${h.week}`}>
                        <td className="text-[12.5px] text-[var(--text-3)]">Wk {h.week}</td>
                        <td className="text-[12.5px] text-[var(--text-3)]">{h.opponent}</td>
                        <td className="num text-[12.5px] text-[var(--text-3)]">
                          {h.snapPct != null ? `${h.snapPct}%` : '—'}
                        </td>
                        <td className="num text-[12.5px] text-[var(--text-3)]">
                          {h.targets ?? '—'}
                        </td>
                        <td className="num text-[12.5px] text-[var(--text-3)]">
                          {h.airYardsShare != null
                            ? `${Math.round(h.airYardsShare * 100)}%`
                            : '—'}
                        </td>
                        <td className="num text-[12.5px] text-[var(--text-3)]">
                          {h.wopr != null ? h.wopr.toFixed(2) : '—'}
                        </td>
                        <td className="num text-[13px] font-semibold text-[var(--text-1)]">
                          {h.ppr.toFixed(1)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <p className="py-4 text-[12.5px] italic text-[var(--text-3)]">
              No weekly history available for this player.
            </p>
          )}

          {detail?.career && (
            <>
              <h2 className="mb-0 mt-8 text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--text-3)]">
                Career
              </h2>
              <div className="mt-3.5 flex border-t border-[var(--border-soft)]">
                {[
                  { v: String(detail.career.gamesPlayed), l: 'Games' },
                  { v: detail.career.careerPpg.toFixed(1), l: 'Career PPG' },
                  { v: detail.career.careerHigh.toFixed(1), l: 'Career high' },
                ].map((c) => (
                  <div key={c.l} className="flex-1 pr-5 pt-4">
                    <div className="tnum text-[17px] font-medium text-[var(--text-1)]">
                      {c.v}
                    </div>
                    <div className="mt-1 text-[10.5px] uppercase tracking-[0.04em] text-[var(--text-3)]">
                      {c.l}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        <div>
          <h2 className="mb-3.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--text-3)]">
            Model insight
          </h2>
          <InsightPanel insight={player.insight} />
        </div>
      </div>
    </div>
  )
}
