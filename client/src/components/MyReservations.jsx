// src/components/MyReservations.jsx
import React, { useState, useEffect } from 'react'
import { getMyReservations, cancelReservation } from '../services/api'

export default function MyReservations({ user, filterExpired = false }) {
  const [myResv, setMyResv] = useState([])
  const [resvLoading, setResvLoading] = useState(false)
  const [resvErr, setResvErr] = useState('')
  const [selectedResv, setSelectedResv] = useState(null)
  const [showRouteModal, setShowRouteModal] = useState(false)
  const [cancelTarget, setCancelTarget] = useState(null)
  const [cancelReason, setCancelReason] = useState('')
  const [refreshTick, setRefreshTick] = useState(0)
  const AUTO_REFRESH_MS = 30000

  useEffect(() => {
    const uid = user?.user_id || user?.id
    if (!uid) return
    let cancelled = false
    const load = async () => {
      if (refreshTick === 0) setResvLoading(true)
      setResvErr('')
      try {
        const data = await getMyReservations(uid)
        if (!cancelled) setMyResv(data)
      } catch (e) {
        if (!cancelled) setResvErr(String(e.message || e))
      } finally {
        if (!cancelled) setResvLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [user, refreshTick])

  useEffect(() => {
    setRefreshTick(0)
    const uid = user?.user_id || user?.id
    if (!uid) return
    const id = setInterval(() => {
      setRefreshTick((t) => (t + 1) % 1_000_000)
    }, AUTO_REFRESH_MS)
    return () => clearInterval(id)
  }, [user])

  const fmt = (s) => {
    try {
      if (!s) return '-'
      const d = new Date(s)
      if (isNaN(d)) return String(s)
      const y = d.getFullYear()
      const M = String(d.getMonth()+1).padStart(2,'0')
      const D = String(d.getDate()).padStart(2,'0')
      const h = String(d.getHours()).padStart(2,'0')
      const m = String(d.getMinutes()).padStart(2,'0')
      return `${y}-${M}-${D} ${h}:${m}`
    } catch { return String(s) }
  }

  const now = new Date()
  const visibleResv = filterExpired
    ? myResv.filter(r => {
        const t = new Date(r.booking_time)
        return !isNaN(t) && t >= now
      })
    : myResv

  return (
    <section className="card">
      <div className="card-title">
        <span>我的預約</span>
      </div>
      <div className="resv-list">
        {resvLoading && <div className="muted small">載入中…</div>}
        {resvErr && <div className="small" style={{ color: '#c0392b' }}>{resvErr}</div>}
        {!resvLoading && !resvErr && visibleResv.length === 0 && (
          <div className="muted small">尚無預約，前往預約吧。</div>
        )}

        {visibleResv.map((r, i) => {
          const cls = (v) => {
            const s = String(v||'').toLowerCase()
            if (s.includes('pending')) return 'pending'
            if (s.includes('approved')||s.includes('paid')||s.includes('assigned')||s.includes('complete')) return 'approved'
            if (s.includes('reject')||s.includes('cancel')||s.includes('fail')) return 'rejected'
            return 'secondary'
          }
          const cancellable = (r.id || r.reservation_id) &&
            ['審核中', 'pending', 'approved', 'not_assigned'].some(keyword =>
              String(r.status || '').includes(keyword) ||
              String(r.review_status || '').toLowerCase().includes(keyword) ||
              String(r.payment_status || '').toLowerCase().includes(keyword) ||
              String(r.dispatch_status || '').toLowerCase().includes(keyword)
            )

          return (
            <div className="resv-card" key={i}>
              <div className="resv-main">
                <div className="resv-title">{r.booking_start_station_name} → {r.booking_end_station_name}</div>
                <div className="resv-sub">{fmt(r.booking_time)} ・ {r.booking_number} 人</div>
                <div className="small muted">預約編號：{r.reservation_id}</div>
                <div className="resv-status">
                  <span className={`status-chip ${cls(r.review_status)}`}>審核 {r.review_status}</span>
                  <span className={`status-chip ${cls(r.payment_status)}`}>支付 {r.payment_status}</span>
                </div>
              </div>
              <div className="resv-actions">
                <button className="btn btn-blue" onClick={() => { setSelectedResv(r); setShowRouteModal(true) }}>查看路線</button>
                {cancellable && (
                  <button className="btn" onClick={() => setCancelTarget(r)}>取消</button>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* 路線資訊 Modal */}
      {selectedResv && showRouteModal && (
        <div className="modal-overlay">
          <div className="modal-card route-modal">
            <div className="modal-header">
  <h3 className="modal-title">路線資訊</h3>
  <button
    className="modal-close"
    onClick={() => setShowRouteModal(false)}
    style={{
      fontSize: '22px',
      fontWeight: '700',
      color: '#333',
      background: 'none',
      border: '2px solid #aaa',
      borderRadius: '6px',
      padding: '4px 10px',
      cursor: 'pointer',
      lineHeight: '1.2',
      transition: 'all 0.2s ease',
    }}
    onMouseEnter={(e) => (e.currentTarget.style.background = '#f2f2f2')}
    onMouseLeave={(e) => (e.currentTarget.style.background = 'none')}
  >
    關閉
  </button>
</div>

<div className="modal-body">
  <p><strong>出發：</strong>{selectedResv.booking_start_station_name}</p>
  <p><strong>到達：</strong>{selectedResv.booking_end_station_name}</p>
  <p><strong>時間：</strong>{fmt(selectedResv.booking_time)}</p>
  <p><strong>人數：</strong>{selectedResv.booking_number}</p>
  <p><strong>預約編號：</strong>{selectedResv.reservation_id}</p>
</div>

<div className="modal-actions">
  <button
    className="btn btn-orange"
    onClick={() => setCancelTarget(selectedResv)}
  >
    取消預約
  </button>

  <button
    className="btn btn-blue"
    onClick={async () => {
      try {
        const amount = String(selectedResv.booking_number * 10)
        const orderNumber = String(selectedResv.reservation_id)

        const confirmed = window.confirm('即將前往付款頁面，是否繼續？')
        if (!confirmed) return

        const resp = await fetch('/payments', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            amount: amount,
            order_number: orderNumber,
          }),
        })

        if (!resp.ok) throw new Error('付款連線失敗')
        const data = await resp.json()
        if (!data.pay_url) throw new Error('未回傳付款連結')

        // 🚀 導向雷門金流頁面
        window.location.href = data.pay_url
      } catch (err) {
        console.error(err)
        alert(err.message || '付款失敗')
      }
    }}
  >
    付款
  </button>
</div>

          </div>
        </div>
      )}

      {/* 取消預約 Modal */}
      {cancelTarget && (
        <div className="modal-overlay">
          <div className="modal-card">
            <h3>請輸入取消原因</h3>
            <textarea
              className="auth-input"
              placeholder="請輸入取消原因"
              value={cancelReason}
              onChange={(e) => setCancelReason(e.target.value)}
            />
            <div className="modal-actions">
              <button
                className="btn btn-orange"
                disabled={!cancelReason.trim()}
                onClick={async () => {
                  try {
                    await cancelReservation(cancelTarget.reservation_id, cancelReason)
                    const uid = user?.id ?? user?.user_id
                    const next = await getMyReservations(uid)
                    setMyResv(next)
                    setCancelTarget(null)
                    setCancelReason('')
                    setShowRouteModal(false)
                  } catch (e) {
                    alert(String(e.message || e))
                  }
                }}
              >
                確定取消
              </button>
              <button className="btn" onClick={() => { setCancelTarget(null); setCancelReason('') }}>返回</button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
