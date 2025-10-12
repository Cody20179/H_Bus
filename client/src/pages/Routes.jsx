import React, { useEffect, useMemo, useState } from 'react'
// import stations from '../data/stations'
import RouteDetail from '../components/RouteDetail'
import { getRoutes } from '../services/api'
import { useParams } from 'react-router-dom'

export default function RoutesPage() {
  const [routes, setRoutes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const { routeId, stopOrder } = useParams()
  const [highlightStop, setHighlightStop] = useState(null)

  useEffect(() => {
    if (routes.length > 0 && routeId) {
      const found = routes.find(r =>
        String(r.id) === String(routeId) ||
        String(r.route_id) === String(routeId) ||
        String(r.key) === String(routeId) ||
        String(r.name) === String(routeId)   // ← 加這個，因為有時候 API 沒有 id
      )
      if (found) {
        setSelected(found)
        if (stopOrder) {
          const stopNum = Number(stopOrder)
          if (!isNaN(stopNum)) {
            setHighlightStop(stopNum)
          }
        }
      }
    }
  }, [routes, routeId, stopOrder])

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        setLoading(true)
        setError(null)
        const apiRoutes = await getRoutes()
        if (!cancelled) setRoutes(apiRoutes)
      } catch (e) {
        console.warn('API 取得路線失敗，改用本地資料：', e)
        if (!cancelled) {
          const fallback = buildRoutesFromStations(stations).map((r) => ({
            ...r,
            source: 'static',
          }))
          setRoutes(fallback)
          setError('無法連線後端 API，已使用本地資料')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  const buildRoutesFromStations = (rows) => {
    const map = new Map()
    rows.forEach((row) => {
      const name = row['路徑名稱'] || '未命名路線'
      const direction = row['路程'] || ''
      const key = `${name} ${direction}`.trim()
      if (!map.has(key)) {
        map.set(key, {
          name,
          direction,
          key,
          sample: row,
        })
      }
    })
    return Array.from(map.values())
  }

  const [selected, setSelected] = useState(null)

  return (
    <div className="routes-page">
      <div className="page-header">
        <h2>所有路線</h2>
        <div className="muted">點選路線可查看詳情</div>
        {loading && <div className="muted">載入中…</div>}
        {error && <div className="muted" style={{ color: '#c25' }}>{error}</div>}
      </div>

      <div className="routes-list">
        {routes.map((r) => (
          <div
            key={r.key}
            className="route-card"
            role="button"
            tabIndex={0}
            onClick={() => setSelected(r)}
            onKeyDown={(e) => e.key === 'Enter' && setSelected(r)}
          >
            <div className="route-left">
              <div className="route-title">{r.name}</div>
              <div className="route-sub muted">{r.direction}</div>
            </div>
            <div className="route-action muted">查看</div>
          </div>
        ))}
      </div>

      {selected && (
        <RouteDetail
          route={selected}
          highlightStop={highlightStop}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  )
}
