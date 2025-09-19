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
    .filter((r) => r.status !== 0) // ??status ??0 ???桀???
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
// ?? /yo_hualien ??暺???
export async function getStations() {
  const res = await fetch(`${BASE}/yo_hualien`, {
    headers: { accept: 'application/json' },
  })
  if (!res.ok) {
    throw new Error(`Failed to load stations: ${res.status}`)
  }
  const data = await res.json()
  // 甇????蝣箔??詨潮?????蝪⊥? id
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
  // 敺垢?桀?? { status, sql }嚗銝?sql ?鞈????
  let rows = []
  if (Array.isArray(data?.reservations)) rows = data.reservations
  else if (Array.isArray(data?.sql)) rows = data.sql
  else if (Array.isArray(data?.data)) rows = data.data
  else if (Array.isArray(data)) rows = data
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
  // 雿?敺垢 FastAPI ?賢??嚗雿輻 Body/Form嚗??身 expects Query ?
  // ?迨?寞?隞?QueryString ?喲?嚗ethod 蝬剜? POST
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

