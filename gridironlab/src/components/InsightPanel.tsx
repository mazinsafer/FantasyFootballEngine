interface Props {
  insight: string | null
  playerName?: string
  role?: string
  emptyNote?: string
}

/** Model insight — an integrated analytical feature, marked by a single
 *  teal rule. The teal accent is reserved exclusively for model insight. */
export function InsightPanel({ insight, playerName, role, emptyNote }: Props) {
  const hasInsight = Boolean(insight)
  return (
    <div
      className="border-l-2 py-0.5 pl-4"
      style={{
        borderColor: hasInsight ? 'var(--teal-dim)' : 'var(--border-strong)',
      }}
    >
      <div
        className="mb-2.5 text-[10.5px] font-semibold uppercase tracking-[0.05em]"
        style={{ color: hasInsight ? 'var(--teal)' : 'var(--text-3)' }}
      >
        Model insight
      </div>
      {playerName && hasInsight && (
        <div className="mb-2 flex items-baseline gap-2">
          <span className="text-[14px] font-semibold text-[var(--text-1)]">
            {playerName}
          </span>
          {role && <span className="text-[11.5px] text-[var(--text-3)]">{role}</span>}
        </div>
      )}
      {hasInsight ? (
        <p className="text-[13px] leading-[1.7] text-[var(--text-2)]">{insight}</p>
      ) : (
        <p className="text-[12.5px] italic text-[var(--text-3)]">
          {emptyNote ??
            'No insight generated — insights cover the top 15 projected players each week.'}
        </p>
      )}
    </div>
  )
}
