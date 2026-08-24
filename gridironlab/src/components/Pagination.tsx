interface Props {
  page: number
  pageSize: number
  total: number
  onPage: (page: number) => void
}

export function Pagination({ page, pageSize, total, onPage }: Props) {
  const pages = Math.max(1, Math.ceil(total / pageSize))
  const from = total === 0 ? 0 : page * pageSize + 1
  const to = Math.min(total, (page + 1) * pageSize)

  const nums: number[] = []
  for (let i = 0; i < pages; i++) {
    if (i < 3 || i >= pages - 1 || Math.abs(i - page) <= 1) nums.push(i)
  }
  const display: (number | 'gap')[] = []
  nums.forEach((n, i) => {
    if (i > 0 && n - nums[i - 1] > 1) display.push('gap')
    display.push(n)
  })

  return (
    <div className="mt-1 flex items-center justify-between pt-4">
      <div className="text-[11.5px] text-[var(--text-3)]">
        Showing {from}–{to} of {total}
      </div>
      {pages > 1 && (
        <div className="flex gap-0.5">
          <button
            className="flex h-6.5 w-6.5 items-center justify-center rounded-md text-[12px] text-[var(--text-3)] hover:text-[var(--text-1)] disabled:opacity-40"
            disabled={page === 0}
            onClick={() => onPage(page - 1)}
          >
            ‹
          </button>
          {display.map((n, i) =>
            n === 'gap' ? (
              <span key={`g${i}`} className="flex h-6.5 w-6.5 items-center justify-center text-[12px] text-[var(--text-3)]">
                …
              </span>
            ) : (
              <button
                key={n}
                onClick={() => onPage(n)}
                className={`flex h-6.5 w-6.5 items-center justify-center rounded-md text-[12px] ${
                  n === page
                    ? 'bg-[var(--raised)] font-semibold text-[var(--text-1)]'
                    : 'text-[var(--text-3)] hover:text-[var(--text-1)]'
                }`}
              >
                {n + 1}
              </button>
            ),
          )}
          <button
            className="flex h-6.5 w-6.5 items-center justify-center rounded-md text-[12px] text-[var(--text-3)] hover:text-[var(--text-1)] disabled:opacity-40"
            disabled={page >= pages - 1}
            onClick={() => onPage(page + 1)}
          >
            ›
          </button>
        </div>
      )}
    </div>
  )
}
