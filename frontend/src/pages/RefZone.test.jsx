import React from 'react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { http, HttpResponse } from 'msw'
import { server } from '../test/setup'
import RefZone, { RefZoneProvider } from './RefZone'
import userEvent from '@testing-library/user-event'

// Mock the crypto helper since JSDOM doesn't support WebCrypto Subtle imports out-of-the-box
vi.mock('../utils/rxCrypto', () => ({
  encryptForRX: vi.fn((val) => Promise.resolve(`encrypted-${val}`))
}))

function renderRefZone() {
  return render(
    <MemoryRouter>
      <RefZoneProvider>
        <RefZone />
      </RefZoneProvider>
    </MemoryRouter>
  )
}

// A simple utility to generate base64 JWT tokens with custom expiry times
function generateMockJwt(expSeconds) {
  const header = window.btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
  const payload = window.btoa(JSON.stringify({ exp: expSeconds, userId: 'user-123' }))
  return `${header}.${payload}.signature`
}

describe('RefZone page and auth integration', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('renders login page by default when no token in localStorage', () => {
    renderRefZone()
    expect(screen.getByRole('heading', { name: /RefZone/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/Email Address/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Password/i)).toBeInTheDocument()
  })

  it('displays error message on invalid credentials login attempt', async () => {
    renderRefZone()
    const emailInput = screen.getByLabelText(/Email Address/i)
    const passwordInput = screen.getByLabelText(/Password/i)
    const submitBtn = screen.getByRole('button', { name: /Sign In/i })

    await userEvent.type(emailInput, 'bad@test.com')
    await userEvent.type(passwordInput, 'wrongpass')
    await userEvent.click(submitBtn)

    await waitFor(() => {
      expect(screen.getByText(/Failed to login/i)).toBeInTheDocument()
    })
  })

  it('successful login transitions to Dashboard and displays appointments', async () => {
    const mockToken = generateMockJwt(Math.floor(Date.now() / 1000) + 3600)
    server.use(
      http.post('/api/refzone/login', () => HttpResponse.json({
        jwtTokens: { accessToken: mockToken },
        userId: 'user-123',
        profile: { firstname: 'Toby', lastname: 'Sanderson', headshot: null }
      }))
    )

    renderRefZone()
    const emailInput = screen.getByLabelText(/Email Address/i)
    const passwordInput = screen.getByLabelText(/Password/i)
    const submitBtn = screen.getByRole('button', { name: /Sign In/i })

    await userEvent.type(emailInput, 'toby@example.com')
    await userEvent.type(passwordInput, 'correctpass')
    await userEvent.click(submitBtn)

    // Verify it transitions to dashboard
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Toby Sanderson' })).toBeInTheDocument()
    })

    // It should render games in "This Weekend" tab by default
    expect(screen.getByText(/Games This Weekend/i)).toBeInTheDocument()
    expect(screen.getByText('Colleagues')).toBeInTheDocument()
    expect(screen.getByText('Mosman')).toBeInTheDocument()
    expect(screen.getByText(/Kentwell Cup/i)).toBeInTheDocument()

    // Test show officials in AppointmentCard (on weekend tab)
    const officialsTrigger = screen.getByRole('button', { name: /Match Officials/i })
    await userEvent.click(officialsTrigger)
    expect(screen.getByText('John Doe')).toBeInTheDocument()
    expect(screen.getByText('Assistant Referee 1')).toBeInTheDocument()

    // Test tab switching
    const comingUpTab = screen.getByRole('button', { name: /Coming Up/i })
    await userEvent.click(comingUpTab)
    expect(screen.getByText(/Upcoming Pending & Confirmed/i)).toBeInTheDocument()
    expect(screen.getByText('Sydney Uni')).toBeInTheDocument()
  })

  it('saves credentials in localStorage and performs auto-login on mount if Remember Me is checked', async () => {
    const mockToken = generateMockJwt(Math.floor(Date.now() / 1000) + 3600)
    server.use(
      http.post('/api/refzone/login', () => HttpResponse.json({
        jwtTokens: { accessToken: mockToken },
        userId: 'user-123',
        profile: { firstname: 'Toby', lastname: 'Sanderson' }
      }))
    )

    renderRefZone()
    const emailInput = screen.getByLabelText(/Email Address/i)
    const passwordInput = screen.getByLabelText(/Password/i)
    const rememberCheckbox = screen.getByLabelText(/Remember me/i)
    const submitBtn = screen.getByRole('button', { name: /Sign In/i })

    await userEvent.type(emailInput, 'remember@test.com')
    await userEvent.type(passwordInput, 'pass123')
    await userEvent.click(rememberCheckbox)
    await userEvent.click(submitBtn)

    // Wait to log in successfully
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Toby Sanderson' })).toBeInTheDocument()
    })

    // Check localStorage contains rx_auth_remember
    const stored = localStorage.getItem('rx_auth_remember')
    expect(stored).not.toBeNull()
    const parsed = JSON.parse(stored)
    expect(parsed.encryptedEmail).toBe('encrypted-remember@test.com')

    // Logout to reset state
    const logoutBtn = screen.getByRole('button', { name: /Logout/i })
    await userEvent.click(logoutBtn)
    expect(screen.getByRole('heading', { name: /RefZone/i })).toBeInTheDocument()
    expect(localStorage.getItem('rx_auth_remember')).toBeNull()
  })

  it('performs auto-login on startup if valid credentials exist in localStorage', async () => {
    const mockToken = generateMockJwt(Math.floor(Date.now() / 1000) + 3600)
    
    // Set localStorage auth data beforehand
    localStorage.setItem('rx_auth_remember', JSON.stringify({
      encryptedEmail: 'encrypted-auto@test.com',
      encryptedPassword: 'encrypted-pass',
      expiresAt: Date.now() + 3600000
    }))

    server.use(
      http.post('/api/refzone/login', () => HttpResponse.json({
        jwtTokens: { accessToken: mockToken },
        userId: 'user-123',
        profile: { firstname: 'Auto', lastname: 'LoggedIn' }
      }))
    )

    renderRefZone()

    // It should perform auto login and load dashboard directly
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Auto LoggedIn' })).toBeInTheDocument()
    })
  })
})
