import { describe, it, expect, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { useApi } from './useApi'

describe('useApi hook', () => {
  it('returns data on resolved fetch', async () => {
    const fetchFn = vi.fn().mockResolvedValue({ name: 'Test' })
    const { result } = renderHook(() => useApi(fetchFn, []))
    expect(result.current.loading).toBe(true)
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.data).toEqual({ name: 'Test' })
    expect(result.current.error).toBeNull()
  })

  it('captures errors correctly', async () => {
    const fetchFn = vi.fn().mockRejectedValue(new Error('network fail'))
    const { result } = renderHook(() => useApi(fetchFn, []))
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.error).toBe('network fail')
    expect(result.current.data).toBeNull()
  })
})
