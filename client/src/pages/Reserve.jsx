import React, { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getStations, createReservation } from '../services/api'

// 從 Planner.jsx 照抄的：動態載入 Leaflet 與 polyline decorator
async function ensureLeafletLoaded() {
  if (window.L) return window.L
  const mod = await import('leaflet')
  const L = mod.default ?? mod
  window.L = L
  return L
}

async function ensurePolylineDecorator() {
  if (window.L && window.L.polylineDecorator) return true
  await import('leaflet-polylinedecorator')
  return true
}

// OSRM 單段路徑（兩點）
async function osrmRouteBetween(a, b) {
  // a/b = [lat, lng]
  const coords = `${a[1]},${a[0]};${b[1]},${b[0]}`
  const url = `https://router.project-osrm.org/route/v1/driving/${coords}` +
              `?overview=full&geometries=geojson&steps=false&continue_straight=true`
  const r = await fetch(url)
  if (!r.ok) throw new Error('OSRM fail')
  const j = await r.json()
  if (!(j.routes && j.routes[0])) throw new Error('No route')
  return j.routes[0]
}

// 畫主要路線＋箭頭樣式（與 Planner.jsx 一致）
function drawRouteWithArrows(L, layer, geojson, theme = 'nav') {
  const themes = {
    nav: { casing: '#ffffff', stroke: '#2563eb' },
    green: { casing: '#ffffff', stroke: '#10b981' },
    night: { casing: '#0b0b10', stroke: '#ffd166' },
    dashed: { casing: '#ffffff', stroke: '#6366f1', dashArray: '8 8' },
  }
  const t = themes[theme] || themes.nav
  L.geoJSON(geojson, { style: { color: t.casing, weight: 12, opacity: 1, lineCap: 'round', lineJoin: 'round' } }).addTo(layer)
  const stroke = L.geoJSON(geojson, { style: { color: t.stroke, weight: 7, opacity: .98, lineCap: 'round', lineJoin: 'round', dashArray: t.dashArray } }).addTo(layer)
  try {
    if (L.polylineDecorator) {
      const poly = stroke.getLayers()[0]
      if (poly) {
        L.polylineDecorator(poly, {
          patterns: [{ offset: 0, repeat: '48px', symbol: L.Symbol.arrowHead({ pixelSize: 11, pathOptions: { color: t.stroke, weight: 6, opacity: 0.95 } }) }]
        }).addTo(layer)
      }
    }
  } catch { }
  return stroke
}

export default function ReservePage({ user, onRequireLogin }) {
  const navigate = useNavigate()
  const AUTH_BASE = import.meta.env.VITE_AUTH_BASE_URL || '';
  // 未登入：維持原行為
  if (!user) {
    return (
      <div className="container">
        <section className="card">
          <div className="card-title"><span>預約服務</span></div>
          <div className="card-body">
            <div className="muted" style={{ marginBottom: 12 }}>尚未登入，無法使用預約功能。</div>
            <button className="btn btn-blue" onClick={onRequireLogin}>前往登入</button>
          </div>
        </section>
      </div>
    )
  }

  // 站點/表單狀態
  const [stations, setStations] = useState([])
  const [fromId, setFromId] = useState('')
  const [toId, setToId] = useState('')
  const [when, setWhen] = useState('')
  const [people, setPeople] = useState(1)
  const [hint, setHint] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  // 地圖
  const mapEl = useRef(null)
  const mapRef = useRef(null)
  const routeLayerRef = useRef(null)

  // 載入站點清單
  useEffect(() => {
    let cancelled = false
    getStations().then((rows) => {
      if (!cancelled) setStations(rows)
    }).catch((e) => console.warn('取得站點失敗', e))
    return () => { cancelled = true }
  }, [])

  // 初始化地圖（與 Planner.jsx 一致的底圖）
  useEffect(() => {
    let destroyed = false
    ensureLeafletLoaded().then((L) => {
      if (destroyed) return
      const map = L.map(mapEl.current, { center: [23.99302, 121.603219], zoom: 14 })
      mapRef.current = map
      L.tileLayer('https://wmts.nlsc.gov.tw/wmts/EMAP/default/GoogleMapsCompatible/{z}/{y}/{x}', { tileSize: 256, attribution: 'Leaflet | © NLSC WMTS | © OpenStreetMap' }).addTo(map)
      L.tileLayer('https://wmts.nlsc.gov.tw/wmts/EMAP2/default/GoogleMapsCompatible/{z}/{y}/{x}', { tileSize: 256, opacity: .9 }).addTo(map)
      routeLayerRef.current = L.layerGroup().addTo(map)
    })
    return () => {
      destroyed = true
      if (mapRef.current) {
        mapRef.current.remove()
        mapRef.current = null
      }
    }
  }, [])

  async function drawRoute(from, to) {
    if (!mapRef.current || !routeLayerRef.current) return
    const L = window.L
    const map = mapRef.current
    const layer = routeLayerRef.current
    layer.clearLayers()
    try {
      await ensurePolylineDecorator()
      const result = await osrmRouteBetween([from.lat, from.lng], [to.lat, to.lng])
      if (result && result.geometry) {
        const stroke = drawRouteWithArrows(L, layer, result.geometry, 'nav')
        map.fitBounds(stroke.getBounds(), { padding: [30, 30], animate: false })
        return
      }
    } catch (e) {
      console.warn('OSRM 路線失敗，改用直線備援', e)
    }
    // 備援：直線
    const poly = L.polyline([[from.lat, from.lng], [to.lat, to.lng]], { color: '#94a3b8', weight: 4, opacity: 0.85, dashArray: '6 8' }).addTo(layer)
    map.fitBounds(poly.getBounds(), { padding: [30, 30], animate: false })
  }

  function validateSelection() {
    setError('')
    const from = stations.find((s) => String(s.id) === String(fromId))
    const to = stations.find((s) => String(s.id) === String(toId))
    if (!from || !to) { setError('請選擇出發與目的地'); return null }
    if (String(fromId) === String(toId)) { setError('請選擇不同點位'); return null }
    return { from, to }
  }

  async function handleViewRoute(e) {
    e.preventDefault()
    const v = validateSelection()
    if (!v) return
    setHint('')
    setLoading(true)
    try {
      await drawRoute(v.from, v.to)
    } finally {
      setLoading(false)
    }
  }

  async function handleSubmit(e) {
    e.preventDefault()
    const v = validateSelection()
    if (!v) return
    if (!when || !people) { setError('請填寫預約時間與人數'); return }

    // 確認送出
    const ok = window.confirm('確認送出預約？\n送出後將進入審核流程。')
    if (!ok) return

    setHint('您的預約正在審核中，審核完畢會另行通知。')
    setLoading(true)
    try {
      await drawRoute(v.from, v.to)
      // 取得 user_id（建議從 /me 取得，這裡直接用 user.user_id）
      const effectiveUserId = user?.user_id || user?.id || 0
      if (!effectiveUserId) {
        setError('找不到使用者 ID，請重新登入')
        return
      }
      // 呼叫 /reservation API（自動判斷 proxy 路徑，支援 VITE_AUTH_BASE_URL）
      const params = new URLSearchParams({
        user_id: effectiveUserId,
        booking_time: when,
        booking_number: String(people),
        booking_start_station_name: v.from.name,
        booking_end_station_name: v.to.name,
      })
      // const apiUrl = AUTH_BASE ? `${AUTH_BASE}/reservation` : '/api/reservation';
      const resp = await fetch(`/api/reservation?${params.toString()}`, {
        method: 'POST'
      })
      const data = await resp.json().catch(()=> ({}))
      if (!resp.ok || data.status !== 'success') {
        setError('預約送出失敗，請稍後再試')
        return
      }
      // 導向「我的預約」，並顯示提示訊息
      navigate('/profile?tab=reservations', { state: { toast: '已送出預約，等待審核中。' } })
    } catch (e) {
      setError('建立預約 API 失敗，請稍後再試')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container">
      <section className="card">
        <div className="card-title"><span>預約服務</span></div>
        <div className="card-body">
          <form onSubmit={handleSubmit} style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
            <div>
              <div className="muted small">站點 1（出發）</div>
              <select className="search-field" value={fromId} onChange={(e) => { setFromId(e.target.value); setHint('') }}>
                <option value="">請選擇</option>
                {stations.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>
            <div>
              <div className="muted small">站點 2（目的）</div>
              <select className="search-field" value={toId} onChange={(e) => { setToId(e.target.value); setHint('') }}>
                <option value="">請選擇</option>
                {stations.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>
            <div>
              <div className="muted small">預約時間</div>
              <input type="datetime-local" className="search-field" value={when} onChange={(e) => { setWhen(e.target.value); setHint('') }} />
            </div>
            <div>
              <div className="muted small">人數</div>
              <input type="number" min={1} className="search-field" value={people} onChange={(e) => { setPeople(e.target.value); setHint('') }} />
            </div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'end', flexWrap: 'wrap' }}>
              <button className="btn" onClick={handleViewRoute} disabled={loading}>
                {loading ? '處理中…' : '查看路線'}
              </button>
              <button className="btn btn-orange" type="submit" disabled={loading || !fromId || !toId || !when || !people}>
                {loading ? '處理中…' : '送出預約'}
              </button>
              {error && <span className="small" style={{ color: '#c0392b' }}>{error}</span>}
              {hint && <span className="muted">{hint}</span>}
            </div>
          </form>
        </div>
      </section>

      <section className="card">
        <div className="card-title"><span>地圖</span><small>顯示您選取的路線</small></div>
        <div ref={mapEl} style={{ height: '60vh', width: '100%', borderRadius: 12, overflow: 'hidden' }} />
      </section>
    </div>
  )
}
