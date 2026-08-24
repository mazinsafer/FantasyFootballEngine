interface Props {
  values: number[]
  height?: number
}

/** Minimal lime sparkline: communicates the shape of recent form, nothing more. */
export function Sparkline({ values, height = 56 }: Props) {
  if (values.length < 2) return null
  const w = 640
  const pad = 4
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * w
    const y = pad + (1 - (v - min) / range) * (height - pad * 2)
    return [x, y] as const
  })
  const last = pts[pts.length - 1]
  return (
    <svg
      width="100%"
      height={height}
      viewBox={`0 0 ${w} ${height}`}
      preserveAspectRatio="none"
      aria-hidden
    >
      <polyline
        fill="none"
        stroke="var(--lime)"
        strokeWidth="1.6"
        points={pts.map(([x, y]) => `${x},${y.toFixed(1)}`).join(' ')}
      />
      <circle cx={last[0]} cy={last[1]} r="2.8" fill="var(--lime)" />
    </svg>
  )
}
