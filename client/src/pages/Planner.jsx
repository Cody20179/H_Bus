import React, { useEffect, useRef, useState } from 'react'
import { getRoutes, getRouteStops } from '../services/api'

async function osrmRouteBetween(a, b) {
  // a/b = [lat, lng]
  const coords = `${a[1]},${a[0]};${b[1]},${b[0]}`;
  const url = `https://router.project-osrm.org/route/v1/driving/${coords}` +
              `?overview=full&geometries=geojson&steps=false&continue_straight=true`;
  const r = await fetch(url);
  if (!r.ok) throw new Error('OSRM segment fail');
  const j = await r.json();
  if (!(j.routes && j.routes[0])) throw new Error('No segment route');
  return j.routes[0]; // {geometry, distance, duration}
}

async function osrmRouteByLegs(points) {
  // points: [[lat,lng], ...] (至少兩點)
  let merged = [];
  let totalDist = 0, totalDur = 0;
  for (let i = 0; i < points.length - 1; i++) {
    try {
      const seg = await osrmRouteBetween(points[i], points[i+1]);
      const segCoords = seg.geometry.coordinates; // [lng,lat]
      if (i === 0) merged = segCoords;
      else merged = merged.concat(segCoords.slice(1)); // 避免交界重複點
      totalDist += seg.distance;
      totalDur  += seg.duration;
    } catch {
      // 備援：畫直線把這一段補起來
      merged.push([points[i+1][1], points[i+1][0]]);
    }
  }
  return {
    geometry: { type: 'LineString', coordinates: merged },
    distance: totalDist,
    duration: totalDur,
  };
}


// Module-based loaders to avoid ORB/CORS issues
async function ensureLeafletLoaded() {
  if (window.L) return window.L
  const mod = await import('leaflet')
  const L = mod.default ?? mod
  // expose to legacy code expecting window.L
  window.L = L
  return L
}

async function ensurePolylineDecorator() {
  if (window.L && window.L.polylineDecorator) return true
  // side-effect import registers plugin onto L
  await import('leaflet-polylinedecorator')
  return true
}

export default function PlannerPage() {
  const mapEl = useRef(null)
  const mapRef = useRef(null)
  const routeLayerRef = useRef(null)
  const stopLayerRef = useRef(null)
  const [routes, setRoutes] = useState([])
  const [routeId, setRouteId] = useState(null)
  const [direction, setDirection] = useState('去程')
  const [busText, setBusText] = useState('')
  const [followBus, setFollowBus] = useState(false)
  const busLayerRef = useRef(null)
  const [ptCount, setPtCount] = useState(0)
  const [dist, setDist] = useState('—')
  const [dur, setDur] = useState('—')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [mapReady, setMapReady] = useState(false)

  useEffect(() => {
    let destroyed = false
    ensureLeafletLoaded().then((L) => {
      if (destroyed) return
      const map = L.map(mapEl.current, { center:[23.99302,121.603219], zoom:14 })
      mapRef.current = map
      const emap = L.tileLayer(
        'https://wmts.nlsc.gov.tw/wmts/EMAP/default/GoogleMapsCompatible/{z}/{y}/{x}',
        { tileSize:256, attribution:'Leaflet | © NLSC WMTS | © OpenStreetMap' }
      ).addTo(map)
      const emap2 = L.tileLayer(
        'https://wmts.nlsc.gov.tw/wmts/EMAP2/default/GoogleMapsCompatible/{z}/{y}/{x}',
        { tileSize:256, opacity:.9 }
      ).addTo(map)

      const routeLayer = L.layerGroup().addTo(map)
      const stopLayer = L.layerGroup().addTo(map)
      const busLayer = L.layerGroup().addTo(map)
      routeLayerRef.current = routeLayer
      stopLayerRef.current = stopLayer
      busLayerRef.current = busLayer
      setMapReady(true)
    })

    return () => {
      destroyed = true
      if (mapRef.current) {
        mapRef.current.remove()
        mapRef.current = null
      }
    }
  }, [])

  // load route list for selection
  useEffect(() => {
    let cancelled = false
    getRoutes().then((rs) => {
      if (cancelled) return
      setRoutes(rs)
      if (rs.length && routeId == null) setRouteId(rs[0].id)
    }).catch((e) => {
      console.log('讀取路線列表失敗', e)
    })
    return () => { cancelled = true }
  }, [])

  // draw selected route from stops
  const drawSelected = async () => {
    if (!mapRef.current || !routeLayerRef.current || !stopLayerRef.current) return
    if (!routeId) return
    setLoading(true); setError(null)
    try {
      const stops = await getRouteStops(routeId, direction)
      // 依站次排序，並去重（相同座標只保留第一筆，避免重複點位）
      const ordered = stops
        .slice()
        .sort((a,b) => (a.stop_order ?? a.order ?? 0) - (b.stop_order ?? b.order ?? 0))

      // De-duplicate stops by proximity (merge points within ~20m)
      const unique = []
      for (const s of ordered) {
        const lat = Number(s.latitude), lng = Number(s.longitude)
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) continue
        const tooClose = unique.some(u => haversine([lat, lng], [Number(u.latitude), Number(u.longitude)]) < 0.02)
        if (!tooClose) unique.push(s)
      }

      const latlngs = unique
        .map(s => [Number(s.latitude), Number(s.longitude)])
        .filter(([lat, lng]) => Number.isFinite(lat) && Number.isFinite(lng))

      const map = mapRef.current
      const L = window.L
      const routeLayer = routeLayerRef.current
      const stopLayer = stopLayerRef.current
      const busLayer = busLayerRef.current
      routeLayer.clearLayers(); stopLayer.clearLayers(); busLayer.clearLayers()

      // Optional bus location parsing: "lat,lon"
      let busLL = null
      const m = (busText || '').trim().match(/(-?\d+(?:\.\d+)?)[,\s]+(-?\d+(?:\.\d+)?)/)
      if (m) busLL = [parseFloat(m[1]), parseFloat(m[2])]

      // If bus present, include as first point for OSRM routing reference
      const forOsrm = [...(busLL ? [busLL] : []), ...latlngs]

      // If we have at least 2 points, fetch OSRM actual route
let fitBoundsHandled = false;
if (forOsrm.length >= 2) {
  await ensurePolylineDecorator();
  // 直接採用「逐段合併」以提高成功率（多點 OSRM 一次性易失敗）
  const routeResult = await osrmRouteByLegs(forOsrm)
  if (routeResult && routeResult.geometry) {
    const stroke = drawRouteWithArrows(L, routeLayer, routeResult.geometry, 'nav')
    map.fitBounds(stroke.getBounds(), { padding:[30,30] })
    fitBoundsHandled = true
    if (typeof routeResult.distance === 'number') setDist(`${(routeResult.distance/1000).toFixed(2)} km`)
    if (typeof routeResult.duration === 'number') setDur(`${Math.round(routeResult.duration/60)} 分鐘`)
  }
}
if (!fitBoundsHandled && latlngs.length >= 2) {
  // 畫備援直線（避免只剩點沒有線）
  const fallback = L.polyline(latlngs, { color:'#94a3b8', weight:4, opacity:0.8, dashArray:'6 8' })
    .addTo(routeLayer);
  map.fitBounds(fallback.getBounds(), { padding:[30,30] });
  fitBoundsHandled = true;
}


      if (!fitBoundsHandled && latlngs.length) {
        map.setView(latlngs[0], 15)
      }

      // add stop markers
      unique.forEach((s, idx) => {
        if (!Number.isFinite(s.latitude) || !Number.isFinite(s.longitude)) return
        L.circleMarker([s.latitude, s.longitude], {
          radius: 5,
          color: '#0033A0',
          weight: 2,
          fillColor: '#eaf2ff',
          fillOpacity: 0.9,
        }).addTo(stopLayer).bindTooltip(`${s.stopName || '站點'}（第${s.order ?? (idx+1)}站）`, { direction:'top' })
      })

      // compute simple sums
      setPtCount(latlngs.length)
      if (!forOsrm.length || forOsrm.length < 2) {
        setDist(`${(sumDistanceKm(latlngs)).toFixed(2)} km`)
      }
      const lastEta = unique.reduce((m, s) => Math.max(m, Number(s.eta_from_start ?? s.etaFromStart) || 0), 0)
      setDur(`${Math.round(lastEta)} 分鐘`)

      // draw bus marker (pulse) if provided
      if (busLL) {
        setBusMarker(L, busLayer, busLL, followBus, map)
      }
    } catch (e) {
      console.log('載入站點/繪製路線失敗', e)
      setError('無法載入此路線站點')
      setPtCount(0); setDist('—'); setDur('—')
    } finally {
      setLoading(false)
    }
  }

  function sumDistanceKm(latlngs) {
    let total = 0
    for (let i=1; i<latlngs.length; i++) {
      total += haversine(latlngs[i-1], latlngs[i])
    }
    return total
  }

  function haversine(a, b) {
    const R = 6371 // km
    const [lat1, lon1] = a
    const [lat2, lon2] = b
    const dLat = (lat2-lat1) * Math.PI/180
    const dLon = (lon2-lon1) * Math.PI/180
    const s1 = Math.sin(dLat/2)**2 + Math.cos(lat1*Math.PI/180)*Math.cos(lat2*Math.PI/180)*Math.sin(dLon/2)**2
    const c = 2 * Math.atan2(Math.sqrt(s1), Math.sqrt(1-s1))
    return R * c
  }

  useEffect(() => {
    if (mapReady) drawSelected()
  }, [routeId, direction, mapReady])

  // Helpers ported from Test2.html for visual styles
  function drawRouteWithArrows(L, layer, geojson, theme='nav') {
    const themes = {
      nav:   { casing: '#ffffff', stroke: '#2563eb' },
      green: { casing: '#ffffff', stroke: '#10b981' },
      night: { casing: '#0b0b10', stroke: '#ffd166' },
      dashed:{ casing: '#ffffff', stroke: '#6366f1', dashArray: '8 8' },
    }
    const t = themes[theme] || themes.nav
    const casing = L.geoJSON(geojson, { style:{ color:t.casing, weight:12, opacity:1, lineCap:'round', lineJoin:'round' }}).addTo(layer)
    const stroke = L.geoJSON(geojson, { style:{ color:t.stroke, weight:7, opacity:.98, lineCap:'round', lineJoin:'round', dashArray:t.dashArray } }).addTo(layer)
    try {
      if (L.polylineDecorator) {
        const poly = stroke.getLayers()[0]
        if (poly) {
          L.polylineDecorator(poly, { patterns:[{ offset:0, repeat:'48px', symbol: L.Symbol.arrowHead({ pixelSize:11, pathOptions:{ color:t.stroke, weight:6, opacity:0.95 } }) }] }).addTo(layer)
        }
      }
    } catch {}
    return stroke
  }

  function setBusMarker(L, busLayer, latlng, follow, map) {
    const [lat, lng] = latlng
    const html = `
      <div class="bus-wrap">
        <div class="bus-pulse"></div>
        <div class="bus-acc"></div>
        <div class="bus-dot"></div>
        <div class="bus-emoji">🚌</div>
        <div class="bus-badge">BUS</div>
      </div>`
    L.marker([lat, lng], { icon: L.divIcon({ className:'', html, iconSize:[1,1] }) }).addTo(busLayer)
    L.circle([lat, lng], { radius:50, color:'#2563eb', weight:1, fillColor:'#2563eb', fillOpacity:.08 }).addTo(busLayer)
    if (follow) map.setView([lat, lng], Math.max(map.getZoom(), 16), { animate:true })
  }

  return (
    <div className="container">
      <section className="card">
        <div className="card-title"><span>公車路線地圖</span></div>
        <div className="card-body" style={{ display:'flex', gap:8, flexWrap:'wrap', alignItems:'center' }}>
          <select value={routeId ?? ''} onChange={(e) => setRouteId(Number(e.target.value) || null)} className="search-field" style={{ maxWidth: '70%' }}>
            {routes.map(r => (
              <option key={r.id} value={r.id}>{r.name}</option>
            ))}
          </select>
          <div style={{ display:'flex', gap:8 }}>
            <button className={`btn ${direction === '去程' ? 'btn-blue' : ''}`} onClick={() => setDirection('去程')}>去程</button>
            <button className={`btn ${direction === '回程' ? 'btn-blue' : ''}`} onClick={() => setDirection('回程')}>回程</button>
          </div>
          <input value={busText} onChange={(e) => setBusText(e.target.value)} placeholder="公車位置 lat,lon（可空）" className="search-field" style={{ maxWidth: 220 }} />
          <button className={`btn ${followBus ? 'btn-orange' : ''}`} onClick={() => setFollowBus(v => !v)}>{followBus ? '取消跟隨' : '跟隨公車'}</button>
          <button className="btn" onClick={drawSelected} disabled={loading}>{loading ? '載入中…' : '顯示路線'}</button>
          {error && <span className="muted small" style={{ color:'#c25' }}>{error}</span>}
        </div>
      </section>

      <section className="card">
        <div className="card-title"><span>地圖</span><small>顯示選擇路線</small></div>
        <div ref={mapEl} style={{ height:'68vh', width:'100%', borderRadius:12, overflow:'hidden' }} />
      </section>

      <section className="card">
        <div className="card-title"><span>路線資訊</span></div>
        <div className="card-body" style={{ display:'flex', gap:16 }}>
          <div>站點數：<strong>{ptCount}</strong></div>
          <div>總距離：<strong>{dist}</strong></div>
          <div>預估時間：<strong>{dur}</strong></div>
        </div>
      </section>
    </div>
  )
}
