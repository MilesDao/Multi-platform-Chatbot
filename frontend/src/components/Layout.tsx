import { Link, NavLink, Outlet } from 'react-router-dom'

import ThemeToggle from './ThemeToggle'
import { Button } from './ui/button'
import { useAuth } from '../lib/auth'

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `text-sm transition-colors ${
    isActive ? 'font-medium text-foreground' : 'text-muted-foreground hover:text-foreground'
  }`

export default function Layout() {
  const { user, logout } = useAuth()

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-10 border-b border-border bg-card/80 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center gap-6 px-4 py-3">
          <Link to="/pages" className="flex items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary text-xs font-bold text-primary-foreground">
              H
            </span>
            <span className="text-sm font-semibold tracking-tight">Hateco Console</span>
          </Link>
          <nav className="flex items-center gap-4">
            <NavLink to="/pages" className={linkClass}>
              Pages
            </NavLink>
            {user?.role === 'admin' && (
              <NavLink to="/users" className={linkClass}>
                Users
              </NavLink>
            )}
          </nav>
          <div className="ml-auto flex items-center gap-3">
            <ThemeToggle />
            <span className="hidden text-xs text-muted-foreground sm:inline">{user?.email}</span>
            <Button variant="outline" size="sm" onClick={logout}>
              Sign out
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  )
}
