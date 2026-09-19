import { useCallback, useEffect, useState } from 'react'

import { Badge } from '../../components/ui/badge'
import { ErrorAlert, InfoNote } from '../../components/ui/alert'
import { Button } from '../../components/ui/button'
import { Card, CardBody } from '../../components/ui/card'
import { EmptyState, LoadingNote } from '../../components/ui/empty-state'
import { Input, Textarea } from '../../components/ui/input'
import { Label } from '../../components/ui/label'
import { apiFetch } from '../../lib/api'
import type { PageSummary, Suggestion } from '../../lib/types'

interface MineResult {
  created: number
  suggestions: Suggestion[]
}

export default function LearningTab({ page }: { page: PageSummary }) {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const [loading, setLoading] = useState(true)
  const [mining, setMining] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [draftQuestion, setDraftQuestion] = useState('')
  const [draftAnswer, setDraftAnswer] = useState('')

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      setSuggestions(
        await apiFetch<Suggestion[]>(`/api/pages/${page.id}/suggestions?status=pending`),
      )
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load suggestions')
    } finally {
      setLoading(false)
    }
  }, [page.id])

  useEffect(() => {
    void reload()
  }, [reload])

  async function mine() {
    setError('')
    setNotice('')
    setMining(true)
    try {
      const result = await apiFetch<MineResult>(`/api/pages/${page.id}/learning/mine`, {
        method: 'POST',
      })
      setNotice(
        result.created === 0
          ? 'No new suggestions — everything recurring is already covered.'
          : `${result.created} new suggestion(s) ready for review.`,
      )
      await reload()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Mining failed')
    } finally {
      setMining(false)
    }
  }

  function startEdit(suggestion: Suggestion) {
    setEditingId(suggestion.id)
    setDraftQuestion(suggestion.question)
    setDraftAnswer(suggestion.answer)
  }

  async function approve(suggestion: Suggestion, withEdits: boolean) {
    setError('')
    setNotice('')
    try {
      await apiFetch(`/api/pages/${page.id}/suggestions/${suggestion.id}/approve`, {
        method: 'POST',
        body: JSON.stringify(
          withEdits ? { title: draftQuestion, answer: draftAnswer } : {},
        ),
      })
      setEditingId(null)
      await reload()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not approve')
    }
  }

  async function reject(suggestion: Suggestion) {
    setError('')
    setNotice('')
    try {
      await apiFetch(`/api/pages/${page.id}/suggestions/${suggestion.id}/reject`, {
        method: 'POST',
      })
      setEditingId(null)
      await reload()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not reject')
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <p className="text-sm text-muted-foreground">
          Mining reads this page's past messages and drafts answers for the questions that
          keep coming back. Nothing reaches the knowledge base until you approve it.
        </p>
        <Button onClick={mine} disabled={mining} className="shrink-0">
          {mining ? 'Mining…' : 'Mine conversations'}
        </Button>
      </div>

      {error && <ErrorAlert>{error}</ErrorAlert>}
      {notice && <InfoNote>{notice}</InfoNote>}

      {loading ? (
        <LoadingNote />
      ) : suggestions.length === 0 ? (
        <EmptyState>
          Nothing to review. Run mining after the page has collected some conversations.
        </EmptyState>
      ) : (
        <ul className="space-y-3">
          {suggestions.map((suggestion) => (
            <li key={suggestion.id}>
              <Card>
                <CardBody className="space-y-3">
                  {editingId === suggestion.id ? (
                    <div className="space-y-3">
                      <div className="space-y-1.5">
                        <Label htmlFor={`question-${suggestion.id}`}>Question</Label>
                        <Input
                          id={`question-${suggestion.id}`}
                          value={draftQuestion}
                          onChange={(event) => setDraftQuestion(event.target.value)}
                        />
                      </div>
                      <div className="space-y-1.5">
                        <Label htmlFor={`answer-${suggestion.id}`}>Answer</Label>
                        <Textarea
                          id={`answer-${suggestion.id}`}
                          rows={5}
                          value={draftAnswer}
                          onChange={(event) => setDraftAnswer(event.target.value)}
                        />
                      </div>
                      <div className="flex gap-2">
                        <Button variant="success" onClick={() => approve(suggestion, true)}>
                          Approve with edits
                        </Button>
                        <Button variant="outline" onClick={() => setEditingId(null)}>
                          Cancel
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <div className="flex items-start justify-between gap-4">
                        <p className="font-medium">{suggestion.question}</p>
                        <Badge variant="accent" className="shrink-0">
                          seen {suggestion.occurrences}×
                        </Badge>
                      </div>
                      <p className="whitespace-pre-wrap text-sm text-muted-foreground">
                        {suggestion.answer}
                      </p>
                      <div className="flex gap-2">
                        <Button variant="success" onClick={() => approve(suggestion, false)}>
                          Approve
                        </Button>
                        <Button variant="outline" onClick={() => startEdit(suggestion)}>
                          Edit
                        </Button>
                        <Button variant="destructive" onClick={() => reject(suggestion)}>
                          Reject
                        </Button>
                      </div>
                    </>
                  )}
                </CardBody>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
