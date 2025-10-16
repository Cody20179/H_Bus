import { getRouteStops, getRouteStopsBulk } from './api'
import { getTodayStatusByDirection } from './schedule'

// In-memory cache with 30s TTL and in-flight de-duplication
const CACHE = new Map()
const TTL = 30000

const normDir = (d) => {
  const t = String(d || '').trim()
  if (/返|回|1/.test(t)) return '返程'
  if (/去|往|0/.test(t)) return '去程'
  return t
}

const keyOf = (routeId, direction) => `${Number(routeId)}-${normDir(direction)}`

// Fetch both directions once per route; cache 30s; de-dupe in-flight
export async function getRouteStopsCached(routeId, direction) {
  const dir = normDir(direction)
  const key = keyOf(routeId, dir)
  const now = Date.now()

  // 1) Serve from per-direction cache if fresh
  const hit = CACHE.get(key)
  if (hit) {
    if (hit.inflight) return hit.inflight
    if (now - hit.ts < TTL && Array.isArray(hit.data)) return hit.data
  }

  // 2) If direction not operational today, short-circuit to avoid fetching stops
  try {
    const statusMap = await getTodayStatusByDirection(routeId)
    const stat = statusMap?.[dir]
    if (stat && String(stat).trim() !== '正常營運') {
      const data = []
      CACHE.set(key, { data, ts: Date.now(), inflight: null })
      return data
    }
  } catch {}

  // 3) If a route-level bulk fetch is running, piggyback
  const bulkKey = `ALL-${Number(routeId)}`
  const bulkHit = CACHE.get(bulkKey)
  if (bulkHit?.inflight) {
    const p = bulkHit.inflight.then(() => {
      const fresh = CACHE.get(key)
      return fresh?.data ?? []
    })
    CACHE.set(key, { data: hit?.data ?? null, ts: hit?.ts ?? 0, inflight: p })
    return p
  }

  // 4) Start bulk fetch for both directions once
  const inflight = getRouteStopsBulk(routeId)
    .then((byDir) => {
      const up = (d) => {
        const k = keyOf(routeId, d)
        const arr = byDir[d] || []
        CACHE.set(k, { data: arr, ts: Date.now(), inflight: null })
      }
      up('去程'); up('返程')
      return (dir === '返程' ? byDir.返程 : byDir.去程) || []
    })
    .catch(async () => {
      // fallback to single direction fetch to avoid blank UI
      const rows = await getRouteStops(routeId, dir)
      CACHE.set(key, { data: rows, ts: Date.now(), inflight: null })
      return rows
    })
    .finally(() => {
      const cur = CACHE.get(bulkKey)
      if (cur) CACHE.set(bulkKey, { data: cur.data ?? null, ts: cur.ts ?? Date.now(), inflight: null })
    })

  // Prime route-level inflight so opposite direction calls wait on same promise
  CACHE.set(bulkKey, { data: null, ts: now, inflight })
  // Also set per-direction inflight so immediate callers get a promise
  CACHE.set(key, { data: hit?.data ?? null, ts: hit?.ts ?? 0, inflight })
  return inflight
}
