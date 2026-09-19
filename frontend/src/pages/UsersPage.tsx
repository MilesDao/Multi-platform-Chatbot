import { useCallback, useEffect, useState, type FormEvent } from 'react'

import { ErrorAlert } from '../components/ui/alert'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Card, CardBody } from '../components/ui/card'
import { LoadingNote } from '../components/ui/empty-state'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Select } from '../components/ui/select'
import { apiFetch } from '../lib/api'
import type { User } from '../lib/types'

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('member')

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      setUsers(await apiFetch<User[]>('/api/users'))
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load users')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void reload()
  }, [reload])

  async function create(event: FormEvent) {
    event.preventDefault()
    setError('')
    try {
      await apiFetch('/api/users', {
        method: 'POST',
        body: JSON.stringify({ email, password, role }),
      })
      setEmail('')
      setPassword('')
      await reload()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not create the user')
    }
  }

  async function deactivate(user: User) {
    setError('')
    try {
      await apiFetch(`/api/users/${user.id}`, { method: 'DELETE' })
      await reload()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not deactivate the user')
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">Users</h1>
        <p className="text-sm text-muted-foreground">
          Accounts that can sign in to the console. Global admins see and edit every page.
        </p>
      </div>

      <Card>
        <CardBody>
          <form onSubmit={create} className="flex flex-wrap items-end gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="user-email">Email</Label>
              <Input
                id="user-email"
                type="email"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="user-password">Password</Label>
              <Input
                id="user-password"
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="user-role">Global role</Label>
              <Select id="user-role" value={role} onChange={(event) => setRole(event.target.value)}>
                <option value="member">member</option>
                <option value="admin">admin</option>
              </Select>
            </div>
            <Button type="submit">Create user</Button>
          </form>
        </CardBody>
      </Card>

      {error && <ErrorAlert>{error}</ErrorAlert>}

      {loading ? (
        <LoadingNote />
      ) : (
        <ul className="space-y-2">
          {users.map((user) => (
            <li key={user.id}>
              <Card>
                <CardBody className="flex items-center justify-between gap-4 py-3">
                  <div>
                    <p className="text-sm">{user.email}</p>
                    <div className="mt-1 flex items-center gap-2">
                      <Badge variant="accent">{user.role}</Badge>
                      {!user.is_active && <Badge variant="warning">deactivated</Badge>}
                    </div>
                  </div>
                  {user.is_active && (
                    <Button variant="destructive" size="sm" onClick={() => deactivate(user)}>
                      Deactivate
                    </Button>
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
