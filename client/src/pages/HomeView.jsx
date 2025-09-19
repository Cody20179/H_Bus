// src/pages/HomeView.jsx
import React from 'react'
import BottomNav from '../components/BottomNav'
import { getMyReservations } from '../services/api'

export default function HomeView({ onAction, user }) {
  const [tomorrowReservations, setTomorrowReservations] = React.useState([])

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
          <button className="btn btn-blue" onClick={() => onAction('附近站點')}>附近站點</button>
          <button className="btn btn-orange" onClick={() => onAction('常用路線')}>常用路線</button>
        </div>
      </section>

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
