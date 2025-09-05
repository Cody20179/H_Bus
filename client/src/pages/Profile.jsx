import React, { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'

export default function ProfilePage({ user, onLogin, onLogout }) {
  const navigate = useNavigate()
  const location = useLocation()
  const [mode, setMode] = useState('login') // 'login' | 'signup'
  const [account, setAccount] = useState('') // email or phone
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('') // for signup
  const [remember, setRemember] = useState(true)
  const [error, setError] = useState(null)

  // Verify code modal state
  const [showVerify, setShowVerify] = useState(false)
  const [verifyCode, setVerifyCode] = useState('')
  const [verifyErr, setVerifyErr] = useState(null)
  const [channel, setChannel] = useState('email') // 'email' | 'sms'
  const [pendingUser, setPendingUser] = useState(null)
  const [resendMsg, setResendMsg] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    if (!account || !password) {
      setError('請輸入帳號與密碼')
      return
    }
    const isEmail = /.+@.+\..+/.test(account)
    const isPhone = /^\+?\d{8,15}$/.test(account.replaceAll(/[-\s]/g, ''))
    if (!isEmail && !isPhone) {
      setError('請輸入正確的 Email 或手機號碼')
      return
    }
    // Prepare for verify step (default code is 1234)
    const display = mode === 'signup' && fullName ? fullName : (isEmail ? account.split('@')[0] : `用戶${account.slice(-4)}`)
    setPendingUser({ name: display, account, provider: isEmail ? 'email' : 'phone', remember })
    setChannel(isEmail ? 'email' : 'sms')
    setVerifyCode('')
    setVerifyErr(null)
    setResendMsg('')
    setShowVerify(true)
  }

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
            <form onSubmit={handleSubmit} className="auth-form" style={{ marginTop: 10 }}>
              {mode === 'signup' && (
                <input
                  className="auth-input"
                  type="text"
                  placeholder="姓名"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  autoComplete="name"
                />
              )}
              <input
                className="auth-input"
                type="text"
                placeholder="Email 或 手機號碼"
                value={account}
                onChange={(e) => setAccount(e.target.value)}
                autoComplete="username"
              />
              <input
                className="auth-input"
                type="password"
                placeholder="密碼"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              />
              <div className="auth-row">
                <label className="auth-remember">
                  <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} /> 記住我
                </label>
                <button type="button" className="auth-link" onClick={() => alert('忘記密碼流程尚未串接 API')}>忘記密碼？</button>
              </div>
              {error && <div className="auth-error">{error}</div>}
              <button className="auth-button" type="submit">{mode==='login' ? 'SIGN IN' : 'SIGN UP'}</button>
            </form>
          </div>
        </section>

        {showVerify && (
          <div className="modal-overlay">
            <div className="modal-card">
              <div className="card-title"><span>輸入驗證碼</span></div>
              <div className="card-body">
                <div className="small" style={{ marginBottom: 8 }}>
                  已傳送驗證碼到 {channel === 'sms' ? '簡訊' : 'Email'}：
                  <strong> {(() => {
                    const v = account
                    if (!v) return ''
                    if (channel === 'email') {
                      const parts = v.split('@')
                      return parts.length === 2 ? `${parts[0].slice(0,1)}***@${parts[1]}` : v
                    }
                    // phone mask
                    const digits = v.replace(/\D/g, '')
                    return digits.length >= 5 ? `${digits.slice(0,3)}****${digits.slice(-2)}` : v
                  })()} </strong>
                </div>
                <input
                  className="auth-input"
                  placeholder="請輸入 1234"
                  value={verifyCode}
                  onChange={(e) => setVerifyCode(e.target.value)}
                  inputMode="numeric"
                />
                {verifyErr && <div className="auth-error" style={{ marginTop: 8 }}>{verifyErr}</div>}
                <div className="auth-row" style={{ marginTop: 10 }}>
                  <div className="chip-group">
                    <button type="button" className={`chip ${channel==='sms'?'active':''}`} onClick={() => setChannel('sms')}>簡訊</button>
                    <button type="button" className={`chip ${channel==='email'?'active':''}`} onClick={() => setChannel('email')}>Email</button>
                  </div>
                  <button
                    type="button"
                    className="link-btn"
                    onClick={() => { setResendMsg(`驗證碼已重新寄送（${channel==='sms'?'簡訊':'Email'}）`); setVerifyErr(null) }}
                  >重新寄送</button>
                </div>
                {resendMsg && <div className="small muted" style={{ marginTop: 6 }}>{resendMsg}</div>}
                <div className="modal-actions">
                  <button className="btn" type="button" onClick={() => setShowVerify(false)}>取消</button>
                  <button
                    className="btn btn-blue"
                    type="button"
                    onClick={() => {
                      if (verifyCode.trim() === '1234') {
                        const params = new URLSearchParams(location.search)
                        const from = params.get('from')
                        onLogin?.(pendingUser || { name: '使用者', account })
                        setShowVerify(false)
                        navigate(from === 'reserve' ? '/reserve' : '/profile', { replace: true })
                      } else {
                        setVerifyErr('驗證碼錯誤，請再試一次（預設 1234）')
                      }
                    }}
                  >確認</button>
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
      {/* 帳號設定 */}
      <section className="card profile-section">
        <div className="section-title">帳號設定（Account）</div>
        <div className="list">
          <div className="item">
            <div className="item-col">
              <div className="avatar">{(user.name||'U').slice(0,2).toUpperCase()}</div>
              <div>
                <div style={{ fontWeight: 800 }}>{user.name}</div>
                <div className="item-desc">使用者 ID：{user.id || '(暫無)'}</div>
              </div>
            </div>
            <span className="badge">一般會員</span>
          </div>
          <div className="item">
            <div>
              <div style={{ fontWeight: 700 }}>電子郵件</div>
              <div className="item-desc">{user.account?.includes('@') ? user.account : '尚未綁定'} · 未驗證</div>
            </div>
            <div className="item-col">
              <button className="btn btn-blue" onClick={() => alert('寄送驗證信（示意）')}>發送驗證</button>
            </div>
          </div>
          <div className="item">
            <div>
              <div style={{ fontWeight: 700 }}>手機</div>
              <div className="item-desc">{user.account && !user.account.includes('@') ? user.account : '尚未綁定'} · 未驗證</div>
            </div>
            <div className="item-col">
              <button className="btn" onClick={() => alert('發送簡訊驗證（示意）')}>發送驗證</button>
            </div>
          </div>
          <div className="item">
            <div>
              <div style={{ fontWeight: 700 }}>更改密碼</div>
              <div className="item-desc">建議定期更新密碼提升安全性</div>
            </div>
            <button className="btn" onClick={() => alert('更改密碼流程（示意）')}>變更</button>
          </div>
          <div className="item">
            <div>
              <div style={{ fontWeight: 700 }}>兩步驟驗證（2FA）</div>
              <div className="item-desc">使用驗證器 App 或簡訊</div>
            </div>
            <input className="switch" type="checkbox" onChange={(e)=>alert(`2FA ${e.target.checked?'啟用':'停用'}（示意）`)} />
          </div>
          <div className="item">
            <div>
              <div style={{ fontWeight: 700 }}>社群/第三方登入</div>
              <div className="item-desc">Google / Apple / Facebook 綁定與解除</div>
            </div>
            <div className="item-col">
              <button className="btn">Google</button>
              <button className="btn">Apple</button>
              <button className="btn">Facebook</button>
            </div>
          </div>
        </div>
      </section>

      {/* 付款與票務 */}
      <section className="card profile-section">
        <div className="section-title">付款與票務（Payment & Ticket）</div>
        <div className="list">
          <div className="item">
            <div>
              <div style={{ fontWeight: 700 }}>付款方式</div>
              <div className="item-desc">尚未新增付款方式</div>
            </div>
            <button className="btn btn-blue" onClick={()=>alert('新增付款方式 / tokenization（示意）')}>新增</button>
          </div>
          <div className="item">
            <div>
              <div style={{ fontWeight: 700 }}>票卡管理</div>
              <div className="item-desc">餘額、儲值紀錄、票種與折扣憑證</div>
            </div>
            <button className="btn" onClick={()=>alert('開啟票卡管理（示意）')}>管理</button>
          </div>
          <div className="item">
            <div>
              <div style={{ fontWeight: 700 }}>發票／帳單資訊</div>
              <div className="item-desc">發票類型、統編、收件地址</div>
            </div>
            <button className="btn" onClick={()=>alert('設定發票資料（示意）')}>設定</button>
          </div>
        </div>
      </section>

      {/* 個人資料 */}
      <section className="card profile-section">
        <div className="section-title">個人資料（Personal info）</div>
        <div className="list">
          <div className="item">
            <div>
              <div style={{ fontWeight: 700 }}>基本資料</div>
              <div className="item-desc">姓名、暱稱、生日、性別</div>
            </div>
            <button className="btn" onClick={()=>alert('編輯基本資料（示意）')}>編輯</button>
          </div>
          <div className="item">
            <div>
              <div style={{ fontWeight: 700 }}>地址與常用站點</div>
              <div className="item-desc">寄送地址、我的最愛路線與站牌</div>
            </div>
            <button className="btn" onClick={()=>alert('管理地址與站點（示意）')}>管理</button>
          </div>
          <div className="item">
            <div>
              <div style={{ fontWeight: 700 }}>身分證明</div>
              <div className="item-desc">上傳證明文件、核驗狀態</div>
            </div>
            <button className="btn" onClick={()=>alert('上傳/查看證明（示意）')}>上傳</button>
          </div>
        </div>
      </section>

      {/* 通知與偏好 */}
      <section className="card profile-section">
        <div className="section-title">通知與偏好（Preferences）</div>
        <div className="list">
          <div className="item">
            <div>
              <div style={{ fontWeight: 700 }}>推播通知</div>
              <div className="item-desc">到站提醒、路況異常、帳單與行程通知</div>
            </div>
            <input type="checkbox" className="switch" />
          </div>
          <div className="item">
            <div>
              <div style={{ fontWeight: 700 }}>語言與時區</div>
              <div className="item-desc">介面語言、時區與地圖顯示偏好</div>
            </div>
            <button className="btn" onClick={()=>alert('設定偏好（示意）')}>設定</button>
          </div>
          <div className="item">
            <div>
              <div style={{ fontWeight: 700 }}>隱私偏好</div>
              <div className="item-desc">位置收集、使用分析資料</div>
            </div>
            <button className="btn" onClick={()=>alert('設定隱私（示意）')}>設定</button>
          </div>
        </div>
      </section>

      {/* 安全與登入狀態 */}
      <section className="card profile-section">
        <div className="section-title">安全與登入狀態（Security & Sessions）</div>
        <div className="list">
          <div className="item">
            <div>
              <div style={{ fontWeight: 700 }}>已登入裝置</div>
              <div className="item-desc">查看裝置並可登出各裝置</div>
            </div>
            <button className="btn" onClick={()=>alert('管理裝置（示意）')}>管理</button>
          </div>
          <div className="item">
            <div>
              <div style={{ fontWeight: 700 }}>安全事件 / 最近活動</div>
              <div className="item-desc">登入時間、IP、位置</div>
            </div>
            <button className="btn" onClick={()=>alert('查看活動（示意）')}>查看</button>
          </div>
          <div className="item">
            <div>
              <div style={{ fontWeight: 700 }}>帳號刪除 / 資料匯出</div>
              <div className="item-desc">刪除流程、資料匯出（JSON / CSV）</div>
            </div>
            <div className="item-col">
              <button className="btn" onClick={()=>alert('資料匯出（示意）')}>匯出</button>
              <button className="btn" onClick={()=>alert('帳號刪除（示意）')}>刪除</button>
            </div>
          </div>
        </div>
      </section>

      {/* 其他：登出、客服與法務 */}
      <section className="card profile-section">
        <div className="section-title">其他</div>
        <div className="list">
          <div className="item">
            <div>
              <div style={{ fontWeight: 700 }}>客服與 FAQ</div>
              <div className="item-desc">聯絡客服、常見問題</div>
            </div>
            <div className="item-col">
              <button className="btn" onClick={()=>alert('聊天（示意）')}>聊天</button>
              <button className="btn" onClick={()=>alert('客服電話（示意）')}>電話</button>
              <button className="btn" onClick={()=>alert('客服 Email（示意）')}>Email</button>
            </div>
          </div>
          <div className="item">
            <div>
              <div style={{ fontWeight: 700 }}>法務連結</div>
              <div className="item-desc">隱私權政策、使用條款、票務規範、退費規則</div>
            </div>
            <button className="btn" onClick={()=>alert('開啟連結（示意）')}>查看</button>
          </div>
          <div className="item">
            <div className="item-col"><strong>登出</strong></div>
            <button className="btn btn-orange" onClick={onLogout}>登出</button>
          </div>
        </div>
      </section>
    </div>
  )
}

