// src/App.jsx
import React, { useEffect, useState } from 'react'
import Header from './components/Header'
import BottomNav from './components/BottomNav'
import RoutesPage from './pages/Routes'
import ReservePage from './pages/Reserve'
import ProfilePage from './pages/Profile'
import { Routes, Route, useNavigate, useLocation, Navigate } from 'react-router-dom'
import NearbyStations from './components/NearbyStations'
import HomeView from './pages/HomeView'

export default function App() {
  const [user, setUser] = useState(null)
  const navigate = useNavigate()
  const location = useLocation()
  const [showNearby, setShowNearby] = useState(false)

  const handleAction = (name) => {
    console.log(`${name} 被觸發`)
    if (name && String(name).includes('附近')) {
      setShowNearby(true)
    }
  }

  const navMap = {
    '首頁': '/',
    '路線': '/routes',
    '預約': '/reserve',
    '個人': '/profile',
  }

  const handleNav = (name) => {
    const to = navMap[name]
    if (to) {
      navigate(to)
    } else {
      console.log(`${name} 沒有對應的路徑`)
    }
  }

  const activeLabel = (() => {
    if (location.pathname.startsWith('/routes')) return '路線'
    if (location.pathname.startsWith('/reserve')) return '預約'
    if (location.pathname.startsWith('/profile')) return '個人'
    return '首頁'
  })()

  // Persist user across sessions
  useEffect(() => {
    try {
      const raw = localStorage.getItem('hb_user')
      if (raw) setUser(JSON.parse(raw))
    } catch {}
  }, [])

  const handleLogin = (u) => {
    setUser(u)
    try { localStorage.setItem('hb_user', JSON.stringify(u)) } catch {}
  }
  const handleLogout = () => {
    setUser(null)
    try { localStorage.removeItem('hb_user') } catch {}
  }

  return (
    <div className="page-root">
      <Header />
      <div className="view">
        <Routes>
          <Route
            path="/"
            element={<HomeView onAction={handleAction} user={user} />}
          />
          {/* 原本的 routes 清單 */}
          <Route path="/routes" element={<RoutesPage />} />
          {/* 新增：指定路線 + 站點的網址 */}
          <Route path="/routes/:routeId/stop/:stopOrder" element={<RoutesPage />} />
          <Route
            path="/reserve"
            element={<ReservePage user={user} onRequireLogin={() => navigate('/profile?from=reserve')} />}
          />
          <Route
            path="/profile"
            element={<ProfilePage user={user} onLogin={handleLogin} onLogout={handleLogout} />}
          />
          <Route path="*" element={<Navigate to="/" replace />} />
          <Route path="/routes/:routeId/stop/:stopOrder" element={<RoutesPage />} />
        </Routes>
      </div>
      <BottomNav onNavClick={handleNav} active={activeLabel} />
      {showNearby && <NearbyStations onClose={() => setShowNearby(false)} />}
    </div>
  )
}
