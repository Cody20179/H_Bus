// Centralized API client for the frontend.
// Dev: use Vite proxy with path `/api`.
// Prod (same-origin deploy): default to '' unless VITE_API_BASE_URL is set.
const envBase = (import.meta.env && import.meta.env.VITE_API_BASE_URL) || ''
const BASE = (envBase?.trim?.() || (import.meta.env?.DEV ? '/api' : ''))

export async function getRoutes() {
  const res = await fetch(`${BASE}/All_Route`, {
    headers: { accept: 'application/json' },
  })
  if (!res.ok) {
    throw new Error(`Failed to load routes: ${res.status}`)
  }

  const data = await res.json()

  return data
    .filter((r) => r.status !== 0) // 把 status 為 0 的項目剔除
    .map((r) => ({
      id: r.route_id,
      name: r.route_name,
      direction: r.direction || '',
      stopCount: r.stop_count ?? null,
      startStop: r.start_stop ?? '',
      endStop: r.end_stop ?? '',
      status: r.status,
      createdAt: r.created_at,
      source: 'api',
      key: `${r.route_name} ${r.direction || ''}`.trim(),
      _raw: r,
    }))
}


export async function getRouteStops(routeId, direction) {
  // Backend expects JSON body: { route_id, direction }
  const res = await fetch(`${BASE}/Route_Stations`, {
    method: 'POST',
    headers: {
      accept: 'application/json',
      'content-type': 'application/json',
    },
    body: JSON.stringify({ route_id: routeId, direction }),
  })
  if (!res.ok) {
    throw new Error(`Failed to load stops: ${res.status}`)
  }
  /** @type {Array} */
  const data = await res.json()
  return data
    .map((s) => ({
      routeId: s.route_id,
      routeName: s.route_name,
      direction: s.direction,
      stopName: s.stop_name,
      latitude: s.latitude,
      longitude: s.longitude,
      etaFromStart: s.eta_from_start,
      order: s.stop_order,
      createdAt: s.created_at,
    }))
    .sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
}

// Bind contacts (phone + email). Backend may not exist yet; handle 404 gracefully.
export async function bindContacts({ username, phone, email }) {
  try {
    const res = await fetch(`${BASE}/profile/bind_contacts`, {
      method: 'POST',
      headers: { 'content-type': 'application/json', accept: 'application/json' },
      body: JSON.stringify({ username, phone, email }),
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data?.detail || `Bind failed: ${res.status}`)
    return { ok: true, data }
  } catch (e) {
    console.warn('[bindContacts] backend unavailable, falling back to localStorage:', e)
    try {
      const key = `hb_contacts_${username || 'user'}`
      localStorage.setItem(key, JSON.stringify({ phone, email, ts: Date.now() }))
      return { ok: true, local: true }
    } catch {}
    return { ok: false, error: String(e.message || e) }
  }
  
}

// --- Stations (Hualien) ---
// 取得 /yo_hualien 的站點清單
export async function getStations() {
  const res = await fetch(`${BASE}/yo_hualien`, {
    headers: { accept: 'application/json' },
  })
  if (!res.ok) {
    throw new Error(`Failed to load stations: ${res.status}`)
  }
  const data = await res.json()
  // 正規化：確保數值類型且提供簡易 id
  return data
    .filter((s) => Number.isFinite(Number(s.latitude)) && Number.isFinite(Number(s.longitude)))
    .map((s, i) => ({
      id: i + 1,
      name: s.station_name,
      address: s.address,
      lat: Number(s.latitude),
      lng: Number(s.longitude),
      _raw: s,
    }))
}

// --- Reservations ---
export async function getMyReservations(userId) {
  const res = await fetch(`${BASE}/reservations/my?user_id=${encodeURIComponent(userId)}`, {
    headers: { accept: 'application/json' },
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(`Failed to load reservations: ${res.status}`)
  // 後端目前回傳 { status, sql }；其中 sql 才是資料列陣列
  const rows = Array.isArray(data?.sql) ? data.sql : (Array.isArray(data) ? data : [])
  return rows
}

export async function cancelReservation(reservationId) {
  const res = await fetch(`${BASE}/reservations/Canceled`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', accept: 'application/json' },
    body: JSON.stringify({ reservation_id: reservationId }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.detail || `Cancel failed: ${res.status}`);
  return data;
}


export async function createReservation(payload) {
  // 你的後端 FastAPI 函式參數（未使用 Body/Form），預設 expects Query 參數
  // 因此改成以 QueryString 傳遞，method 維持 POST
  const params = new URLSearchParams()
  Object.entries(payload || {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null) params.append(k, String(v))
  })
  const url = `${BASE}/reservations?${params.toString()}`
  const res = await fetch(url, {
    method: 'POST',
    headers: { accept: 'application/json' },
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data?.detail || `Create failed: ${res.status}`)
  return data
}

export async function getReservation(reservationId) {
  const res = await fetch(`${BASE}/reservations/${encodeURIComponent(reservationId)}`, {
    headers: { accept: 'application/json' },
  })
  if (!res.ok) throw new Error(`Get failed: ${res.status}`)
  return await res.json()
}

export async function updateReservation(reservationId, fields) {
  const params = new URLSearchParams()
  Object.entries(fields || {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null) params.append(k, String(v))
  })
  const res = await fetch(`${BASE}/reservations/${encodeURIComponent(reservationId)}`, {
    method: 'PUT',
    headers: { 'content-type': 'application/x-www-form-urlencoded', accept: 'application/json' },
    body: params.toString(),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data?.detail || `Update failed: ${res.status}`)
  return data
}
