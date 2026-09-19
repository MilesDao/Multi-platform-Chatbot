import { useState, type FormEvent } from 'react'

import TestChatPanel from '../../components/TestChatPanel'
import { ErrorAlert, SuccessNote } from '../../components/ui/alert'
import { Button } from '../../components/ui/button'
import { Card, CardBody } from '../../components/ui/card'
import { Input, Textarea } from '../../components/ui/input'
import { Label } from '../../components/ui/label'
import { apiFetch } from '../../lib/api'
import type { PageSummary } from '../../lib/types'

export default function InstructionsTab({
  page,
  reloadPage,
}: {
  page: PageSummary
  reloadPage: () => Promise<void>
}) {
  const [systemPrompt, setSystemPrompt] = useState(page.system_prompt)
  const [closingMessage, setClosingMessage] = useState(page.closing_message)
  const [llmModel, setLlmModel] = useState(page.llm_model)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const [busy, setBusy] = useState(false)

  async function save(event: FormEvent) {
    event.preventDefault()
    setError('')
    setSaved(false)
    setBusy(true)
    try {
      await apiFetch(`/api/pages/${page.id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          system_prompt: systemPrompt,
          closing_message: closingMessage,
          llm_model: llmModel,
        }),
      })
      setSaved(true)
      await reloadPage()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not save the instructions')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardBody>
          <form onSubmit={save} className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="system-prompt">Instructions</Label>
              <p className="text-xs text-muted-foreground">
                How this page should answer: tone, persona, rules. Leave empty to use the
                default admissions counsellor persona.
              </p>
              <Textarea
                id="system-prompt"
                rows={12}
                value={systemPrompt}
                onChange={(event) => setSystemPrompt(event.target.value)}
                className="font-mono"
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="llm-model">Model override</Label>
              <Input
                id="llm-model"
                value={llmModel}
                onChange={(event) => setLlmModel(event.target.value)}
                placeholder="google/gemini-2.5-flash"
                className="font-mono"
              />
              <p className="text-xs text-muted-foreground">
                An OpenRouter model id. Leave empty to use the server default.
              </p>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="closing-message">Closing message</Label>
              <p className="text-xs text-muted-foreground">
                Appended after every answer to hand the student off to a human — a hotline
                number or "gọi cho trường để được tư vấn thêm nhé!". Leave empty to append
                nothing.
              </p>
              <Textarea
                id="closing-message"
                rows={2}
                value={closingMessage}
                onChange={(event) => setClosingMessage(event.target.value)}
              />
            </div>

            {error && <ErrorAlert>{error}</ErrorAlert>}
            {saved && <SuccessNote>Saved.</SuccessNote>}

            <Button type="submit" disabled={busy}>
              Save instructions
            </Button>
          </form>
        </CardBody>
      </Card>

      <TestChatPanel page={page} />
    </div>
  )
}
