// src/pages/HomeView.jsx
import React from 'react'
import BottomNav from '../components/BottomNav'

export default function HomeView({ onAction }) {
  return (
    <main className="container">
      {/* 把你現有的搜尋、即時到站、公告等區塊搬過來 */}
      <section className="search-section">
        <div className="search-input" role="button" tabIndex={0} onClick={()=>onAction('搜尋框')}>搜尋路線、站點或目的地</div>
        <div className="search-actions">
          <button className="btn btn-blue" onClick={()=>onAction('附近站點')}>附近站點</button>
          <button className="btn btn-orange" onClick={()=>onAction('常用路線')}>常用路線</button>
        </div>
      </section>

      {/* 這裡可貼入你先前的即時到站卡片（arrivals）與公告卡片 */}
    </main>
  )
}
