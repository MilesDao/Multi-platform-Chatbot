import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { PageSummary } from '../lib/types'
import TestChatPanel from './TestChatPanel'

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

function mockApi(route: { status: number; body: unknown }) {
  const spy = vi.fn(async () => ({
    ok: route.status >= 200 && route.status < 300,
    status: route.status,
    text: async () => JSON.stringify(route.body),
  }))
  vi.stubGlobal('fetch', spy)
  return spy
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('TestChatPanel', () => {
  it('shows the generated answer', async () => {
    mockApi({ status: 200, body: { answer: 'Chao em!', context: ['Hoc phi 15 trieu.'] } })
    render(<TestChatPanel page={PAGE} />)

    await userEvent.type(screen.getByLabelText(/test message/i), 'Hoc phi bao nhieu?')
    await userEvent.click(screen.getByRole('button', { name: /send/i }))

    expect(await screen.findByText('Chao em!')).toBeInTheDocument()
  })

  it('shows the retrieved context chunks', async () => {
    mockApi({ status: 200, body: { answer: 'Chao em!', context: ['Hoc phi 15 trieu.'] } })
    render(<TestChatPanel page={PAGE} />)

    await userEvent.type(screen.getByLabelText(/test message/i), 'Hoc phi?')
    await userEvent.click(screen.getByRole('button', { name: /send/i }))

    expect(await screen.findByText('Hoc phi 15 trieu.')).toBeInTheDocument()
  })

  it('surfaces a failure', async () => {
    mockApi({ status: 500, body: { detail: 'LLM provider unavailable' } })
    render(<TestChatPanel page={PAGE} />)

    await userEvent.type(screen.getByLabelText(/test message/i), 'Hoc phi?')
    await userEvent.click(screen.getByRole('button', { name: /send/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent('LLM provider unavailable')
  })
})
