import type { ApiClient, Schemas } from '@agent-team/api-client'
import { useState } from 'react'
import { useApi } from '../../api/context'
import { unwrap } from '../../api/errors'
import { setScopeResources } from '../../api/scopes'
import { useQuery } from '../../api/useQuery'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { FormModal } from '../../components/FormModal'
import { ResourceChecklist } from '../../components/ResourceChecklist'
import { AddButton, Async, DeleteButton, EmptyState, Field, PageHeader, SectionHeader } from '../../components/layout'
import { byId } from '../../lib/format'

type Resource = Schemas['Resource']

/** A context scope, described by what owns it. */
type ScopeEntry = {
  id: string
  title: string
  description: string
  kind: 'main' | 'custom' | 'role'
  resources: string[]
  /** Resources this scope may contain: anything for main and role scopes, the project's own for custom ones. */
  choices: Resource[]
}

// The API has no "list all scopes" endpoint: every scope belongs to a project or a role, so collect them from there.
async function loadScopes(api: ApiClient) {
  const [projects, roles, agents, library] = await Promise.all([
    unwrap(api.GET('/api/project')),
    unwrap(api.GET('/api/role')),
    unwrap(api.GET('/api/agent')),
    unwrap(api.GET('/api/resource')),
  ])
  const scopeIds = [...projects.flatMap((p) => p.context_scopes), ...roles.map((r) => r.context_scope)]
  const scopes = byId(
    await Promise.all(scopeIds.map((id) => unwrap(api.GET('/api/scope/{scope_id}', { params: { path: { scope_id: id } } })))),
  )
  const resourcesOf = (scopeId: string) => scopes.get(scopeId)?.resources ?? []

  const projectScopes: ScopeEntry[] = projects.flatMap((project) => {
    const mainResources = resourcesOf(project.main_scope)
    const projectLibrary = library.filter((r) => mainResources.includes(r.id))
    // Main scope first: it's the one the others are carved out of.
    const ids = [project.main_scope, ...project.context_scopes.filter((id) => id !== project.main_scope)]
    return ids.map((id): ScopeEntry => {
      if (id === project.main_scope)
        return {
          id,
          title: project.name,
          description: 'Every resource in the project',
          kind: 'main',
          resources: mainResources,
          choices: library,
        }
      const users = agents.filter((agent) => agent.context_scope === id).map((agent) => agent.name)
      return {
        id,
        title: `${project.name}, custom`,
        description: users.length ? `Used by ${users.join(', ')}` : 'Not used by any agent',
        kind: 'custom',
        resources: resourcesOf(id),
        choices: projectLibrary,
      }
    })
  })
  const roleScopes = roles.map(
    (role): ScopeEntry => ({
      id: role.context_scope,
      title: role.name,
      description: 'Default for agents with this role, limited to their project’s resources',
      kind: 'role',
      resources: resourcesOf(role.context_scope),
      choices: library,
    }),
  )
  return { projects, library, projectScopes, roleScopes, scopes }
}

export function ScopesTab() {
  const api = useApi()
  const data = useQuery(() => loadScopes(api), [api])
  const [creating, setCreating] = useState(false)
  const [editing, setEditing] = useState<ScopeEntry | null>(null)
  const [deleting, setDeleting] = useState<ScopeEntry | null>(null)

  return (
    <>
      <PageHeader
        title="Scopes"
        description="A scope is a set of resources. Projects and roles each have one; custom scopes give agents a subset of their project’s resources."
        action={<AddButton label="New scope" onClick={() => setCreating(true)} />}
      />
      <Async query={data}>
        {({ library, projectScopes, roleScopes }) => {
          const names = byId(library)
          const list = (entries: ScopeEntry[]) => (
            <ul className="rows">
              {entries.map((entry) => (
                <li key={entry.id} className="row">
                  <button
                    type="button"
                    className="row-main row-button"
                    onClick={() => setEditing(entry)}
                    aria-label={`Edit resources of ${entry.title}`}
                  >
                    <span className="row-title">{entry.title}</span>
                    <span className="row-desc">{entry.description}</span>
                    <span className="tags">
                      {entry.resources.length === 0 ? (
                        <span className="muted">No resources</span>
                      ) : (
                        entry.resources.map((id) => (
                          <span key={id} className="tag">
                            {names.get(id)?.name ?? 'Unknown resource'}
                          </span>
                        ))
                      )}
                    </span>
                  </button>
                  {/* Main and role scopes are deleted with their project or role, so only custom ones get a button. */}
                  {entry.kind === 'custom' && (
                    <DeleteButton label={`Delete ${entry.title} scope`} onClick={() => setDeleting(entry)} />
                  )}
                </li>
              ))}
            </ul>
          )
          return (
            <>
              <section className="section">
                <SectionHeader title="Project scopes" />
                {projectScopes.length ? list(projectScopes) : <p className="muted">No projects yet.</p>}
              </section>
              <section className="section">
                <SectionHeader title="Role scopes" />
                {roleScopes.length ? list(roleScopes) : <p className="muted">No roles yet.</p>}
              </section>
            </>
          )
        }}
      </Async>

      {creating && data.status === 'loaded' && (
        <NewScopeModal
          projects={data.data.projects}
          library={data.data.library}
          mainResources={(project) => data.data.scopes.get(project.main_scope)?.resources ?? []}
          onCreated={data.reload}
          onClose={() => setCreating(false)}
        />
      )}
      {editing && (
        <EditScopeModal entry={editing} onSaved={data.reload} onClose={() => setEditing(null)} />
      )}
      {deleting && (
        <ConfirmDialog
          title={`Delete this ${deleting.title} scope?`}
          confirmLabel="Delete scope"
          onConfirm={async () => {
            await unwrap(api.DELETE('/api/scope/{scope_id}', { params: { path: { scope_id: deleting.id } } }))
            data.reload()
          }}
          onClose={() => setDeleting(null)}
        >
          <p>Agents using it go back to their default context. The resources themselves are not deleted.</p>
        </ConfirmDialog>
      )}
    </>
  )
}

const EDIT_NOTES: Record<ScopeEntry['kind'], string> = {
  main: 'Removing a resource here also removes it from every custom scope in the project.',
  custom: 'Only resources in the project can be added.',
  role: 'Agents with this role that use the default context see the change.',
}

function EditScopeModal({ entry, onSaved, onClose }: { entry: ScopeEntry; onSaved: () => void; onClose: () => void }) {
  const api = useApi()
  const [selected, setSelected] = useState(() => new Set(entry.resources))

  return (
    <FormModal
      title={`Resources of ${entry.title}`}
      submitLabel="Save resources"
      onSubmit={async () => {
        await setScopeResources(api, entry.id, entry.resources, [...selected])
        onSaved()
      }}
      onClose={onClose}
    >
      <p className="notice">{EDIT_NOTES[entry.kind]}</p>
      {entry.choices.length === 0 ? (
        <EmptyState>
          <p>There are no resources to choose from yet.</p>
        </EmptyState>
      ) : (
        <ResourceChecklist label="Resources" resources={entry.choices} selected={selected} onChange={setSelected} />
      )}
    </FormModal>
  )
}

function NewScopeModal({
  projects,
  library,
  mainResources,
  onCreated,
  onClose,
}: {
  projects: Schemas['Project'][]
  library: Resource[]
  mainResources: (project: Schemas['Project']) => string[]
  onCreated: () => void
  onClose: () => void
}) {
  const api = useApi()
  const [projectId, setProjectId] = useState(projects[0]?.id ?? '')
  const [selected, setSelected] = useState(new Set<string>())
  const project = projects.find((p) => p.id === projectId)
  const choices = project ? library.filter((r) => mainResources(project).includes(r.id)) : []

  function changeProject(id: string) {
    setProjectId(id)
    // Reset the dependent state in the same event, rather than in an effect that runs after a wrong render.
    setSelected(new Set())
  }

  return (
    <FormModal
      title="New scope"
      submitLabel="Create scope"
      submitDisabled={!project}
      onSubmit={async () => {
        await unwrap(
          api.POST('/api/project/{project_id}/scopes', {
            params: { path: { project_id: projectId } },
            body: { resource_ids: [...selected] },
          }),
        )
        onCreated()
      }}
      onClose={onClose}
    >
      {projects.length === 0 ? (
        <p className="notice">Custom scopes belong to a project. Create a project first.</p>
      ) : (
        <>
          <Field label="Project">
            <select value={projectId} onChange={(e) => changeProject(e.target.value)}>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </Field>
          {choices.length === 0 ? (
            <p className="notice">{project?.name} has no resources yet, so the scope will start empty.</p>
          ) : (
            <ResourceChecklist label="Resources" resources={choices} selected={selected} onChange={setSelected} />
          )}
        </>
      )}
    </FormModal>
  )
}
