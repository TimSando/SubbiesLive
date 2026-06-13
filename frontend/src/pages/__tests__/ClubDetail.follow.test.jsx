import React from 'react'
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import ClubDetail from '../ClubDetail.jsx'

describe('ClubDetail Follow Integration', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  afterEach(() => {
    localStorage.clear()
  })

  it('follow button adds club to localStorage and dispatches event', async () => {
    const eventSpy = vi.fn()
    window.addEventListener('followingUpdated', eventSpy)

    render(
      <MemoryRouter initialEntries={['/clubs/1']}>
        <Routes>
          <Route path="/clubs/:id" element={<ClubDetail />} />
        </Routes>
      </MemoryRouter>
    )

    // Wait for the loading skeleton to disappear and the club title to render
    const title = await screen.findByText('Colleagues')
    expect(title).toBeInTheDocument()

    // The button title should be "Follow club" and show empty star '☆'
    const button = screen.getByTitle('Follow club')
    expect(button.textContent).toBe('☆')

    // Click to follow
    await userEvent.click(button)

    // Check localStorage has been updated
    const following = JSON.parse(localStorage.getItem('subbies_following_clubs') || '[]')
    expect(following).toHaveLength(1)
    expect(following[0]).toEqual({ id: 1, name: 'Colleagues', logo_url: null })

    // Button should now show filled star '⭐' and title "Unfollow club"
    expect(button.textContent).toBe('⭐')
    expect(screen.getByTitle('Unfollow club')).toBeInTheDocument()

    // Event should be dispatched
    expect(eventSpy).toHaveBeenCalledTimes(1)
    window.removeEventListener('followingUpdated', eventSpy)
  })

  it('unfollow button removes club from localStorage', async () => {
    // Pre-seed localStorage with the club
    localStorage.setItem(
      'subbies_following_clubs',
      JSON.stringify([{ id: 1, name: 'Colleagues', logo_url: null }])
    )

    render(
      <MemoryRouter initialEntries={['/clubs/1']}>
        <Routes>
          <Route path="/clubs/:id" element={<ClubDetail />} />
        </Routes>
      </MemoryRouter>
    )

    const title = await screen.findByText('Colleagues')
    expect(title).toBeInTheDocument()

    const button = await screen.findByTitle('Unfollow club')
    expect(button.textContent).toBe('⭐')

    // Click to unfollow
    await userEvent.click(button)

    // Check localStorage
    const following = JSON.parse(localStorage.getItem('subbies_following_clubs') || '[]')
    expect(following).toHaveLength(0)

    // Button reverts
    expect(button.textContent).toBe('☆')
    expect(screen.getByTitle('Follow club')).toBeInTheDocument()
  })

  it('follow state initialises correctly from localStorage', async () => {
    // Pre-seed
    localStorage.setItem(
      'subbies_following_clubs',
      JSON.stringify([{ id: 1, name: 'Colleagues', logo_url: null }])
    )

    render(
      <MemoryRouter initialEntries={['/clubs/1']}>
        <Routes>
          <Route path="/clubs/:id" element={<ClubDetail />} />
        </Routes>
      </MemoryRouter>
    )

    await screen.findByText('Colleagues')
    const button = await screen.findByTitle('Unfollow club')
    expect(button.textContent).toBe('⭐')
  })
})
