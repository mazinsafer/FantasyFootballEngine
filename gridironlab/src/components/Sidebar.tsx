import { NavLink } from 'react-router-dom'
import {
  IconCalendar,
  IconDashboard,
  IconRankings,
  IconTeam,
  SparkMark,
} from './Icons'
import { usePredictions } from '../hooks/usePredictions'

const NAV = [
  { to: '/', label: 'Dashboard', icon: IconDashboard, end: true },
  { to: '/rankings', label: 'Rankings', icon: IconRankings, end: false },
  { to: '/teams', label: 'Teams', icon: IconTeam, end: false },
  { to: '/slate', label: 'Weekly results', icon: IconCalendar, end: false },
]

interface Props {
  open: boolean
  onClose: () => void
}

export function Sidebar({ open, onClose }: Props) {
  const { data } = usePredictions()

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={onClose}
        />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-[220px] flex-col border-r border-[var(--border-soft)] bg-[var(--surface)] transition-transform duration-150 lg:sticky lg:top-0 lg:h-screen lg:translate-x-0 ${
          open ? 'translate-x-0 shadow-[20px_0_60px_rgba(0,0,0,0.5)]' : '-translate-x-full'
        }`}
      >
        <div className="flex items-center gap-2.5 px-5 pb-5 pt-6">
          <SparkMark />
          <div>
            <div className="text-[14px] font-bold tracking-[-0.01em] text-[var(--text-1)]">
              Gridiron Lab
            </div>
            <div className="mt-0.5 text-[10.5px] tracking-[0.02em] text-[var(--text-3)]">
              Fantasy analytics
            </div>
          </div>
        </div>

        <nav className="flex flex-1 flex-col gap-px px-2">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={onClose}
              className={({ isActive }) =>
                `-ml-0.5 flex items-center gap-2.5 rounded-md border-l-2 px-3 py-2 text-[13px] font-medium ${
                  isActive
                    ? 'border-[var(--lime)] bg-[rgba(198,227,107,0.045)] text-[var(--text-1)]'
                    : 'border-transparent text-[var(--text-2)] hover:bg-white/[0.02] hover:text-[var(--text-1)]'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <Icon
                    className={isActive ? 'text-[var(--lime)]' : 'opacity-75'}
                  />
                  <span>{label}</span>
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="flex flex-col gap-2.5 border-t border-[var(--border-soft)] px-4 pb-4.5 pt-3.5">
          {data && (
            <div className="text-[12px] text-[var(--text-2)]">
              <b className="font-semibold text-[var(--text-1)]">
                {data.season} · Week {data.week}
              </b>
              <span className="text-[var(--text-3)]"> · Full PPR</span>
            </div>
          )}
          <div className="flex items-center gap-1.5 text-[11px] text-[var(--text-3)]">
            <span
              className="h-[5px] w-[5px] rounded-full"
              style={{
                background: data?.source === 'live' ? 'var(--green)' : 'var(--text-3)',
              }}
            />
            <span>{data?.source === 'live' ? 'Live data' : 'Sample data'}</span>
          </div>
          <NavLink
            to="/model"
            onClick={onClose}
            className="text-[11px] text-[var(--text-3)] hover:text-[var(--text-2)]"
          >
            Model details
          </NavLink>
        </div>
      </aside>
    </>
  )
}
