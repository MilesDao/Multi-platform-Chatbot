import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { PageSummary } from '../../lib/types'
import MembersTab from './MembersTab'

const PAGE: PageSummary = {
  id: 7,
  fb_page_id: '1',
  name: 'Hateco',
  system_prompt: '',
  closing_message: '',
  llm_model: '',
  is_active: true,
  has_access_token: true,
  my_role: 'owner',
  knowledge_count: 1,
  created_at: '2026-09-18T00:00:00Z',
}

const MEMBER = { user_id: 2, email: 'editor@hateco.vn', role: 'editor' }
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
      text: async () => (route.status === 204 ? '' : JSON.stringify(route.body)),
    }
  })
  vi.stubGlobal('fetch', spy)
  return spy
}

const standardApi = (path: string) =>
  path.startsWith('/api/users')
    ? { status: 200, body: USERS }
    : { status: 200, body: [MEMBER] }

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('MembersTab', () => {
  it('lists the current members with their role', async () => {
    mockApi(standardApi)
    render(<MembersTab page={PAGE} />)

    expect(await screen.findByText('editor@hateco.vn')).toBeInTheDocument()
    expect(screen.getByDisplayValue('editor')).toBeInTheDocument()
  })

  it('adds a member with the chosen role', async () => {
    const spy = mockApi(standardApi)
    render(<MembersTab page={PAGE} />)
    await screen.findByText('editor@hateco.vn')

    await userEvent.selectOptions(screen.getByLabelText(/add user/i), '1')
    await userEvent.selectOptions(screen.getByLabelText(/new member role/i), 'viewer')
    await userEvent.click(screen.getByRole('button', { name: /^add$/i }))

    await waitFor(() => {
      const put = spy.mock.calls.find(([, init]) => (init as RequestInit)?.method === 'PUT')
      expect(JSON.parse(put![1]!.body as string)).toEqual({ user_id: 1, role: 'viewer' })
    })
  })

  it('changes an existing member role', async () => {
    const spy = mockApi(standardApi)
    render(<MembersTab page={PAGE} />)

    await userEvent.selectOptions(await screen.findByDisplayValue('editor'), 'owner')

    await waitFor(() => {
      const put = spy.mock.calls.find(([, init]) => (init as RequestInit)?.method === 'PUT')
      expect(JSON.parse(put![1]!.body as string)).toEqual({ user_id: 2, role: 'owner' })
    })
  })

  it('removes a member', async () => {
    const spy = mockApi(standardApi)
    render(<MembersTab page={PAGE} />)

    await userEvent.click(await screen.findByRole('button', { name: /remove/i }))

    await waitFor(() =>
      expect(
        spy.mock.calls.some(
          ([url, init]) =>
            String(url).includes('/members/2') &&
            (init as RequestInit)?.method === 'DELETE',
        ),
      ).toBe(true),
    )
  })

  it('shows the server error when the change is refused', async () => {
    mockApi((path, init) =>
      init?.method === 'PUT'
        ? { status: 403, body: { detail: "Requires page role 'owner'" } }
        : standardApi(path),
    )
    render(<MembersTab page={PAGE} />)

    await userEvent.selectOptions(await screen.findByDisplayValue('editor'), 'viewer')

    expect(await screen.findByRole('alert')).toHaveTextContent("Requires page role 'owner'")
  })
})
