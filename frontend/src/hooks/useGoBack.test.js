import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useGoBack } from './useGoBack'
import { useNavigate, useLocation } from 'react-router-dom'

vi.mock('react-router-dom', () => ({
  useNavigate: vi.fn(),
  useLocation: vi.fn(),
}))

describe('useGoBack hook', () => {
  const mockNavigate = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useNavigate).mockReturnValue(mockNavigate)
  })

  it('navigates back (-1) when location.key is not default', () => {
    vi.mocked(useLocation).mockReturnValue({
      pathname: '/some-page',
      search: '',
      hash: '',
      state: null,
      key: 'abc12345',
    })

    const { result } = renderHook(() => useGoBack('/fallback'))
    result.current()

    expect(mockNavigate).toHaveBeenCalledTimes(1)
    expect(mockNavigate).toHaveBeenCalledWith(-1)
  })

  it('navigates to fallback URL with replace when location.key is default', () => {
    vi.mocked(useLocation).mockReturnValue({
      pathname: '/some-page',
      search: '',
      hash: '',
      state: null,
      key: 'default',
    })

    const { result } = renderHook(() => useGoBack('/fallback'))
    result.current()

    expect(mockNavigate).toHaveBeenCalledTimes(1)
    expect(mockNavigate).toHaveBeenCalledWith('/fallback', { replace: true })
  })

  it('defaults to root URL "/" as fallback if not specified', () => {
    vi.mocked(useLocation).mockReturnValue({
      pathname: '/some-page',
      search: '',
      hash: '',
      state: null,
      key: 'default',
    })

    const { result } = renderHook(() => useGoBack())
    result.current()

    expect(mockNavigate).toHaveBeenCalledTimes(1)
    expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true })
  })
})
