import React from 'react'
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { http, HttpResponse } from 'msw'
import { server } from '../../test/setup'
import Home from '../Home.jsx'

// Mock useRefZone
const mockUseRefZone = vi.fn()
vi.mock('../RefZone.jsx', () => ({
  useRefZone: () => mockUseRefZone(),
}))

describe('Home Page Redesign', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
    // Default mock implementation
    mockUseRefZone.mockReturnValue({ userId: null })
  })

  afterEach(() => {
    localStorage.clear()
  })

  it('shows empty state when no clubs followed', async () => {
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    )

    expect(await screen.findByText('Personalize Your Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Follow your favourite clubs to get quick access to their live games, recent results, and upcoming fixtures right here.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Browse Clubs' })).toBeInTheDocument()
  })

  it('shows tab bar and tab content when clubs are followed', async () => {
    localStorage.setItem(
      'subbies_following_clubs',
      JSON.stringify([
        { id: 1, name: 'Colleagues', logo_url: null },
        { id: 2, name: 'Mosman', logo_url: null },
      ])
    )

    // Setup MSW to return mock games for club 1
    server.use(
      http.get('/api/games', ({ request }) => {
        const url = new URL(request.url)
        const clubId = url.searchParams.get('club_id')
        const status = url.searchParams.get('status')
        if (clubId === '1' && status === 'completed') {
          return HttpResponse.json([
            {
              id: 101,
              competition_name: 'Kentwell Cup',
              round_name: 'Round 1',
              status: 'completed',
              game_date: '2026-06-06T15:00:00',
              home_team: { name: 'Colleagues 1st' },
              away_team: { name: 'Mosman 1st' },
              home_score: 25,
              away_score: 10,
            }
          ])
        }
        return HttpResponse.json([])
      })
    )

    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    )

    // Verify tabs
    expect(await screen.findByText('Colleagues')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Mosman' })).toBeInTheDocument()

    // Verify games for active tab (Colleagues by default)
    expect(await screen.findByText('Colleagues 1st')).toBeInTheDocument()
  })

  it('switches tab content on click', async () => {
    localStorage.setItem(
      'subbies_following_clubs',
      JSON.stringify([
        { id: 1, name: 'Colleagues', logo_url: null },
        { id: 2, name: 'Mosman', logo_url: null },
      ])
    )

    let requestedClubId = null

    server.use(
      http.get('/api/games', ({ request }) => {
        const url = new URL(request.url)
        requestedClubId = url.searchParams.get('club_id')
        const status = url.searchParams.get('status')
        if (requestedClubId === '2' && status === 'completed') {
          return HttpResponse.json([
            {
              id: 102,
              competition_name: 'Kentwell Cup',
              round_name: 'Round 1',
              status: 'completed',
              game_date: '2026-06-06T15:00:00',
              home_team: { name: 'Mosman 1st' },
              away_team: { name: 'Waverley 1st' },
              home_score: 15,
              away_score: 5,
            }
          ])
        }
        return HttpResponse.json([])
      })
    )

    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    )

    const mosmanTab = await screen.findByRole('button', { name: 'Mosman' })
    await userEvent.click(mosmanTab)

    await waitFor(() => {
      expect(requestedClubId).toBe('2')
    })
    expect(await screen.findByText('Waverley 1st')).toBeInTheDocument()
  })

  it('migrates legacy subbies_fav_club_id', async () => {
    localStorage.setItem('subbies_fav_club_id', '1')

    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    )

    // Wait for the backfill mock call to complete and update state
    await screen.findByText('Colleagues')

    const following = JSON.parse(localStorage.getItem('subbies_following_clubs') || '[]')
    expect(following).toHaveLength(1)
    expect(following[0].id).toBe(1)
    expect(following[0].name).toBe('Colleagues')
    expect(localStorage.getItem('subbies_fav_club_id')).toBeNull()
  })

  it('RefZone section shows login prompt for unauthenticated users', async () => {
    mockUseRefZone.mockReturnValue({ userId: null })

    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    )

    expect(await screen.findByText('Referee Hub')).toBeInTheDocument()
    expect(screen.getByText('Sign in to RugbyXplorer to see your upcoming referee appointments and manage match preparation.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Sign in to RefZone' })).toBeInTheDocument()
  })

  it('RefZone dismiss persists to localStorage', async () => {
    mockUseRefZone.mockReturnValue({ userId: null })

    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    )

    const dismissButton = await screen.findByTitle('Dismiss prompt')
    await userEvent.click(dismissButton)

    expect(localStorage.getItem('refzone_prompt_dismissed')).toBe('true')
    expect(screen.queryByText('Referee Hub')).not.toBeInTheDocument()
  })
})
