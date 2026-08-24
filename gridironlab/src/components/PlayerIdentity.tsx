import type { Position } from '../types/Player'
import { PosLabel } from './PosLabel'

function initials(name: string): string {
  return name
    .split(' ')
    .map((w) => w[0])
    .filter(Boolean)
    .slice(0, 2)
    .join('')
    .toUpperCase()
}

interface Props {
  name: string
  position?: Position
  team?: string
  size?: 'sm' | 'md'
}

/** The dominant cell in every table: avatar, name, quiet position/team sub-line. */
export function PlayerIdentity({ name, position, team, size = 'md' }: Props) {
  const avatar = size === 'sm' ? 'h-6 w-6 text-[9px]' : 'h-7 w-7 text-[10px]'
  return (
    <div className="flex items-center gap-2.5">
      <div
        className={`${avatar} flex flex-none items-center justify-center rounded-full border border-[var(--border)] bg-[var(--raised)] font-semibold text-[var(--text-3)]`}
      >
        {initials(name)}
      </div>
      <div className="min-w-0">
        <div className="whitespace-nowrap text-[13px] font-semibold text-[var(--text-1)]">
          {name}
        </div>
        {(position || team) && (
          <div className="mt-0.5 flex items-center gap-1.5 leading-none">
            {position && <PosLabel position={position} />}
            {team && <span className="text-[11px] text-[var(--text-3)]">{team}</span>}
          </div>
        )}
      </div>
    </div>
  )
}
