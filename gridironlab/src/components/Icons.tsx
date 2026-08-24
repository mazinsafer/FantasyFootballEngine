interface IconProps {
  size?: number
  className?: string
}

function base(size: number | undefined, className: string | undefined) {
  return {
    width: size ?? 15,
    height: size ?? 15,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.6,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
    className,
  }
}

export function SparkMark({ size = 20 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path
        d="M4 17L10 6L13 13L20 4"
        stroke="var(--lime)"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export function IconDashboard(p: IconProps) {
  return (
    <svg {...base(p.size, p.className)}>
      <rect x="3" y="3" width="7" height="9" rx="1.5" />
      <rect x="14" y="3" width="7" height="5" rx="1.5" />
      <rect x="14" y="12" width="7" height="9" rx="1.5" />
      <rect x="3" y="16" width="7" height="5" rx="1.5" />
    </svg>
  )
}

export function IconRankings(p: IconProps) {
  return (
    <svg {...base(p.size, p.className)}>
      <path d="M4 19V10" />
      <path d="M12 19V5" />
      <path d="M20 19v-6" />
    </svg>
  )
}

export function IconTeam(p: IconProps) {
  return (
    <svg {...base(p.size, p.className)}>
      <path d="M3 21V9l9-6 9 6v12" />
      <path d="M9 21v-7h6v7" />
    </svg>
  )
}

export function IconCalendar(p: IconProps) {
  return (
    <svg {...base(p.size, p.className)}>
      <rect x="3" y="4" width="18" height="17" rx="2" />
      <path d="M3 9h18" />
      <path d="M8 2v4M16 2v4" />
    </svg>
  )
}

export function IconSearch(p: IconProps) {
  return (
    <svg {...base(p.size, p.className)} strokeWidth={1.8}>
      <circle cx="11" cy="11" r="7" />
      <path d="M21 21l-4.3-4.3" />
    </svg>
  )
}

export function IconMenu(p: IconProps) {
  return (
    <svg {...base(p.size, p.className)} strokeWidth={2}>
      <path d="M4 6h16M4 12h16M4 18h16" />
    </svg>
  )
}

export function IconAlert(p: IconProps) {
  return (
    <svg {...base(p.size, p.className)} strokeWidth={1.4}>
      <path d="M12 9v4M12 17h.01" />
      <circle cx="12" cy="12" r="9" />
    </svg>
  )
}

export function IconSearchOff(p: IconProps) {
  return (
    <svg {...base(p.size, p.className)} strokeWidth={1.4}>
      <circle cx="11" cy="11" r="7" />
      <path d="M21 21l-4.3-4.3" />
      <path d="M8 8l6 6M14 8l-6 6" />
    </svg>
  )
}
