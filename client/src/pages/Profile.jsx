import React, { useEffect, useState, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { otpRequest, otpVerify, otpConsume, bindContacts } from '../services/api'
import { getMyReservations, cancelReservation } from '../services/api'
function ProfilePage({ user, onLogin, onLogout }) {
  const navigate = useNavigate()
  const location = useLocation()
  const [mode, setMode] = useState('login')
  const [account, setAccount] = useState('') // 使用者帳號
  const [password, setPassword] = useState('') // 密碼
  const [confirmPassword, setConfirmPassword] = useState('') // 再次確認密碼
  const [email, setEmail] = useState('') // Email
  const [phone, setPhone] = useState('') // 手機
  const [verifyCode, setVerifyCode] = useState('') // 驗證碼
  const [fullName, setFullName] = useState('') // 姓名
  const [remember, setRemember] = useState(true)
  const [error, setError] = useState(null)
  // Moved up to keep hooks order stable
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [otpMask, setOtpMask] = useState('')
  const [otpLoading, setOtpLoading] = useState(false)
  const [cooldown, setCooldown] = useState(0)

  const [showEditModal, setShowEditModal] = useState(false)
  const [editField, setEditField] = useState('') // 'email' | 'phone' | 'password'
  const [editValue, setEditValue] = useState('')
  const [editCode, setEditCode] = useState('')
  const [editError, setEditError] = useState('')




  // API endpoints
  useEffect(() => {
    const endpoints = {
      routes: '/api/All_Route',
      routeStops: '/api/Route_Stations',
      realtime: '/api/realtime',
      reservationsMy: '/api/reservations/my',
      reservationNext: '/api/reservations/next',
      cancelReservation: '/api/reservations/cancel',
      paymentMethods: '/api/payments/methods',
      paymentTransactions: '/api/payments/transactions',
      tripsRecent: '/api/trips/recent',
      tripDetail: '/api/trips/:id',
    }
    console.log('[Profile] API endpoints reserved:', endpoints)
  }, [])

  const handleTestPush = async () => {
    try {
      if (!('Notification' in window)) {
        alert('此瀏覽器不支援通知功能')
        return
      }
      const perm = await Notification.requestPermission()
      console.log('[Push] permission:', perm)
      if (perm !== 'granted') {
        alert('通知權限未開啟')
        return
      }
      const title = '測試通知'
      const body = `這是一則測試通知：${new Date().toLocaleTimeString()}`

      // 測試通知 SW 及 HTTPS 環境
      if ('serviceWorker' in navigator && window.isSecureContext) {
        const reg = await navigator.serviceWorker.register('/sw.js')
        await reg.update().catch(()=>{})
        await reg.showNotification(title, { body, icon: '/icon.png', tag: 'hbus-test', renotify: true })
        console.log('[Push] one-shot notification via ServiceWorker shown')
        return
      }

      // 瀏覽器不支援 SW 或非 HTTPS 環境
      try {
        new Notification(title, { body, icon: '/icon.png', tag: 'hbus-fallback' })
        console.log('[Push] fallback Notification shown (no SW)')
      } catch (e) {
        console.warn('[Push] fallback Notification failed. Secure context likely required.', e)
        alert('此環境需要 Service Worker，請在 HTTPS 或 localhost 測試通知')
      }
    } catch (e) {
      console.error('[Push] error', e)
      alert('推播發送失敗，請查看主控台')
    }
  }

  // Verify code modal state
  const [showVerify, setShowVerify] = useState(false)
  const [verifyErr, setVerifyErr] = useState(null)
  const [channel, setChannel] = useState('email') // 'email' | 'sms'
  const [pendingUser, setPendingUser] = useState(null)
  const [resendMsg, setResendMsg] = useState('')
  const [debugCode, setDebugCode] = useState('')
  const otpPurpose = mode === 'signup' ? 'signup_username' : 'login_username'
  // 綁定聯絡方式
  const [showBind, setShowBind] = useState(false)
  const [bindEmail, setBindEmail] = useState('')
  const [bindPhone, setBindPhone] = useState('')
  const [bindLoading, setBindLoading] = useState(false)
  const [bindErr, setBindErr] = useState('')
  // 我的預約（列表、錯誤、提示、定位）
  const [myResv, setMyResv] = useState([])
  const [resvLoading, setResvLoading] = useState(false)
  const [resvErr, setResvErr] = useState('')
  const [toastMsg, setToastMsg] = useState('')
  const resvRef = useRef(null)

  

  // 進頁面即嘗試載入我的預約
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

  const handleLogin = async (e) => {
  e.preventDefault()
  setError(null)
  if (!account || !password) {
    setError('請輸入帳號與密碼')
    return
  }
  try {
    setOtpLoading(true)
    setVerifyErr(null)
    setResendMsg('')
    // 先以帳密打登入 API
    const resp = await fetch('/api/users/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: account, password })
    })
    if (!resp.ok) {
      const msg = await resp.text().catch(()=> '')
      throw new Error(msg || '登入失敗，請檢查帳號或密碼')
    }
    const data = await resp.json().catch(()=> ({}))
    setPendingUser(data || { name: account, account, provider: 'username' })

    // 接著送 OTP
    const req = await otpRequest({ account, purpose: 'login_username', channel })
    if (req?.debug_code) setDebugCode(String(req.debug_code))
    setOtpMask(req?.sent_to || '')
    setCooldown(Number(req?.cooldown || 60))
    setShowVerify(true)
  } catch (err) {
    setError(String(err.message || err))
  } finally {
    setOtpLoading(false)
  }
}

const handleRegister = async (e) => {
  e.preventDefault()
  setError(null)
  if (!account) { setError('請輸入帳號'); return }
  if (!phone) { setError('請輸入手機號碼'); return }
  if (!password || !confirmPassword) { setError('請輸入密碼並再次確認'); return }
  if (password !== confirmPassword) { setError('兩次密碼不一致'); return }
  try {
    setOtpLoading(true)
    setVerifyErr(null)
    setResendMsg('')
    const resp = await fetch('/api/Create_users', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        line_id: null,
        username: account,
        password,
        email: email || '',
        phone,
        status: 'active',
        reservation_status: 'no_reservation',
        preferences: '',
        privacy_settings: ''
      })
    })
    if (!resp.ok) {
      const msg = await resp.text().catch(()=> '')
      throw new Error(msg || '註冊失敗，請稍後再試')
    }
    const data = await resp.json().catch(()=> ({}))
    setPendingUser(data || { name: account, account, provider: 'username' })
    const req = await otpRequest({ account, purpose: 'signup_username', channel })
    if (req?.debug_code) setDebugCode(String(req.debug_code))
    setOtpMask(req?.sent_to || '')
    setCooldown(Number(req?.cooldown || 60))
    setShowVerify(true)
  } catch (err) {
    setError(String(err.message || err))
  } finally {
    setOtpLoading(false)
  }
}

  // 驗證碼倒數計時
  useEffect(() => {
    if (!showVerify || cooldown <= 0) return
    const id = setInterval(() => setCooldown((c) => (c > 0 ? c - 1 : 0)), 1000)
    return () => clearInterval(id)
  }, [showVerify, cooldown])

  // 進頁面即嘗試載入我的預約
  useEffect(() => {
    if (!user || !user.id) return
    let cancelled = false
    setResvLoading(true); setResvErr('')
    getMyReservations(user.id)
      .then((rows) => { if (!cancelled) setMyResv(rows) })
      .catch((e) => { if (!cancelled) setResvErr(String(e.message || e)) })
      .finally(() => { if (!cancelled) setResvLoading(false) })
    return () => { cancelled = true }
  }, [user])

  // 接收導覽狀態（從 /reserve 送出預約後帶來的提示），並滾動到「我的預約」
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
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location])

  if (!user) {
    return (
      <div className="container auth-container">
        <section className="auth-card auth-full" style={{ paddingTop: 18, paddingBottom: 18 }}>
          <div className="card-title" style={{ marginTop: 4 }}><span>{mode === 'login' ? '登入' : '註冊'}</span></div>
          <div className="card-body">
            <div className="auth-tabs" role="tablist" aria-label="Auth tabs">
              <button className={`auth-tab ${mode==='login'?'active':''}`} onClick={() => setMode('login')}>登入</button>
              <button className={`auth-tab ${mode==='signup'?'active':''}`} onClick={() => setMode('signup')}>註冊</button>
            </div>
            {mode === 'login' ? (
              <form onSubmit={handleLogin} className="auth-form" style={{ marginTop: 10 }}>
  <input className="auth-input" type="text" placeholder="請輸入帳號/Username" value={account} onChange={e => setAccount(e.target.value)} autoComplete="username" />
  <input className="auth-input" type="password" placeholder="請輸入密碼" value={password} onChange={e => setPassword(e.target.value)} autoComplete="current-password" />
  {error && <div className="auth-error">{error}</div>}
  <button className="auth-button" type="submit">登入</button>
</form>
            ) : (
              <form onSubmit={handleRegister} className="auth-form" style={{ marginTop: 10 }}>
                <input className="auth-input" type="text" placeholder="請輸入帳號/Username" value={account} onChange={e => setAccount(e.target.value)} autoComplete="username" />
                <input className="auth-input" type="email" placeholder="Email (選填)" value={email} onChange={e => setEmail(e.target.value)} />
                <input className="auth-input" type="tel" placeholder="手機號碼" value={phone} onChange={e => setPhone(e.target.value)} />
                <input className="auth-input" type="password" placeholder="請輸入密碼" value={password} onChange={e => setPassword(e.target.value)} autoComplete="new-password" />
                <input className="auth-input" type="password" placeholder="再次確認密碼" value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} autoComplete="new-password" />
                {error && <div className="auth-error">{error}</div>}
                <button className="auth-button" type="submit">註冊</button>
              </form>
            )}
          </div>
        </section>

        {showVerify && (
          <div className="modal-overlay">
            <div className="modal-card">
              <div className="card-title"><span>驗證碼</span></div>
              <div className="card-body">
                {channel ? (
                  <>已寄送至 {channel === 'sms' ? '簡訊' : 'Email'}：<strong>{otpMask || '(隱碼)'}</strong></>
                ) : (
                  <>請輸入驗證碼{debugCode && (<span style={{ marginLeft: 6 }}>(開發碼 <strong>{debugCode}</strong>)</span>)} </>
                )}
                <input
                  className="auth-input"
                  placeholder="請輸入驗證碼"
                  value={verifyCode}
                  onChange={(e) => setVerifyCode(e.target.value)}
                  inputMode="numeric"
                />
                {verifyErr && <div className="auth-error" style={{ marginTop: 8 }}>{verifyErr}</div>}
                <div className="auth-row" style={{ marginTop: 10 }}>
                  {channel && (
                    <div className="chip-group" aria-hidden>
                      <button type="button" className={`chip ${channel==='sms'?'active':''}`} onClick={() => setChannel('sms')}>簡訊</button>
                      <button type="button" className={`chip ${channel==='email'?'active':''}`} onClick={() => setChannel('email')}>Email</button>
                    </div>
                  )}
                  <button
                    type="button"
                    className="link-btn"
                    disabled={cooldown > 0 || otpLoading}
                    onClick={async () => {
                      if (cooldown > 0) return
                      try {
                        setVerifyErr(null)
                        setOtpLoading(true)
                        const resp = await otpRequest({ account, purpose: otpPurpose, channel })
                        setResendMsg(`已重新發送${channel ? '，透過' + (channel==='sms'?'簡訊':'Email') : ''}`)
                        if (resp?.debug_code) console.log('[OTP] debug_code:', resp.debug_code)
                        setOtpMask(resp?.sent_to || '')
                        if (resp?.debug_code) setDebugCode(String(resp.debug_code))
                        setCooldown(Number(resp?.cooldown || 60))
                      } catch (e) {
                        setVerifyErr(String(e.message || e))
                        setResendMsg('')
                        if (!cooldown) setCooldown(60)
                      } finally {
                        setOtpLoading(false)
                      }
                    }}
                  >{cooldown > 0 ? `重新發送(${cooldown}s)` : '重新發送'}</button>
                </div>
                {resendMsg && <div className="small muted">帳號：{user.username || '(未設定)'}</div>}
                <div className="modal-actions">
                  <button className="btn" type="button" onClick={() => setShowVerify(false)}>取消</button>
                  <button
                    className="btn btn-blue"
                    type="button"
                    disabled={!verifyCode || otpLoading}
                    onClick={async () => {
                      try {
                        setVerifyErr(null)
                        setOtpLoading(true)
                        const v = await otpVerify({ account, code: verifyCode.trim(), purpose: otpPurpose })
                        console.log('[OTP] verify ok, ticket=', v.ticket)
                        const info = await otpConsume(v.ticket)
                        console.log('[OTP] consume ok:', info)
                        setShowVerify(false)
                        const userResp = await fetch(`/api/users/${account}`)
                        const userData = await userResp.json()
                        if (onLogin) onLogin(userData)
                      } catch (e) {
                        console.error('[OTP] verify/consume failed:', e)
                        setVerifyErr(String(e.message || e))
                      } finally {
                        setOtpLoading(false)
                      }
                    }}
                  >{otpLoading ? '驗證中' : '驗證'}</button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    )
  }

  

  return (
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
          {myResv.map((r) => {
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
            const cancellable = (String(r.status).includes('審核中') || String(r.review_status||'').toLowerCase().includes('pending'))
            return (
              <div className="resv-card" key={r.id}>
                <div className="resv-main">
                  <div className="resv-title">{r.fromName} → {r.toName}</div>
                  <div className="resv-sub">{fmt(r.when)} ・ {r.people} 人</div>
                  <div className="resv-status">
                    <span className={`status-chip ${cls(r.review_status)}`}>審核 {r.review_status || '-'}</span>
                    <span className={`status-chip ${cls(r.dispatch_status)}`}>調度 {r.dispatch_status || '-'}</span>
                    <span className={`status-chip ${cls(r.payment_status)}`}>支付 {r.payment_status || '-'}</span>
                  </div>
                </div>
                <div className="resv-actions">
                  <button className="btn btn-blue" onClick={() => alert(`${r.fromName} → ${r.toName}\n${fmt(r.when)} ・ ${r.people} 人`) }>查看路線</button>
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

      {/* 假資料區塊加上 TODO */}
      {/* 最近行程 */}
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

      {/* 支付方式 */}
      <section className="card">
        <div className="card-title"><span>支付方式</span></div>
        <div className="list">
          <div className="item">
            <div>
              <div style={{ fontWeight:700 }}>信用卡</div>
              <div className="item-desc">VISA  - 到期日 05/27</div>
            </div>
            <button className="btn-pay-manage" onClick={()=>alert('管理支付方式 /api/payments/methods')}>管理</button>
          </div>
        </div>
      </section>

      {/* 測試推播 */}
      <section className="card">
        <div className="card-title"><span>推播測試</span></div>
        <div className="card-body">
          <button className="btn btn-blue" onClick={handleTestPush}>發送測試推播</button>
          <div className="small muted" style={{ marginTop: 8 }}>請在 HTTPS 或 localhost 環境下測試推播功能</div>
        </div>
      </section>

      {/* 登出 */}
      <section className="card">
        <div className="list">
          <div className="item">
            <div className="item-col"><strong></strong></div>
            <button className="btn btn-orange" onClick={onLogout}>登出</button>
          </div>
        </div>
      </section>

      {/* 高級設定 */}
      <section className="card">
        <div className="card-title">
          <span>高級設定</span>
          <button className="link-btn" onClick={() => setShowAdvanced(v=>!v)}>{showAdvanced ? '隱藏' : '顯示'}</button>
        </div>
        {!showAdvanced && (
          <div className="small muted">高級設定包含更多選項，請小心操作</div>
        )}
      </section>

      {showAdvanced && (
        <>
      
      {/* 帳號設定 */}
      <section className="card profile-section">
        <div className="section-title">帳號設定</div>
        <div className="list">
          {/* 綁定聯絡方式 */}
          <div className="item">
            <div>
              <div style={{ fontWeight: 700 }}>電子郵件</div>
              <div className="item-desc">{user.email || '未設定'} - 已驗證</div>
            </div>
            <div className="item-col">
              <button className="btn-pay-manage" onClick={() => {
                setEditField('email');
                setEditValue(user.email || '');
                setShowEditModal(true);
              }}>修改</button>
            </div>
          </div>
          <div className="item">
            <div>
              <div style={{ fontWeight: 700 }}>手機號碼</div>
              <div className="item-desc">{user.phone || '未設定'} - 已驗證</div>
            </div>
            <div className="item-col">
              <button className="btn-pay-manage" onClick={() => {
                setEditField('phone');
                setEditValue(user.phone || '');
                setShowEditModal(true);
              }}>修改</button>
            </div>
          </div>
          <div className="item">
            <div>
              <div style={{ fontWeight: 700 }}>密碼</div>
              <div className="item-desc">已設定密碼</div>
            </div>
            <button className="btn-pay-manage" onClick={() => {
              setEditField('password');
              setEditValue('');
              setShowEditModal(true);
            }}>修改</button>
          </div>
          <div className="item">
            <div>
              <div style={{ fontWeight: 700 }}>雙重驗證/2FA</div>
              <div className="item-desc">使用 App 進行雙重驗證</div>
            </div>
            <input className="switch" type="checkbox" onChange={(e)=>alert(`2FA ${e.target.checked ? '已開啟' : '已關閉'}（示意）`)} />
          </div>
          <div className="item">
            <div>
              <div style={{ fontWeight: 700 }}>社交帳號綁定</div>
              <div className="item-desc">Google / Apple / Facebook 綁定</div>
            </div>
            <div className="item-col">
              <button className="btn">Google</button>
              <button className="btn">Apple</button>
              <button className="btn">Facebook</button>
            </div>
          </div>
        </div>
      </section>

      {/* 支付方式 */}
      {/* TODO: 支付方式區塊 */}
      {/* 偏好設定 */}
      <section className="card profile-section">
        <div className="section-title">偏好設定</div>
        <div className="list">
          <div className="item">
            <div>
              <div style={{ fontWeight: 700 }}>推播通知</div>
              <div className="item-desc">開啟推播通知</div>
            </div>
            <input type="checkbox" className="switch" />
          </div>
          <div className="item">
            <div>
              <div style={{ fontWeight: 700 }}>語言設定</div>
              <div className="item-desc">選擇顯示語言</div>
            </div>
            <button className="btn" onClick={()=>alert('語言設定')}>設定</button>
          </div>
          <div className="item">
            <div>
              <div style={{ fontWeight: 700 }}>主題設定</div>
              <div className="item-desc">選擇顯示主題</div>
            </div>
            <button className="btn" onClick={()=>alert('主題設定')}>設定</button>
          </div>
        </div>
      </section>

      {/* 安全與會話 */}
      <section className="card profile-section">
        <div className="section-title">安全與會話</div>
        <div className="list">
          <div className="item">
            <div>
              <div style={{ fontWeight: 700 }}>登出所有裝置</div>
              <div className="item-desc">登出所有已登入裝置</div>
            </div>
            <button className="btn" onClick={()=>alert('登出所有裝置')}>登出</button>
          </div>
          <div className="item">
            <div>
              <div style={{ fontWeight: 700 }}>刪除帳號</div>
              <div className="item-desc">永久刪除帳號</div>
            </div>
            <button className="btn" onClick={()=>alert('刪除帳號')}>刪除</button>
          </div>
          <div className="item">
            <div>
              <div style={{ fontWeight: 700 }}>匯出資料</div>
              <div className="item-desc">匯出帳號資料為 JSON / CSV</div>
            </div>
            <div className="item-col">
              <button className="btn" onClick={()=>alert('匯出資料')}>匯出</button>
              <button className="btn" onClick={()=>alert('刪除資料')}>刪除</button>
            </div>
          </div>
        </div>
      </section>

      {/* 幫助 */}
      <section className="card profile-section">
        <div className="section-title">幫助</div>
        <div className="list">
          <div className="item">
            <div>
              <div style={{ fontWeight: 700 }}>常見問題 FAQ</div>
              <div className="item-desc">查看常見問題</div>
            </div>
            <div className="item-col">
              <button className="btn" onClick={()=>alert('查看常見問題')}>查看</button>
              <button className="btn" onClick={()=>alert('聯絡客服')}>聯絡客服</button>
              <button className="btn" onClick={()=>alert('發送 Email')}>Email</button>
            </div>
          </div>
          <div className="item">
            <div>
              <div style={{ fontWeight: 700 }}>隱私政策</div>
              <div className="item-desc">查看隱私政策</div>
            </div>
            <button className="btn" onClick={()=>alert('查看隱私政策')}>查看</button>
          </div>
        </div>
      </section>
      </>
      )}
      {showEditModal && (
        <div className="modal-overlay">
          <div className="modal-card">
            <div className="card-title"><span>修改{editField === 'email' ? '電子郵件' : editField === 'phone' ? '手機號碼' : '密碼'}</span></div>
            <div className="card-body">
              <input
                className="auth-input"
                type={editField === 'password' ? 'password' : 'text'}
                placeholder={`請輸入新${editField === 'email' ? '電子郵件' : editField === 'phone' ? '手機號碼' : '密碼'}`}
                value={editValue}
                onChange={e => setEditValue(e.target.value)}
              />
              <input
                className="auth-input"
                type="text"
                placeholder="請輸入驗證碼"
                value={editCode}
                onChange={e => setEditCode(e.target.value)}
              />
              {editError && <div className="auth-error">{editError}</div>}
              <div className="modal-actions">
                <button className="btn" type="button" onClick={() => setShowEditModal(false)}>取消</button>
                <button className="btn btn-blue" type="button" onClick={async () => {
                  setEditError('')
                  try {
                    const body = { code: editCode }
                    body[editField] = editValue
                    const resp = await fetch(`/api/users/${user.username}`, {
                      method: 'PUT',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify(body)
                    })
                    if (!resp.ok) throw new Error(await resp.text())
                    setShowEditModal(false)
                    // 重新取得用戶資料
                    const userResp = await fetch(`/api/users/${user.username}`)
                    const userData = await userResp.json()
                    if (onLogin) onLogin(userData)
                  } catch (err) {
                    setEditError(String(err.message || err))
                  }
                }}>送出</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
export default ProfilePage





