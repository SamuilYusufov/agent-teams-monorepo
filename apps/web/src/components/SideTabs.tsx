import { useRef, type KeyboardEvent } from 'react'

export type Tab<Id extends string> = { id: Id; label: string }

type SideTabsProps<Id extends string> = {
  tabs: readonly Tab<Id>[]
  active: Id
  onChange: (id: Id) => void
}

const STEPS: Record<string, number> = { ArrowDown: 1, ArrowRight: 1, ArrowUp: -1, ArrowLeft: -1 }

/**
 * The side rail of section tabs, following the WAI-ARIA tabs pattern: Tab moves focus into the tab list and on
 * to the panel, arrow keys move between tabs, Home and End jump to the first and last tab.
 */
export function SideTabs<Id extends string>({ tabs, active, onChange }: SideTabsProps<Id>) {
  const buttons = useRef(new Map<Id, HTMLButtonElement>())

  function handleKeyDown(event: KeyboardEvent, index: number) {
    let next: number
    if (event.key in STEPS) next = (index + STEPS[event.key] + tabs.length) % tabs.length
    else if (event.key === 'Home') next = 0
    else if (event.key === 'End') next = tabs.length - 1
    else return
    event.preventDefault() // the arrow keys would otherwise also scroll the page
    onChange(tabs[next].id)
    buttons.current.get(tabs[next].id)?.focus()
  }

  return (
    <nav className="rail" aria-label="Sections">
      <p className="brand">Agent team</p>
      <div role="tablist" aria-orientation="vertical" className="tabs">
        {tabs.map((tab, index) => (
          <button
            key={tab.id}
            ref={(element) => {
              if (element) buttons.current.set(tab.id, element)
              else buttons.current.delete(tab.id)
            }}
            type="button"
            role="tab"
            id={`tab-${tab.id}`}
            aria-selected={tab.id === active}
            aria-controls={`panel-${tab.id}`}
            // Only the active tab is a Tab stop; the arrow keys reach the others.
            tabIndex={tab.id === active ? 0 : -1}
            className="tab"
            onClick={() => onChange(tab.id)}
            onKeyDown={(event) => handleKeyDown(event, index)}
          >
            {tab.label}
          </button>
        ))}
      </div>
    </nav>
  )
}
