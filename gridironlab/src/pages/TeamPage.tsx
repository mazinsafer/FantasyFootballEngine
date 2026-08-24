import { useNavigate, useParams } from 'react-router-dom'
import { useTeamRoster } from '../hooks/useTeamRoster'
import { usePredictions } from '../hooks/usePredictions'
import { TEAM_NAMES, teamName } from '../services/teamService'
import { PlayerIdentity } from '../components/PlayerIdentity'
import { PosLabel } from '../components/PosLabel'
import { Projection } from '../components/Num'
import { fmt1 } from '../components/format'
import { EmptyState, SkeletonRows } from '../components/States'
import type { Position } from '../types/Player'

const ORDER: Position[] = ['QB', 'RB', 'WR', 'TE']

export function TeamPage() {
  const { abbr = 'KC' } = useParams()
  const navigate = useNavigate()
  const { data, loading } = useTeamRoster(abbr)
  const { data: predictions } = usePredictions()

  const roster = data?.items ?? []

  return (
    <div className="mx-auto max-w-[1200px] px-4 py-9 lg:px-8">
      <div className="mb-8 flex flex-wrap items-center justify-between gap-4 border-b border-[var(--border-soft)] pb-6">
        <div className="flex items-center gap-3.5">
          <div className="tnum flex h-[42px] w-[42px] items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--raised)] text-[14px] font-semibold text-[var(--text-2)]">
            {abbr}
          </div>
          <div>
            <h1 className="text-[17px] font-semibold text-[var(--text-1)]">
              {teamName(abbr)}
            </h1>
            <p className="mt-0.5 text-[12.5px] text-[var(--text-3)]">
              {predictions ? `Week ${predictions.week} roster` : 'Roster'}
            </p>
          </div>
        </div>
        <select
          value={abbr}
          onChange={(e) => navigate(`/teams/${e.target.value}`)}
          className="cursor-pointer border-b border-[var(--border)] bg-transparent px-0.5 py-1 text-[12.5px] text-[var(--text-2)] outline-none hover:text-[var(--text-1)]"
        >
          {Object.keys(TEAM_NAMES).map((t) => (
            <option key={t} value={t}>
              {t} — {TEAM_NAMES[t]}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <SkeletonRows rows={8} />
      ) : roster.length === 0 ? (
        <EmptyState
          title="No roster data for this team."
          desc="This team has no players in the current dataset. Try another team."
        />
      ) : (
        ORDER.map((pos) => {
          const group = roster
            .filter((r) => r.position === pos)
            .sort((a, b) => (a.depthRank ?? 99) - (b.depthRank ?? 99))
          if (group.length === 0) return null
          return (
            <div key={pos} className="mb-8">
              <div className="mb-3 flex items-baseline gap-2">
                <PosLabel position={pos} />
                <span className="text-[11px] text-[var(--text-3)]">
                  {group.length} on roster
                </span>
              </div>
              <div className="overflow-x-auto xl:overflow-x-visible">
                <table className="tbl min-w-[520px]">
                  <thead>
                    <tr>
                      <th>Player</th>
                      <th className="num">Depth</th>
                      <th className="num">Proj PPR</th>
                      <th className="num">Actual</th>
                      <th>Opp</th>
                    </tr>
                  </thead>
                  <tbody>
                    {group.map((r) => (
                      <tr
                        key={r.playerId}
                        className="row-link"
                        onClick={() => navigate(`/players/${r.playerId}`)}
                      >
                        <td>
                          <PlayerIdentity name={r.playerName} />
                        </td>
                        <td className="num text-[12.5px] text-[var(--text-3)]">
                          {r.depthRank ?? '—'}
                        </td>
                        <td className="num">
                          {r.projectedPpr != null ? (
                            <Projection value={r.projectedPpr} className="text-[14px]" />
                          ) : (
                            <span className="text-[var(--text-3)]">—</span>
                          )}
                        </td>
                        <td className="num text-[12.5px]">{fmt1(r.actualPpr)}</td>
                        <td className="text-[12.5px] text-[var(--text-3)]">
                          {r.opponent ?? '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )
        })
      )}
    </div>
  )
}
