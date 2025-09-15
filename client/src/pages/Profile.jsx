import React, { useEffect, useState, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { getMyReservations, cancelReservation } from '../services/api'

// 主要功能：Profile 頁面，根據 session 狀態顯示登入或主介面
function ProfilePage({ user, onLogin, onLogout }) {
  const navigate = useNavigate()
  const location = useLocation()
  // 狀態管理
  const [showVerify, setShowVerify] = useState(false)
  const [sessionUser, setSessionUser] = useState(null)
  const [sessionLoading, setSessionLoading] = useState(true)
  const [unauthorized, setUnauthorized] = useState(false)
  const [myResv, setMyResv] = useState([])
  const [resvLoading, setResvLoading] = useState(false)
  const [resvErr, setResvErr] = useState('')
  const [toastMsg, setToastMsg] = useState('')
  const [cooldown, setCooldown] = useState(0)
  const resvRef = useRef(null)
  const AUTH_BASE = import.meta.env.VITE_AUTH_BASE_URL;
  console.log('AUTH_BASE =', import.meta.env.VITE_AUTH_BASE_URL);
  // 檢查 session 狀態，決定是否顯示登入介面
  useEffect(() => {
    async function checkSession() {
      setSessionLoading(true)
      try {
        const resp = await fetch(`/me`, { credentials: 'include' });
        if (!resp.ok) throw new Error('未登入')
        const data = await resp.json()
        if (data && data.user_id) {
          setSessionUser(data)
          if (onLogin) onLogin(data)
        } else {
          setSessionUser(null)
        }
      } catch {
        setSessionUser(null)
        setUnauthorized(true)
      } finally {
        setSessionLoading(false)
      }
    }
    checkSession()
  }, [])

  // 當確認為未登入（/me 回 401 或錯誤）時，通知父層清空使用者狀態
  useEffect(() => {
    if (unauthorized) {
      try { if (onLogout) onLogout() } catch {}
    }
  }, [unauthorized])

  // 預約列表載入
  useEffect(() => {
    const uid = user?.id ?? user?.user_id
    if (!uid) return
    let cancelled = false
    setResvLoading(true); setResvErr('')
    getMyReservations(uid)
      .then((rows) => { if (!cancelled) setMyResv(rows) })
      .catch((e) => { if (!cancelled) setResvErr(String(e.message || e)) })
      .finally(() => { if (!cancelled) setResvLoading(false) })
    return () => { cancelled = true }
  }, [user])

  // 導覽狀態處理（預約完成提示、滾動）
  useEffect(() => {
    if (!location) return
    const params = new URLSearchParams(location.search || '')
    const tab = params.get('tab')
    const toast = location.state && location.state.toast
    if (toast) {
      setToastMsg(String(toast))
      try { navigate(location.pathname + location.search, { replace: true, state: {} }) } catch {}
    }
    if (tab === 'reservations' && resvRef.current) {
      setTimeout(() => { resvRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }) }, 100)
    }
  }, [location])

  // 登出功能
  const handleLogout = () => {
    window.location.href = `/logout`;
  };

  // 推播測試
  const handleTestPush = async () => {
    try {
      if (!('Notification' in window)) {
        alert('此瀏覽器不支援通知功能')
        return
      }
      const perm = await Notification.requestPermission()
      if (perm !== 'granted') {
        alert('通知權限未開啟')
        return
      }
      const title = '測試通知'
      const body = `這是一則測試通知：${new Date().toLocaleTimeString()}`
      if ('serviceWorker' in navigator && window.isSecureContext) {
        const reg = await navigator.serviceWorker.register('/sw.js')
        await reg.update().catch(()=>{})
        await reg.showNotification(title, { body, icon: '/icon.png', tag: 'hbus-test', renotify: true })
        return
      }
      try {
        new Notification(title, { body, icon: '/icon.png', tag: 'hbus-fallback' })
      } catch (e) {
        alert('此環境需要 Service Worker，請在 HTTPS 或 localhost 測試通知')
      }
    } catch (e) {
      alert('推播發送失敗，請查看主控台')
    }
  }

  // ========== 介面渲染 ==========
  if (sessionLoading) {
    return <div className="auth-wrapper"><div className="auth-card">載入中…</div></div>
  }
  if (sessionUser && sessionUser.user_id) {
    user = sessionUser
  }
  if (sessionUser === null) {
    user = null
  }
  if (unauthorized) {
    user = null
  }
  if (!user) {
    return (
      <div className="auth-wrapper">
        <div className="auth-card">
          <h2 className="auth-title">歡迎回來</h2>
          <p className="auth-subtitle">請使用 LINE 登入以繼續</p>
          <button className="line-login-button" onClick={() => {
            const ret = `${window.location.origin}/profile`
            window.location.href = `/auth/line/login?return_to=${encodeURIComponent(ret)}`
          }}>
            <img src="https://scdn.line-apps.com/n/line_reg_v2_oauth/img/naver/btn_login_base.png" alt="LINE Login" className="line-icon" />
            使用 LINE 登入
          </button>
        </div>
      </div>
    );
  }
  
    return (
      /* 主頁面內容 */
      <div className="container">
        {toastMsg && (
          <div style={{ background:'#ecfdf5', border:'1px solid #34d399', color:'#065f46', padding:10, borderRadius:8, marginBottom:12 }}>
            {toastMsg}
          </div>
        )}

        {/* 使用者 App 概覽 */}
        <section className="card profile-overview">
          <div className="overview-hero">
            <div className="overview-meta">
              <div className="meta-title">{user.username} 的帳戶</div>
              <div className="meta-list">
                <div className="small muted">帳號：{user.account || '(未設定)'}</div>
                <div className="small muted">狀態：一般使用者</div>
              </div>
            </div>
          </div>
        </section>
  
        {/* 預約紀錄（串接後端） */}
        <section className="card" ref={resvRef}>
          <div className="card-title">
            <span>我的預約</span>
            <button
              className="link-btn"
              onClick={() => {
                const uid = user?.id ?? user?.user_id
                if (!uid) { alert('請先登入'); return }
                setResvLoading(true); setResvErr('')
                getMyReservations(uid)
                  .then(setMyResv)
                  .catch((e) => setResvErr(String(e.message || e)))
                  .finally(() => setResvLoading(false))
              }}
            >刷新</button>
          </div>
          <div className="resv-list">
            {resvLoading && <div className="muted small">載入中…</div>}
            {resvErr && <div className="small" style={{ color: '#c0392b' }}>{resvErr}</div>}
            {!resvLoading && !resvErr && myResv.length === 0 && (
              <div className="muted small">尚無預約，前往預約吧。</div>
            )}
            {myResv.map((r, index) => {
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
              const cls = (v) => {
                const s = String(v||'').toLowerCase()
                if (s.includes('pending')) return 'pending'
                if (s.includes('approved')||s.includes('paid')||s.includes('assigned')||s.includes('complete')) return 'approved'
                if (s.includes('reject')||s.includes('cancel')||s.includes('fail')) return 'rejected'
                return 'secondary'
              }
              const cancellable = ((r.id || r.reservation_id) && (String(r.status||'').includes('審核中') || String(r.review_status||'').toLowerCase().includes('pending')))
              return (
                <div className="resv-card" key={index}>
                  <div className="resv-main">
                    <div className="resv-title">{r.booking_start_station_name} → {r.booking_end_station_name}</div>
                    <div className="resv-sub">{fmt(r.booking_time)} ・ {r.booking_number} 人</div>
                    <div className="resv-status">
                      <span className={`status-chip ${cls(r.review_status)}`}>審核 {r.review_status || '-'}</span>
                      <span className={`status-chip ${cls(r.payment_status)}`}>支付 {r.payment_status || '-'}</span>
                    </div>
                  </div>
                  <div className="resv-actions">
                    <button className="btn btn-blue" onClick={() => alert(`${r.booking_start_station_name} → ${r.booking_end_station_name}\n${fmt(r.booking_time)} ・ ${r.booking_number} 人`) }>查看路線</button>
                    {cancellable && (
                      <button
                        className="btn"
                        onClick={async () => {
                          if (!window.confirm('確定取消此預約？')) return
                          try {
                            await cancelReservation({ reservationId: r.id })
                            const uid = user?.id ?? user?.user_id
                            const next = await getMyReservations(uid)
                            setMyResv(next)
                          } catch (e) {
                            alert(String(e.message || e))
                          }
                        }}
                      >取消</button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </section>
  
        {/* 最近行程（範例靜態） */}
        <section className="card">
          <div className="card-title"><span>最近行程</span></div>
          <div className="list">
            {[
              { id:1, route:'202 路線', dir:'去程', date:'09/05 08:32', fare:28, status:'已完成' },
              { id:2, route:'路線 2', dir:'回程', date:'09/04 18:11', fare:24, status:'已完成' },
              { id:3, route:'路線 7', dir:'去程', date:'09/03 08:29', fare:20, status:'已完成' },
            ].map((t)=> (
              <div className="item" key={t.id}>
                <div>
                  <div style={{ fontWeight:700 }}>{t.route} - {t.dir}</div>
                  <div className="item-desc">{t.date} - ${t.fare} - {t.status}</div>
                </div>
                <button className="btn-pay-manage" onClick={()=>alert('查看行程 /api/trips/', t.id)}>查看</button>
              </div>
            ))}
          </div>
          <div className="mt-12" style={{ display:'flex', justifyContent:'flex-end' }}>
            <button className="btn" onClick={()=>alert('查看更多 /api/trips/recent')}>查看更多</button>
          </div>
        </section>

        {/* 推播測試 */}
        <section className="card">
          <div className="card-title"><span>推播測試</span></div>
          <div className="card-body">
            <button className="btn btn-blue" onClick={handleTestPush}>發送測試推播</button>
            <div className="small muted" style={{ marginTop: 8 }}>請在 HTTPS 或 localhost 環境下測試推播功能</div>
          </div>
        </section>
  
        {/* 常見問題 */}
        <section className="card profile-section">
          <div className="section-title">幫助</div>
          <div className="list">
            <div className="item">
              <div>
                <div style={{ fontWeight: 700 }}>常見問題 FAQ</div>
                <div className="item-desc">查看常見問題</div>
              </div>
              <div className="item-col">
                <button className="btn btn-blue" onClick={()=>alert('查看常見問題')}>查看</button>
                <button className="btn btn-blue" onClick={()=>alert('聯絡客服')}>聯絡客服</button>
              </div>
            </div>
            <div className="item">
              <div>
                <div style={{ fontWeight: 700 }}>隱私政策</div>
                <div className="item-desc">查看隱私政策</div>
              </div>
              <button className="btn btn-blue" onClick={()=>alert('查看隱私政策')}>查看</button>
            </div>
          </div>
        </section>

        {/* 登出 */}
        <section className="card">
          <div className="list">
            <div className="item">
              <div className="item-col"><strong></strong></div>
              <button className="btn btn-orange" onClick={handleLogout}>登出</button>
            </div>
          </div>
        </section>
      </div>
    )
}
export default ProfilePage
