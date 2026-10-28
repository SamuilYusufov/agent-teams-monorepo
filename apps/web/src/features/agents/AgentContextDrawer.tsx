import type { ApiClient, Schemas } from '@agent-team/api-client'
import { useState } from 'react'
import { useApi } from '../../api/context'
import { unwrap } from '../../api/errors'
import { setScopeResources } from '../../api/scopes'
import { useAction } from '../../api/useAction'
import { useQuery } from '../../api/useQuery'
import { Modal } from '../../components/Modal'
import { ResourceChecklist } from '../../components/ResourceChecklist'
import { Async, EmptyState } from '../../components/layout'

type Agent = Schemas['AgentWorker']

/**
 * Lets the user pick which of the project's resources an agent sees.
 *
 * In the API an agent's context is a context scope: either the default (the resources its project and role
 * share) or one of the project's scopes it is pinned to. Here the user just ticks resources; saving takes care of
 * the scopes.
 */
export function AgentContextDrawer({ agent, onClose, onSaved }: { agent: Agent; onClose: () => void; onSaved: () => void }) {
  const api = useApi()
  const data = useQuery(() => loadContext(api, agent), [api, agent])

  return (
    <Modal title={agent.name} onClose={onClose} variant="drawer">
      <Async query={data}>
        {(context) => <ContextForm agent={agent} {...context} onSaved={onSaved} onClose={onClose} />}
      </Async>
    </Modal>
  )
}

async function loadContext(api: ApiClient, agent: Agent) {
  const project = await unwrap(api.GET('/api/project/{project_id}', { params: { path: { project_id: agent.project } } }))
  const [role, resources, teammates] = await Promise.all([
    unwrap(api.GET('/api/role/{role_id}', { params: { path: { role_id: agent.role } } })),
    unwrap(api.GET('/api/scope/{scope_id}/resources', { params: { path: { scope_id: project.main_scope } } })),
    unwrap(api.GET('/api/agent', { params: { query: { project_id: agent.project } } })),
  ])
  // Without its own scope, the agent sees the resources that are both in the project and in its role's scope,
  // the same rule the API applies.
  const scopeId = agent.context_scope ?? role.context_scope
  const scope = await unwrap(api.GET('/api/scope/{scope_id}', { params: { path: { scope_id: scopeId } } }))
  const selected = resources.filter((r) => scope.resources.includes(r.id)).map((r) => r.id)
  return { project, role, resources, teammates, selected }
}

type ContextFormProps = Awaited<ReturnType<typeof loadContext>> & {
  agent: Agent
  onSaved: () => void
  onClose: () => void
}

function ContextForm({ agent, project, role, resources, teammates, selected: initial, onSaved, onClose }: ContextFormProps) {
  const api = useApi()
  // Mounted only once the data has loaded, so the initial selection can seed the state directly.
  const [selected, setSelected] = useState(() => new Set(initial))
  const { run, busy, error } = useAction()

  const pinned = agent.context_scope
  // A scope only this agent uses can be edited in place. The main scope, or one shared with teammates, can't:
  // changing it would change what other agents see. `ownScope` is the ID of the agent's own scope, if it has one.
  const ownScope =
    pinned !== null &&
    pinned !== project.main_scope &&
    teammates.every((teammate) => teammate.id === agent.id || teammate.context_scope !== pinned)
      ? pinned
      : null
  const changed = selected.size !== initial.length || initial.some((id) => !selected.has(id))

  async function save() {
    const wanted = resources.filter((r) => selected.has(r.id)).map((r) => r.id)
    const saved = await run(async () => {
      if (ownScope) {
        await setScopeResources(api, ownScope, initial, wanted)
      } else {
        const scope = await unwrap(
          api.POST('/api/project/{project_id}/scopes', {
            params: { path: { project_id: project.id } },
            body: { resource_ids: wanted },
          }),
        )
        await unwrap(
          api.PUT('/api/agent/{agent_id}/scope', {
            params: { path: { agent_id: agent.id } },
            body: { context_scope: scope.id },
          }),
        )
      }
    })
    if (saved) {
      onSaved()
      onClose()
    }
  }

  async function resetToDefault() {
    const saved = await run(() =>
      ownScope
        ? // Nobody else uses the scope: delete it, and the agent falls back to the default.
          unwrap(api.DELETE('/api/scope/{scope_id}', { params: { path: { scope_id: ownScope } } }))
        : unwrap(
            api.PUT('/api/agent/{agent_id}/scope', {
              params: { path: { agent_id: agent.id } },
              body: { context_scope: null },
            }),
          ),
    )
    if (saved) {
      onSaved()
      onClose()
    }
  }

  return (
    <div className="drawer-content">
      <p className="lede">
        {role.name} in {project.name}
      </p>
      <p className="notice">
        {pinned === null
          ? `Uses the default context: the project's resources that are also in the ${role.name} role.`
          : 'Uses a custom context.'}
      </p>
      {resources.length === 0 ? (
        <EmptyState>
          <p>{project.name} has no resources yet. Add them on the project's page, then pick them here.</p>
        </EmptyState>
      ) : (
        <ResourceChecklist
          label={`Resources ${agent.name} can see`}
          resources={resources}
          selected={selected}
          onChange={setSelected}
        />
      )}
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <div className="form-actions">
        {pinned !== null && (
          <button type="button" className="button-quiet" onClick={resetToDefault} disabled={busy}>
            Reset to default
          </button>
        )}
        <button type="button" className="button" onClick={save} disabled={busy || !changed}>
          {busy ? 'Saving…' : 'Save context'}
        </button>
      </div>
    </div>
  )
}
