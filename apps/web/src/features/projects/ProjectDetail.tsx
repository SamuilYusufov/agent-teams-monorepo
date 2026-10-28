import type { ApiClient, Schemas } from '@agent-team/api-client'
import { useState } from 'react'
import { useApi } from '../../api/context'
import { unwrap } from '../../api/errors'
import { useAction } from '../../api/useAction'
import { useQuery } from '../../api/useQuery'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { FormModal } from '../../components/FormModal'
import { ResourceChecklist } from '../../components/ResourceChecklist'
import { BackIcon, CloseIcon, PlusIcon, SearchIcon } from '../../components/icons'
import { AddButton, Async, EmptyState, SectionHeader } from '../../components/layout'
import { AgentContextDrawer } from '../agents/AgentContextDrawer'
import { AgentFormModal } from '../agents/AgentFormModal'
import { AgentList } from '../agents/AgentList'
import { ResourceFormModal } from '../resources/ResourceFormModal'

async function loadProject(api: ApiClient, projectId: string) {
  const project = await unwrap(api.GET('/api/project/{project_id}', { params: { path: { project_id: projectId } } }))
  // These requests don't depend on each other, so send them at the same time instead of one after another.
  const [roles, agents, resources, library] = await Promise.all([
    unwrap(api.GET('/api/role')),
    unwrap(api.GET('/api/agent', { params: { query: { project_id: projectId } } })),
    unwrap(api.GET('/api/scope/{scope_id}/resources', { params: { path: { scope_id: project.main_scope } } })),
    unwrap(api.GET('/api/resource')),
  ])
  return { project, roles, agents, resources, library }
}

type ProjectData = Awaited<ReturnType<typeof loadProject>>

/**
 * One project: its roles, agents and resources. The page loads everything in one query and reloads it after
 * every change, which keeps all sections consistent without any cache logic.
 */
export function ProjectDetail({ projectId, onBack }: { projectId: string; onBack: () => void }) {
  const api = useApi()
  const data = useQuery(() => loadProject(api, projectId), [api, projectId])

  return (
    <>
      <button type="button" className="back" onClick={onBack}>
        <BackIcon />
        All projects
      </button>
      <Async query={data}>
        {(loaded) => (
          <>
            <header className="page-header">
              <div>
                <h1>{loaded.project.name}</h1>
                <p className="lede">{loaded.project.description}</p>
              </div>
            </header>
            <ProjectRoles {...loaded} onChange={data.reload} />
            <ProjectAgents {...loaded} onChange={data.reload} />
            <ProjectResources {...loaded} onChange={data.reload} />
          </>
        )}
      </Async>
    </>
  )
}

type SectionProps = ProjectData & { onChange: () => void }

function ProjectRoles({ project, roles, onChange }: SectionProps) {
  const api = useApi()
  const { run, error } = useAction()
  const [search, setSearch] = useState('')

  // Derived on every render from props and state instead of kept in state: there is nothing to keep in sync.
  const inProject = roles.filter((role) => project.roles.includes(role.id))
  const query = search.trim().toLowerCase()
  const matches = query
    ? roles.filter(
        (role) =>
          !project.roles.includes(role.id) &&
          (role.name.toLowerCase().includes(query) || role.description.toLowerCase().includes(query)),
      )
    : []
  const path = (roleId: string) => ({ params: { path: { project_id: project.id, role_id: roleId } } })

  async function add(roleId: string) {
    if (await run(() => unwrap(api.PUT('/api/project/{project_id}/roles/{role_id}', path(roleId))))) {
      setSearch('')
      onChange()
    }
  }

  async function remove(roleId: string) {
    if (await run(() => unwrap(api.DELETE('/api/project/{project_id}/roles/{role_id}', path(roleId))))) onChange()
  }

  return (
    <section className="section">
      <SectionHeader title="Roles" description="The roles agents in this project can have." />
      {inProject.length > 0 ? (
        <ul className="chips">
          {inProject.map((role) => (
            <li key={role.id} className="chip">
              {role.name}
              <button
                type="button"
                className="chip-remove"
                aria-label={`Remove ${role.name} from ${project.name}`}
                title="Remove from project"
                onClick={() => remove(role.id)}
              >
                <CloseIcon size={14} />
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">No roles yet. Search for one below to add it.</p>
      )}

      <div className="search">
        <label className="search-box">
          <SearchIcon />
          <span className="visually-hidden">Search roles to add</span>
          <input
            type="search"
            placeholder="Search roles to add"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
        {query && (
          // aria-live: screen readers announce the results as they change while typing.
          <div aria-live="polite">
            {matches.length > 0 ? (
              <ul className="search-results">
                {matches.map((role) => (
                  <li key={role.id}>
                    <button type="button" className="search-result" onClick={() => add(role.id)}>
                      <span>
                        <span className="row-title">{role.name}</span>
                        <span className="row-desc">{role.description}</span>
                      </span>
                      <span className="search-add">
                        <PlusIcon size={16} />
                        Add
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted search-empty">
                No roles match “{search.trim()}”. Create new roles in the Roles tab.
              </p>
            )}
          </div>
        )}
      </div>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
    </section>
  )
}

function ProjectAgents({ project, roles, agents, onChange }: SectionProps) {
  const [creating, setCreating] = useState(false)
  const [opened, setOpened] = useState<Schemas['AgentWorker'] | null>(null)
  const hasRoles = project.roles.length > 0

  return (
    <section className="section">
      <SectionHeader
        title="Agents"
        description={hasRoles ? 'Open an agent to choose which resources it sees.' : 'Add a role first: every agent needs one.'}
        action={<AddButton label="New agent" onClick={() => setCreating(true)} disabled={!hasRoles} />}
      />
      {agents.length === 0 ? (
        <p className="muted">No agents yet.</p>
      ) : (
        <AgentList agents={agents} roles={roles} onOpen={setOpened} onDeleted={onChange} />
      )}
      {creating && (
        <AgentFormModal
          projects={[project]}
          roles={roles}
          projectId={project.id}
          onCreated={onChange}
          onClose={() => setCreating(false)}
        />
      )}
      {opened && <AgentContextDrawer agent={opened} onSaved={onChange} onClose={() => setOpened(null)} />}
    </section>
  )
}

function ProjectResources({ project, resources, library, onChange }: SectionProps) {
  const api = useApi()
  const [adding, setAdding] = useState(false)
  const [creating, setCreating] = useState(false)
  const [removing, setRemoving] = useState<Schemas['Resource'] | null>(null)
  const available = library.filter((resource) => !resources.some((r) => r.id === resource.id))

  function addToProject(resourceIds: string[]) {
    return Promise.all(
      resourceIds.map((id) =>
        unwrap(
          api.PUT('/api/scope/{scope_id}/resources/{resource_id}', {
            params: { path: { scope_id: project.main_scope, resource_id: id } },
          }),
        ),
      ),
    )
  }

  return (
    <section className="section">
      <SectionHeader
        title="Resources"
        description="Everything agents in this project can be given as context."
        action={
          <>
            <button type="button" className="button-secondary" onClick={() => setAdding(true)}>
              Add existing
            </button>
            <AddButton label="New resource" onClick={() => setCreating(true)} />
          </>
        }
      />
      {resources.length === 0 ? (
        <p className="muted">No resources yet.</p>
      ) : (
        <ul className="rows">
          {resources.map((resource) => (
            <li key={resource.id} className="row">
              <div className="row-main">
                <span className="row-title">{resource.name}</span>
              </div>
              <span className="tag">{resource.type}</span>
              <button
                type="button"
                className="icon-button"
                aria-label={`Remove ${resource.name} from ${project.name}`}
                title="Remove from project"
                onClick={() => setRemoving(resource)}
              >
                <CloseIcon />
              </button>
            </li>
          ))}
        </ul>
      )}

      {adding && (
        <AddResourcesModal
          available={available}
          onAdd={async (ids) => {
            await addToProject(ids)
            onChange()
          }}
          onClose={() => setAdding(false)}
        />
      )}
      {creating && (
        <ResourceFormModal
          submitLabel="Create and add"
          onCreated={async (resource) => {
            await addToProject([resource.id])
            onChange()
          }}
          onClose={() => setCreating(false)}
        />
      )}
      {removing && (
        <ConfirmDialog
          title={`Remove ${removing.name} from ${project.name}?`}
          confirmLabel="Remove from project"
          onConfirm={async () => {
            await unwrap(
              api.DELETE('/api/scope/{scope_id}/resources/{resource_id}', {
                params: { path: { scope_id: project.main_scope, resource_id: removing.id } },
              }),
            )
            onChange()
          }}
          onClose={() => setRemoving(null)}
        >
          <p>Agents in this project lose it from their context too. The resource itself is not deleted.</p>
        </ConfirmDialog>
      )}
    </section>
  )
}

function AddResourcesModal({
  available,
  onAdd,
  onClose,
}: {
  available: Schemas['Resource'][]
  onAdd: (ids: string[]) => Promise<unknown>
  onClose: () => void
}) {
  const [selected, setSelected] = useState(new Set<string>())

  return (
    <FormModal
      title="Add resources"
      submitLabel={selected.size > 1 ? `Add ${selected.size} resources` : 'Add resource'}
      submitDisabled={selected.size === 0}
      onSubmit={() => onAdd([...selected])}
      onClose={onClose}
    >
      {available.length === 0 ? (
        <EmptyState>
          <p>Every resource is already in this project. Use “New resource” to create another.</p>
        </EmptyState>
      ) : (
        <ResourceChecklist label="Resources" resources={available} selected={selected} onChange={setSelected} />
      )}
    </FormModal>
  )
}
