import React from 'react'
import { describe, it, expect } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { http, HttpResponse } from 'msw'
import { server } from '../test/setup'
import Clubs from './Clubs'
import userEvent from '@testing-library/user-event'

function renderWithRouter(ui) {
  return render(<MemoryRouter>{ui}</MemoryRouter>)
}

describe('Clubs page', () => {
  beforeEach(() => {
    sessionStorage.clear()
    localStorage.clear()
  })

  it('shows skeleton loading state initially', () => {
    renderWithRouter(<Clubs />)
    const skeletons = document.querySelectorAll('.skeleton')
    expect(skeletons.length).toBeGreaterThan(0)
  })

  it('renders a list of clubs from MSW handlers', async () => {
    renderWithRouter(<Clubs />)
    await waitFor(() => expect(screen.getByText('Colleagues')).toBeInTheDocument())
  })

  it('filters clubs when typing in search input', async () => {
    // Add an extra mock handler specifically for this test to show filtering
    server.use(
      http.get('/api/clubs', () => HttpResponse.json([
        { id: 1, name: 'Colleagues', short_name: 'Colleagues', logo_url: null, has_womens_team: false },
        { id: 2, name: 'Mosman Whales', short_name: 'Mosman', logo_url: null, has_womens_team: false }
      ]))
    )

    renderWithRouter(<Clubs />)
    await waitFor(() => expect(screen.getByText('Colleagues')).toBeInTheDocument())
    expect(screen.getByText('Mosman Whales')).toBeInTheDocument()

    const searchInput = screen.getByPlaceholderText(/search clubs by name/i)
    await userEvent.type(searchInput, 'Mosman')

    expect(screen.getByText('Mosman Whales')).toBeInTheDocument()
    expect(screen.queryByText('Colleagues')).not.toBeInTheDocument()
  })

  it('shows error state on API failure', async () => {
    server.use(
      http.get('/api/clubs', () => new HttpResponse(null, { status: 500 }))
    )
    renderWithRouter(<Clubs />)
    await waitFor(() => expect(screen.getByText(/Failed to load clubs/i)).toBeInTheDocument())
  })

  it('allows following and unfollowing a club directly from the list', async () => {
    server.use(
      http.get('/api/clubs', () => HttpResponse.json([
        { id: 1, name: 'Colleagues', short_name: 'Colleagues', logo_url: null, has_womens_team: false }
      ]))
    )

    renderWithRouter(<Clubs />)
    await waitFor(() => expect(screen.getByText('Colleagues')).toBeInTheDocument())

    const followButton = screen.getByTitle('Follow club')
    expect(followButton).not.toHaveClass('page-subscribe-btn--active')

    await userEvent.click(followButton)

    // Verify it updates class and localstorage
    expect(followButton).toHaveClass('page-subscribe-btn--active')
    const following = JSON.parse(localStorage.getItem('subbies_following_clubs') || '[]')
    expect(following).toHaveLength(1)
    expect(following[0].id).toBe(1)

    // Click again to unfollow
    await userEvent.click(followButton)
    expect(followButton).not.toHaveClass('page-subscribe-btn--active')
    const followingEmpty = JSON.parse(localStorage.getItem('subbies_following_clubs') || '[]')
    expect(followingEmpty).toHaveLength(0)
  })
})
