import { IconAlert, IconSearchOff } from './Icons'

export function EmptyState({ title, desc }: { title: string; desc: string }) {
  return (
    <div className="flex flex-col items-center gap-2 px-5 py-16 text-center">
      <IconSearchOff size={32} className="text-[var(--text-3)] opacity-60" />
      <div className="text-[13.5px] font-semibold text-[var(--text-2)]">{title}</div>
      <div className="max-w-[300px] text-[12px] text-[var(--text-3)]">{desc}</div>
    </div>
  )
}

export function ErrorState({ title, desc }: { title: string; desc: string }) {
  return (
    <div className="flex flex-col items-center gap-2 px-5 py-16 text-center">
      <IconAlert size={32} className="text-[var(--red)] opacity-80" />
      <div className="text-[13.5px] font-semibold text-[var(--red)]">{title}</div>
      <div className="max-w-[300px] text-[12px] text-[var(--text-3)]">{desc}</div>
    </div>
  )
}

export function SkeletonRows({ rows = 6 }: { rows?: number }) {
  return (
    <div>
      {Array.from({ length: rows }, (_, i) => (
        <div
          key={i}
          className="flex items-center gap-3.5 border-b border-[var(--border-soft)] py-3 last:border-b-0"
        >
          <div className="skel h-7 w-7 rounded-full" />
          <div className="flex flex-1 flex-col gap-1.5">
            <div className="skel h-2.5 rounded" style={{ width: `${55 - (i % 3) * 8}%` }} />
            <div className="skel h-2.5 rounded" style={{ width: `${32 - (i % 3) * 4}%` }} />
          </div>
          <div className="skel h-2.5 w-9 rounded" />
        </div>
      ))}
      <style>{`
        .skel {
          background: linear-gradient(90deg, var(--border-soft) 25%, var(--raised) 50%, var(--border-soft) 75%);
          background-size: 400% 100%;
          animation: gl-shimmer 1.8s ease infinite;
        }
        @keyframes gl-shimmer {
          0% { background-position: 100% 0; }
          100% { background-position: -100% 0; }
        }
      `}</style>
    </div>
  )
}
