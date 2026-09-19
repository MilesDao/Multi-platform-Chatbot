import { useState, type FormEvent } from 'react'

import { ErrorAlert } from './ui/alert'
import { Button } from './ui/button'
import { Card, CardBody } from './ui/card'
import { Label } from './ui/label'
import { Textarea } from './ui/input'
import { apiFetch } from '../lib/api'
import type { PageSummary } from '../lib/types'

interface TestChatResult {
  answer: string
  context: string[]
}

export default function TestChatPanel({ page }: { page: PageSummary }) {
  const [message, setMessage] = useState('')
  const [result, setResult] = useState<TestChatResult | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function send(event: FormEvent) {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      setResult(
        await apiFetch<TestChatResult>(`/api/pages/${page.id}/test-chat`, {
          method: 'POST',
          body: JSON.stringify({ message }),
        }),
      )
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not generate an answer')
      setResult(null)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card>
      <CardBody className="space-y-3">
        <div>
          <h2 className="text-sm font-medium">Test chat</h2>
          <p className="text-xs text-muted-foreground">
            Answers exactly as this page would. Nothing is sent to Facebook and nothing is
            logged as a conversation.
          </p>
        </div>

        <form onSubmit={send} className="space-y-2">
          <Label htmlFor="test-message">Test message</Label>
          <Textarea
            id="test-message"
            required
            rows={3}
            value={message}
            onChange={(event) => setMessage(event.target.value)}
          />
          <Button type="submit" disabled={busy}>
            {busy ? 'Sending…' : 'Send'}
          </Button>
        </form>

        {error && <ErrorAlert>{error}</ErrorAlert>}

        {result && (
          <div className="space-y-3">
            <div className="rounded-md bg-muted p-3">
              <p className="text-xs font-medium text-muted-foreground">Answer</p>
              <p className="mt-1 whitespace-pre-wrap text-sm">{result.answer}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-muted-foreground">Retrieved context</p>
              <ul className="mt-1 space-y-1">
                {result.context.map((chunk, index) => (
                  <li
                    key={index}
                    className="whitespace-pre-wrap rounded-md border border-border p-2 text-xs text-muted-foreground"
                  >
                    {chunk}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </CardBody>
    </Card>
  )
}
