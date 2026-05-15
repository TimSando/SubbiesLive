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

export const api = {
  // Health
  health: () => request('/health'),

  // Competitions
  getCompetitions: () => request('/competitions'),
  getCompetition: (id) => request(`/competitions/${id}`),

  // Clubs
  getClubs: () => request('/clubs'),
  getClub: (id) => request(`/clubs/${id}`),

  // Games
  getGames: (params = {}) => {
    const query = new URLSearchParams(params).toString()
    return request(`/games${query ? '?' + query : ''}`)
  },
  getGame: (id) => request(`/games/${id}`),

  // Players
  getPlayers: (params = {}) => {
    const query = new URLSearchParams(params).toString()
    return request(`/players${query ? '?' + query : ''}`)
  },
  getPlayer: (id) => request(`/players/${id}`),

  // Standings
  getStandings: (competitionId) => request(`/standings/${competitionId}`),
}
