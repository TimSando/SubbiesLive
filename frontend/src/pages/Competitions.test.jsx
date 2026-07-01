import React from 'react'
import { describe, it, expect } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { http, HttpResponse } from 'msw'
import { server } from '../test/setup'
import Competitions from './Competitions'
import userEvent from '@testing-library/user-event'

function renderWithRouter(ui) {
  return render(<MemoryRouter>{ui}</MemoryRouter>)
}

describe('Competitions page', () => {
  it('shows skeleton loading state initially', () => {
    renderWithRouter(<Competitions />)
    const skeletons = document.querySelectorAll('.skeleton')
    expect(skeletons.length).toBeGreaterThan(0)
  })

  it('renders a list of competitions from MSW handlers', async () => {
    renderWithRouter(<Competitions />)
    await waitFor(() => expect(screen.getByText('Kentwell Cup')).toBeInTheDocument())
    expect(screen.getByText('Shute Shield', { selector: '.comp-row__name' })).toBeInTheDocument()
  })

  it('filters competitions when typing in search query input', async () => {
    renderWithRouter(<Competitions />)
    await waitFor(() => expect(screen.getByText('Kentwell Cup')).toBeInTheDocument())

    const searchInput = screen.getByPlaceholderText(/search by club name/i)
    await userEvent.type(searchInput, 'Shute')

    expect(screen.getByText('Shute Shield', { selector: '.comp-row__name' })).toBeInTheDocument()
    expect(screen.queryByText('Kentwell Cup')).not.toBeInTheDocument()
  })

  it('shows error state on API failure', async () => {
    server.use(
      http.get('/api/competitions', () => new HttpResponse(null, { status: 500 }))
    )
    renderWithRouter(<Competitions />)
    await waitFor(() => expect(screen.getByText(/Failed to load competitions/i)).toBeInTheDocument())
  })
})
