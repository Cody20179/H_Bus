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
