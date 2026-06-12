import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { http, HttpResponse } from 'msw'
import { server } from '../test/setup'
import RefZone, { RefZoneProvider } from './RefZone'
import userEvent from '@testing-library/user-event'

function renderRefZone() {
  return render(
    <MemoryRouter>
      <RefZoneProvider>
        <RefZone />
      </RefZoneProvider>
    </MemoryRouter>
  )
}

describe('RefZone page and auth integration', () => {
  beforeEach(() => {
    // Reset any runtime request handlers added in tests
    server.resetHandlers()
  })

  it('renders login page by default when status endpoint returns unauthenticated', async () => {
    server.use(
      http.get('/api/refzone/status', () => {
        return HttpResponse.json({ authenticated: false, userId: null })
      })
    )

    renderRefZone()

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /RefZone/i })).toBeInTheDocument()
      expect(screen.getByLabelText(/Email Address/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/Password/i)).toBeInTheDocument()
    })
  })

  it('displays error message on invalid credentials login attempt', async () => {
    server.use(
      http.get('/api/refzone/status', () => {
        return HttpResponse.json({ authenticated: false, userId: null })
      }),
      http.post('/api/refzone/login', () => {
        return new HttpResponse(null, { status: 401 })
      })
    )

    renderRefZone()
    
    const emailInput = await screen.findByLabelText(/Email Address/i)
    const passwordInput = screen.getByLabelText(/Password/i)
    const submitBtn = screen.getByRole('button', { name: /Sign In/i })

    await userEvent.type(emailInput, 'bad@test.com')
    await userEvent.type(passwordInput, 'wrongpass')
    await userEvent.click(submitBtn)

    await waitFor(() => {
      expect(screen.getByText(/Failed to login/i)).toBeInTheDocument()
    })
  })

  it('successful login without MFA transitions to Dashboard and displays appointments', async () => {
    server.use(
      http.get('/api/refzone/status', () => {
        return HttpResponse.json({ authenticated: false, userId: null })
      }),
      http.post('/api/refzone/login', () => {
        return HttpResponse.json({
          status: 'ok',
          userId: 'user-123'
        })
      }),
      http.get('/api/refzone/profile', () => {
        return HttpResponse.json({
          firstname: 'Toby',
          lastname: 'Sanderson',
          headshot: null
        })
      }),
      http.get('/api/refzone/appointments', () => {
        return HttpResponse.json([
          {
            _id: 'app-1',
            status: 'confirmed',
            isActive: true,
            match: {
              moment: Date.now() + 86400000, // tomorrow
              homeTeam: { name: 'Colleagues' },
              awayTeam: { name: 'Mosman' },
              competition: { name: 'Kentwell Cup' },
              officials: [
                {
                  official: { firstname: 'John', lastname: 'Doe' },
                  role: 'Assistant Referee 1'
                }
              ]
            }
          }
        ])
      })
    )

    renderRefZone()
    
    const emailInput = await screen.findByLabelText(/Email Address/i)
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
    await waitFor(() => {
      expect(screen.getByText(/Games This Weekend/i)).toBeInTheDocument()
      expect(screen.getByText('Colleagues')).toBeInTheDocument()
      expect(screen.getByText('Mosman')).toBeInTheDocument()
      expect(screen.getByText(/Kentwell Cup/i)).toBeInTheDocument()
    })
  })

  it('login requiring MFA shows verification code form and transitions to dashboard after successful 2FA code submission', async () => {
    server.use(
      http.get('/api/refzone/status', () => {
        return HttpResponse.json({ authenticated: false, userId: null })
      }),
      http.post('/api/refzone/login', () => {
        return HttpResponse.json({
          status: 'mfa_required',
          mfa_token: 'mfa-challenge-token'
        })
      }),
      http.post('/api/refzone/verify-2fa', () => {
        return HttpResponse.json({
          userId: 'user-123'
        })
      }),
      http.get('/api/refzone/profile', () => {
        return HttpResponse.json({
          firstname: 'Toby',
          lastname: 'Sanderson',
          headshot: null
        })
      }),
      http.get('/api/refzone/appointments', () => {
        return HttpResponse.json([])
      })
    )

    renderRefZone()

    const emailInput = await screen.findByLabelText(/Email Address/i)
    const passwordInput = screen.getByLabelText(/Password/i)
    const submitBtn = screen.getByRole('button', { name: /Sign In/i })

    await userEvent.type(emailInput, 'toby@example.com')
    await userEvent.type(passwordInput, 'correctpass')
    await userEvent.click(submitBtn)

    // Verify 2FA form is shown
    const mfaInput = await screen.findByLabelText(/Verification Code/i)
    expect(mfaInput).toBeInTheDocument()
    expect(screen.queryByLabelText(/Email Address/i)).not.toBeInTheDocument()

    // Submit invalid 2FA code
    server.use(
      http.post('/api/refzone/verify-2fa', () => {
        return new HttpResponse(null, { status: 401 })
      })
    )

    const verifyBtn = screen.getByRole('button', { name: /Verify Code/i })
    await userEvent.type(mfaInput, '000000')
    await userEvent.click(verifyBtn)

    await waitFor(() => {
      expect(screen.getByText(/Invalid 2FA code/i)).toBeInTheDocument()
    })

    // Submit valid 2FA code
    server.use(
      http.post('/api/refzone/verify-2fa', () => {
        return HttpResponse.json({
          userId: 'user-123'
        })
      })
    )

    await userEvent.clear(mfaInput)
    await userEvent.type(mfaInput, '123456')
    await userEvent.click(verifyBtn)

    // Verify it transitions to dashboard
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Toby Sanderson' })).toBeInTheDocument()
    })
  })

  it('restores session on mount if status endpoint returns authenticated', async () => {
    server.use(
      http.get('/api/refzone/status', () => {
        return HttpResponse.json({ authenticated: true, userId: 'user-123' })
      }),
      http.get('/api/refzone/profile', () => {
        return HttpResponse.json({
          firstname: 'Auto',
          lastname: 'LoggedIn',
          headshot: null
        })
      }),
      http.get('/api/refzone/appointments', () => {
        return HttpResponse.json([])
      })
    )

    renderRefZone()

    // It should perform auto login and load dashboard directly
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Auto LoggedIn' })).toBeInTheDocument()
    })
  })

  it('logout clears session and returns to login page', async () => {
    server.use(
      http.get('/api/refzone/status', () => {
        return HttpResponse.json({ authenticated: true, userId: 'user-123' })
      }),
      http.get('/api/refzone/profile', () => {
        return HttpResponse.json({
          firstname: 'Toby',
          lastname: 'Sanderson',
          headshot: null
        })
      }),
      http.get('/api/refzone/appointments', () => {
        return HttpResponse.json([])
      }),
      http.post('/api/refzone/logout', () => {
        return HttpResponse.json({ status: 'logged_out' })
      })
    )

    renderRefZone()

    // Confirm dashboard loaded
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Toby Sanderson' })).toBeInTheDocument()
    })

    // Click logout
    const logoutBtn = screen.getByRole('button', { name: /Logout/i })
    
    // Once clicked, we stub status to return unauthenticated
    server.use(
      http.get('/api/refzone/status', () => {
        return HttpResponse.json({ authenticated: false, userId: null })
      })
    )

    await userEvent.click(logoutBtn)

    // Confirm it goes back to Login
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /RefZone/i })).toBeInTheDocument()
      expect(screen.getByLabelText(/Email Address/i)).toBeInTheDocument()
    })
  })
})
