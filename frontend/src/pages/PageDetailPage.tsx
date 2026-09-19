import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { Tabs, type TabDefinition } from '../components/Tabs'
import { ErrorAlert } from '../components/ui/alert'
import { Badge } from '../components/ui/badge'
import { LoadingNote } from '../components/ui/empty-state'
import { apiFetch } from '../lib/api'
import type { PageSummary } from '../lib/types'
import ConversationsTab from './tabs/ConversationsTab'
import InstructionsTab from './tabs/InstructionsTab'
import KnowledgeTab from './tabs/KnowledgeTab'
import LearningTab from './tabs/LearningTab'
import MembersTab from './tabs/MembersTab'
import SettingsTab from './tabs/SettingsTab'

const TABS: TabDefinition[] = [
  { id: 'knowledge', label: 'Knowledge' },
  { id: 'instructions', label: 'Instructions' },
  { id: 'conversations', label: 'Conversations' },
  { id: 'learning', label: 'Learning' },
  { id: 'members', label: 'Members' },
  { id: 'settings', label: 'Settings' },
]

export default function PageDetailPage() {
  const { pageId } = useParams()
  const [page, setPage] = useState<PageSummary | null>(null)
  const [error, setError] = useState('')
  const [active, setActive] = useState('knowledge')

  const reloadPage = useCallback(async () => {
    try {
      setPage(await apiFetch<PageSummary>(`/api/pages/${pageId}`))
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load the page')
    }
  }, [pageId])

  useEffect(() => {
    void reloadPage()
  }, [reloadPage])

  if (error) {
    return (
      <div className="space-y-4">
        <ErrorAlert>{error}</ErrorAlert>
        <Link to="/pages" className="text-sm text-primary underline underline-offset-4">
          Back to pages
        </Link>
      </div>
    )
  }

  if (!page) return <LoadingNote />

  return (
    <div className="space-y-6">
      <div>
        <Link to="/pages" className="text-xs text-muted-foreground hover:text-foreground">
          ← Pages
        </Link>
        <div className="mt-1 flex items-center gap-2">
          <h1 className="text-lg font-semibold tracking-tight">{page.name}</h1>
          {!page.is_active && <Badge variant="warning">Inactive</Badge>}
        </div>
        <p className="font-mono text-xs text-muted-foreground">{page.fb_page_id}</p>
      </div>

      <Tabs tabs={TABS} active={active} onChange={setActive} />

      {active === 'knowledge' && <KnowledgeTab page={page} />}
      {active === 'instructions' && <InstructionsTab page={page} reloadPage={reloadPage} />}
      {active === 'conversations' && <ConversationsTab page={page} />}
      {active === 'learning' && <LearningTab page={page} />}
      {active === 'members' && <MembersTab page={page} />}
      {active === 'settings' && <SettingsTab page={page} reloadPage={reloadPage} />}
    </div>
  )
}
