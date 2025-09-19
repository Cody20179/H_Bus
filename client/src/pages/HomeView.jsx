// src/pages/HomeView.jsx
import React from 'react'
import BottomNav from '../components/BottomNav'
import { getMyReservations, getStations } from '../services/api'

export default function HomeView({ onAction, user }) {
  const [tomorrowReservations, setTomorrowReservations] = React.useState([])
  const [nearbyStops, setNearbyStops] = React.useState([])
  const [locationError, setLocationError] = React.useState('')

  React.useEffect(() => {
    const uid = user?.user_id || user?.id
    if (!uid) return

    getMyReservations(uid).then(rows => {
      const tomorrow = new Date()
      tomorrow.setDate(tomorrow.getDate() + 1)

      const yyyy = tomorrow.getFullYear()
      const mm = tomorrow.getMonth() + 1
      const dd = tomorrow.getDate()

      const filtered = rows.filter(r => {
        const d = new Date(r.booking_time)
        if (isNaN(d)) return false
        return (
          d.getFullYear() === yyyy &&
          d.getMonth() + 1 === mm &&
          d.getDate() === dd
        )
      })

      setTomorrowReservations(filtered)
    }).catch(e => console.warn("載入明日預約失敗", e))
  }, [user])

  // --- 計算距離（Haversine formula） ---
  function haversine(lat1, lon1, lat2, lon2) {
    const R = 6371e3 // 地球半徑（公尺）
    const toRad = (d) => (d * Math.PI) / 180
    const φ1 = toRad(lat1), φ2 = toRad(lat2)
    const Δφ = toRad(lat2 - lat1)
    const Δλ = toRad(lon2 - lon1)
    const a = Math.sin(Δφ/2) * Math.sin(Δφ/2) +
              Math.cos(φ1) * Math.cos(φ2) *
              Math.sin(Δλ/2) * Math.sin(Δλ/2)
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a))
    return R * c
  }

  // --- 取得附近站點 ---
  async function handleNearbyStops() {
    try {
      setLocationError('')
      if (!navigator.geolocation) {
        setLocationError('瀏覽器不支援定位功能')
        return
      }
      navigator.geolocation.getCurrentPosition(async (pos) => {
        const { latitude, longitude } = pos.coords
        const stations = await getStations()
        const withDist = stations.map(s => ({
          ...s,
          distance: haversine(latitude, longitude, s.lat, s.lng)
        }))
        const nearest = withDist.sort((a, b) => a.distance - b.distance).slice(0, 5)
        setNearbyStops(nearest)
      }, (err) => {
        setLocationError('定位失敗：' + err.message)
      })
    } catch (e) {
      setLocationError('錯誤：' + e.message)
    }
  }

  return (
    <main className="container">
      {/* 搜尋區塊 */}
      <section className="search-section">
        <div
          className="search-input"
          role="button"
          tabIndex={0}
          onClick={() => onAction('搜尋框')}
        >
          搜尋路線、站點或目的地
        </div>
        <div className="search-actions">
          <button className="btn btn-blue" onClick={handleNearbyStops}>附近站點</button>
          <button className="btn btn-orange" onClick={() => onAction('常用路線')}>常用路線</button>
        </div>
      </section>

      {/* 定位錯誤 */}
      {locationError && (
        <div className="small" style={{ color: 'red', marginTop: 8 }}>{locationError}</div>
      )}

      {/* 附近站點結果 */}
      {nearbyStops.length > 0 && (
        <section className="card">
          <div className="card-title"><span>最近的 5 個站點</span></div>
          <div className="card-body">
            {nearbyStops.map(s => (
              <div key={s.id} className="item">
                <div>{s.name}</div>
                <div className="small muted">
                  {s.address} ・ 距離 {(s.distance/1000).toFixed(2)} km
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* 明日預約區塊 */}
      {tomorrowReservations.length > 0 && (
        <section className="card">
          <div className="card-title"><span>明日預約</span></div>
          <div className="card-body">
            {tomorrowReservations.map(r => (
              <div key={r.reservation_id} className="item">
                <div>{r.booking_start_station_name} → {r.booking_end_station_name}</div>
                <div className="small muted">{r.booking_time} ・ {r.booking_number} 人</div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* 這裡還可以放即時到站卡片與公告 */}
    </main>
  )
}
