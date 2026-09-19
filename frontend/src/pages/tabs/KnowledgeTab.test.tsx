import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { KnowledgeItem, PageSummary } from '../../lib/types'
import KnowledgeTab from './KnowledgeTab'

const PAGE: PageSummary = {
  id: 7,
  fb_page_id: '100000000000001',
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

const ITEM: KnowledgeItem = {
  id: 3,
  page_id: 7,
  title: 'Hoc phi',
  content: '15 trieu moi ky.',
  source: 'manual',
  is_active: true,
  created_at: '2026-09-18T00:00:00Z',
  updated_at: '2026-09-18T00:00:00Z',
}

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

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('KnowledgeTab', () => {
  it('lists the page knowledge', async () => {
    mockApi(() => ({ status: 200, body: [ITEM] }))
    render(<KnowledgeTab page={PAGE} />)

    expect(await screen.findByText('Hoc phi')).toBeInTheDocument()
    expect(screen.getByText('15 trieu moi ky.')).toBeInTheDocument()
  })

  it('requests knowledge for the right page', async () => {
    const spy = mockApi(() => ({ status: 200, body: [] }))
    render(<KnowledgeTab page={PAGE} />)

    await waitFor(() =>
      expect(spy).toHaveBeenCalledWith(
        'http://localhost:8000/api/pages/7/knowledge',
        expect.anything(),
      ),
    )
  })

  it('creates a knowledge item', async () => {
    let items: KnowledgeItem[] = []
    mockApi((_path, init) => {
      if (init?.method === 'POST') {
        items = [ITEM]
        return { status: 201, body: ITEM }
      }
      return { status: 200, body: items }
    })
    render(<KnowledgeTab page={PAGE} />)

    await userEvent.click(await screen.findByRole('button', { name: /add item/i }))
    await userEvent.type(screen.getByLabelText(/title/i), 'Hoc phi')
    await userEvent.type(screen.getByLabelText(/content/i), '15 trieu moi ky.')
    await userEvent.click(screen.getByRole('button', { name: /^save$/i }))

    expect(await screen.findByText('Hoc phi')).toBeInTheDocument()
  })

  it('deletes a knowledge item', async () => {
    let items: KnowledgeItem[] = [ITEM]
    mockApi((_path, init) => {
      if (init?.method === 'DELETE') {
        items = []
        return { status: 204, body: null }
      }
      return { status: 200, body: items }
    })
    render(<KnowledgeTab page={PAGE} />)

    await userEvent.click(await screen.findByRole('button', { name: /delete/i }))

    await waitFor(() => expect(screen.queryByText('Hoc phi')).not.toBeInTheDocument())
  })

  it('shows the learned badge for mined knowledge', async () => {
    mockApi(() => ({ status: 200, body: [{ ...ITEM, source: 'learned' }] }))
    render(<KnowledgeTab page={PAGE} />)

    expect(await screen.findByText(/learned/i)).toBeInTheDocument()
  })

  it('shows an empty state', async () => {
    mockApi(() => ({ status: 200, body: [] }))
    render(<KnowledgeTab page={PAGE} />)

    expect(await screen.findByText(/no knowledge yet/i)).toBeInTheDocument()
  })
})
