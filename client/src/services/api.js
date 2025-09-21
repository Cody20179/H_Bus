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

export async function cancelReservation(reservationId, cancelReason) {
  const res = await fetch(`${BASE}/reservations/Canceled`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', accept: 'application/json' },
    body: JSON.stringify({
      reservation_id: reservationId,
      cancel_reason: cancelReason,
    }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.detail || `Cancel failed: ${res.status}`);
  return data;
}

export async function getTomorrowReservations(userId) {
  console.log("[API] getTomorrowReservations called with", userId)
  const res = await fetch(`${BASE}/reservations/tomorrow?user_id=${encodeURIComponent(userId)}`, {
    headers: { accept: 'application/json' },
  })
  console.log("[API] fetch done, status=", res.status)
  const data = await res.json().catch(() => ({}))
  console.log("[API] response json:", data)
  if (!res.ok) throw new Error(`Failed to load tomorrow reservations: ${res.status}`)

  if (Array.isArray(data?.sql)) return data.sql
  if (Array.isArray(data?.reservations)) return data.reservations
  return []
}

