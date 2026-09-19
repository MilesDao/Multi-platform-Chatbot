import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { PageSummary } from '../../lib/types'
import InstructionsTab from './InstructionsTab'

const PAGE: PageSummary = {
  id: 7,
  fb_page_id: '1',
  name: 'Hateco',
  system_prompt: 'Ban la tu van vien.',
  closing_message: 'Goi hotline 0123 456 789 de duoc tu van them nhe!',
  llm_model: 'google/gemini-2.5-flash',
  is_active: true,
  has_access_token: true,
  my_role: 'owner',
  knowledge_count: 1,
  created_at: '2026-09-18T00:00:00Z',
}

function mockApi(status = 200, body: unknown = PAGE) {
  const spy = vi.fn(async (_url: string, _init?: RequestInit) => ({
    ok: status >= 200 && status < 300,
    status,
    text: async () => JSON.stringify(body),
  }))
  vi.stubGlobal('fetch', spy)
  return spy
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('InstructionsTab', () => {
  it('pre-fills the current instructions', () => {
    mockApi()
    render(<InstructionsTab page={PAGE} reloadPage={async () => {}} />)

    expect(screen.getByLabelText(/instructions/i)).toHaveValue('Ban la tu van vien.')
    expect(screen.getByLabelText(/closing message/i)).toHaveValue(
      'Goi hotline 0123 456 789 de duoc tu van them nhe!',
    )
    expect(screen.getByLabelText(/model/i)).toHaveValue('google/gemini-2.5-flash')
  })

  it('saves the edited instructions', async () => {
    const spy = mockApi()
    const reloadPage = vi.fn(async () => {})
    render(<InstructionsTab page={PAGE} reloadPage={reloadPage} />)

    await userEvent.clear(screen.getByLabelText(/instructions/i))
    await userEvent.type(screen.getByLabelText(/instructions/i), 'Ban la tro ly moi.')
    await userEvent.click(screen.getByRole('button', { name: /save instructions/i }))

    await waitFor(() => expect(reloadPage).toHaveBeenCalled())
    const body = JSON.parse(spy.mock.calls[0][1]!.body as string)
    expect(body.system_prompt).toBe('Ban la tro ly moi.')
  })

  it('saves the edited closing message', async () => {
    const spy = mockApi()
    render(<InstructionsTab page={PAGE} reloadPage={async () => {}} />)

    await userEvent.clear(screen.getByLabelText(/closing message/i))
    await userEvent.type(
      screen.getByLabelText(/closing message/i),
      'Lien he hotline 0987 654 321 nhe!',
    )
    await userEvent.click(screen.getByRole('button', { name: /save instructions/i }))

    await waitFor(() => {
      const body = JSON.parse(spy.mock.calls[0][1]!.body as string)
      expect(body.closing_message).toBe('Lien he hotline 0987 654 321 nhe!')
    })
  })

  it('confirms a successful save', async () => {
    mockApi()
    render(<InstructionsTab page={PAGE} reloadPage={async () => {}} />)

    await userEvent.click(screen.getByRole('button', { name: /save instructions/i }))

    expect(await screen.findByText(/saved/i)).toBeInTheDocument()
  })

  it('shows the server error when saving fails', async () => {
    mockApi(403, { detail: "Requires page role 'owner'" })
    render(<InstructionsTab page={PAGE} reloadPage={async () => {}} />)

    await userEvent.click(screen.getByRole('button', { name: /save instructions/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent("Requires page role 'owner'")
  })
})
