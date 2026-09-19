import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'

import { ErrorAlert, SuccessNote } from '../../components/ui/alert'
import { Button } from '../../components/ui/button'
import { Card, CardBody } from '../../components/ui/card'
import { Input } from '../../components/ui/input'
import { Label } from '../../components/ui/label'
import { apiFetch } from '../../lib/api'
import type { PageSummary } from '../../lib/types'

export default function SettingsTab({
  page,
  reloadPage,
}: {
  page: PageSummary
  reloadPage: () => Promise<void>
}) {
  const navigate = useNavigate()
  const [name, setName] = useState(page.name)
  const [accessToken, setAccessToken] = useState('')
  const [isActive, setIsActive] = useState(page.is_active)
  const [confirmation, setConfirmation] = useState('')
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)

  async function save(event: FormEvent) {
    event.preventDefault()
    setError('')
    setSaved(false)
    const payload: Record<string, unknown> = { name, is_active: isActive }
    if (accessToken) payload.access_token = accessToken
    try {
      await apiFetch(`/api/pages/${page.id}`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      })
      setAccessToken('')
      setSaved(true)
      await reloadPage()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not save the settings')
    }
  }

  async function remove() {
    setError('')
    try {
      await apiFetch(`/api/pages/${page.id}`, { method: 'DELETE' })
      navigate('/pages')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not delete the page')
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardBody>
          <form onSubmit={save} className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="settings-name">Display name</Label>
              <Input
                id="settings-name"
                required
                value={name}
                onChange={(event) => setName(event.target.value)}
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="settings-token">New Page Access Token</Label>
              <Input
                id="settings-token"
                type="password"
                value={accessToken}
                onChange={(event) => setAccessToken(event.target.value)}
                placeholder={page.has_access_token ? 'A token is stored' : 'No token stored'}
              />
              <p className="text-xs text-muted-foreground">
                Leave empty to keep the current token. Tokens are stored encrypted and never
                shown again.
              </p>
            </div>

            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={isActive}
                onChange={(event) => setIsActive(event.target.checked)}
                className="h-4 w-4 rounded border-input accent-[var(--color-primary)]"
              />
              Page is active
            </label>
            <p className="text-xs text-muted-foreground">
              An inactive page still logs incoming messages but never replies.
            </p>

            {error && <ErrorAlert>{error}</ErrorAlert>}
            {saved && <SuccessNote>Saved.</SuccessNote>}

            <Button type="submit">Save settings</Button>
          </form>
        </CardBody>
      </Card>

      <Card className="border-destructive/30">
        <CardBody className="space-y-3">
          <div>
            <h2 className="text-sm font-medium text-destructive">Delete this page</h2>
            <p className="text-xs text-muted-foreground">
              Removes the page with its knowledge, conversations and suggestions.
              This cannot be undone.
            </p>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="delete-confirm">Type the Facebook Page ID to confirm</Label>
            <Input
              id="delete-confirm"
              value={confirmation}
              onChange={(event) => setConfirmation(event.target.value)}
              className="font-mono"
            />
          </div>
          <Button
            variant="destructive"
            onClick={remove}
            disabled={confirmation !== page.fb_page_id}
          >
            Delete this page
          </Button>
        </CardBody>
      </Card>
    </div>
  )
}
