import { afterEach, describe, expect, it, vi } from 'vitest'

import { ApiError, apiFetch, getToken, setToken } from './api'

function mockFetch(status: number, body: unknown) {
  const response = {
    ok: status >= 200 && status < 300,
    status,
    text: async () => (body === undefined ? '' : JSON.stringify(body)),
  }
  const spy = vi.fn().mockResolvedValue(response)
  vi.stubGlobal('fetch', spy)
  return spy
}

afterEach(() => {
  vi.unstubAllGlobals()
  localStorage.clear()
})

describe('apiFetch', () => {
  it('returns the parsed JSON body', async () => {
    mockFetch(200, { status: 'ok' })

    await expect(apiFetch('/api/health')).resolves.toEqual({ status: 'ok' })
  })

  it('attaches the bearer token when one is stored', async () => {
    setToken('tok-123')
    const spy = mockFetch(200, {})

    await apiFetch('/api/auth/me')

    const headers = spy.mock.calls[0][1].headers as Headers
    expect(headers.get('Authorization')).toBe('Bearer tok-123')
  })

  it('sends no Authorization header when signed out', async () => {
    const spy = mockFetch(200, {})

    await apiFetch('/api/health')

    const headers = spy.mock.calls[0][1].headers as Headers
    expect(headers.get('Authorization')).toBeNull()
  })

  it('throws an ApiError carrying the status and the detail', async () => {
    mockFetch(401, { detail: 'Invalid credentials' })

    await expect(apiFetch('/api/auth/login')).rejects.toMatchObject({
      status: 401,
      message: 'Invalid credentials',
    })
  })

  it('resolves to undefined for a 204 response', async () => {
    mockFetch(204, undefined)

    await expect(apiFetch('/api/pages/1')).resolves.toBeUndefined()
  })

  it('keeps ApiError instances recognisable', async () => {
    mockFetch(500, { detail: 'boom' })

    await expect(apiFetch('/api/health')).rejects.toBeInstanceOf(ApiError)
  })
})

describe('token storage', () => {
  it('round-trips and clears the token', () => {
    setToken('tok-123')
    expect(getToken()).toBe('tok-123')

    setToken(null)
    expect(getToken()).toBeNull()
  })
})
