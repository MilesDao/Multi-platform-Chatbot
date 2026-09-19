import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'

import { Badge } from '../components/ui/badge'
import { ErrorAlert } from '../components/ui/alert'
import { Button } from '../components/ui/button'
import { Card, CardBody } from '../components/ui/card'
import { EmptyState, LoadingNote } from '../components/ui/empty-state'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { apiFetch } from '../lib/api'
import type { PageSummary } from '../lib/types'

export default function PagesListPage() {
  const [pages, setPages] = useState<PageSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [error, setError] = useState('')
  const [fbPageId, setFbPageId] = useState('')
  const [name, setName] = useState('')
  const [accessToken, setAccessToken] = useState('')

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      setPages(await apiFetch<PageSummary[]>('/api/pages'))
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load pages')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void reload()
  }, [reload])

  async function createPage(event: FormEvent) {
    event.preventDefault()
    setError('')
    try {
      await apiFetch<PageSummary>('/api/pages', {
        method: 'POST',
        body: JSON.stringify({
          fb_page_id: fbPageId,
          name,
          access_token: accessToken,
        }),
      })
      setShowForm(false)
      setFbPageId('')
      setName('')
      setAccessToken('')
      await reload()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not create the page')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Pages</h1>
          <p className="text-sm text-muted-foreground">
            Every Facebook Page connected to the chatbot.
          </p>
        </div>
        <Button onClick={() => setShowForm((open) => !open)}>Add page</Button>
      </div>

      {showForm && (
        <Card>
          <CardBody>
            <form onSubmit={createPage} className="space-y-3">
              <div className="space-y-1.5">
                <Label htmlFor="fb-page-id">Facebook Page ID</Label>
                <Input
                  id="fb-page-id"
                  required
                  value={fbPageId}
                  onChange={(event) => setFbPageId(event.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="page-name">Display name</Label>
                <Input
                  id="page-name"
                  required
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="page-token">Page Access Token</Label>
                <Input
                  id="page-token"
                  type="password"
                  value={accessToken}
                  onChange={(event) => setAccessToken(event.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Stored encrypted. It is never shown again after saving.
                </p>
              </div>
              <Button type="submit">Create</Button>
            </form>
          </CardBody>
        </Card>
      )}

      {error && <ErrorAlert>{error}</ErrorAlert>}

      {loading ? (
        <LoadingNote />
      ) : pages.length === 0 ? (
        <EmptyState>No pages yet. Add the first Facebook Page to start.</EmptyState>
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2">
          {pages.map((page) => (
            <li key={page.id}>
              <Link to={`/pages/${page.id}`} className="block">
                <Card className="p-5 transition-colors hover:border-primary/40">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{page.name}</span>
                    <Badge variant="accent">{page.my_role}</Badge>
                  </div>
                  <p className="mt-1 font-mono text-xs text-muted-foreground">
                    {page.fb_page_id}
                  </p>
                  <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <span>{page.knowledge_count} knowledge items</span>
                    {!page.is_active && <Badge variant="warning">Inactive</Badge>}
                    {!page.has_access_token && (
                      <Badge variant="destructive">No access token</Badge>
                    )}
                  </div>
                </Card>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
