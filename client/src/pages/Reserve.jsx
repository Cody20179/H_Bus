import React from 'react'

export default function ReservePage({ user, onRequireLogin }) {
  if (!user) {
    return (
      <div className="container">
        <section className="card">
          <div className="card-title"><span>預約服務</span></div>
          <div className="card-body">
            <div className="muted" style={{ marginBottom: 12 }}>尚未登入，無法使用預約功能。</div>
            <button className="btn btn-blue" onClick={onRequireLogin}>前往登入</button>
          </div>
        </section>
      </div>
    )
  }

  return (
    <div className="container">
      <section className="card">
        <div className="card-title"><span>預約服務</span></div>
        <div className="card-body">
          <div>您好，{user.name}，請選擇欲預約的服務（範例）。</div>
          <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
            <button className="btn btn-orange">新增預約</button>
            <button className="btn">查看預約</button>
          </div>
        </div>
      </section>
    </div>
  )
}

