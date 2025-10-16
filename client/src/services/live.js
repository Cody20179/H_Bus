const envBase = (import.meta.env && import.meta.env.VITE_API_BASE_URL) || ''
const BASE = (envBase?.trim?.() || (import.meta.env?.DEV ? '/api' : ''))

let __LIVE = { ts: 0, data: null, inflight: null }
const __LIVE_TTL = 30000

export async function getLiveSummaries() {
  const now = Date.now()
  if (__LIVE.inflight) return __LIVE.inflight
  if (__LIVE.data && (now - __LIVE.ts < __LIVE_TTL)) return __LIVE.data

  const p = (async () => {
    const res = await fetch(`${BASE}/GIS_AllFast`, { headers: { accept: 'application/json' } })
    const json = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(`Failed to load live summaries: ${res.status}`)
    const rows = Array.isArray(json?.data) ? json.data : Array.isArray(json) ? json : []
    const mapped = rows.map(r => ({
      route: r.route ?? r.route_id ?? r.route_no ?? null,
      X: r.X != null ? parseFloat(r.X) : null,
      Y: r.Y != null ? parseFloat(r.Y) : null,
      direction: r.direction ?? null,
      currentLocation: r.nearest_stop_name ?? r.Current_Loaction ?? null,
      licensePlate: r.license_plate ?? null,
    }))
    // 規則：若資料為 None（如 X/Y 或最近站 None），前端視為「未發車」，
    // 因此這裡直接濾掉讓 RouteDetail 找不到 car 進而顯示「未發車」。
    const ready = mapped.filter(x => x.X != null && x.Y != null && x.currentLocation)
    __LIVE = { ts: Date.now(), data: ready, inflight: null }
    return ready
  })()
  __LIVE.inflight = p
  try { return await p } finally { __LIVE.inflight = null }
}
