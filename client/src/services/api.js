// Centralized API client for the frontend.
// Uses Vite dev server proxy: requests to `/api` are proxied to your backend.

const BASE = '/api'

export async function getRoutes() {
  const res = await fetch(`${BASE}/All_Route`, {
    headers: { accept: 'application/json' },
  })
  if (!res.ok) {
    throw new Error(`Failed to load routes: ${res.status}`)
  }
  /** @type {Array} */
  const data = await res.json()
  // Normalize the shape to what UI expects
  return data.map((r) => ({
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

// --- OTP (驗證碼) APIs ---
export async function otpRequest({ account, purpose = 'login', channel }) {
  const res = await fetch(`${BASE}/auth/otp/request`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', accept: 'application/json' },
    body: JSON.stringify({ account, purpose, channel }),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error(data?.detail || `OTP request failed: ${res.status}`)
  }
  return data
}

export async function otpVerify({ account, code, purpose = 'login' }) {
  const res = await fetch(`${BASE}/auth/otp/verify`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', accept: 'application/json' },
    body: JSON.stringify({ account, code, purpose }),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok || !data?.ok) {
    throw new Error(data?.detail || `OTP verify failed: ${res.status}`)
  }
  return data // { ok, ticket, expires_in }
}

export async function otpConsume(ticket) {
  const res = await fetch(`${BASE}/auth/otp/consume?ticket=${encodeURIComponent(ticket)}`, {
    method: 'POST',
    headers: { accept: 'application/json' },
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok || !data?.ok) {
    throw new Error(data?.detail || `OTP consume failed: ${res.status}`)
  }
  return data // { ok, account, purpose }
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
