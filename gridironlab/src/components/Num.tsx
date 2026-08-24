import { fmt1 } from './format'

/** Numeric display components — the semantic color system lives here.
 *  Lime = projection, green = positive delta, red = negative delta/risk. */

export function Projection({
  value,
  trend,
  className = '',
}: {
  value: number | null
  trend?: 'up' | 'down'
  className?: string
}) {
  return (
    <span className={`tnum font-semibold text-[var(--lime)] ${className}`}>
      {fmt1(value)}
      {trend && (
        <span
          className={`ml-1.5 text-[11px] font-normal ${
            trend === 'up' ? 'text-[var(--lime-dim)]' : 'text-[var(--red)]'
          }`}
        >
          {trend === 'up' ? '↑' : '↓'}
        </span>
      )}
    </span>
  )
}

export function Delta({
  projected,
  actual,
}: {
  projected: number | null
  actual: number | null
}) {
  if (projected == null || actual == null)
    return <span className="text-[var(--text-3)]">—</span>
  const d = actual - projected
  return (
    <span
      className={`tnum text-[12px] font-medium ${
        d >= 0 ? 'text-[var(--green)]' : 'text-[var(--red)]'
      }`}
    >
      {d >= 0 ? '+' : '−'}
      {Math.abs(d).toFixed(1)}
    </span>
  )
}
