import type { Schemas } from '@agent-team/api-client'
import { useState } from 'react'
import { useApi } from '../../api/context'
import { unwrap } from '../../api/errors'
import { FormModal } from '../../components/FormModal'
import { Field } from '../../components/layout'
import { textField } from '../../lib/format'

type AgentFormModalProps = {
  projects: Schemas['Project'][]
  roles: Schemas['AgentRole'][]
  /** Create the agent in this project, without asking. */
  projectId?: string
  onCreated: () => void
  onClose: () => void
}

/** Form to create an agent. The role must be one of the project's roles, so the role list follows the project. */
export function AgentFormModal({ projects, roles, projectId: fixedProjectId, onCreated, onClose }: AgentFormModalProps) {
  const api = useApi()
  const [projectId, setProjectId] = useState(fixedProjectId ?? projects[0]?.id ?? '')
  const project = projects.find((p) => p.id === projectId)
  const projectRoles = roles.filter((role) => project?.roles.includes(role.id))

  async function submit(form: FormData) {
    await unwrap(
      api.POST('/api/agent', {
        body: { name: textField(form, 'name'), project_id: projectId, role_id: textField(form, 'role_id') },
      }),
    )
    onCreated()
  }

  return (
    <FormModal
      title={project && fixedProjectId ? `New agent in ${project.name}` : 'New agent'}
      submitLabel="Create agent"
      onSubmit={submit}
      onClose={onClose}
      submitDisabled={projectRoles.length === 0}
    >
      <Field label="Name" hint="Agents address each other by name, so it must be unique.">
        <input name="name" required data-autofocus />
      </Field>
      {!fixedProjectId && (
        <Field label="Project">
          <select value={projectId} onChange={(e) => setProjectId(e.target.value)} required>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </Field>
      )}
      {projectRoles.length > 0 ? (
        <Field label="Role">
          {/* key: a new project means a new list of roles, so start the select over instead of keeping a stale choice. */}
          <select key={projectId} name="role_id" required>
            {projectRoles.map((role) => (
              <option key={role.id} value={role.id}>
                {role.name}
              </option>
            ))}
          </select>
        </Field>
      ) : (
        <p className="notice">
          {project ? `${project.name} has no roles yet. Add a role to the project first.` : 'Create a project first.'}
        </p>
      )}
    </FormModal>
  )
}
