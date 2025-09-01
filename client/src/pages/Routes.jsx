// src/pages/Routes.jsx
import React, { useEffect, useMemo, useState } from 'react'
import stations from '../data/stations' // CSV 轉檔的本地資料（作為失敗備援）
import RouteDetail from '../components/RouteDetail'
import { getRoutes } from '../services/api'

export default function RoutesPage() {
  const [routes, setRoutes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // 優先從 API 載入；若失敗則退回本地 stations 資料彙整
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
          // 依「路徑名稱 + 路程」聚合出路線列表
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
      // 使用 name + direction 當 key（有去/回時可分）
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

      {/* Route detail area (simple overlay / panel) */}
      {selected && (
        <RouteDetail
          route={selected}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  )
}
