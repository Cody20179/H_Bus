import React, { useEffect, useState, useRef } from 'react'
import MyReservations from '../components/MyReservations'
import { useNavigate, useLocation } from 'react-router-dom'
import { getMyReservations, cancelReservation } from '../services/api'

// 主要功能：Profile 頁面，根據 session 狀態顯示登入或主介面
function ProfilePage({ user, onLogin, onLogout }) {
  const navigate = useNavigate()
  const location = useLocation()
  const [sessionUser, setSessionUser] = useState(null)
  const [sessionLoading, setSessionLoading] = useState(true)
  const [unauthorized, setUnauthorized] = useState(false)
  const [myResv, setMyResv] = useState([])
  const [toastMsg, setToastMsg] = useState('')
  const resvRef = useRef(null)
  const [contactField, setContactField] = useState(null)
  const [contactValue, setContactValue] = useState('')
  const [contactError, setContactError] = useState('')
  const [contactSaving, setContactSaving] = useState(false)
  const [showMoreTrips, setShowMoreTrips] = useState(false)
  const supportPhone = "0800-827656"; // ← 真實電話請覆寫
  const phoneDisplay = supportPhone.replace(/(\d{4})(\d{3})(\d{3})/,'$1 $2 $3'); // 0951 861 516 格式化
  const supportEmail = "aspring51000@gmail.com";
  const emailLink = `mailto:${supportEmail}`;

  function copyToClipboard(text){
    if (!navigator?.clipboard) {
      // fallback
      const ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand('copy'); } catch(e){}
      document.body.removeChild(ta);
      // 可顯示短暫提示
      showToast && setToastMsg('已複製');
      return;
    }
    navigator.clipboard.writeText(text)
      .then(()=> showToast && setToastMsg('已複製'))
      .catch(()=> showToast && setToastMsg('複製失敗'));
  }

  // 點按查看隱私 / 權益的處理器（可改為 route push 或打開 modal）
  function viewPrivacy(){ /* e.g. router.push('/privacy') or setShowPrivacy(true) */ }
  function viewRights(){ /* e.g. router.push('/rights') or setShowRights(true) */ }

  // 加上時間判斷
  const now = new Date()

  // 未過期 & 狀態正常 → 我的預約
  const validReservations = myResv.filter(r => {
    const bookingTime = new Date(r.booking_time)
    const notExpired = !isNaN(bookingTime) && bookingTime >= now
    const notFailed = !(
      String(r.review_status||'').toLowerCase().includes('reject') ||
      String(r.review_status||'').toLowerCase().includes('canceled') ||
      String(r.payment_status||'').toLowerCase().includes('fail')
    )
    return notExpired && notFailed
  })

  // 已過期 or 狀態失敗 → 最近行程
  const recentTrips = myResv.filter(r => {
    const bookingTime = new Date(r.booking_time)
    const expired = !isNaN(bookingTime) && bookingTime < now
    const failed = (
      String(r.review_status||'').toLowerCase().includes('reject') ||
      String(r.review_status||'').toLowerCase().includes('canceled') ||
      String(r.payment_status||'').toLowerCase().includes('fail')
    )
    return expired || failed
  })

  
  useEffect(() => {
  if (!toastMsg) return;
  const timer = setTimeout(() => setToastMsg(''), 2000); // 2 秒後清空
  return () => clearTimeout(timer);
}, [toastMsg]);

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

  const getEffectiveUser = () => (sessionUser && sessionUser.user_id) ? sessionUser : user
  
  const statusText = (s) => {
    const str = String(s || '').toLowerCase()
    if (str.includes('approved') || str.includes('paid') || str.includes('assigned') || str.includes('complete')) {
      return '通過'
    }
    if (str.includes('pending') || str.includes('not_assigned')) {
      return '待辦'
    }
    if (str.includes('reject') || str.includes('cancel') || str.includes('fail')) {
      return '失敗'
    }
    return str || '-'
  }

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
                <div className="meta-list meta-inline">
                  <div className="meta-item">
                    <div className="meta-label">狀態</div>
                    <div className="meta-value">{user?.role_display || '一般使用者'}</div>
                  </div>

                  <div className="meta-item">
                    <div className="meta-label">Email</div>
                    <div className="meta-value">
                      <span className="ellipsis" title={displayEmail}>{displayEmail || '未設定'}</span>
                      <button className="link-btn" onClick={() => openContactDialog('email')}>修改</button>
                    </div>
                  </div>

                  <div className="meta-item">
                    <div className="meta-label">手機</div>
                    <div className="meta-value">
                      <span className="ellipsis" title={displayPhone}>{displayPhone || '未設定'}</span>
                      <button className="link-btn" onClick={() => openContactDialog('phone')}>修改</button>
                    </div>
                  </div>
                </div>
            </div>
          </div>
        </section>
  
        {/* 預約紀錄（串接後端） */}
<MyReservations user={user} filterExpired={true} />



<section className="card">
  <div className="card-title"><span>最近行程</span></div>
  <div className="list">
    {(showMoreTrips ? recentTrips : recentTrips.slice(0, 3))
      .filter(r => !String(r.review_status||'').toLowerCase().includes('canceled'))
      .map((r, idx) => {
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
          <div
            className="trip-card"
            key={idx}
            style={{
              background: '#fff',
              borderRadius: 10,
              padding: '12px 14px',
              marginBottom: 10,
              boxShadow: '0 1px 3px rgba(0,0,0,0.08)'
            }}
          >
            <div style={{ fontWeight: 600, marginBottom: 4 }}>
              {r.booking_start_station_name} → {r.booking_end_station_name}
            </div>
            <div style={{ fontSize: 14, color: '#374151' }}>
              {fmt(r.booking_time)} ・ {r.booking_number} 人
            </div>
            <div style={{ fontSize: 12, color: '#6b7280', marginTop: 2 }}>
              狀態：審核 {statusText(r.review_status)} ・ 支付 {statusText(r.payment_status)} ・ 編號：{r.reservation_id}
            </div>
          </div>
        )
      })}
  </div>
  {recentTrips.length > 3 && (
    <div className="mt-12" style={{ display:'flex', justifyContent:'flex-end' }}>
      <button className="btn btn-primary" onClick={()=>setShowMoreTrips(!showMoreTrips)}>
        {showMoreTrips ? '收起' : '查看更多'}
      </button>
    </div>
  )}
</section>

        <section className="card help-card" aria-labelledby="help-title">
          <div className="card-title" id="help-title"><span>幫助</span></div>
          <div className="card-body">
            <div className="help-list">

<div
  className="help-item"
  style={{
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    padding: '8px 0',
  }}
>
  {/* 標題區 */}
  <div className="help-left">
    <div
      className="help-title"
      style={{ fontWeight: 600, fontSize: '16px', marginBottom: '4px' }}
    >
      聯絡客服
    </div>
    <div
      className="help-sub muted"
      style={{ fontSize: '13px', color: '#666', marginBottom: '8px' }}
    >
      聯絡時間：週一–週五 09:00 – 18:00
    </div>
  </div>

  {/* 聯絡資訊區 */}
  <div
    className="help-right"
    style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'flex-start',
      gap: '8px',
    }}
  >
    {/* 電話組 */}
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        flexWrap: 'nowrap',
      }}
    >
      <a
        className="phone-pill"
        href={`tel:${supportPhone}`}
        aria-label={`撥打客服電話 ${supportPhone}`}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '6px',
          color: '#2563eb',
          background: '#eef5ff',
          borderRadius: '20px',
          padding: '6px 12px',
          fontWeight: 600,
          textDecoration: 'none',
          fontSize: '14px',
        }}
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path
            d="M22 16.92v3a2 2 0 0 1-2.18 2 19.87 19.87 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6A19.87 19.87 0 0 1 3.08 4.18 2 2 0 0 1 5 2h3a2 2 0 0 1 2 1.72c.12 1.05.38 2.08.78 3.02a2 2 0 0 1-.45 2.11L9.91 10.09a16 16 0 0 0 6 6l1.24-1.24a2 2 0 0 1 2.11-.45c.94.4 1.97.66 3.02.78A2 2 0 0 1 22 16.92z"
            fill="currentColor"
          />
        </svg>
        <span title={supportPhone}>{phoneDisplay}</span>
      </a>
      <button
        type="button"
        onClick={() => copyToClipboard(supportPhone)}
        aria-label="複製電話"
        title="複製電話"
        style={{
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          padding: '4px',
          borderRadius: '6px',
        }}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
          <path
            d="M16 1H4a2 2 0 0 0-2 2v14h2V3h12V1zM20 5H8a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2zm0 16H8V7h12v14z"
            fill="currentColor"
          />
        </svg>
      </button>
    </div>

    {/* 信箱組 */}
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        flexWrap: 'nowrap',
      }}
    >
      <a
        className="email-pill"
        href={emailLink}
        aria-label={`寄信至 ${supportEmail}`}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '6px',
          color: '#2563eb',
          background: '#eef5ff',
          borderRadius: '20px',
          padding: '6px 12px',
          fontWeight: 600,
          textDecoration: 'none',
          fontSize: '14px',
        }}
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path
            d="M20 4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2zm0 2v.01L12 13 4 6.01V6h16zM4 18V8.99l8 6 8-6V18H4z"
            fill="currentColor"
          />
        </svg>
        <span title={supportEmail}>{supportEmail}</span>
      </a>
      <button
        type="button"
        onClick={() => copyToClipboard(supportEmail)}
        aria-label="複製信箱"
        title="複製信箱"
        style={{
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          padding: '4px',
          borderRadius: '6px',
        }}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
          <path
            d="M16 1H4a2 2 0 0 0-2 2v14h2V3h12V1zM20 5H8a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2zm0 16H8V7h12v14z"
            fill="currentColor"
          />
        </svg>
      </button>
    </div>
  </div>
</div>

              <div className="help-item">
                <div className="help-left">
                  <div className="help-title">隱私政策</div>
                  <div className="help-sub muted">查看隱私政策與個資使用說明</div>
                </div>
                <div className="help-right">
                  <button type="button" className="btn btn-primary" onClick={viewPrivacy} aria-label="查看隱私政策">查看</button>
                </div>
              </div>
              <div className="help-item help-rights">
                <div className="help-left">
                  <div className="help-title">權益與保障</div>
                  <div className="help-sub muted">退款、申訴與個資權益重點</div>
                  <ul className="rights-list">
                    <li><strong>退款/退票：</strong>依本平台退票規範辦理，申請後 7 個工作日處理。</li>
                    <li><strong>客訴處理：</strong>受理後 48 小時內回覆處理進度。</li>
                    <li><strong>個資保護：</strong>可提出刪除或資料限縮請求，平台將依法定程序回覆。</li>
                  </ul>
                </div>
              </div>
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
      </div>
    )
}
export default ProfilePage
