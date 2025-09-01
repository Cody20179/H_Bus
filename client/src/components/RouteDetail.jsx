// src/components/RouteDetail.jsx
import React, { useEffect, useMemo, useState } from 'react'
import stations from '../data/stations'
import { getRouteStops } from '../services/api'

export default function RouteDetail({ route, onClose }) {
  // API: manage selected direction + fetched stops
  const [selectedDir, setSelectedDir] = useState('去程')
  const [stops, setStops] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const isStatic = route.source === 'static'
  const isSingleDirection = route.direction && route.direction.includes('單向')

  // A lightweight timer to refresh simulated statuses
  const [tick, setTick] = useState(0)
  useEffect(() => {
    const id = setInterval(() => setTick((t) => (t + 1) % 1_000_000), 15000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    if (!isStatic) {
      // For API routes, (re)load when route or selectedDir changes
      let cancelled = false
      setLoading(true)
      setError(null)
      getRouteStops(route.id, selectedDir)
        .then((data) => {
          if (!cancelled) setStops(data)
        })
        .catch((e) => {
          if (!cancelled) {
            setStops([])
            setError('無法載入站點資料')
            console.warn('Route stops fetch failed:', e)
          }
        })
        .finally(() => {
          if (!cancelled) setLoading(false)
        })
      return () => {
        cancelled = true
      }
    }
  }, [route, selectedDir, isStatic])

  // 靜態資料情況：依名稱/路程過濾站點
  const list = useMemo(() => {
    if (!isStatic) return []
    return stations
      .filter((s) => {
        const nameMatch = (s['路徑名稱'] || '') === route.name
        const dirMatch = route.direction ? (s['路程'] || '') === route.direction : true
        return nameMatch && dirMatch
      })
      .sort((a, b) => {
        const na = Number(a['站次'] || 0)
        const nb = Number(b['站次'] || 0)
        return na - nb
      })
  }, [route, isStatic])

  // Normalize stops for display and compute a simulated real-time status
  const displayStops = useMemo(() => {
    // Build a unified list with: name, order, etaFromStart
    const unified = isStatic
      ? list.map((s, idx) => ({
          name: s['站點'] || s['位置'] || `第${idx + 1}站`,
          order: Number(s['站次'] ?? (idx + 1)) || (idx + 1),
          etaFromStart: Number(s['首站到此站時間'] ?? (idx * 3)) || (idx * 3),
        }))
      : stops.map((s, idx) => ({
          name: s.stopName || `第${idx + 1}站`,
          order: Number(s.order ?? (idx + 1)) || (idx + 1),
          etaFromStart: Number(s.etaFromStart ?? (idx * 3)) || (idx * 3),
        }))

    // Determine cycle length (minutes) based on last stop ETA
    const lastEta = unified.reduce((m, s) => Math.max(m, s.etaFromStart || 0), 0)
    const cycle = Math.max(lastEta + 5, unified.length * 3) || 20
    const nowMin = (Date.now() / 60000) % cycle

    const annotate = (eta) => {
      const delta = eta - nowMin // minutes until arrival
      if (delta <= -1.0) return { label: '已過站', tone: 'muted', etaText: null }
      if (delta <= 0.25) return { label: '到站中', tone: 'green', etaText: '0 分鐘' }
      if (delta <= 2.0) return { label: '即將到站', tone: 'orange', etaText: `${Math.ceil(delta)} 分鐘` }
      return { label: '等待中', tone: 'blue', etaText: `${Math.ceil(delta)} 分鐘` }
    }

    return unified
      .sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
      .map((s) => ({ ...s, status: annotate(s.etaFromStart) }))
  // include tick so it recomputes periodically
  }, [isStatic, list, stops, tick])

  return (
    <div className="route-detail-overlay" role="dialog" aria-modal="true">
      <div className="route-detail-panel">
        <div className="panel-head">
          <div>
            <div className="route-title">{route.name}</div>
            <div className="muted small">
              {isStatic ? route.direction : selectedDir}
            </div>
          </div>
          <div>
            <button className="btn btn-orange" onClick={onClose}>關閉</button>
          </div>
        </div>

        {/* API 路線：顯示方向切換與站點清單 */}
        {!isStatic ? (
          <>
            {!isSingleDirection && (
              <div className="card" style={{ marginBottom: 12 }}>
                <div className="card-body" style={{ display: 'flex', gap: 8 }}>
                  <button
                    className={`btn ${selectedDir === '去程' ? 'btn-blue' : ''}`}
                    onClick={() => setSelectedDir('去程')}
                  >去程</button>
                  <button
                    className={`btn ${selectedDir === '回程' ? 'btn-blue' : ''}`}
                    onClick={() => setSelectedDir('回程')}
                  >回程</button>
                </div>
              </div>
            )}

            <div className="stops-list">
              {loading && <div className="muted">載入中…</div>}
              {error && <div className="muted" style={{ color: '#c25' }}>{error}</div>}
              {!loading && displayStops.map((s, idx) => (
                <div key={`${s.order}-${s.name}-${idx}`} className="stop-item">
                  <div className="stop-left">
                    <div className="stop-name">{s.name}</div>
                    <div className="muted small">第 {s.order ?? (idx + 1)} 站 • 首站起 {s.etaFromStart ?? '-'} 分鐘</div>
                  </div>
                  <div className="stop-right">
                    <span
                      className="muted small"
                      style={{
                        padding: '2px 8px',
                        borderRadius: 12,
                        background: s.status.tone === 'green' ? '#e7f7ec' : s.status.tone === 'orange' ? '#fff2e5' : s.status.tone === 'blue' ? '#eaf2ff' : '#f2f3f5',
                        color: s.status.tone === 'green' ? '#16794c' : s.status.tone === 'orange' ? '#a24a00' : s.status.tone === 'blue' ? '#1d4ed8' : '#6b7280',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {s.status.label}{s.status.etaText ? ` • ${s.status.etaText}` : ''}
                    </span>
                  </div>
                </div>
              ))}
              {!loading && displayStops.length === 0 && !error && (
                <div className="muted">此方向目前無站點資料</div>
              )}
            </div>
          </>
        ) : (
          <div className="stops-list">
            {displayStops.map((s, idx) => (
              <div key={idx} className="stop-item">
                <div className="stop-left">
                  <div className="stop-name">{s.name}</div>
                  <div className="muted small">第 {s.order ?? (idx + 1)} 站 • 首站起 {s.etaFromStart ?? '-'} 分鐘</div>
                </div>
                <div className="stop-right">
                  <span
                    className="muted small"
                    style={{
                      padding: '2px 8px',
                      borderRadius: 12,
                      background: s.status.tone === 'green' ? '#e7f7ec' : s.status.tone === 'orange' ? '#fff2e5' : s.status.tone === 'blue' ? '#eaf2ff' : '#f2f3f5',
                      color: s.status.tone === 'green' ? '#16794c' : s.status.tone === 'orange' ? '#a24a00' : s.status.tone === 'blue' ? '#1d4ed8' : '#6b7280',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {s.status.label}{s.status.etaText ? ` • ${s.status.etaText}` : ''}
                  </span>
                </div>
              </div>
            ))}
            {displayStops.length === 0 && <div className="muted">找不到此路線的站點資料</div>}
          </div>
        )}
      </div>
    </div>
  )
}
