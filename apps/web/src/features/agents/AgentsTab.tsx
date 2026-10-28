import type { Schemas } from '@agent-team/api-client'
import { useState } from 'react'
import { useApi } from '../../api/context'
import { unwrap } from '../../api/errors'
import { useQuery } from '../../api/useQuery'
import { AddButton, Async, EmptyState, PageHeader } from '../../components/layout'
import { byId } from '../../lib/format'
import { AgentContextDrawer } from './AgentContextDrawer'
import { AgentFormModal } from './AgentFormModal'
import { AgentList } from './AgentList'

export function AgentsTab() {
  const api = useApi()
  const data = useQuery(async () => {
    const [agents, projects, roles] = await Promise.all([
      unwrap(api.GET('/api/agent')),
      unwrap(api.GET('/api/project')),
      unwrap(api.GET('/api/role')),
    ])
    return { agents, projects, roles }
  }, [api])
  const [creating, setCreating] = useState(false)
  const [opened, setOpened] = useState<Schemas['AgentWorker'] | null>(null)

  return (
    <>
      <PageHeader
        title="Agents"
        description="Every agent works in one project with one role. Open an agent to choose what it sees."
        action={<AddButton label="New agent" onClick={() => setCreating(true)} />}
      />
      <Async query={data}>
        {({ agents, projects, roles }) => {
          const projectsById = byId(projects)
          return agents.length === 0 ? (
            <EmptyState>
              <p>No agents yet.</p>
              <AddButton label="Create the first agent" onClick={() => setCreating(true)} />
            </EmptyState>
          ) : (
            <AgentList
              agents={agents}
              roles={roles}
              describe={(agent) => projectsById.get(agent.project)?.name}
              onOpen={setOpened}
              onDeleted={data.reload}
            />
          )
        }}
      </Async>

      {creating && data.status === 'loaded' && (
        <AgentFormModal
          projects={data.data.projects}
          roles={data.data.roles}
          onCreated={data.reload}
          onClose={() => setCreating(false)}
        />
      )}
      {opened && <AgentContextDrawer agent={opened} onSaved={data.reload} onClose={() => setOpened(null)} />}
    </>
  )
}
