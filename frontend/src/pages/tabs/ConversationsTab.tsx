import { useCallback, useEffect, useState, type FormEvent } from 'react'

import { ErrorAlert } from '../../components/ui/alert'
import { Button } from '../../components/ui/button'
import { Card } from '../../components/ui/card'
import { EmptyState, LoadingNote } from '../../components/ui/empty-state'
import { Input } from '../../components/ui/input'
import { Label } from '../../components/ui/label'
import { apiFetch } from '../../lib/api'
import type { ConversationDetail, ConversationSummary, PageSummary } from '../../lib/types'

function formatTime(value: string): string {
  return new Date(value).toLocaleString()
}

export default function ConversationsTab({ page }: { page: PageSummary }) {
  const [summaries, setSummaries] = useState<ConversationSummary[]>([])
  const [detail, setDetail] = useState<ConversationDetail | null>(null)
  const [query, setQuery] = useState('')
  const [appliedQuery, setAppliedQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (appliedQuery.trim()) params.set('q', appliedQuery.trim())
      const suffix = params.toString() ? `?${params}` : ''
      setSummaries(
        await apiFetch<ConversationSummary[]>(
          `/api/pages/${page.id}/conversations${suffix}`,
        ),
      )
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load conversations')
    } finally {
      setLoading(false)
    }
  }, [page.id, appliedQuery])

  useEffect(() => {
    void reload()
  }, [reload])

  async function open(conversationId: number) {
    setError('')
    try {
      setDetail(
        await apiFetch<ConversationDetail>(
          `/api/pages/${page.id}/conversations/${conversationId}`,
        ),
      )
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load the transcript')
    }
  }

  function search(event: FormEvent) {
    event.preventDefault()
    setAppliedQuery(query)
  }

  return (
    <div className="space-y-4">
      <form onSubmit={search} className="flex items-end gap-2">
        <div className="flex-1 space-y-1.5">
          <Label htmlFor="conversation-search">Search</Label>
          <Input
            id="conversation-search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Message text or PSID"
          />
        </div>
        <Button type="submit">Search</Button>
      </form>

      {error && <ErrorAlert>{error}</ErrorAlert>}

      <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
        <div>
          {loading ? (
            <LoadingNote />
          ) : summaries.length === 0 ? (
            <EmptyState>No conversations found.</EmptyState>
          ) : (
            <ul className="space-y-2">
              {summaries.map((summary) => (
                <li key={summary.id}>
                  <button
                    type="button"
                    onClick={() => open(summary.id)}
                    className="w-full text-left"
                  >
                    <Card
                      className={`p-4 transition-colors ${
                        detail?.id === summary.id ? 'border-primary' : 'hover:border-primary/40'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-xs">{summary.psid}</span>
                        <span className="text-xs text-muted-foreground">
                          {summary.message_count} msgs
                        </span>
                      </div>
                      <p className="mt-1 truncate text-sm text-foreground">
                        {summary.last_message_preview}
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {formatTime(summary.last_message_at)}
                      </p>
                    </Card>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div>
          {detail === null ? (
            <EmptyState>Select a conversation to read the transcript.</EmptyState>
          ) : (
            <Card className="space-y-2 p-4" data-testid="transcript">
              <ul className="space-y-2">
                {detail.messages.map((message) => (
                  <li
                    key={message.id}
                    data-direction={message.direction}
                    className={
                      message.direction === 'in'
                        ? 'mr-8 rounded-lg bg-muted p-3'
                        : 'ml-8 rounded-lg bg-primary p-3 text-primary-foreground'
                    }
                  >
                    <p className="whitespace-pre-wrap text-sm">{message.text}</p>
                    {message.attachments.length > 0 && (
                      <p className="mt-1 text-xs opacity-70">
                        {message.attachments.length} attachment(s)
                      </p>
                    )}
                    <p className="mt-1 text-xs opacity-60">{formatTime(message.created_at)}</p>
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
