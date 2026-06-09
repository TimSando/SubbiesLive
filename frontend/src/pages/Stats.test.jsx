import React from 'react'
import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { http, HttpResponse } from 'msw'
import { server } from '../test/setup'
import Stats from './Stats'
import userEvent from '@testing-library/user-event'

function renderWithRouter(ui) {
  return render(<MemoryRouter>{ui}</MemoryRouter>)
}

const mockPlayerStats = [
  {
    player_id: 101,
    player_name: 'Bernard Foley',
    club_name: 'Sydney Uni',
    games_played: 10,
    tries: 2,
    conversions: 15,
    penalties: 5,
    drop_goals: 1,
    total_points: 58,
    yellow_cards: 1,
    red_cards: 0
  },
  {
    player_id: 102,
    player_name: 'Christian Kagiasis',
    club_name: 'Colleagues',
    games_played: 8,
    tries: 5,
    conversions: 10,
    penalties: 2,
    drop_goals: 0,
    total_points: 51,
    yellow_cards: 0,
    red_cards: 0
  }
]

const mockClubStats = [
  {
    club_id: 1,
    club_name: 'Colleagues',
    logo_url: null,
    games_played: 15,
    tries: 45,
    conversions: 30,
    penalties: 12,
    drop_goals: 0,
    total_points: 321,
    yellow_cards: 4,
    red_cards: 1
  }
]

const mockClubDepthStats = [
  {
    club_id: 1,
    club_name: 'Colleagues',
    logo_url: null,
    total_players: 45,
    core_players: 30,
    dedicated_players: 25,
    swing_players: 10,
    avg_games: 6.2
  }
]

const mockOverview = {
  total_tries: 120,
  total_conversions: 85,
  total_penalties: 30,
  total_yellow_cards: 15,
  total_red_cards: 2,
  top_scorer_name: 'Bernard Foley',
  top_scorer_points: 58,
  top_try_scorer_name: 'Christian Kagiasis',
  top_try_scorer_tries: 5,
  games_played: 24
}

describe('Stats page', () => {
  beforeEach(() => {
    // Setup standard mock returns
    server.use(
      http.get('/api/stats/players', () => HttpResponse.json(mockPlayerStats)),
      http.get('/api/stats/clubs', () => HttpResponse.json(mockClubStats)),
      http.get('/api/stats/clubs/depth', () => HttpResponse.json(mockClubDepthStats)),
      http.get('/api/stats/overview', () => HttpResponse.json(mockOverview)),
      http.get('/api/games/live', () => HttpResponse.json([]))
    )
    sessionStorage.clear()
  })

  it('shows skeleton loading state initially', () => {
    renderWithRouter(<Stats />)
    const skeletons = document.querySelectorAll('.skeleton')
    expect(skeletons.length).toBeGreaterThan(0)
  })

  it('renders players stats by default', async () => {
    renderWithRouter(<Stats />)
    await waitFor(() => expect(screen.getByText('Bernard Foley')).toBeInTheDocument())
    expect(screen.getByText('Christian Kagiasis')).toBeInTheDocument()
    expect(screen.getByText('Colleagues')).toBeInTheDocument()
    expect(screen.getByText('58')).toBeInTheDocument() // Bernard Foley total points
  })

  it('allows switching tabs to Clubs and displays club stats', async () => {
    renderWithRouter(<Stats />)
    await waitFor(() => expect(screen.getByText('Bernard Foley')).toBeInTheDocument())

    const clubsTab = screen.getByRole('button', { name: /^clubs$/i })
    await userEvent.click(clubsTab)

    // Verify Club stats table header or content
    await waitFor(() => expect(screen.getByText('Club Scoring & Discipline')).toBeInTheDocument())
    expect(screen.getByText('Squad Depth & Participation')).toBeInTheDocument()
    expect(screen.getAllByText('Colleagues')).toHaveLength(2) // 1 in each table
    expect(screen.getByText('321')).toBeInTheDocument() // Club points
    expect(screen.getByText('6.20')).toBeInTheDocument() // Avg Games/Player
  })

  it('allows switching tabs to Season and displays overview', async () => {
    renderWithRouter(<Stats />)
    await waitFor(() => expect(screen.getByText('Bernard Foley')).toBeInTheDocument())

    const seasonTab = screen.getByRole('button', { name: /^season$/i })
    await userEvent.click(seasonTab)

    await waitFor(() => expect(screen.getByText('Total Tries')).toBeInTheDocument())
    expect(screen.getByText('120')).toBeInTheDocument() // total tries
    expect(screen.getByText('85')).toBeInTheDocument() // conversions
    expect(screen.getByText('30')).toBeInTheDocument() // penalties
    expect(screen.getByText('Bernard Foley')).toBeInTheDocument() // Top Scorer subtext
  })

  it('searches for a player in autocomplete input', async () => {
    // Override /api/players endpoint for search
    server.use(
      http.get('/api/players', ({ request }) => {
        const url = new URL(request.url)
        const search = url.searchParams.get('search')
        if (search === 'Christian') {
          return HttpResponse.json([
            { id: 102, name: 'Christian Kagiasis', current_team: 'Colleagues' }
          ])
        }
        return HttpResponse.json([])
      })
    )

    renderWithRouter(<Stats />)
    await waitFor(() => expect(screen.getByText('Bernard Foley')).toBeInTheDocument())

    const searchInput = screen.getByPlaceholderText(/search for any player/i)
    await userEvent.type(searchInput, 'Christian')

    // Wait for the debounce search (300ms)
    await waitFor(() => expect(screen.getByText('Colleagues')).toBeInTheDocument(), { timeout: 1000 })
    // The player's name in autocomplete result dropdown
    const autocompleteResults = screen.getAllByText('Christian Kagiasis')
    expect(autocompleteResults.length).toBeGreaterThan(0)
  })

  it('changes view mode between total and average and recalculates stats', async () => {
    renderWithRouter(<Stats />)
    await waitFor(() => expect(screen.getByText('Bernard Foley')).toBeInTheDocument())

    // Initial total points
    expect(screen.getByText('58')).toBeInTheDocument()

    // Find view mode toggle (ToggleSwitch)
    // The ToggleSwitch component has buttons for Total and Avg
    const avgButton = screen.getByRole('button', { name: /average/i })
    await userEvent.click(avgButton)

    // Average points should show: 58 / 10 = 5.80
    await waitFor(() => expect(screen.getByText('5.80')).toBeInTheDocument())
  })

  it('applies filters and fetches updated stats', async () => {
    let capturedParams = null
    server.use(
      http.get('/api/stats/players', ({ request }) => {
        const url = new URL(request.url)
        capturedParams = {
          competition_id: url.searchParams.get('competition_id'),
          parent_competition: url.searchParams.get('parent_competition'),
          division: url.searchParams.get('division')
        }
        return HttpResponse.json(mockPlayerStats)
      })
    )

    renderWithRouter(<Stats />)
    await waitFor(() => expect(screen.getByText('Bernard Foley')).toBeInTheDocument())

    const selectEl = screen.getByLabelText(/filter by/i)
    // Select a competition e.g. "comp:1"
    await userEvent.selectOptions(selectEl, 'comp:1')

    await waitFor(() => {
      expect(capturedParams).toEqual({
        competition_id: '1',
        parent_competition: null,
        division: null
      })
    })
  })

  it('shows error message if API fails', async () => {
    server.use(
      http.get('/api/stats/players', () => new HttpResponse(null, { status: 500 }))
    )
    renderWithRouter(<Stats />)
    await waitFor(() => expect(screen.getByText(/Failed to load/i)).toBeInTheDocument())
  })
})
