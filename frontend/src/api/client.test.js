import { describe, it, expect } from 'vitest'
import { api } from './client'
import { server } from '../test/setup'
import { http, HttpResponse } from 'msw'

describe('API client', () => {
  it('calls health endpoint successfully', async () => {
    const res = await api.health()
    expect(res).toEqual({ status: 'healthy' })
  })

  it('calls getCompetitions successfully', async () => {
    const res = await api.getCompetitions()
    expect(res).toHaveLength(2)
    expect(res[0].name).toBe('Kentwell Cup')
  })

  it('handles API errors correctly', async () => {
    server.use(
      http.get('/api/competitions', () => {
        return new HttpResponse(null, { status: 500 })
      })
    )

    await expect(api.getCompetitions()).rejects.toThrow('API error: 500')
  })

  it('builds query parameters correctly in getGames', async () => {
    let capturedUrl = null
    server.use(
      http.get('/api/games', ({ request }) => {
        capturedUrl = request.url
        return HttpResponse.json([{ id: 1 }])
      })
    )

    await api.getGames({ competition_id: 7, status: 'completed', empty: '' })
    
    // The query string should match
    expect(capturedUrl).toContain('competition_id=7')
    expect(capturedUrl).toContain('status=completed')
    expect(capturedUrl).not.toContain('empty')
  })
})
