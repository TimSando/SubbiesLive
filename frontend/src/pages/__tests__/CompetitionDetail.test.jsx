import React from 'react'
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { http, HttpResponse } from 'msw'
import { server } from '../../test/setup'
import CompetitionDetail from '../CompetitionDetail.jsx'

describe('CompetitionDetail Page', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    vi.restoreAllMocks()
  })

  afterEach(() => {
    localStorage.clear()
    sessionStorage.clear()
  })

  const mockCompetition = {
    id: 1,
    name: 'Kentwell Cup',
    team_count: 8,
    rounds: [
      {
        id: 101,
        name: 'Round 1',
        game_count: 4,
        completed_game_count: 4,
        latest_game_date: '2026-05-01T15:00:00'
      },
      {
        id: 102,
        name: 'Round 2',
        game_count: 4,
        completed_game_count: 0,
        latest_game_date: '2026-07-01T15:00:00' // Future
      }
    ]
  }

  const mockStandings = {
    standings: [
      {
        team_id: 1,
        team_name: 'Colleagues 1st',
        club_id: 10,
        club_name: 'Colleagues',
        position: 1,
        played: 1,
        won: 1,
        drawn: 0,
        lost: 0,
        points_for: 30,
        points_against: 10,
        points_diff: 20,
        bonus_points: 1,
        competition_points: 5
      }
    ]
  }

  it('renders competition info, tab switches, and live games section', async () => {
    // Mock API responses
    server.use(
      http.get('/api/competitions/1', () => HttpResponse.json(mockCompetition)),
      http.get('/api/competitions/1/standings', () => HttpResponse.json(mockStandings)),
      http.get('/api/games', ({ request }) => {
        const url = new URL(request.url)
        const status = url.searchParams.get('status')
        const compId = url.searchParams.get('competition_id')
        
        if (compId === '1' && status === 'in_progress') {
          return HttpResponse.json([
            {
              id: 201,
              competition_name: 'Kentwell Cup',
              round_name: 'Round 2',
              status: 'in_progress',
              game_date: '2026-06-13T15:00:00',
              home_team: { name: 'Colleagues 1st' },
              away_team: { name: 'Mosman 1st' },
              home_score: 12,
              away_score: 7
            }
          ])
        }
        return HttpResponse.json([])
      })
    )

    render(
      <MemoryRouter initialEntries={['/competitions/1']}>
        <Routes>
          <Route path="/competitions/:id" element={<CompetitionDetail />} />
        </Routes>
      </MemoryRouter>
    )

    // Verify loading detail info
    expect(await screen.findByRole('heading', { name: 'Kentwell Cup', level: 1 })).toBeInTheDocument()
    expect(screen.getByText('8 teams · 2 rounds')).toBeInTheDocument()

    // Verify live games section is rendered
    expect(screen.getByText('Live Matches')).toBeInTheDocument()
    expect(screen.getByText('Colleagues 1st')).toBeInTheDocument()

    // Switch to Fixtures & Results tab
    const fixturesTab = screen.getByRole('button', { name: 'Fixtures & Results' })
    await userEvent.click(fixturesTab)

    // Verify round buttons and styling
    const round1Btn = await screen.findByRole('button', { name: 'Round 1' })
    const round2Btn = screen.getByRole('button', { name: 'Round 2' })

    // By default, Round 1 is active, so it should have active class and not completed class
    expect(round1Btn).toHaveClass('round-selector__btn--active')
    expect(round1Btn).not.toHaveClass('round-selector__btn--completed')

    // Click Round 2 to switch active round
    await userEvent.click(round2Btn)
    expect(round2Btn).toHaveClass('round-selector__btn--active')

    // Now Round 1 is inactive, it should show completed class because it is in the past & completed
    expect(round1Btn).toHaveClass('round-selector__btn--completed')
    expect(round2Btn).not.toHaveClass('round-selector__btn--completed')
  })
})
