import type { ReactNode } from 'react'

export function EmptyState({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-border bg-muted/40 p-8 text-center text-sm text-muted-foreground">
      {children}
    </div>
  )
}

export function LoadingNote({ children = 'Loading…' }: { children?: ReactNode }) {
  return <p className="text-sm text-muted-foreground">{children}</p>
}
