import type { Schemas } from '@agent-team/api-client'
import { useId } from 'react'

type ResourceChecklistProps = {
  resources: Schemas['Resource'][]
  selected: Set<string>
  onChange: (selected: Set<string>) => void
  /** Accessible name of the group, e.g. "Resources in Ada's context". */
  label: string
}

/** Checkboxes for picking resources, with shortcuts to pick all or none. Controlled: the parent owns `selected`. */
export function ResourceChecklist({ resources, selected, onChange, label }: ResourceChecklistProps) {
  const labelId = useId()

  function toggle(id: string) {
    // State is never changed in place: build a new Set so React sees that it changed.
    const next = new Set(selected)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    onChange(next)
  }

  return (
    <fieldset className="checklist" aria-labelledby={labelId}>
      <div className="checklist-toolbar">
        <span id={labelId} className="field-label">
          {label}
        </span>
        <span className="muted">
          {selected.size} of {resources.length} selected
        </span>
        <button type="button" className="button-quiet" onClick={() => onChange(new Set(resources.map((r) => r.id)))}>
          All
        </button>
        <button type="button" className="button-quiet" onClick={() => onChange(new Set())}>
          None
        </button>
      </div>
      <ul>
        {resources.map((resource) => (
          <li key={resource.id}>
            <label className="check">
              <input type="checkbox" checked={selected.has(resource.id)} onChange={() => toggle(resource.id)} />
              <span className="check-name">{resource.name}</span>
              <span className="tag">{resource.type}</span>
            </label>
          </li>
        ))}
      </ul>
    </fieldset>
  )
}
