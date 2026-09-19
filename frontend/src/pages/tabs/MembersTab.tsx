import { useCallback, useEffect, useState, type FormEvent } from 'react'

import { ErrorAlert } from '../../components/ui/alert'
import { Button } from '../../components/ui/button'
import { Card, CardBody } from '../../components/ui/card'
import { LoadingNote } from '../../components/ui/empty-state'
import { Label } from '../../components/ui/label'
import { Select } from '../../components/ui/select'
import { apiFetch } from '../../lib/api'
import type { Member, PageSummary, User } from '../../lib/types'

const ROLES = ['viewer', 'editor', 'owner'] as const

export default function MembersTab({ page }: { page: PageSummary }) {
  const [members, setMembers] = useState<Member[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [selectedUserId, setSelectedUserId] = useState('')
  const [newRole, setNewRole] = useState<string>('viewer')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      setMembers(await apiFetch<Member[]>(`/api/pages/${page.id}/members`))
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load members')
    } finally {
      setLoading(false)
    }
  }, [page.id])

  useEffect(() => {
    void reload()
    // Only admins may list users; members simply get no picker.
    apiFetch<User[]>('/api/users')
      .then(setUsers)
      .catch(() => setUsers([]))
  }, [reload])

  async function setRole(userId: number, role: string) {
    setError('')
    try {
      await apiFetch(`/api/pages/${page.id}/members`, {
        method: 'PUT',
        body: JSON.stringify({ user_id: userId, role }),
      })
      await reload()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not update the member')
    }
  }

  async function add(event: FormEvent) {
    event.preventDefault()
    if (!selectedUserId) return
    await setRole(Number(selectedUserId), newRole)
    setSelectedUserId('')
  }

  async function remove(userId: number) {
    setError('')
    try {
      await apiFetch(`/api/pages/${page.id}/members/${userId}`, { method: 'DELETE' })
      await reload()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not remove the member')
    }
  }

  const candidates = users.filter(
    (user) => !members.some((member) => member.user_id === user.id),
  )

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Viewers read. Editors change knowledge, instructions and the review queue. Owners
        also manage page settings and members.
      </p>

      {error && <ErrorAlert>{error}</ErrorAlert>}

      <Card>
        <CardBody>
          <form onSubmit={add} className="flex flex-wrap items-end gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="add-user">Add user</Label>
              <Select
                id="add-user"
                value={selectedUserId}
                onChange={(event) => setSelectedUserId(event.target.value)}
              >
                <option value="">Select a user…</option>
                {candidates.map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.email}
                  </option>
                ))}
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="new-member-role">New member role</Label>
              <Select
                id="new-member-role"
                value={newRole}
                onChange={(event) => setNewRole(event.target.value)}
              >
                {ROLES.map((role) => (
                  <option key={role} value={role}>
                    {role}
                  </option>
                ))}
              </Select>
            </div>
            <Button type="submit">Add</Button>
          </form>
        </CardBody>
      </Card>

      {loading ? (
        <LoadingNote />
      ) : (
        <ul className="space-y-2">
          {members.map((member) => (
            <li key={member.user_id}>
              <Card>
                <CardBody className="flex items-center justify-between gap-4 py-3">
                  <span className="text-sm">{member.email}</span>
                  <div className="flex items-center gap-2">
                    <Label className="sr-only" htmlFor={`role-${member.user_id}`}>
                      Role for {member.email}
                    </Label>
                    <Select
                      id={`role-${member.user_id}`}
                      value={member.role}
                      onChange={(event) => setRole(member.user_id, event.target.value)}
                      className="px-2 py-1 text-xs"
                    >
                      {ROLES.map((role) => (
                        <option key={role} value={role}>
                          {role}
                        </option>
                      ))}
                    </Select>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => remove(member.user_id)}
                    >
                      Remove
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
