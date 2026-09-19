import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import PagesListPage from './PagesListPage'

const PAGE = {
  id: 1,
  fb_page_id: '100000000000001',
  name: 'Hateco Tuyen Sinh',
  system_prompt: '',
  llm_model: '',
  is_active: true,
  has_access_token: true,
  my_role: 'owner',
  knowledge_count: 5,
  created_at: '2026-09-18T00:00:00Z',
}

function mockApi(handler: (path: string, init?: RequestInit) => { status: number; body: unknown }) {
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

function renderPage() {
  return render(
    <MemoryRouter>
      <PagesListPage />
    </MemoryRouter>,
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('PagesListPage', () => {
  it('lists the pages returned by the API', async () => {
    mockApi(() => ({ status: 200, body: [PAGE] }))
    renderPage()

    expect(await screen.findByText('Hateco Tuyen Sinh')).toBeInTheDocument()
    expect(screen.getByText('100000000000001')).toBeInTheDocument()
  })

  it('shows an empty state when there are no pages', async () => {
    mockApi(() => ({ status: 200, body: [] }))
    renderPage()

    expect(await screen.findByText(/no pages yet/i)).toBeInTheDocument()
  })

  it('creates a page and shows it in the list', async () => {
    let created = false
    mockApi((path, init) => {
      if (init?.method === 'POST') {
        created = true
        return { status: 201, body: PAGE }
      }
      return { status: 200, body: created ? [PAGE] : [] }
    })
    renderPage()

    await userEvent.click(await screen.findByRole('button', { name: /add page/i }))
    await userEvent.type(screen.getByLabelText(/facebook page id/i), '100000000000001')
    await userEvent.type(screen.getByLabelText(/display name/i), 'Hateco Tuyen Sinh')
    await userEvent.type(screen.getByLabelText(/page access token/i), 'EAAG-secret')
    await userEvent.click(screen.getByRole('button', { name: /^create$/i }))

    expect(await screen.findByText('Hateco Tuyen Sinh')).toBeInTheDocument()
  })

  it('shows the server error when creation fails', async () => {
    mockApi((_path, init) =>
      init?.method === 'POST'
        ? { status: 409, body: { detail: 'A page with this Facebook Page ID already exists' } }
        : { status: 200, body: [] },
    )
    renderPage()

    await userEvent.click(await screen.findByRole('button', { name: /add page/i }))
    await userEvent.type(screen.getByLabelText(/facebook page id/i), '1')
    await userEvent.type(screen.getByLabelText(/display name/i), 'Dup')
    await userEvent.click(screen.getByRole('button', { name: /^create$/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent('already exists')
  })

  it('marks an inactive page', async () => {
    mockApi(() => ({ status: 200, body: [{ ...PAGE, is_active: false }] }))
    renderPage()

    expect(await screen.findByText(/inactive/i)).toBeInTheDocument()
  })
})
