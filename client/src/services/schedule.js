const envBase = (import.meta.env && import.meta.env.VITE_API_BASE_URL) || ''
const BASE = (envBase?.trim?.() || (import.meta.env?.DEV ? '/api' : ''))

// 30s in-memory cache with in-flight dedupe
let __SCHEDULE = { ts: 0, data: null, inflight: null }
const __TTL = 30000
const __now = () => Date.now()

export async function getRouteScheduleAll() {
  const now = __now()
  if (__SCHEDULE.inflight) return __SCHEDULE.inflight
  if (__SCHEDULE.data && (now - __SCHEDULE.ts < __TTL)) return __SCHEDULE.data

  const p = (async () => {
    const res = await fetch(`${BASE}/route_schedule`, { headers: { accept: 'application/json' } })
    const json = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(`Failed to load route schedule: ${res.status}`)
    let rows = []
    if (Array.isArray(json?.data)) rows = json.data
    else if (Array.isArray(json)) rows = json
    __SCHEDULE = { ts: __now(), data: rows, inflight: null }
    return rows
  })()
  __SCHEDULE.inflight = p
  try { return await p } finally { __SCHEDULE.inflight = null }
}

export async function getRouteScheduleForRoute(routeId) {
  const all = await getRouteScheduleAll()
  const rid = Number(routeId)
  const today = new Date()
  const yyyy = today.getFullYear()
  const mm = String(today.getMonth() + 1).padStart(2, '0')
  const dd = String(today.getDate()).padStart(2, '0')
  const dateStr = `${yyyy}-${mm}-${dd}`
  return all.filter((r) => Number(r.route_no) === rid && String(r.date).slice(0, 10) === dateStr)
}

export function normalizeDirection(d) {
  const t = String(d || '').trim()
  if (/返|回|1/.test(t)) return '返程'
  if (/去|往|0/.test(t)) return '去程'
  return t
}

export async function getTodayStatusByDirection(routeId) {
  const rows = await getRouteScheduleForRoute(routeId)
  const pick = (dir) => {
    const list = (rows || []).filter(r => normalizeDirection(r.direction) === dir)
    if (list.some(r => String(r.operation_status).trim() === '正常營運')) return '正常營運'
    if (list.length > 0) return String(list[0].operation_status || '尚未排班')
    return '尚未排班'
  }
  return { 去程: pick('去程'), 返程: pick('返程') }
}
