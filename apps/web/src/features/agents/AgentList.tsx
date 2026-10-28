import type { Schemas } from '@agent-team/api-client'
import { useState } from 'react'
import { useApi } from '../../api/context'
import { unwrap } from '../../api/errors'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { DeleteButton } from '../../components/layout'
import { byId } from '../../lib/format'

type Agent = Schemas['AgentWorker']

type AgentListProps = {
  agents: Agent[]
  roles: Schemas['AgentRole'][]
  /** Extra detail per agent, e.g. its project in the list of all agents. */
  describe?: (agent: Agent) => string | undefined
  onOpen: (agent: Agent) => void
  onDeleted: () => void
}

/** Agents with their role and context, used both in the Agents tab and inside a project. */
export function AgentList({ agents, roles, describe, onOpen, onDeleted }: AgentListProps) {
  const api = useApi()
  const rolesById = byId(roles)
  const [deleting, setDeleting] = useState<Agent | null>(null)

  return (
    <>
      <ul className="rows">
        {agents.map((agent) => (
          <li key={agent.id} className="row">
            <button type="button" className="row-main row-button" onClick={() => onOpen(agent)}>
              <span className="row-title">{agent.name}</span>
              <span className="row-desc">
                {[rolesById.get(agent.role)?.name, describe?.(agent)].filter(Boolean).join(' in ')}
              </span>
            </button>
            <span className="row-meta">{agent.context_scope ? 'Custom context' : 'Default context'}</span>
            <DeleteButton label={`Delete ${agent.name}`} onClick={() => setDeleting(agent)} />
          </li>
        ))}
      </ul>
      {deleting && (
        <ConfirmDialog
          title={`Delete ${deleting.name}?`}
          confirmLabel="Delete agent"
          onConfirm={async () => {
            await unwrap(api.DELETE('/api/agent/{agent_id}', { params: { path: { agent_id: deleting.id } } }))
            onDeleted()
          }}
          onClose={() => setDeleting(null)}
        >
          <p>Its running sessions are stopped and it is archived in Anthropic. This can't be undone.</p>
        </ConfirmDialog>
      )}
    </>
  )
}
