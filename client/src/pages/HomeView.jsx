import React, { useState, useEffect, useRef } from 'react'
import { getRoutes, getRouteStops, getTomorrowReservations } from '../services/api'

export default function HomeView({ onAction, user, onNavigateRoutes }) {
  // 🔹 搜尋相關 state
  const [allRoutes, setAllRoutes] = useState([])
  const [searchOpen, setSearchOpen] = useState(false)
  const [query, setQuery] = useState('')

  // 🔹 即時到站相關 state
  const [arrivals, setArrivals] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [tick, setTick] = useState(0)
  const [refreshing, setRefreshing] = useState(false)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [pressedKey, setPressedKey] = useState(null)

  // 🔹 明日預約
  const [tomorrowReservations, setTomorrowReservations] = useState([])

  // --- Auto refresh 控制 ---
  const AUTO_REFRESH_MS = 30000 // 30s
  const interactingRef = useRef(false)
  const interactTimer = useRef(null)

  // 標記使用者互動，避免 refresh jank
  useEffect(() => {
    const markInteract = () => {
      interactingRef.current = true
      clearTimeout(interactTimer.current)
      interactTimer.current = setTimeout(() => (interactingRef.current = false), 900)
    }
    const onScroll = () => markInteract()
    const onTouchStart = () => markInteract()
    const onTouchEnd = () => markInteract()
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('touchstart', onTouchStart, { passive: true })
    window.addEventListener('touchend', onTouchEnd, { passive: true })
    return () => {
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('touchstart', onTouchStart)
      window.removeEventListener('touchend', onTouchEnd)
      clearTimeout(interactTimer.current)
    }
  }, [])

  // 定時更新 tick
  useEffect(() => {
    const id = setInterval(() => {
      if (document.hidden) return
      if (interactingRef.current) return
      if (searchOpen) return
      setTick((t) => (t + 1) % 1_000_000)
    }, AUTO_REFRESH_MS)
    return () => clearInterval(id)
  }, [searchOpen])

  // --- 抓即時到站 ---
  useEffect(() => {
    let cancelled = false
    const refresh = async ({ hard = false } = {}) => {
      try {
        if (hard) setLoading(true)
        setError(null)
        const routes = allRoutes.length ? allRoutes : await getRoutes()
        if (!allRoutes.length) setAllRoutes(routes)
        const pick = routes.slice(0, 3)
        const perRoute = await Promise.all(
          pick.map(async (r) => {
            let stops = []
            try {
              stops = await getRouteStops(r.id, '去程')
            } catch {
              try { stops = await getRouteStops(r.id, '回程') } catch {}
            }
            return { route: r, stops }
          })
        )
        const items = perRoute.flatMap(({ route: r, stops }) => {
          if (!stops || stops.length === 0) return []
          const lastEta = stops.reduce((m, s) => Math.max(m, Number(s.etaFromStart) || 0), 0)
          const cycle = Math.max(lastEta + 5, stops.length * 3) || 20
          const nowMin = (Date.now() / 60000) % cycle
          const annotate = (eta) => {
            const delta = eta - nowMin
            if (delta <= -1.0) return { label: '已過站', etaText: null, score: 999 }
            if (delta <= 0.25) return { label: '到站中', etaText: '0 分鐘', score: 0 }
            if (delta <= 5.0) return { label: '即將到站', etaText: `${Math.ceil(delta)} 分鐘`, score: delta }
            return { label: '等待中', etaText: `${Math.ceil(delta)} 分鐘`, score: delta + 100 }
          }
          const enriched = stops
            .map((s, idx) => {
              const eta = Number(s.etaFromStart ?? (idx * 3))
              const a = annotate(eta)
              return {
                route: r.name,
                directionLabel: r.direction?.includes('回') ? '(回)' : '(去)',
                stop: s.stopName || `第${(s.order ?? (idx + 1))}站`,
                eta: a.etaText || '-',
                status: a.label,
                score: a.score,
                key: `${r.id}-${s.order ?? idx}`,
              }
            })
            .sort((a, b) => a.score - b.score)
          return enriched.slice(0, 1)
        })
        if (!cancelled) {
          const next = items.slice(0, 3)
          const a = JSON.stringify(next)
          const b = JSON.stringify(arrivals)
          if (a !== b) setArrivals(next)
          setLastUpdated(new Date())
        }
      } catch (e) {
        if (!cancelled) {
          setError('無法載入即將到站資料')
          console.warn('Home arrivals load error:', e)
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
          setRefreshing(false)
        }
      }
    }
    refresh({ hard: true })
    return () => { cancelled = true }
  }, [tick]) // eslint-disable-line

  // --- 抓明日預約 ---
  useEffect(() => {
    const uid = user?.user_id || user?.id
    if (!uid) return
    getTomorrowReservations(uid)
      .then(rows => setTomorrowReservations(rows))
      .catch(e => console.warn("載入明日預約失敗", e))
  }, [user])

  return (
    <main className="container">
      {/* 🔎 搜尋區 */}
      <section className="search-section">
        {!searchOpen ? (
          <div
            className="search-input"
            role="button"
            tabIndex={0}
            onClick={() => setSearchOpen(true)}
            onKeyDown={(e) => e.key === 'Enter' && setSearchOpen(true)}
          >
            搜尋路線、站點或目的地
          </div>
        ) : (
          <div className="search-input" style={{ padding: 10 }}>
            <input
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="輸入路線名稱關鍵字"
              className="search-field"
              onKeyDown={(e) => { if (e.key === 'Escape') setSearchOpen(false) }}
            />
            <div className="search-suggestions">
              {allRoutes && query.trim() !== '' ? (
                allRoutes
                  .filter((r) => (r.name || '').toLowerCase().includes(query.trim().toLowerCase()))
                  .slice(0, 10)
                  .map((r) => (
                    <div
                      key={r.key}
                      className="suggest-item"
                      role="button"
                      tabIndex={0}
                      onClick={() => { setSearchOpen(false); onNavigateRoutes && onNavigateRoutes() }}
                      onKeyDown={(e) => { if (e.key === 'Enter') { setSearchOpen(false); onNavigateRoutes && onNavigateRoutes() } }}
                    >
                      <div className="suggest-name">{r.name}</div>
                      <div className="muted small">{r.direction}</div>
                    </div>
                  ))
              ) : (
                <div className="muted small">輸入關鍵字以搜尋路線</div>
              )}
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
              <button className="btn" onClick={() => setSearchOpen(false)}>取消</button>
              <button className="btn btn-blue" onClick={() => onNavigateRoutes && onNavigateRoutes()}>查看全部路線</button>
            </div>
          </div>
        )}

        <div className="search-actions">
          <button className="btn btn-blue" onClick={() => onAction('附近站點')}>附近站點</button>
          <button className="btn btn-orange" onClick={() => onNavigateRoutes && onNavigateRoutes()}>常用路線</button>
        </div>
      </section>

      {/* 🚌 即時到站 */}
      <section className="card">
        <div className="card-title">
          <span>即時到站</span>
          <button
            className="link-btn"
            onClick={() => { setRefreshing(true); setTick((t) => t + 1) }}
            disabled={refreshing}
          >{refreshing ? '更新中…' : '更新'}</button>
        </div>
        <div className="arrival-list">
          {loading && <div className="muted small">載入中…</div>}
          {error && <div className="muted small" style={{ color: '#c25' }}>{error}</div>}
          {!loading && arrivals.map((a) => (
            <div
              key={a.key}
              className={`arrival-item arrival-item--tight ${pressedKey === a.key ? 'is-pressed' : ''}`}
              role="button"
              tabIndex={0}
              onPointerDown={() => setPressedKey(a.key)}
              onPointerUp={() => setPressedKey(null)}
              onPointerCancel={() => setPressedKey(null)}
              onPointerLeave={() => setPressedKey(null)}
              onClick={() => onAction(`${a.route} ${a.directionLabel} ${a.stop} - ${a.eta}`)}
              onKeyDown={(e) => e.key === 'Enter' && onAction(`${a.route} ${a.directionLabel} ${a.stop} - ${a.eta}`)}
            >
              <div className="arrival-left arrival-left--nowrap">
                <div className="route-line">
                  <div className="route-name route-name--wrap">{a.route}</div>
                  <div className="direction">{a.directionLabel}</div>
                </div>
                <div className="arrival-stop muted">{a.stop}</div>
              </div>
              <div className="arrival-right">
                <div className="eta eta--right">{a.status} {a.eta ? `• ${a.eta}` : ''}</div>
              </div>
            </div>
          ))}
          {!loading && arrivals.length === 0 && !error && (
            <div className="muted small">暫無即將到站資訊</div>
          )}
        </div>
      </section>

      {/* 📅 明日預約 */}
      <section className="card">
        <div className="card-title"><span>明日預約</span></div>
        {tomorrowReservations.length > 0 ? (
          <div className="card-body">
            {tomorrowReservations.map((r) => (
              <div key={r.reservation_id} className="item">
                <div>{r.booking_start_station_name} → {r.booking_end_station_name}</div>
                <div className="small muted">{r.booking_time} ・ {r.booking_number}人</div>
              </div>
            ))}
          </div>
        ) : (
          <div className="card-body center-vertical">
            <div className="muted">尚無明日預約</div>
            <button className="btn btn-block btn-blue mt-12" onClick={() => onAction('新增預約')}>新增預約</button>
          </div>
        )}
      </section>

      {/* 📢 服務公告 */}
      <section className="card">
        <div className="card-title"><span>服務公告</span></div>
        <div className="announcement">
          <div className="announce-item" role="button" tabIndex={0} onClick={() => onAction('新路線開通')}>
            <strong>新路線開通</strong>
            <div className="muted small">202 路線新增內湖科技園區站點，提供更便利的交通服務。</div>
          </div>
          <div className="announce-item" role="button" tabIndex={0} onClick={() => onAction('服務調整通知')}>
            <strong>服務調整通知</strong>
            <div className="muted small">因應天候因素，部分路線班次可能延誤，請耐心等候。</div>
          </div>
        </div>
      </section>
    </main>
  )
}
