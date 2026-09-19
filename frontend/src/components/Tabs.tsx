import { cn } from '../lib/cn'

export interface TabDefinition {
  id: string
  label: string
}

export function Tabs({
  tabs,
  active,
  onChange,
}: {
  tabs: TabDefinition[]
  active: string
  onChange: (id: string) => void
}) {
  return (
    <div role="tablist" className="flex gap-1 overflow-x-auto border-b border-border">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          role="tab"
          type="button"
          aria-selected={active === tab.id}
          onClick={() => onChange(tab.id)}
          className={cn(
            '-mb-px shrink-0 border-b-2 px-3 py-2 text-sm transition-colors',
            active === tab.id
              ? 'border-primary font-medium text-foreground'
              : 'border-transparent text-muted-foreground hover:text-foreground',
          )}
        >
          {tab.label}
        </button>
      ))}
    </div>
  )
}
