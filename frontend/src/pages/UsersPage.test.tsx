import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import UsersPage from './UsersPage'

const USERS = [
  { id: 1, email: 'boss@hateco.vn', role: 'admin', is_active: true },
  { id: 2, email: 'editor@hateco.vn', role: 'member', is_active: true },
]

function mockApi(
  handler: (path: string, init?: RequestInit) => { status: number; body: unknown },
) {
  const spy = vi.fn(async (url: string, init?: RequestInit) => {
    const route = handler(url.replace('http://localhost:8000', ''), init)
    return {
      ok: route.status >= 200 && route.status < 300,
      status: route.status,
      text: async () => JSON.stringify(route.body),
    }
  })
  vi.stubGlobal('fetch', spy)
  return spy
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('UsersPage', () => {
  it('lists the users', async () => {
    mockApi(() => ({ status: 200, body: USERS }))
    render(<UsersPage />)

    expect(await screen.findByText('boss@hateco.vn')).toBeInTheDocument()
    expect(screen.getByText('editor@hateco.vn')).toBeInTheDocument()
  })

  it('creates a user', async () => {
    const spy = mockApi((_path, init) =>
      init?.method === 'POST'
        ? { status: 201, body: USERS[1] }
        : { status: 200, body: USERS },
    )
    render(<UsersPage />)
    await screen.findByText('boss@hateco.vn')

    await userEvent.type(screen.getByLabelText(/^email$/i), 'new@hateco.vn')
    await userEvent.type(screen.getByLabelText(/^password$/i), 'another-pass-1')
    await userEvent.click(screen.getByRole('button', { name: /create user/i }))

    await waitFor(() => {
      const post = spy.mock.calls.find(([, init]) => (init as RequestInit)?.method === 'POST')
      expect(JSON.parse(post![1]!.body as string)).toEqual({
        email: 'new@hateco.vn',
        password: 'another-pass-1',
        role: 'member',
      })
    })
  })

  it('shows the server error when the email is taken', async () => {
    mockApi((_path, init) =>
      init?.method === 'POST'
        ? { status: 409, body: { detail: 'Email already registered' } }
        : { status: 200, body: USERS },
    )
    render(<UsersPage />)
    await screen.findByText('boss@hateco.vn')

    await userEvent.type(screen.getByLabelText(/^email$/i), 'boss@hateco.vn')
    await userEvent.type(screen.getByLabelText(/^password$/i), 'another-pass-1')
    await userEvent.click(screen.getByRole('button', { name: /create user/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Email already registered')
  })

  it('deactivates a user', async () => {
    const spy = mockApi((_path, init) =>
      init?.method === 'DELETE'
        ? { status: 200, body: { ...USERS[1], is_active: false } }
        : { status: 200, body: USERS },
    )
    render(<UsersPage />)

    const rows = await screen.findAllByRole('button', { name: /deactivate/i })
    await userEvent.click(rows[0])

    await waitFor(() =>
      expect(
        spy.mock.calls.some(([, init]) => (init as RequestInit)?.method === 'DELETE'),
      ).toBe(true),
    )
  })

  it('marks deactivated users', async () => {
    mockApi(() => ({ status: 200, body: [{ ...USERS[1], is_active: false }] }))
    render(<UsersPage />)

    expect(await screen.findByText(/deactivated/i)).toBeInTheDocument()
  })
})
