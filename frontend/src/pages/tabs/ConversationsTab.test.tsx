import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { PageSummary } from '../../lib/types'
import ConversationsTab from './ConversationsTab'

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

const SUMMARY = {
  id: 11,
  psid: 'psid-a',
  started_at: '2026-09-18T00:00:00Z',
  last_message_at: '2026-09-18T01:00:00Z',
  message_count: 2,
  last_message_preview: '15 trieu em nhe',
}

const DETAIL = {
  id: 11,
  psid: 'psid-a',
  started_at: '2026-09-18T00:00:00Z',
  last_message_at: '2026-09-18T01:00:00Z',
  messages: [
    {
      id: 1,
      direction: 'in',
      text: 'Hoc phi bao nhieu?',
      attachments: [],
      created_at: '2026-09-18T00:00:00Z',
    },
    {
      id: 2,
      direction: 'out',
      text: '15 trieu em nhe',
      attachments: [],
      created_at: '2026-09-18T01:00:00Z',
    },
  ],
}

function mockApi(handler: (path: string) => { status: number; body: unknown }) {
  const spy = vi.fn(async (url: string) => {
    const route = handler(url.replace('http://localhost:8000', ''))
    return {
      ok: route.status >= 200 && route.status < 300,
      status: route.status,
      text: async () => JSON.stringify(route.body),
    }
  })
  vi.stubGlobal('fetch', spy)
  return spy
}

const standardApi = (path: string) =>
  path.includes('/conversations/')
    ? { status: 200, body: DETAIL }
    : { status: 200, body: [SUMMARY] }

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('ConversationsTab', () => {
  it('lists conversations with their preview', async () => {
    mockApi(standardApi)
    render(<ConversationsTab page={PAGE} />)

    expect(await screen.findByText('psid-a')).toBeInTheDocument()
    expect(screen.getByText('15 trieu em nhe')).toBeInTheDocument()
  })

  it('opens the transcript when a conversation is clicked', async () => {
    mockApi(standardApi)
    render(<ConversationsTab page={PAGE} />)

    await userEvent.click(await screen.findByRole('button', { name: /psid-a/ }))

    expect(await screen.findByText('Hoc phi bao nhieu?')).toBeInTheDocument()
  })

  it('sends the search term to the API', async () => {
    const spy = mockApi(standardApi)
    render(<ConversationsTab page={PAGE} />)
    await screen.findByText('psid-a')

    await userEvent.type(screen.getByLabelText(/search/i), 'hoc phi')
    await userEvent.click(screen.getByRole('button', { name: /^search$/i }))

    await waitFor(() =>
      expect(
        spy.mock.calls.some(([url]) => String(url).includes('q=hoc+phi')),
      ).toBe(true),
    )
  })

  it('shows an empty state when nothing matches', async () => {
    mockApi(() => ({ status: 200, body: [] }))
    render(<ConversationsTab page={PAGE} />)

    expect(await screen.findByText(/no conversations/i)).toBeInTheDocument()
  })

  it('distinguishes inbound from outbound messages', async () => {
    mockApi(standardApi)
    render(<ConversationsTab page={PAGE} />)

    await userEvent.click(await screen.findByRole('button', { name: /psid-a/ }))
    const transcript = within(await screen.findByTestId('transcript'))
    const inbound = transcript.getByText('Hoc phi bao nhieu?')
    const outbound = transcript.getByText('15 trieu em nhe')

    expect(inbound.closest('li')).toHaveAttribute('data-direction', 'in')
    expect(outbound.closest('li')).toHaveAttribute('data-direction', 'out')
  })
})
