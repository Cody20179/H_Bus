import React, { useState } from 'react'

export default function ProfilePage({ user, onLogin, onLogout }) {
  const [name, setName] = useState('測試用戶')

  if (!user) {
    return (
      <div className="container">
        <section className="card">
          <div className="card-title"><span>個人中心</span></div>
          <div className="card-body">
            <div className="muted small" style={{ marginBottom: 10 }}>請先登入以使用預約等服務</div>
            <div style={{ display: 'flex', gap: 8 }}>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="輸入姓名"
                className="search-field"
                style={{ flex: 1 }}
              />
              <button className="btn btn-blue" onClick={() => onLogin({ name })}>登入</button>
            </div>
          </div>
        </section>
      </div>
    )
  }

  return (
    <div className="container">
      <section className="card">
        <div className="card-title"><span>個人中心</span></div>
        <div className="card-body">
          <div className="muted">已登入：{user.name}</div>
          <button className="btn mt-12" onClick={onLogout}>登出</button>
        </div>
      </section>
    </div>
  )
}

