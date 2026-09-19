import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { PageSummary } from '../../lib/types'
import SettingsTab from './SettingsTab'

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

function mockApi(status = 200, body: unknown = PAGE) {
  const spy = vi.fn(async (_url: string, _init?: RequestInit) => ({
    ok: status >= 200 && status < 300,
    status,
    text: async () => (status === 204 ? '' : JSON.stringify(body)),
  }))
  vi.stubGlobal('fetch', spy)
  return spy
}

function renderTab(props: { page: PageSummary; reloadPage: () => Promise<void> }) {
  return render(
    <MemoryRouter>
      <SettingsTab {...props} />
    </MemoryRouter>,
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('SettingsTab', () => {
  it('renames the page', async () => {
    const spy = mockApi()
    renderTab({ page: PAGE, reloadPage: async () => {} })

    await userEvent.clear(screen.getByLabelText(/display name/i))
    await userEvent.type(screen.getByLabelText(/display name/i), 'Renamed')
    await userEvent.click(screen.getByRole('button', { name: /save settings/i }))

    await waitFor(() =>
      expect(JSON.parse(spy.mock.calls[0][1]!.body as string).name).toBe('Renamed'),
    )
  })

  it('sends no token field when none was typed', async () => {
    const spy = mockApi()
    renderTab({ page: PAGE, reloadPage: async () => {} })

    await userEvent.click(screen.getByRole('button', { name: /save settings/i }))

    const body = JSON.parse(spy.mock.calls[0][1]!.body as string)
    expect(body).not.toHaveProperty('access_token')
  })

  it('rotates the access token when one is typed', async () => {
    const spy = mockApi()
    renderTab({ page: PAGE, reloadPage: async () => {} })

    await userEvent.type(screen.getByLabelText(/new page access token/i), 'EAAG-new')
    await userEvent.click(screen.getByRole('button', { name: /save settings/i }))

    await waitFor(() =>
      expect(JSON.parse(spy.mock.calls[0][1]!.body as string).access_token).toBe('EAAG-new'),
    )
  })

  it('toggles the active flag', async () => {
    const spy = mockApi()
    renderTab({ page: PAGE, reloadPage: async () => {} })

    await userEvent.click(screen.getByLabelText(/page is active/i))
    await userEvent.click(screen.getByRole('button', { name: /save settings/i }))

    await waitFor(() =>
      expect(JSON.parse(spy.mock.calls[0][1]!.body as string).is_active).toBe(false),
    )
  })

  it('only enables delete after the page id is typed', async () => {
    mockApi(204, null)
    renderTab({ page: PAGE, reloadPage: async () => {} })

    const deleteButton = screen.getByRole('button', { name: /delete this page/i })
    expect(deleteButton).toBeDisabled()

    await userEvent.type(screen.getByLabelText(/type the facebook page id/i), '100000000000001')

    expect(deleteButton).toBeEnabled()
  })
})
