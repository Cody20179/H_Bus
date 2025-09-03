// src/components/RouteDetail.jsx
import React, { useEffect, useMemo, useRef, useState } from 'react'
import stations from '../data/stations'
import { getRouteStops } from '../services/api'

export default function RouteDetail({ route, onClose }) {
  // API: manage selected direction + fetched stops
  const [selectedDir, setSelectedDir] = useState('去程')
  const [stops, setStops] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [viewMode, setViewMode] = useState('list') // 'list' | 'map'

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

  // 將靜態資料轉成 RouteMap 可用格式
  const staticStopsForMap = useMemo(() => {
    if (!isStatic) return []
    return list.map((s, idx) => ({
      stop_name: s['站點'] || s['位置'] || `第${idx + 1}站`,
      stop_order: Number(s['站次'] ?? idx + 1) || idx + 1,
      latitude: Number(s['去程緯度'] ?? s['緯度'] ?? s['lat'] ?? s['Lat'] ?? 0),
      longitude: Number(s['去程經度'] ?? s['經度'] ?? s['lng'] ?? s['Lon'] ?? 0),
      etaFromStart: Number(s['首站到此站時間'] ?? idx * 3) || idx * 3,
    }))
      .filter((x) => Number.isFinite(x.latitude) && Number.isFinite(x.longitude))
      .sort((a, b) => (a.stop_order ?? 0) - (b.stop_order ?? 0))
  }, [isStatic, list])

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
            <button className="btn" onClick={() => setViewMode(viewMode === 'list' ? 'map' : 'list')} style={{ marginRight: 8 }}>{viewMode === 'list' ? '地圖' : '列表'}</button>
            <button className="btn btn-orange" onClick={onClose}>關閉</button>
          </div>
        </div>

        {/* API 路線：顯示方向切換與站點清單 */}
        {!isStatic ? (
          <>
            {!isSingleDirection && (
              <div className="card" style={{ marginBottom: 12 }}>
                <div className="card-body" style={{ display: 'flex', gap: 8, alignItems:'center' }}>
                  <div className="muted small">方向</div>
                  <button className={`btn ${selectedDir === '去程' ? 'btn-blue' : ''}`} onClick={() => setSelectedDir('去程')}>去程</button>
                  <button className={`btn ${selectedDir === '回程' ? 'btn-blue' : ''}`} onClick={() => setSelectedDir('回程')}>回程</button>
                </div>
              </div>
            )}

            {viewMode === 'map' ? (
              <RouteMap stops={stops} />
            ) : (
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
            )}
          </>
        ) : (
          viewMode === 'map' ? (
            <RouteMap stops={staticStopsForMap} />
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
          )
        )}
      </div>
    </div>
  )
}

// Leaflet loader and map renderer
function useLeaflet() {
  const [ready, setReady] = useState(false)
  useEffect(() => {
    let cancelled = false
    if (window.L) { setReady(true); return }
    import('leaflet').then((mod) => {
      const L = mod.default ?? mod
      if (!cancelled) {
        window.L = L
        setReady(true)
      }
    })
    return () => { cancelled = true }
  }, [])
  return ready
}

function RouteMap({ stops }) {
  const ready = useLeaflet()
  const elRef = useRef(null)
  const mapRef = useRef(null)
  const layerRouteRef = useRef(null)
  const layerStopsRef = useRef(null)
  const layerBusRef = useRef(null)

  function ensurePolylineDecorator() {
    return new Promise((resolve) => {
      if (window.L && window.L.polylineDecorator) return resolve(true)
      import('leaflet-polylinedecorator').then(() => resolve(true))
    })
  }

  useEffect(() => {
    if (!ready || !elRef.current || mapRef.current) return
    const L = window.L
    const map = L.map(elRef.current, { center:[23.99302,121.603219], zoom:14 })
    L.tileLayer('https://wmts.nlsc.gov.tw/wmts/EMAP/default/GoogleMapsCompatible/{z}/{y}/{x}', { tileSize:256 }).addTo(map)
    L.tileLayer('https://wmts.nlsc.gov.tw/wmts/EMAP2/default/GoogleMapsCompatible/{z}/{y}/{x}', { tileSize:256, opacity:.9 }).addTo(map)
    mapRef.current = map
    layerRouteRef.current = L.layerGroup().addTo(map)
    layerStopsRef.current = L.layerGroup().addTo(map)
    layerBusRef.current = L.layerGroup().addTo(map)
  }, [ready])

  useEffect(() => {
    if (!ready || !mapRef.current) return
    const L = window.L
    const routeLayer = layerRouteRef.current
    const stopLayer = layerStopsRef.current
    const busLayer = layerBusRef.current
    routeLayer.clearLayers(); stopLayer.clearLayers(); busLayer.clearLayers()

    const ordered = (stops || [])
      .slice()
      .sort((a,b) => (a.order ?? a.stop_order ?? 0) - (b.order ?? b.stop_order ?? 0))

    // overlap handling: bigger offset to fully separate
    const seen = new Map()
    const offsetLatLng = ([lat,lng], meters=14, angleDeg=0) => {
      const R=6378137
      const dLat = (meters*Math.cos(angleDeg*Math.PI/180))/R
      const dLng = (meters*Math.sin(angleDeg*Math.PI/180))/(R*Math.cos(lat*Math.PI/180))
      return [lat + dLat*180/Math.PI, lng + dLng*180/Math.PI]
    }
    const llOriginal = ordered.map((s) => {
      const lat = Number(s.latitude ?? s.lat), lng = Number(s.longitude ?? s.lng)
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null
      return [lat, lng]
    }).filter(Boolean)

    const ll = ordered.map((s) => {
      const lat = Number(s.latitude ?? s.lat), lng = Number(s.longitude ?? s.lng)
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null
      const key = lat.toFixed(6)+','+lng.toFixed(6)
      const n = (seen.get(key) || 0); seen.set(key, n+1)
      return n===0 ? [lat,lng] : offsetLatLng([lat,lng], (n)*14, n*45)
    }).filter(Boolean)

    // Draw road-snapped route using OSRM (fallback to straight line)
    const draw = async () => {
      if (llOriginal.length >= 2) {
        const coords = llOriginal.map(([lat,lng]) => `${lng},${lat}`).join(';')
        const url = `https://router.project-osrm.org/route/v1/driving/${coords}?overview=full&geometries=geojson&steps=false`
        try {
          await ensurePolylineDecorator()
          const r = await fetch(url)
          if (!r.ok) throw new Error(String(r.status))
          const j = await r.json()
          const g = j?.routes?.[0]?.geometry
          if (g) {
            const casing = L.geoJSON(g, { style:{ color:'#ffffff', weight:12, opacity:1, lineCap:'round', lineJoin:'round' } }).addTo(routeLayer)
            const stroke = L.geoJSON(g, { style:{ color:'#2563eb', weight:7, opacity:.98, lineCap:'round', lineJoin:'round' } }).addTo(routeLayer)
            try {
              if (L.polylineDecorator) {
                const poly = stroke.getLayers()[0]
                if (poly) {
                  L.polylineDecorator(poly, { patterns:[{ offset:0, repeat:'48px', symbol: L.Symbol.arrowHead({ pixelSize:11, pathOptions:{ color:'#2563eb', weight:6, opacity:0.95 } }) }] }).addTo(routeLayer)
                }
              }
            } catch {}
            mapRef.current.fitBounds(stroke.getBounds(), { padding:[30,30] })
          } else {
            const line = L.polyline(llOriginal, { color:'#2563eb', weight:6, opacity:.95 }).addTo(routeLayer)
            mapRef.current.fitBounds(line.getBounds(), { padding:[30,30] })
          }
        } catch (e) {
          const line = L.polyline(llOriginal, { color:'#2563eb', weight:6, opacity:.95 }).addTo(routeLayer)
          mapRef.current.fitBounds(line.getBounds(), { padding:[30,30] })
        }
      } else if (ll.length === 1) {
        mapRef.current.setView(ll[0], 15)
      }
    }
    draw()

    const icon = (label, cls='') => L.divIcon({ className:'', html:`<div class="stop-badge ${cls}">${label}</div>`, iconSize:[24,24], iconAnchor:[12,12] })
    ordered.forEach((s, idx) => {
      const p = ll[idx]; if (!p) return
      const isFirst = idx===0, isLast = idx===ordered.length-1
      const label = isFirst ? 'S' : (s.order ?? s.stop_order ?? idx+1)
      const cls = isFirst ? 'stop-start' : (isLast ? 'stop-end' : '')
      L.marker(p, { icon: icon(label, cls) }).addTo(stopLayer).bindTooltip(`${s.stopName || s.stop_name || '站點'}`, { direction:'top' })
    })

    // Simulate bus location: pick nearest upcoming stop by etaFromStart
    const times = ordered.map((s, i) => Number(s.etaFromStart ?? s.eta_from_start ?? i*3) || i*3)
    const lastEta = times.reduce((m, t) => Math.max(m, t), 0)
    const cycle = Math.max(lastEta + 5, ordered.length * 3) || 20
    const nowMin = (Date.now() / 60000) % cycle
    let busIdx = times.findIndex(t => t >= nowMin - 0.25)
    if (busIdx < 0) busIdx = Math.min(ordered.length-1, 1) // default第二站
    const busPt = ll[busIdx]
    if (busPt) {
      const html = `
        <div class="bus-wrap">
          <div class="bus-pulse"></div>
          <div class="bus-dot"></div>
          <div class="bus-emoji">🚌</div>
          <div class="bus-badge">BUS</div>
        </div>`
      L.marker(busPt, { icon: L.divIcon({ className:'', html, iconSize:[1,1] }) }).addTo(busLayer)
      L.circle(busPt, { radius:50, color:'#2563eb', weight:1, fillColor:'#2563eb', fillOpacity:.08 }).addTo(busLayer)
    }
  }, [ready, stops])

  return (
    <div style={{ height:'60vh', borderRadius: 12, overflow:'hidden' }} ref={elRef} />
  )
}
