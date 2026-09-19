import { useCallback, useEffect, useState, type FormEvent } from 'react'

import { Badge } from '../../components/ui/badge'
import { ErrorAlert } from '../../components/ui/alert'
import { Button } from '../../components/ui/button'
import { Card, CardBody } from '../../components/ui/card'
import { EmptyState, LoadingNote } from '../../components/ui/empty-state'
import { Input, Textarea } from '../../components/ui/input'
import { Label } from '../../components/ui/label'
import { apiFetch } from '../../lib/api'
import type { KnowledgeItem, PageSummary } from '../../lib/types'

export default function KnowledgeTab({ page }: { page: PageSummary }) {
  const [items, setItems] = useState<KnowledgeItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editingId, setEditingId] = useState<number | 'new' | null>(null)
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      setItems(await apiFetch<KnowledgeItem[]>(`/api/pages/${page.id}/knowledge`))
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load knowledge')
    } finally {
      setLoading(false)
    }
  }, [page.id])

  useEffect(() => {
    void reload()
  }, [reload])

  function startCreate() {
    setEditingId('new')
    setTitle('')
    setContent('')
  }

  function startEdit(item: KnowledgeItem) {
    setEditingId(item.id)
    setTitle(item.title)
    setContent(item.content)
  }

  async function save(event: FormEvent) {
    event.preventDefault()
    setError('')
    try {
      if (editingId === 'new') {
        await apiFetch(`/api/pages/${page.id}/knowledge`, {
          method: 'POST',
          body: JSON.stringify({ title, content }),
        })
      } else {
        await apiFetch(`/api/pages/${page.id}/knowledge/${editingId}`, {
          method: 'PATCH',
          body: JSON.stringify({ title, content }),
        })
      }
      setEditingId(null)
      await reload()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not save the item')
    }
  }

  async function remove(item: KnowledgeItem) {
    setError('')
    try {
      await apiFetch(`/api/pages/${page.id}/knowledge/${item.id}`, { method: 'DELETE' })
      await reload()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not delete the item')
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <p className="text-sm text-muted-foreground">
          What this page knows. Saving rebuilds the search index immediately.
        </p>
        <Button onClick={startCreate} className="shrink-0">
          Add item
        </Button>
      </div>

      {editingId !== null && (
        <Card>
          <CardBody>
            <form onSubmit={save} className="space-y-3">
              <div className="space-y-1.5">
                <Label htmlFor="knowledge-title">Title</Label>
                <Input
                  id="knowledge-title"
                  required
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="knowledge-content">Content</Label>
                <Textarea
                  id="knowledge-content"
                  required
                  rows={6}
                  value={content}
                  onChange={(event) => setContent(event.target.value)}
                />
              </div>
              <div className="flex gap-2">
                <Button type="submit">Save</Button>
                <Button type="button" variant="outline" onClick={() => setEditingId(null)}>
                  Cancel
                </Button>
              </div>
            </form>
          </CardBody>
        </Card>
      )}

      {error && <ErrorAlert>{error}</ErrorAlert>}

      {loading ? (
        <LoadingNote />
      ) : items.length === 0 ? (
        <EmptyState>No knowledge yet. Add what this page should be able to answer.</EmptyState>
      ) : (
        <ul className="space-y-3">
          {items.map((item) => (
            <li key={item.id}>
              <Card>
                <CardBody className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <p className="font-medium">{item.title}</p>
                    <p className="mt-1 whitespace-pre-wrap text-sm text-muted-foreground">
                      {item.content}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    {item.source !== 'manual' && (
                      <Badge variant="success">{item.source}</Badge>
                    )}
                    <Button variant="outline" size="sm" onClick={() => startEdit(item)}>
                      Edit
                    </Button>
                    <Button variant="destructive" size="sm" onClick={() => remove(item)}>
                      Delete
                    </Button>
                  </div>
                </CardBody>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
