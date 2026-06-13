import React from 'react'
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import GamePill from '../GamePill.jsx'

const completedGame = {
  id: 101,
  competition_name: 'Kentwell Cup',
  round_name: 'Round 1',
  status: 'completed',
  game_date: '2026-06-06T15:00:00',
  home_team: { name: 'Colleagues 1st', club_name: 'Colleagues' },
  away_team: { name: 'Mosman 1st', club_name: 'Mosman' },
  home_score: 25,
  away_score: 10,
}

const liveGame = {
  id: 102,
  competition_name: 'Kentwell Cup',
  round_name: 'Round 1',
  status: 'in_progress',
  game_date: '2026-06-06T15:00:00',
  home_team: { name: 'Colleagues 1st', club_name: 'Colleagues' },
  away_team: { name: 'Mosman 1st', club_name: 'Mosman' },
  home_score: 12,
  away_score: 12,
}

const scheduledGame = {
  id: 103,
  competition_name: 'Kentwell Cup',
  round_name: 'Round 1',
  status: 'scheduled',
  game_date: '2026-06-06T15:00:00',
  home_team: { name: 'Colleagues 1st', club_name: 'Colleagues' },
  away_team: { name: 'Mosman 1st', club_name: 'Mosman' },
  home_score: null,
  away_score: null,
}

describe('GamePill Component', () => {
  it('renders completed game with scores', () => {
    render(
      <MemoryRouter>
        <GamePill game={completedGame} />
      </MemoryRouter>
    )

    expect(screen.getByText('Colleagues')).toBeInTheDocument()
    expect(screen.getByText('Mosman')).toBeInTheDocument()
    expect(screen.getByText('25')).toBeInTheDocument()
    expect(screen.getByText('10')).toBeInTheDocument()
    expect(screen.getByText('completed')).toBeInTheDocument()
  })

  it('renders live game with live badge', () => {
    const { container } = render(
      <MemoryRouter>
        <GamePill game={liveGame} />
      </MemoryRouter>
    )

    expect(screen.getByText('Live')).toBeInTheDocument()
    expect(container.querySelector('.game-pill--live')).toBeInTheDocument()
    expect(screen.getAllByText('12')).toHaveLength(2)
  })

  it('renders scheduled game without scores', () => {
    render(
      <MemoryRouter>
        <GamePill game={scheduledGame} />
      </MemoryRouter>
    )

    expect(screen.queryByText('25')).not.toBeInTheDocument()
    expect(screen.getByText('scheduled')).toBeInTheDocument()
  })

  it('links to game detail page', () => {
    render(
      <MemoryRouter>
        <GamePill game={completedGame} />
      </MemoryRouter>
    )

    const link = screen.getByRole('link')
    expect(link.getAttribute('href')).toBe('/games/101')
  })
})
