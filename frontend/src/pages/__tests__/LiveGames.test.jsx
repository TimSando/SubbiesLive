import React from 'react'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { http, HttpResponse } from 'msw'
import { server } from '../../test/setup'
import LiveGames from '../LiveGames.jsx'

describe('LiveGames Page', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders live games grid', async () => {
    const mockLiveGames = [
      {
        id: 101,
        competition_name: 'Kentwell Cup',
        round_name: 'Round 1',
        status: 'in_progress',
        game_date: '2026-06-06T15:00:00',
        home_team: { name: 'Colleagues 1st' },
        away_team: { name: 'Mosman 1st' },
        home_score: 12,
        away_score: 12,
      },
      {
        id: 102,
        competition_name: 'Kentwell Cup',
        round_name: 'Round 1',
        status: 'in_progress',
        game_date: '2026-06-06T15:00:00',
        home_team: { name: 'Waverley 1st' },
        away_team: { name: 'Mosman 1st' },
        home_score: 20,
        away_score: 5,
      },
    ]

    server.use(
      http.get('/api/games/live', () => HttpResponse.json(mockLiveGames))
    )

    render(
      <MemoryRouter>
        <LiveGames />
      </MemoryRouter>
    )

    // Wait for mock games to be fetched and displayed
    expect(await screen.findByText('Colleagues 1st')).toBeInTheDocument()
    expect(screen.getByText('Waverley 1st')).toBeInTheDocument()
    expect(screen.getAllByText('Live')).toHaveLength(2)
  })

  it('shows empty message when no live games', async () => {
    server.use(
      http.get('/api/games/live', () => HttpResponse.json([]))
    )

    render(
      <MemoryRouter>
        <LiveGames />
      </MemoryRouter>
    )

    expect(await screen.findByText('There are no live matches right now.')).toBeInTheDocument()
  })

  it('shows skeleton while loading', () => {
    // Mock API to hang
    server.use(
      http.get('/api/games/live', () => new Promise(() => {}))
    )

    const { container } = render(
      <MemoryRouter>
        <LiveGames />
      </MemoryRouter>
    )

    expect(container.querySelector('.skeleton')).toBeInTheDocument()
  })
})
