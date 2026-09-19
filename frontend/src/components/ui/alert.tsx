import type { HTMLAttributes } from 'react'

import { cn } from '../../lib/cn'

export function ErrorAlert({ className, ...props }: HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p
      role="alert"
      className={cn(
        'rounded-md border border-destructive/20 bg-destructive-muted px-3 py-2 text-sm text-destructive',
        className,
      )}
      {...props}
    />
  )
}

export function SuccessNote({ className, ...props }: HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p
      className={cn(
        'rounded-md border border-success/20 bg-success-muted px-3 py-2 text-sm text-success',
        className,
      )}
      {...props}
    />
  )
}

export function InfoNote({ className, ...props }: HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p className={cn('rounded-md bg-muted px-3 py-2 text-sm text-foreground', className)} {...props} />
  )
}
