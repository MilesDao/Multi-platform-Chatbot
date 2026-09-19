import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { PageSummary } from '../../lib/types'
import LearningTab from './LearningTab'

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

const SUGGESTION = {
  id: 21,
  page_id: 7,
  question: 'Hoc phi bao nhieu?',
  answer: '15 trieu moi ky.',
  occurrences: 14,
  status: 'pending' as const,
  created_at: '2026-09-18T00:00:00Z',
  reviewed_at: null,
  knowledge_item_id: null,
}

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

describe('LearningTab', () => {
  it('lists pending suggestions with their occurrence count', async () => {
    mockApi(() => ({ status: 200, body: [SUGGESTION] }))
    render(<LearningTab page={PAGE} />)

    expect(await screen.findByText('Hoc phi bao nhieu?')).toBeInTheDocument()
    expect(screen.getByText(/seen 14/i)).toBeInTheDocument()
  })

  it('shows an empty state when the queue is clear', async () => {
    mockApi(() => ({ status: 200, body: [] }))
    render(<LearningTab page={PAGE} />)

    expect(await screen.findByText(/nothing to review/i)).toBeInTheDocument()
  })

  it('mines conversations and shows the new drafts', async () => {
    let mined = false
    mockApi((path) => {
      if (path.includes('/learning/mine')) {
        mined = true
        return { status: 200, body: { created: 1, suggestions: [SUGGESTION] } }
      }
      return { status: 200, body: mined ? [SUGGESTION] : [] }
    })
    render(<LearningTab page={PAGE} />)

    await userEvent.click(
      await screen.findByRole('button', { name: /mine conversations/i }),
    )

    expect(await screen.findByText('Hoc phi bao nhieu?')).toBeInTheDocument()
  })

  it('reports when mining finds nothing new', async () => {
    mockApi((path) =>
      path.includes('/learning/mine')
        ? { status: 200, body: { created: 0, suggestions: [] } }
        : { status: 200, body: [] },
    )
    render(<LearningTab page={PAGE} />)

    await userEvent.click(
      await screen.findByRole('button', { name: /mine conversations/i }),
    )

    expect(await screen.findByText(/no new suggestions/i)).toBeInTheDocument()
  })

  it('approves a suggestion and removes it from the queue', async () => {
    let pending = [SUGGESTION]
    const spy = mockApi((path) => {
      if (path.includes('/approve')) {
        pending = []
        return { status: 200, body: { ...SUGGESTION, status: 'approved' } }
      }
      return { status: 200, body: pending }
    })
    render(<LearningTab page={PAGE} />)

    await userEvent.click(await screen.findByRole('button', { name: /^approve$/i }))

    await waitFor(() =>
      expect(screen.queryByText('Hoc phi bao nhieu?')).not.toBeInTheDocument(),
    )
    expect(
      spy.mock.calls.some(([url]) =>
        String(url).includes('/api/pages/7/suggestions/21/approve'),
      ),
    ).toBe(true)
  })

  it('sends the edited answer when approving after an edit', async () => {
    const spy = mockApi((path) =>
      path.includes('/approve')
        ? { status: 200, body: { ...SUGGESTION, status: 'approved' } }
        : { status: 200, body: [SUGGESTION] },
    )
    render(<LearningTab page={PAGE} />)

    await userEvent.click(await screen.findByRole('button', { name: /^edit$/i }))
    const answerBox = screen.getByLabelText(/answer/i)
    await userEvent.clear(answerBox)
    await userEvent.type(answerBox, '20 trieu moi ky.')
    await userEvent.click(screen.getByRole('button', { name: /approve with edits/i }))

    await waitFor(() => {
      const approveCall = spy.mock.calls.find(([url]) =>
        String(url).includes('/approve'),
      )
      expect(JSON.parse(approveCall![1]!.body as string).answer).toBe('20 trieu moi ky.')
    })
  })

  it('rejects a suggestion', async () => {
    let pending = [SUGGESTION]
    const spy = mockApi((path) => {
      if (path.includes('/reject')) {
        pending = []
        return { status: 200, body: { ...SUGGESTION, status: 'rejected' } }
      }
      return { status: 200, body: pending }
    })
    render(<LearningTab page={PAGE} />)

    await userEvent.click(await screen.findByRole('button', { name: /^reject$/i }))

    await waitFor(() =>
      expect(
        spy.mock.calls.some(([url]) => String(url).includes('/reject')),
      ).toBe(true),
    )
  })

  it('shows the server error when mining fails', async () => {
    mockApi((path) =>
      path.includes('/learning/mine')
        ? { status: 403, body: { detail: "Requires page role 'editor'" } }
        : { status: 200, body: [] },
    )
    render(<LearningTab page={PAGE} />)

    await userEvent.click(
      await screen.findByRole('button', { name: /mine conversations/i }),
    )

    expect(await screen.findByRole('alert')).toHaveTextContent("Requires page role 'editor'")
  })
})
