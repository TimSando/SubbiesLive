import React from 'react'
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { http, HttpResponse } from 'msw'
import { server } from '../../test/setup'
import TeamDetail from '../TeamDetail.jsx'

describe('TeamDetail Page', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    vi.restoreAllMocks()
  })

  afterEach(() => {
    localStorage.clear()
    sessionStorage.clear()
  })

  const mockTeam = {
    id: 1,
    name: 'Colleagues 1st Grade',
    external_id: 2001,
    club_id: 10,
    club_name: 'Colleagues',
    club_logo_url: 'http://example.com/logo.png',
    competition_id: 5,
    competition_name: 'Kentwell Cup',
    year: 2026,
    stats: {
      games_played: 14,
      wins: 10,
      losses: 3,
      draws: 1,
      points_for: 350,
      points_against: 180,
      total_tries: 45,
      total_conversions: 35,
      total_penalty_goals: 12,
      total_drop_goals: 0,
      total_yellow_cards: 4,
      total_red_cards: 0
    }
  }

  const mockGames = [
    {
      id: 301,
      competition_name: 'Kentwell Cup',
      round_name: 'Round 1',
      status: 'completed',
      game_date: '2026-05-02T15:00:00',
      home_team: { id: 1, name: 'Colleagues 1st Grade', club_name: 'Colleagues' },
      away_team: { id: 2, name: 'Mosman 1st Grade', club_name: 'Mosman' },
      home_score: 24,
      away_score: 15,
      location: 'Woollahra Oval'
    }
  ]

  it('renders team info, stats, and matches list', async () => {
    server.use(
      http.get('/api/teams/1', () => HttpResponse.json(mockTeam)),
      http.get('/api/games', () => HttpResponse.json(mockGames))
    )

    render(
      <MemoryRouter initialEntries={['/teams/1']}>
        <Routes>
          <Route path="/teams/:id" element={<TeamDetail />} />
        </Routes>
      </MemoryRouter>
    )

    // Verify header info
    expect(await screen.findByRole('heading', { name: 'Colleagues 1st Grade', level: 1 })).toBeInTheDocument()
    expect(screen.getAllByText('Colleagues').length).toBeGreaterThan(0)
    expect(screen.getByText('Kentwell Cup')).toBeInTheDocument()


    // Verify stats overview
    expect(screen.getByText('Games Played')).toBeInTheDocument()
    expect(screen.getByText('14')).toBeInTheDocument()
    expect(screen.getByText('Wins')).toBeInTheDocument()
    expect(screen.getByText('10')).toBeInTheDocument()
    expect(screen.getByText('Losses')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText('Points For')).toBeInTheDocument()
    expect(screen.getByText('350')).toBeInTheDocument()

    // Verify matches list
    expect(await screen.findByText(/Woollahra Oval/)).toBeInTheDocument()
    expect(screen.getAllByText('Colleagues').length).toBeGreaterThan(0)
    expect(screen.getByText('Mosman')).toBeInTheDocument()
    expect(screen.getByText('24')).toBeInTheDocument()
    expect(screen.getByText('15')).toBeInTheDocument()



  })

  it('fetches games using the team competition year', async () => {
    let requestedYear = null

    server.use(
      http.get('/api/teams/1', () => HttpResponse.json({ ...mockTeam, year: 2025 })),
      http.get('/api/games', ({ request }) => {
        const url = new URL(request.url)
        requestedYear = url.searchParams.get('year')
        return HttpResponse.json([])
      })
    )

    render(
      <MemoryRouter initialEntries={['/teams/1']}>
        <Routes>
          <Route path="/teams/:id" element={<TeamDetail />} />
        </Routes>
      </MemoryRouter>
    )

    await screen.findByRole('heading', { name: 'Colleagues 1st Grade', level: 1 })
    
    await waitFor(() => {
      expect(requestedYear).toBe('2025')
    })
  })
})
