import React, { useEffect, useState, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { getMyReservations, cancelReservation } from '../services/api'

// 主要功能：Profile 頁面，根據 session 狀態顯示登入或主介面
function ProfilePage({ user, onLogin, onLogout }) {
  const navigate = useNavigate()
  const location = useLocation()
  // 狀態管理
  const [showVerify, setShowVerify] = useState(false)
  const [showRouteModal, setShowRouteModal] = useState(false)
  const [selectedResv, setSelectedResv] = useState(null)
  const [sessionUser, setSessionUser] = useState(null)
  const [sessionLoading, setSessionLoading] = useState(true)
  const [unauthorized, setUnauthorized] = useState(false)
  const [myResv, setMyResv] = useState([])
  const [resvLoading, setResvLoading] = useState(false)
  const [resvErr, setResvErr] = useState('')
  const [toastMsg, setToastMsg] = useState('')
  const [cooldown, setCooldown] = useState(0)
  const resvRef = useRef(null)
  const [contactField, setContactField] = useState(null)
  const [contactValue, setContactValue] = useState('')
  const [contactError, setContactError] = useState('')
  const [contactSaving, setContactSaving] = useState(false)
  const [showMoreTrips, setShowMoreTrips] = useState(false)
  const validReservations = myResv.filter(r =>
    !(String(r.review_status||'').toLowerCase().includes('reject') ||
      String(r.review_status||'').toLowerCase().includes('canceled') ||
      String(r.payment_status||'').toLowerCase().includes('fail'))
  )

  const failedReservations = myResv.filter(r =>
    String(r.review_status||'').toLowerCase().includes('reject') ||
    String(r.review_status||'').toLowerCase().includes('canceled') ||
    String(r.payment_status||'').toLowerCase().includes('fail')
  )
  const AUTH_BASE = import.meta.env.VITE_AUTH_BASE_URL;
  console.log('AUTH_BASE =', import.meta.env.VITE_AUTH_BASE_URL);
  
  useEffect(() => {
    if (import.meta.env.MODE === 'production') return
    const helper = async (passcode, overrides = {}) => {
      if (passcode !== 'Lab@109**') {
        console.warn('[H_Bus] 測試密碼錯誤')
        return false
      }
      const nowIso = new Date().toISOString()
      const fakeUser = {
        user_id: overrides.user_id ?? -999,
        line_id: overrides.line_id ?? 'lab-tester',
        username: overrides.username ?? 'Lab 測試人員',
        email: overrides.email ?? 'lab@example.com',
        phone: overrides.phone ?? null,
        last_login: overrides.last_login ?? nowIso,
        testing: true,
        source: 'local-dev',
        ...overrides,
      }
      setSessionUser(fakeUser)
      setUnauthorized(false)
      setSessionLoading(false)
      if (onLogin) {
        try { onLogin(fakeUser) } catch (err) { console.warn(err) }
      }
      setToastMsg('已以測試帳號登入 (僅本地用途)')
      console.info('[H_Bus] 已載入測試帳號，重新整理即可恢復。')
      return true
    }
    Object.defineProperty(window, 'hbusTestLogin', { value: helper, configurable: true })
    console.info('[H_Bus] 測試模式：在 console 呼叫 hbusTestLogin(\'Lab@109**\') 可載入測試帳號。')
    return () => {
      if (window.hbusTestLogin === helper) {
        delete window.hbusTestLogin
      }
    }
  }, [onLogin])

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
    const current = (sessionUser && sessionUser.user_id) ? sessionUser : user
    const uid = current?.id ?? current?.user_id
    if (!uid) return
    let cancelled = false
    setResvLoading(true)
    setResvErr('')
    getMyReservations(uid)
      .then((rows) => { if (!cancelled) setMyResv(rows) })
      .catch((e) => { if (!cancelled) setResvErr(String(e.message || e)) })
      .finally(() => { if (!cancelled) setResvLoading(false) })
    return () => { cancelled = true }
  }, [sessionUser, user])

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

  const getEffectiveUser = () => (sessionUser && sessionUser.user_id) ? sessionUser : user

  // 共用時間格式化函式
  const fmt = (s) => {
    try {
      if (!s) return '-'
      const d = new Date(s)
      if (isNaN(d)) return String(s)
      const y = d.getFullYear()
      const M = String(d.getMonth() + 1).padStart(2, '0')
      const D = String(d.getDate()).padStart(2, '0')
      const h = String(d.getHours()).padStart(2, '0')
      const m = String(d.getMinutes()).padStart(2, '0')
      return `${y}-${M}-${D} ${h}:${m}`
    } catch {
      return String(s)
    }
  }


  const openContactDialog = (field) => {
    const currentUser = getEffectiveUser()
    const currentValue = field === 'email' ? (currentUser?.email ?? '') : (currentUser?.phone ?? '')
    setContactField(field)
    setContactValue(currentValue || '')
    setContactError('')
  }

  const closeContactDialog = () => {
    if (contactSaving) return
    setContactField(null)
    setContactValue('')
    setContactError('')
  }

  const handleContactSubmit = async (e) => {
    e.preventDefault()
    if (!contactField) return
    const trimmed = contactValue.trim()
    if (!trimmed) {
      setContactError(contactField === 'email' ? '請輸入 Email' : '請輸入手機號碼')
      return
    }
    if (contactField === 'email' && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(trimmed)) {
      setContactError('請輸入有效的 Email')
      return
    }
    if (contactField === 'phone' && !/^[0-9+\-#* ]{6,}$/.test(trimmed)) {
      setContactError('請輸入有效的手機號碼')
      return
    }
    const currentUser = getEffectiveUser()
    const userId = currentUser?.user_id ?? currentUser?.id
    if (!userId) {
      setContactError('找不到使用者 ID')
      return
    }

    setContactSaving(true)
    setContactError('')
    const endpoint = contactField === 'email' ? '/api/users/update_mail' : '/api/users/update_phone'
    const params = new URLSearchParams({ user_id: String(userId) })
    params.append(contactField, trimmed)

    try {
      const resp = await fetch(`${endpoint}?${params.toString()}`, { method: 'POST' })
      if (!resp.ok) {
        throw new Error('更新失敗')
      }
      const data = await resp.json().catch(() => ({}))
      if (data.status !== 'success') {
        throw new Error(data.detail || '更新失敗')
      }
      const updatedUser = { ...(currentUser || {}), [contactField]: trimmed }
      setSessionUser(updatedUser)
      if (onLogin) {
        try { onLogin(updatedUser) } catch (err) { console.warn(err) }
      }
      setToastMsg(contactField === 'email' ? 'Email 已更新' : '手機已更新')
      setContactSaving(false)
      closeContactDialog()
    } catch (err) {
      console.error(err)
      setContactError(err.message || '更新失敗')
      setContactSaving(false)
    }
  }

  // ========== 介面渲染 ==========
  if (sessionLoading) {
    return <div className="auth-wrapper"><div className="auth-card">載入中…</div></div>
  }

  const effectiveUser = getEffectiveUser()
  const displayEmail = effectiveUser?.email || '尚未填寫'
  const displayPhone = effectiveUser?.phone || '尚未填寫'
  const contactLabel = contactField === 'email' ? 'Email' : '手機'
  const dialogValue = contactField === 'email' ? displayEmail : displayPhone

  if (!effectiveUser) {
    return (
      <div className="auth-wrapper">
        <div className="auth-card">
          <h2 className="auth-title">尚未登入</h2>
          <p className="auth-subtitle">請先登入後再查看個人資訊。</p>
          <button
            className="line-login-button"
            onClick={() => {
              const ret = `${window.location.origin}/profile`
              window.location.href = `/auth/line/login?return_to=${encodeURIComponent(ret)}`
            }}
          >
            <img src="https://scdn.line-apps.com/n/line_reg_v2_oauth/img/naver/btn_login_base.png" alt="LINE Login" className="line-icon" />
            使用 LINE 登入
          </button>
        </div>
      </div>
    )
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
                {/* Email / Phone 修改區塊 */}
                <div className="small">Email：{displayEmail}
                  <button className="link-btn" onClick={() => openContactDialog('email')}>修改</button>
                </div>
                <div className="small">手機：{displayPhone}
                  <button className="link-btn" onClick={() => openContactDialog('phone')}>修改</button>
                </div>
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
            {validReservations.map((r, index) => {
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
              const cancellable = (r.id || r.reservation_id) &&
              ['審核中', 'pending', 'approved', 'not_assigned'].some(keyword =>
                String(r.status || '').includes(keyword) ||
                String(r.review_status || '').toLowerCase().includes(keyword) ||
                String(r.payment_status || '').toLowerCase().includes(keyword) ||
                String(r.dispatch_status || '').toLowerCase().includes(keyword)
              )

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
                    <button
                      className="btn btn-blue"
                      onClick={() => {
                        setSelectedResv(r)
                        setShowRouteModal(true)
                      }}
                    >
                      查看路線
                    </button>
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
            {(showMoreTrips ? failedReservations : failedReservations.slice(0, 3)).map((r, idx) => {
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
              return (
                <div className="item" key={idx}>
                  <div>
                    <div style={{ fontWeight:700 }}>
                      {r.booking_start_station_name} → {r.booking_end_station_name}
                    </div>
                    <div className="item-desc">
                      {fmt(r.booking_time)} ・ {r.booking_number} 人 ・ 狀態: {r.review_status}/{r.payment_status}
                    </div>
                  </div>
                  <button className="btn-pay-manage" onClick={()=>alert('查看詳情', r.reservation_id)}>查看</button>
                </div>
              )
            })}
          </div>
          {failedReservations.length > 3 && (
            <div className="mt-12" style={{ display:'flex', justifyContent:'flex-end' }}>
              <button className="btn" onClick={()=>setShowMoreTrips(!showMoreTrips)}>
                {showMoreTrips ? '收起' : '查看更多'}
              </button>
            </div>
          )}
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

{contactField && (
  <div className="modal-overlay">
    <div className="modal-card">
      <h3 style={{ fontWeight: "800", fontSize: "18px", marginBottom: "12px" }}>
        {contactField === 'email' ? '修改 Email' : '修改手機號碼'}
      </h3>

      <form onSubmit={handleContactSubmit} className="auth-form">
        <input
          className="auth-input"
          type={contactField === 'email' ? 'email' : 'tel'}
          value={contactValue}
          onChange={(e) => setContactValue(e.target.value)}
          disabled={contactSaving}
          placeholder={contactField === 'email' ? '請輸入新 Email' : '請輸入新手機號碼'}
        />
        {contactError && <div className="auth-error">{contactError}</div>}

        <div className="modal-actions">
          <button
            type="submit"
            className="btn btn-blue"
            disabled={contactSaving}
          >
            {contactSaving ? '儲存中...' : '儲存'}
          </button>
          <button
            type="button"
            className="btn btn-orange"
            onClick={closeContactDialog}
            disabled={contactSaving}
          >
            取消
          </button>
        </div>
      </form>
    </div>
  </div>
)}

{selectedResv && showRouteModal && (
  <div className="modal-overlay">
    <div className="modal-card route-modal">
      {/* 頂部：標題 + 右上角關閉 */}
      <div className="modal-header">
        <h3 className="modal-title">路線資訊</h3>
        <button className="modal-close" onClick={() => setShowRouteModal(false)}>×</button>
      </div>

      {/* 內容 */}
      <div className="modal-body">
        <p><strong>出發：</strong>{selectedResv.booking_start_station_name}</p>
        <p><strong>到達：</strong>{selectedResv.booking_end_station_name}</p>
        <p><strong>時間：</strong>{fmt(selectedResv.booking_time)}</p>
        <p><strong>人數：</strong>{selectedResv.booking_number}</p>
      </div>

      {/* 底部兩顆按鈕 */}
      <div className="modal-actions">
        <button className="btn btn-orange">取消預約</button>
        <button className="btn btn-blue">付款</button>
      </div>
    </div>
  </div>
)}

      </div>
    )
}
export default ProfilePage
