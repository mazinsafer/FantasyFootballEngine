import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { IconMenu, IconSearch } from './Icons'
import { PosLabel } from './PosLabel'
import { usePredictions } from '../hooks/usePredictions'

interface Props {
  onOpenSidebar: () => void
}

export function TopBar({ onOpenSidebar }: Props) {
  const { data } = usePredictions()
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [focused, setFocused] = useState(false)
  const wrapRef = useRef<HTMLDivElement>(null)

  const matches =
    query.trim().length > 0 && data
      ? data.items
          .filter((p) =>
            p.playerName.toLowerCase().includes(query.trim().toLowerCase()),
          )
          .slice(0, 8)
      : []

  useEffect(() => {
    function onDown(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setFocused(false)
      }
    }
    document.addEventListener('mousedown', onDown)
    return () => document.removeEventListener('mousedown', onDown)
  }, [])

  function go(playerId: string) {
    setQuery('')
    setFocused(false)
    navigate(`/players/${playerId}`)
  }

  return (
    <header className="sticky top-0 z-30 flex h-12 items-center gap-4 border-b border-[var(--border-soft)] bg-[rgba(11,13,17,0.94)] px-4 backdrop-blur-md lg:px-8">
      <button
        className="flex h-7 w-7 items-center justify-center rounded-md text-[var(--text-2)] hover:text-[var(--text-1)] lg:hidden"
        onClick={onOpenSidebar}
        aria-label="Open navigation"
      >
        <IconMenu />
      </button>

      <div ref={wrapRef} className="relative w-full max-w-[260px]">
        <IconSearch
          size={14}
          className="pointer-events-none absolute left-0 top-1/2 -translate-y-1/2 text-[var(--text-3)]"
        />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setFocused(true)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && matches.length > 0) go(matches[0].playerId)
            if (e.key === 'Escape') setFocused(false)
          }}
          placeholder="Search players…"
          className="w-full border-b border-transparent bg-transparent py-1.5 pl-[22px] pr-1 text-[13px] text-[var(--text-1)] outline-none transition-colors placeholder:text-[var(--text-3)] focus:border-[var(--border-strong)]"
        />
        {focused && matches.length > 0 && (
          <div className="absolute left-0 right-0 top-full z-40 mt-1 overflow-hidden rounded-md border border-[var(--border)] bg-[var(--surface)] shadow-[0_12px_40px_rgba(0,0,0,0.5)]">
            {matches.map((p) => (
              <button
                key={p.playerId}
                onClick={() => go(p.playerId)}
                className="flex w-full items-center justify-between px-3 py-2 text-left hover:bg-white/[0.03]"
              >
                <span className="text-[12.5px] font-medium text-[var(--text-1)]">
                  {p.playerName}
                </span>
                <span className="flex items-center gap-1.5">
                  <PosLabel position={p.position} />
                  <span className="text-[11px] text-[var(--text-3)]">{p.team}</span>
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="ml-auto hidden text-[12px] text-[var(--text-3)] sm:block">
        {data ? (
          <span>
            <span className="text-[var(--text-2)]">
              {data.season} · Week {data.week}
            </span>{' '}
            · Full PPR
          </span>
        ) : (
          '—'
        )}
      </div>
    </header>
  )
}
