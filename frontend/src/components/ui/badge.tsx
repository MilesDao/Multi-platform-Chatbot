import type { HTMLAttributes } from 'react'

import { cn } from '../../lib/cn'

export type BadgeVariant = 'neutral' | 'success' | 'warning' | 'destructive' | 'accent'

const VARIANT_CLASSES: Record<BadgeVariant, string> = {
  neutral: 'bg-secondary text-secondary-foreground',
  success: 'bg-success-muted text-success',
  warning: 'bg-warning-muted text-warning',
  destructive: 'bg-destructive-muted text-destructive',
  accent: 'bg-accent text-accent-foreground',
}

export function Badge({
  className,
  variant = 'neutral',
  ...props
}: HTMLAttributes<HTMLSpanElement> & { variant?: BadgeVariant }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
        VARIANT_CLASSES[variant],
        className,
      )}
      {...props}
    />
  )
}
