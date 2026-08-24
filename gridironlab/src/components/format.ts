/** Numeric formatting helpers shared by the display components and pages. */

export function fmt1(n: number | null | undefined): string {
  return n == null ? '—' : n.toFixed(1)
}

export function fmtPct(n: number | null | undefined): string {
  return n == null ? '—' : `${Math.round(n * 100)}%`
}

export function fmtSigned(n: number | null | undefined): string {
  if (n == null) return '—'
  return `${n > 0 ? '+' : n < 0 ? '−' : ''}${Math.abs(n).toFixed(1)}`
}
