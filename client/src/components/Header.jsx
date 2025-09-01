// src/components/Header.jsx
import React from 'react'

export default function Header() {
  const handleLogo = () => {
    console.log('返回 首頁（Logo） 被按下')
  }

  return (
    <header className="header">
      <div className="header-inner">
        <div
          className="logo-square"
          role="button"
          tabIndex={0}
          onClick={handleLogo}
          onKeyDown={(e) => e.key === 'Enter' && handleLogo()}
          aria-label="回到首頁"
        />
        <div className="title-block">
          <div className="app-title">智慧公車</div>
          <div className="subtitle muted">公車查詢服務</div>
        </div>
      </div>
    </header>
  )
}
