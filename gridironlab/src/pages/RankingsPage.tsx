import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { usePredictions } from '../hooks/usePredictions'
import { PlayerIdentity } from '../components/PlayerIdentity'
import { Delta, Projection } from '../components/Num'
import { fmt1, fmtPct, fmtSigned } from '../components/format'
import { EmptyState, ErrorState, SkeletonRows } from '../components/States'
import { Pagination } from '../components/Pagination'
import type { Prediction } from '../types/Prediction'
import type { Position } from '../types/Player'

const PAGE_SIZE = 50
const POSITIONS: ('All' | Position)[] = ['All', 'QB', 'RB', 'WR', 'TE']

type SortKey =
  | 'projectedPpr'
  | 'actualPpr'
  | 'impliedTotal'
  | 'spread'
  | 'winProb'
  | 'oppDefPprAllowed'
  | 'threeWkAvg'
  | 'prevSeasonPpg'

const NUMERIC_COLUMNS: { key: SortKey; label: string }[] = [
  { key: 'projectedPpr', label: 'Proj PPR' },
  { key: 'actualPpr', label: 'Actual' },
  { key: 'impliedTotal', label: 'Impl total' },
  { key: 'spread', label: 'Spread' },
  { key: 'winProb', label: 'Win%' },
  { key: 'oppDefPprAllowed', label: 'Opp def' },
  { key: 'threeWkAvg', label: '3-wk avg' },
  { key: 'prevSeasonPpg', label: 'Prev PPG' },
]

function venueNote(p: Prediction): { text: string; risk: boolean } | null {
  if (p.isDome) return { text: 'dome', risk: false }
  if (p.isBadWeather) return { text: 'weather', risk: true }
  return null
}

export function RankingsPage() {
  const { data, loading, error } = usePredictions()
  const navigate = useNavigate()

  const [position, setPosition] = useState<'All' | Position>('All')
  const [team, setTeam] = useState('All')
  const [minProj, setMinProj] = useState(0)
  const [sort, setSort] = useState<{ key: SortKey; desc: boolean }>({
    key: 'projectedPpr',
    desc: true,
  })
  const [page, setPage] = useState(0)

  const teams = useMemo(
    () => (data ? [...new Set(data.items.map((p) => p.team))].sort() : []),
    [data],
  )

  const filtered = useMemo(() => {
    if (!data) return []
    const rows = data.items.filter(
      (p) =>
        (position === 'All' || p.position === position) &&
        (team === 'All' || p.team === team) &&
        p.projectedPpr >= minProj,
    )
    const dir = sort.desc ? -1 : 1
    return [...rows].sort((a, b) => {
      const av = a[sort.key]
      const bv = b[sort.key]
      if (av == null && bv == null) return 0
      if (av == null) return 1
      if (bv == null) return -1
      return (av - bv) * dir
    })
  }, [data, position, team, minProj, sort])

  const pageRows = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  function toggleSort(key: SortKey) {
    setPage(0)
    setSort((s) => (s.key === key ? { key, desc: !s.desc } : { key, desc: true }))
  }

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

  return (
    <div className="mx-auto max-w-[1200px] px-4 py-9 lg:px-8">
      <div className="mb-6">
        <h1 className="text-[20px] font-semibold tracking-[-0.01em] text-[var(--text-1)]">
          Rankings
        </h1>
        <p className="mt-1 text-[12.5px] text-[var(--text-3)]">
          Week {data.week} · Full PPR · {data.items.length} players
        </p>
      </div>

      {/* filter bar */}
      <div className="mb-1 flex flex-wrap items-center gap-x-6 gap-y-3 border-b border-[var(--border)] pb-4">
        <div className="flex items-center gap-0.5">
          {POSITIONS.map((pos) => (
            <button
              key={pos}
              onClick={() => {
                setPosition(pos)
                setPage(0)
              }}
              className={`border-b-2 px-2.5 py-1.5 text-[12.5px] ${
                position === pos
                  ? 'border-[var(--lime)] font-semibold text-[var(--text-1)]'
                  : 'border-transparent font-medium text-[var(--text-2)] hover:text-[var(--text-1)]'
              }`}
            >
              {pos}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-semibold uppercase tracking-[0.04em] text-[var(--text-3)]">
            Team
          </span>
          <select
            value={team}
            onChange={(e) => {
              setTeam(e.target.value)
              setPage(0)
            }}
            className="cursor-pointer border-b border-[var(--border)] bg-transparent px-0.5 py-1 text-[12.5px] text-[var(--text-2)] outline-none hover:text-[var(--text-1)]"
          >
            <option value="All">All teams</option>
            {teams.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>
        <div className="flex min-w-[190px] items-center gap-2.5">
          <span className="text-[11px] font-semibold uppercase tracking-[0.04em] text-[var(--text-3)]">
            Min proj
          </span>
          <input
            type="range"
            min={0}
            max={25}
            step={0.5}
            value={minProj}
            onChange={(e) => {
              setMinProj(Number(e.target.value))
              setPage(0)
            }}
            className="h-[3px] flex-1"
          />
          <span className="tnum min-w-[32px] text-[12px] text-[var(--text-1)]">
            {minProj.toFixed(1)}
          </span>
        </div>
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          title="No players match these filters."
          desc="Try widening the position, team, or minimum projected PPR."
        />
      ) : (
        <>
          <div className="overflow-x-auto xl:overflow-x-visible">
            <table className="tbl min-w-[900px]">
              <thead>
                <tr>
                  <th>Player</th>
                  <th>Matchup</th>
                  {NUMERIC_COLUMNS.slice(0, 2).map((c) => (
                    <th key={c.key} className="num">
                      <button
                        className={sort.key === c.key ? 'sorted' : ''}
                        onClick={() => toggleSort(c.key)}
                      >
                        {c.label}
                        {sort.key === c.key && (
                          <span className="ml-1 text-[8px] opacity-70">
                            {sort.desc ? '▼' : '▲'}
                          </span>
                        )}
                      </button>
                    </th>
                  ))}
                  <th className="num">Δ</th>
                  {NUMERIC_COLUMNS.slice(2).map((c) => (
                    <th key={c.key} className="num">
                      <button
                        className={sort.key === c.key ? 'sorted' : ''}
                        onClick={() => toggleSort(c.key)}
                      >
                        {c.label}
                        {sort.key === c.key && (
                          <span className="ml-1 text-[8px] opacity-70">
                            {sort.desc ? '▼' : '▲'}
                          </span>
                        )}
                      </button>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {pageRows.map((p) => {
                  const note = venueNote(p)
                  return (
                    <tr
                      key={p.playerId}
                      className="row-link"
                      onClick={() => navigate(`/players/${p.playerId}`)}
                    >
                      <td>
                        <PlayerIdentity name={p.playerName} position={p.position} team={p.team} />
                      </td>
                      <td className="text-[12.5px] text-[var(--text-3)]">
                        {p.isHome ? 'vs' : '@'} {p.opponent}
                        {note && (
                          <span
                            className={`ml-2 text-[10.5px] ${
                              note.risk ? 'text-[var(--red)]' : 'text-[var(--text-3)] opacity-70'
                            }`}
                          >
                            {note.text}
                          </span>
                        )}
                      </td>
                      <td className="num">
                        <Projection value={p.projectedPpr} className="text-[14.5px]" />
                      </td>
                      <td className="num text-[12.5px]">{fmt1(p.actualPpr)}</td>
                      <td className="num">
                        <Delta projected={p.projectedPpr} actual={p.actualPpr} />
                      </td>
                      <td className="num text-[12.5px] text-[var(--text-3)]">
                        {fmt1(p.impliedTotal)}
                      </td>
                      <td className="num text-[12.5px] text-[var(--text-3)]">
                        {fmtSigned(p.spread)}
                      </td>
                      <td
                        className={`num text-[12.5px] ${
                          p.winProb != null && p.winProb < 0.4
                            ? 'text-[var(--red)]'
                            : 'text-[var(--text-3)]'
                        }`}
                      >
                        {fmtPct(p.winProb)}
                      </td>
                      <td className="num text-[12.5px] text-[var(--text-3)]">
                        {fmt1(p.oppDefPprAllowed)}
                      </td>
                      <td className="num text-[12.5px] text-[var(--text-3)]">
                        {fmt1(p.threeWkAvg)}
                      </td>
                      <td className="num text-[12.5px] text-[var(--text-3)]">
                        {fmt1(p.prevSeasonPpg)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          <Pagination
            page={page}
            pageSize={PAGE_SIZE}
            total={filtered.length}
            onPage={setPage}
          />
        </>
      )}
    </div>
  )
}
