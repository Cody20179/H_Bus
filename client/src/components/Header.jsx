// src/components/Header.jsx
import React from 'react'
import { useNavigate } from 'react-router-dom'

export default function Header() {
  const navigate = useNavigate()
  const handleLogo = () => {
    navigate('/')
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
        >
          <span className="logo-emoji" aria-hidden>🚌</span>
        </div>
        <div className="title-block">
          <div className="app-title">智慧公車</div>
          <div className="subtitle muted">公車查詢服務</div>
        </div>
      </div>
    </header>
  )
}
