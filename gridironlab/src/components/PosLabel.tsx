import type { Position } from '../types/Player'

/** Neutral position label — positions carry no accent color by design. */
export function PosLabel({ position }: { position: Position }) {
  return (
    <span className="text-[10px] font-semibold uppercase tracking-[0.03em] text-[var(--pos)]">
      {position}
    </span>
  )
}
