import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { AuthProvider } from '../lib/auth'
import LoginPage from './LoginPage'

type Route = { status: number; body: unknown }

function mockRoutes(routes: Record<string, Route>) {
  const spy = vi.fn(async (url: string) => {
    const path = url.replace('http://localhost:8000', '')
    const route = routes[path] ?? { status: 404, body: { detail: 'not mocked' } }
    return {
      ok: route.status >= 200 && route.status < 300,
      status: route.status,
      text: async () => JSON.stringify(route.body),
    }
  })
  vi.stubGlobal('fetch', spy)
  return spy
}

function renderLogin() {
  return render(
    <AuthProvider>
      <LoginPage />
    </AuthProvider>,
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('LoginPage', () => {
  it('signs in and stores the token', async () => {
    const spy = mockRoutes({
      '/api/auth/bootstrap-available': { status: 200, body: { available: false } },
      '/api/auth/login': {
        status: 200,
        body: {
          access_token: 'tok-abc',
          token_type: 'bearer',
          user: { id: 1, email: 'boss@hateco.vn', role: 'admin', is_active: true },
        },
      },
    })
    renderLogin()

    await userEvent.type(screen.getByLabelText(/email/i), 'boss@hateco.vn')
    await userEvent.type(screen.getByLabelText(/password/i), 'hunter2hunter2')
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => expect(localStorage.getItem('hateco.token')).toBe('tok-abc'))
    expect(spy).toHaveBeenCalled()
  })

  it('shows the server error when the credentials are wrong', async () => {
    mockRoutes({
      '/api/auth/bootstrap-available': { status: 200, body: { available: false } },
      '/api/auth/login': { status: 401, body: { detail: 'Invalid credentials' } },
    })
    renderLogin()

    await userEvent.type(screen.getByLabelText(/email/i), 'boss@hateco.vn')
    await userEvent.type(screen.getByLabelText(/password/i), 'wrong-password')
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid credentials')
  })

  it('offers to create the first admin when bootstrap is available', async () => {
    mockRoutes({
      '/api/auth/bootstrap-available': { status: 200, body: { available: true } },
    })
    renderLogin()

    expect(
      await screen.findByRole('button', { name: /create the first admin/i }),
    ).toBeInTheDocument()
  })

  it('hides the bootstrap button once a user exists', async () => {
    mockRoutes({
      '/api/auth/bootstrap-available': { status: 200, body: { available: false } },
    })
    renderLogin()

    await screen.findByRole('button', { name: /sign in/i })
    expect(
      screen.queryByRole('button', { name: /create the first admin/i }),
    ).not.toBeInTheDocument()
  })
})
