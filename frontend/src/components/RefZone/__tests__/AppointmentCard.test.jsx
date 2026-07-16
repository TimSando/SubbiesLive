import React from 'react'
import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import AppointmentCard from '../AppointmentCard.jsx'
import * as api from '../../../api/refzone'

vi.mock('../../../api/refzone', () => ({
  updateAppointmentStatus: vi.fn(),
  fetchVenueWeather: vi.fn().mockResolvedValue({ latitude: null, longitude: null, weather: null }),
}))

const mockAppointmentPending = {
  _id: 'app-pending',
  status: 'pending',
  isActive: true,
  type: 'Referee',
  match: {
    moment: Date.now() + 86400000, // tomorrow
    homeTeam: { name: 'Colleagues' },
    awayTeam: { name: 'Mosman' },
    competition: { name: 'Kentwell Cup' },
  },
}

const mockAppointmentApproved = {
  _id: 'app-approved',
  status: 'approved',
  isActive: true,
  type: 'Referee',
  match: {
    moment: Date.now() + 86400000, // tomorrow
    homeTeam: { name: 'Colleagues' },
    awayTeam: { name: 'Mosman' },
    competition: { name: 'Kentwell Cup' },
  },
}

const mockAppointmentDeclined = {
  _id: 'app-declined',
  status: 'declined',
  isActive: true,
  type: 'Referee',
  match: {
    moment: Date.now() + 86400000, // tomorrow
    homeTeam: { name: 'Colleagues' },
    awayTeam: { name: 'Mosman' },
    competition: { name: 'Kentwell Cup' },
  },
}

const mockAppointmentPast = {
  _id: 'app-past',
  status: 'pending',
  isActive: true,
  type: 'Referee',
  match: {
    moment: Date.now() - 86400000, // yesterday
    homeTeam: { name: 'Colleagues' },
    awayTeam: { name: 'Mosman' },
    competition: { name: 'Kentwell Cup' },
  },
}

describe('AppointmentCard Component', () => {
  it('renders pending appointment with both Accept and Reject buttons', () => {
    render(
      <MemoryRouter>
        <AppointmentCard appointment={mockAppointmentPending} />
      </MemoryRouter>
    )

    expect(screen.getByRole('button', { name: /Accept/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Reject/i })).toBeInTheDocument()
  })

  it('renders approved upcoming appointment with only Reject button', () => {
    render(
      <MemoryRouter>
        <AppointmentCard appointment={mockAppointmentApproved} />
      </MemoryRouter>
    )

    expect(screen.queryByRole('button', { name: /Accept/i })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Reject/i })).toBeInTheDocument()
  })

  it('renders declined appointment with neither button', () => {
    render(
      <MemoryRouter>
        <AppointmentCard appointment={mockAppointmentDeclined} />
      </MemoryRouter>
    )

    expect(screen.queryByRole('button', { name: /Accept/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Reject/i })).not.toBeInTheDocument()
  })

  it('renders past pending appointment with neither button', () => {
    render(
      <MemoryRouter>
        <AppointmentCard appointment={mockAppointmentPast} />
      </MemoryRouter>
    )

    expect(screen.queryByRole('button', { name: /Accept/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Reject/i })).not.toBeInTheDocument()
  })

  it('calls updateAppointmentStatus and onUpdate when Accept clicked', async () => {
    const onUpdateSpy = vi.fn()
    api.updateAppointmentStatus.mockResolvedValueOnce({ status: 'ok' })

    render(
      <MemoryRouter>
        <AppointmentCard appointment={mockAppointmentPending} onUpdate={onUpdateSpy} />
      </MemoryRouter>
    )

    const acceptBtn = screen.getByRole('button', { name: /Accept/i })
    await userEvent.click(acceptBtn)

    expect(api.updateAppointmentStatus).toHaveBeenCalledWith('app-pending', 'approved')
    await waitFor(() => {
      expect(onUpdateSpy).toHaveBeenCalled()
    })
  })

  it('calls updateAppointmentStatus and onUpdate when Reject clicked', async () => {
    const onUpdateSpy = vi.fn()
    api.updateAppointmentStatus.mockResolvedValueOnce({ status: 'ok' })

    render(
      <MemoryRouter>
        <AppointmentCard appointment={mockAppointmentPending} onUpdate={onUpdateSpy} />
      </MemoryRouter>
    )

    const rejectBtn = screen.getByRole('button', { name: /Reject/i })
    await userEvent.click(rejectBtn)

    expect(api.updateAppointmentStatus).toHaveBeenCalledWith('app-pending', 'declined')
    await waitFor(() => {
      expect(onUpdateSpy).toHaveBeenCalled()
    })
  })

  it('hides both Accept and Reject buttons when hideActions is true', () => {
    render(
      <MemoryRouter>
        <AppointmentCard appointment={mockAppointmentPending} hideActions={true} />
      </MemoryRouter>
    )

    expect(screen.queryByRole('button', { name: /Accept/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Reject/i })).not.toBeInTheDocument()
  })

  it('renders Google Maps link when venue is present', () => {
    const appointmentWithVenue = {
      ...mockAppointmentPending,
      match: {
        ...mockAppointmentPending.match,
        venue: { name: 'Forsyth Park' },
      },
    }

    render(
      <MemoryRouter>
        <AppointmentCard appointment={appointmentWithVenue} />
      </MemoryRouter>
    )

    const link = screen.getByRole('link', { name: /Forsyth Park/i })
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute('href', 'https://www.google.com/maps/search/?api=1&query=Forsyth%20Park%20Sydney')
    expect(link).toHaveAttribute('target', '_blank')
  })

  it('renders weather details and updates map link when venue-weather is loaded', async () => {
    const appointmentWithVenue = {
      ...mockAppointmentPending,
      match: {
        ...mockAppointmentPending.match,
        venue: { name: 'Forsyth Park' },
      },
    }

    const mockWeather = {
      temperature: 19.5,
      precipitation_probability: 20,
      wind_speed: 12.5,
    }

    api.fetchVenueWeather.mockResolvedValueOnce({
      latitude: -33.8,
      longitude: 151.2,
      weather: mockWeather,
    })

    render(
      <MemoryRouter>
        <AppointmentCard appointment={appointmentWithVenue} />
      </MemoryRouter>
    )

    // Initially displays loading weather placeholder
    expect(screen.getByText(/Loading.../i)).toBeInTheDocument()

    // Wait for the state to update, display weather details, and check maps link updates to use resolved coordinates
    await waitFor(() => {
      expect(screen.getByText(/19.5°C/i)).toBeInTheDocument()
      expect(screen.getByText(/20%/i)).toBeInTheDocument()
      expect(screen.getByText(/12.5 km\/h/i)).toBeInTheDocument()

      const link = screen.getByRole('link', { name: /Forsyth Park/i })
      expect(link).toHaveAttribute('href', 'https://www.google.com/maps/search/?api=1&query=-33.8,151.2')
    })
  })
})

