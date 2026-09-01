const API_BASE =
  (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000'

export type DataSource = 'live' | 'sample'

/** Fetch JSON from the FastAPI backend. Timeout is long enough for a Render
 *  cold start; if it still fails the UI falls back to bundled sample data. */
export async function getJson<T>(path: string, timeoutMs = 20000): Promise<T> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const res = await fetch(`${API_BASE}${path}`, { signal: controller.signal })
    if (!res.ok) throw new Error(`Request failed: ${res.status}`)
    return (await res.json()) as T
  } finally {
    clearTimeout(timer)
  }
}
