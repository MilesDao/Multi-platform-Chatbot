import { useEffect, useState, type FormEvent } from 'react'

import { Button } from '../components/ui/button'
import { ErrorAlert } from '../components/ui/alert'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { apiFetch } from '../lib/api'
import { useAuth } from '../lib/auth'

export default function LoginPage() {
  const { login, bootstrap } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [canBootstrap, setCanBootstrap] = useState(false)

  useEffect(() => {
    apiFetch<{ available: boolean }>('/api/auth/bootstrap-available')
      .then((result) => setCanBootstrap(result.available))
      .catch(() => setCanBootstrap(false))
  }, [])

  async function submit(event: FormEvent, mode: 'login' | 'bootstrap') {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      if (mode === 'login') await login(email, password)
      else await bootstrap(email, password)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Something went wrong')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-background px-4">
      <div
        aria-hidden
        className="pointer-events-none absolute -top-40 left-1/2 h-96 w-[42rem] -translate-x-1/2 rounded-full bg-primary/10 blur-3xl"
      />
      <form
        onSubmit={(event) => submit(event, 'login')}
        className="relative w-full max-w-sm space-y-5 rounded-2xl border border-border bg-card p-8 shadow-xl shadow-black/5"
      >
        <div className="space-y-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-sm font-bold text-primary-foreground">
            H
          </div>
          <div>
            <h1 className="text-xl font-semibold tracking-tight">Hateco Chatbot Console</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {canBootstrap ? 'No account exists yet.' : 'Sign in to manage your pages.'}
            </p>
          </div>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </div>

        {error && <ErrorAlert>{error}</ErrorAlert>}

        <Button type="submit" disabled={busy} className="w-full">
          {busy ? 'Signing in…' : 'Sign in'}
        </Button>

        {canBootstrap && (
          <Button
            type="button"
            variant="outline"
            disabled={busy}
            onClick={(event) => submit(event, 'bootstrap')}
            className="w-full"
          >
            Create the first admin
          </Button>
        )}
      </form>
    </div>
  )
}
