/**
 * API client for communicating with the FastAPI backend.
 * All requests go through /api/ which Nginx proxies to the backend.
 */

const API_BASE = '/api'

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`

  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  })

  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`)
  }

  return response.json()
}

function buildQuery(params = {}) {
  const clean = Object.fromEntries(
    Object.entries(params).filter(([_, v]) => v != null && v !== '')
  )
  const query = new URLSearchParams(clean).toString()
  return query ? '?' + query : ''
}

export const api = {
  // Health
  health: () => request('/health'),

  // Competitions
  getCompetitions: (params = {}) => request(`/competitions${buildQuery(params)}`),
  getCompetition: (id) => request(`/competitions/${id}`),

  // Clubs
  getClubs: (params = {}) => request(`/clubs${buildQuery(params)}`),
  getClub: (id, params = {}) => request(`/clubs/${id}${buildQuery(params)}`),

  // Games
  getGames: (params = {}) => {
    return request(`/games${buildQuery(params)}`)
  },
  getLiveGames: () => request('/games/live'),
  getGame: (id) => request(`/games/${id}`),

  // Players
  getPlayers: (params = {}) => {
    return request(`/players${buildQuery(params)}`)
  },
  getPlayer: (id, params = {}) => request(`/players/${id}${buildQuery(params)}`),

  // Teams
  getTeam: (id, params = {}) => request(`/teams/${id}${buildQuery(params)}`),


  // Standings
  getStandings: (competitionId) => request(`/standings/${competitionId}`),

  // Stats
  getPlayerStats: (params = {}) => {
    return request(`/stats/players${buildQuery(params)}`)
  },
  getClubStats: (params = {}) => {
    return request(`/stats/clubs${buildQuery(params)}`)
  },
  getClubDepthStats: (params = {}) => {
    return request(`/stats/clubs/depth${buildQuery(params)}`)
  },
  getSeasonOverview: (params = {}) => {
    return request(`/stats/overview${buildQuery(params)}`)
  },
  getTeamFormStats: (teamId) => request(`/stats/team/${teamId}/form`),




  // Notifications
  getVapidPublicKey: () => request('/notifications/vapid-public-key'),
  subscribeNotifications: (subscription) => request('/notifications/subscribe', {
    method: 'POST',
    body: JSON.stringify(subscription)
  }),
  getMySubscriptions: (endpoint) => request('/notifications/my-subscriptions', {
    method: 'POST',
    body: JSON.stringify({ endpoint })
  }),
  toggleSubscriptionTopic: (payload) => request('/notifications/toggle-topic', {
    method: 'POST',
    body: JSON.stringify(payload)
  }),

  // Weather/Venue
  getVenueWeather: (venueName, moment, dbGameId) => {
    let query = `?venue_name=${encodeURIComponent(venueName)}&moment=${encodeURIComponent(moment)}`
    if (dbGameId) {
      query += `&db_game_id=${dbGameId}`
    }
    return request(`/refzone/venue-weather${query}`)
  },
}
