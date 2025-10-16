import React, { useEffect, useMemo, useRef, useState } from 'react'
import { getRouteStops, getCarPositions } from '../services/api'
import debounce from 'lodash.debounce'
import dayjs from "dayjs"

export default function RouteDetail({ route, onClose, highlightStop }) {
  const [selectedDir, setSelectedDir] = useState('去程')
  const [stops, setStops] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [viewMode, setViewMode] = useState('list')
  const isStatic = route.source === 'static'
  const isSingleDirection = route.direction && route.direction.includes('單向')
  const [loadingCars, setLoadingCars] = useState(false)
  const [initialLoading, setInitialLoading] = useState(true)
  const [tick, setTick] = useState(0)
  const [cars, setCars] = useState([])

  // 定時刷新 tick
  useEffect(() => {
    const id = setInterval(() => setTick((t) => (t + 1) % 1_000_000), 15000)
    return () => clearInterval(id)
  }, [])

  // 一進頁：等站點與車輛資料都載入完才解除初始載入
  useEffect(() => {
    let cancelled = false

    async function loadAll() {
      try {
        setInitialLoading(true)
        setLoading(true)
        setLoadingCars(true)
        setError(null)

        // 同步抓取站點與車輛
        const [stopData, carData] = await Promise.all([
          getRouteStops(route.id, selectedDir),
          getCarPositions()
        ])

        if (!cancelled) {
          setStops(stopData || [])
          setCars(carData || [])
        }
      } catch (err) {
        if (!cancelled) {
          console.warn("初始載入失敗:", err)
          setError("無法載入資料")
          setStops([])
        }
      } finally {
        if (!cancelled) {
          setInitialLoading(false)   // ✅ 真正載完才解除
          setLoading(false)
          setLoadingCars(false)
        }
      }
    }

    loadAll()
    return () => { cancelled = true }
  }, [route, selectedDir])

  // 抓取站點
  useEffect(() => {
    if (!isStatic) {
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

  // 抓取車輛位置
  useEffect(() => {
    let cancelled = false
    const [loadingCars, setLoadingCars] = [setLoading, setLoading] // reuse loading state if you already have it

    // 防止太頻繁呼叫 API（3 秒內多次只會執行一次）
    const fetchCars = debounce(async () => {
      try {
        setLoading(true)
        const data = await getCarPositions()
        if (!cancelled) {
          setCars([...data])
          setTick((t) => t + 1)
        }
      } catch (e) {
        if (!cancelled) console.warn('載入即時車輛位置失敗', e)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }, 3000)

    // 初次載入 + 每 15 秒刷新
    fetchCars()
    const id = setInterval(fetchCars, 30000)

    return () => {
      cancelled = true
      clearInterval(id)
      fetchCars.cancel()
    }
  }, [])

  // 靜態站點
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

  // 顯示的站點 + 車輛狀態
  const displayStops = useMemo(() => {
    const unified = (isStatic ? list : stops).map((s, idx) => ({
      name: s.stopName || s['站點'] || `第${idx+1}站`,
      order: Number(s.order ?? s['站次'] ?? (idx+1)),
      latitude: Number(s.latitude ?? s['去程緯度'] ?? s['緯度']),
      longitude: Number(s.longitude ?? s['去程經度'] ?? s['經度']),
      etaFromStart: s.etaFromStart ?? s['首站到此站時間'] ?? null,
      etaToHere: s.etaToHere ?? null,
      schedule: s.schedule || s['schedule'] || s['時刻表'] || "", // 👈 新增這行
    }))


    const car = cars.find(c =>
      String(c.route) === String(route.id) ||
      String(c.route) === String(route.route_id) ||
      String(c.route) === String(route.name)
    )

    if (!car) {
      return unified.map(s => ({
        ...s,
        status: { label: "未發車", tone: "orange" }
      }))
    }

    // 如果方向不符 → 全部顯示未發車
    if (car.direction !== selectedDir) {
      return unified.map(s => ({
        ...s,
        status: { label: "未發車", tone: "orange" }
      }))
    }

    // 找到目前所在站
    let currentIndex = unified.findIndex(s => s.name === car.currentLocation)

    return unified.map((s, idx) => {
      const now = dayjs()
      const scheduleStr = s.schedule || s.full_schedule || ""
      const times = scheduleStr
        .split(",")
        .map((t) => dayjs(t.trim(), "HH:mm"))
        .filter((t) => t.isValid())

      const next = times.find((t) => t.isAfter(now)) || times[times.length - 1]
      const nextTimeLabel = next ? next.format("HH:mm") : "-"

      if (idx === currentIndex) {
        return { ...s, status: { label: "到站中", tone: "green" } }
      } else {
        return { ...s, status: { label: `下一班時間 ${nextTimeLabel}`, tone: "blue" } }
      }

    })

  }, [isStatic, list, stops, cars, route.id, selectedDir])

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

  if (initialLoading) {
    return (
      <div className="route-detail-overlay" role="dialog" aria-modal="true">
        <div className="route-detail-panel" style={{ display:'flex', alignItems:'center', justifyContent:'center', height:'60vh' }}>
          <div className="spinner" />
          <div className="muted small" style={{ marginTop:8 }}>載入中…</div>
        </div>
      </div>
    )
  }
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
            <button
              className="btn"
              onClick={() => setViewMode(viewMode === 'list' ? 'map' : 'list')}
              style={{
                marginRight: 8,
                backgroundColor: viewMode === 'list' ? '#007bff' : '#ffa726',
                color: '#fff'
              }}
            >
              {viewMode === 'list' ? '地圖' : '列表'}
            </button>
            <button className="btn btn-orange" onClick={onClose}>關閉</button>
          </div>
        </div>

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
              <RouteMap stops={stops} cars={cars} route={route} />
            ) : (
              <div className="stops-list">
                {loading && <div className="muted">載入中…</div>}
                {error && <div className="muted" style={{ color: '#c25' }}>{error}</div>}
                {loading && (
                  <div className="spinner-container">
                    <div className="spinner" />
                    <span className="muted small">載入車輛位置中…</span>
                  </div>
                )}

                {displayStops.map((s, idx) => {
                const isHighlight =
                  highlightStop !== null &&
                  highlightStop !== undefined &&
                  (s.order === highlightStop ||
                  s.stop_order === highlightStop ||
                  Number(s['站次']) === highlightStop)

                  return (
                    <div
                      key={idx}
                      className="stop-item"
                      style={isHighlight ? { border: '2px solid red', borderRadius: '8px' } : {}}
                    >
                      <div className="stop-left">
                        <div className="stop-name">{s.name}</div>
                        <div className="muted small">
                          第 {s.order ?? (idx + 1)} 站 • 首站起 {s.etaFromStart ?? '-'} 分鐘
                        </div>
                      </div>
                      <div className="stop-right">
                        <span
                          className="muted small"
                          style={{
                            padding: '2px 8px',
                            borderRadius: 12,
                            background:
                              s.status.tone === 'green'
                                ? '#e7f7ec'
                                : s.status.tone === 'orange'
                                ? '#fff2e5'
                                : s.status.tone === 'blue'
                                ? '#eaf2ff'
                                : '#f2f3f5',
                            color:
                              s.status.tone === 'green'
                                ? '#16794c'
                                : s.status.tone === 'orange'
                                ? '#a24a00'
                                : s.status.tone === 'blue'
                                ? '#1d4ed8'
                                : '#6b7280',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {s.status.label}
                        </span>
                      </div>
                    </div>
                  )
                })}
                {!loading && displayStops.length === 0 && !error && (
                  <div className="muted">此方向目前無站點資料</div>
                )}
              </div>
            )}
          </>
        ) : (
          viewMode === 'map' ? (
            <RouteMap stops={staticStopsForMap} cars={cars} route={route} />
          ) : (
            <div className="stops-list">
              {displayStops.map((s, idx) => (
                <div key={idx} className="stop-item">
                  <div className="stop-left">
                    <div className="stop-name">{s.name}</div>
                    <div className="muted small">
                      第 {s.order ?? (idx + 1)} 站 • 首站起 {s.etaFromStart ?? '-'} 分鐘
                    </div>
                  </div>
                  <div className="stop-right">
                    <span
                      className="muted small"
                      style={{
                        padding: '2px 8px',
                        borderRadius: 12,
                        background:
                          s.status.tone === 'green'
                            ? '#e7f7ec'
                            : s.status.tone === 'orange'
                            ? '#fff2e5'
                            : s.status.tone === 'blue'
                            ? '#eaf2ff'
                            : '#f2f3f5',
                        color:
                          s.status.tone === 'green'
                            ? '#16794c'
                            : s.status.tone === 'orange'
                            ? '#a24a00'
                            : s.status.tone === 'blue'
                            ? '#1d4ed8'
                            : '#6b7280',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {s.status.label}
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

function RouteMap({ stops, cars, route }) {
  const ready = useLeaflet()
  const elRef = useRef(null)
  const mapRef = useRef(null)
  const layerRouteRef = useRef(null)
  const layerStopsRef = useRef(null)
  const layerBusRef = useRef(null)

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

  // (A) 畫路線 + 站點，只在 stops 改變時觸發
  useEffect(() => {
    if (!ready || !mapRef.current) return
    const L = window.L
    const routeLayer = layerRouteRef.current
    const stopLayer = layerStopsRef.current
    routeLayer.clearLayers(); stopLayer.clearLayers()

    const ordered = (stops || []).slice().sort((a,b) => (a.order ?? a.stop_order ?? 0) - (b.order ?? b.stop_order ?? 0))
    const llOriginal = ordered.map(s => {
      const lat = Number(s.latitude ?? s.lat)
      const lng = Number(s.longitude ?? s.lng)
      return Number.isFinite(lat) && Number.isFinite(lng) ? [lat, lng] : null
    }).filter(Boolean)

    async function drawFullRoute() {
      if (llOriginal.length < 2) return
      await import('leaflet-polylinedecorator')

      let shapeCoords = route.shape // ← 後端 API 帶回來的完整 shape

      if (!shapeCoords || shapeCoords.length === 0) {
        // fallback：一次丟全部站點給 OSRM
        const coords = llOriginal.map(p => `${p[1]},${p[0]}`).join(";")
        const url = `https://router.project-osrm.org/route/v1/driving/${coords}?overview=full&geometries=geojson`
        try {
          const res = await fetch(url)
          const data = await res.json()
          if (data.routes && data.routes[0]?.geometry) {
            shapeCoords = data.routes[0].geometry.coordinates.map(([lng, lat]) => [lat, lng])
          }
        } catch (err) {
          console.warn("OSRM 失敗，退回直線", err)
          shapeCoords = llOriginal
        }
      }

      if (shapeCoords && shapeCoords.length > 0) {
        const stroke = L.polyline(shapeCoords, { color:'#2563eb', weight:7, opacity:.98 }).addTo(layerRouteRef.current)
        if (L.polylineDecorator) {
          L.polylineDecorator(stroke, {
            patterns: [{ offset:0, repeat:'48px', symbol: L.Symbol.arrowHead({ pixelSize:11, pathOptions:{ color:'#2563eb', weight:6 } }) }]
          }).addTo(layerRouteRef.current)
        }
        mapRef.current.fitBounds(stroke.getBounds(), { padding:[30,30] })
      }
    }


    drawFullRoute()

    // 畫站點
    const icon = (label, cls='') => L.divIcon({
      className:'',
      html:`<div class="stop-badge ${cls}">${label}</div>`,
      iconSize:[24,24], iconAnchor:[12,12]
    })
    ordered.forEach((s, idx) => {
      const p = llOriginal[idx]; if (!p) return
      const isFirst = idx===0, isLast = idx===ordered.length-1
      const label = isFirst ? 'S' : (s.order ?? s.stop_order ?? idx+1)
      const cls = isFirst ? 'stop-start' : (isLast ? 'stop-end' : '')
      L.marker(p, { icon: icon(label, cls) }).addTo(stopLayer).bindTooltip(`${s.stopName || s.stop_name || '站點'}`, { direction:'top' })
    })
  }, [ready, stops])

  // (B) 畫公車，只在 cars 改變時觸發
  useEffect(() => {
    if (!ready || !mapRef.current) return
    const L = window.L
    const busLayer = layerBusRef.current
    busLayer.clearLayers()

    cars.filter(c =>
      String(c.route) === String(route.id) ||
      String(c.route) === String(route.route_id) ||
      String(c.route) === String(route.name)
    ).forEach(car => {
      const busPt = [car.Y, car.X]
      const html = `
        <div class="bus-wrap">
          <div class="bus-pulse"></div>
          <div class="bus-dot"></div>
          <div class="bus-emoji">🚌</div>
          <div class="bus-badge">${car.direction}</div>
        </div>`
      L.marker(busPt, { icon: L.divIcon({ className:'', html, iconSize:[1,1] }) }).addTo(busLayer)
      L.circle(busPt, { radius:50, color:'#2563eb', weight:1, fillColor:'#2563eb', fillOpacity:.08 }).addTo(busLayer)
    })
  }, [ready, cars, route])

  return <div style={{ height:'60vh', borderRadius:12, overflow:'hidden' }} ref={elRef} />
}
