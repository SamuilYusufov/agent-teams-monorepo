// Small building blocks shared by every tab, so the tabs look and behave the same.
import type { ReactNode } from 'react'
import type { Query } from '../api/useQuery'
import { PlusIcon, TrashIcon } from './icons'

export function PageHeader({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return (
    <header className="page-header">
      <div>
        <h1>{title}</h1>
        <p className="lede">{description}</p>
      </div>
      {action}
    </header>
  )
}

export function SectionHeader({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return (
    <header className="section-header">
      <div>
        <h2>{title}</h2>
        {description && <p className="muted">{description}</p>}
      </div>
      {action && <div className="section-actions">{action}</div>}
    </header>
  )
}

/** The "+" button that opens a create form. */
export function AddButton({ label, onClick, disabled }: { label: string; onClick: () => void; disabled?: boolean }) {
  return (
    <button type="button" className="button" onClick={onClick} disabled={disabled}>
      <PlusIcon />
      {label}
    </button>
  )
}

/** An icon-only delete button. `label` names what it deletes, for screen readers and as a tooltip. */
export function DeleteButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button type="button" className="icon-button icon-button-danger" aria-label={label} title={label} onClick={onClick}>
      <TrashIcon />
    </button>
  )
}

export function EmptyState({ children }: { children: ReactNode }) {
  return <div className="empty">{children}</div>
}

/** A labelled form field. Wrapping the input in the <label> connects the two without IDs. */
export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {children}
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  )
}

/** Shows loading and error states of a query, and its data once loaded. */
export function Async<T>({ query, children }: { query: Query<T>; children: (data: T) => ReactNode }) {
  if (query.status === 'loading') return <p className="muted">Loading…</p>
  if (query.status === 'error')
    return (
      <div role="alert" className="error error-block">
        <p>{query.message}</p>
        <button type="button" className="button-quiet" onClick={query.reload}>
          Try again
        </button>
      </div>
    )
  return children(query.data)
}
