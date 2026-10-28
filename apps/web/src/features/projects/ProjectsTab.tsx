import type { Schemas } from '@agent-team/api-client'
import { useState } from 'react'
import { useApi } from '../../api/context'
import { unwrap } from '../../api/errors'
import { useQuery } from '../../api/useQuery'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { FormModal } from '../../components/FormModal'
import { Modal } from '../../components/Modal'
import { AddButton, Async, DeleteButton, EmptyState, Field, PageHeader } from '../../components/layout'
import { plural, textField } from '../../lib/format'
import { ProjectDetail } from './ProjectDetail'

export function ProjectsTab() {
  const [openId, setOpenId] = useState<string | null>(null)
  // key: opening another project mounts a fresh ProjectDetail, so no state leaks from the previous one.
  if (openId) return <ProjectDetail key={openId} projectId={openId} onBack={() => setOpenId(null)} />
  return <ProjectList onOpen={setOpenId} />
}

function ProjectList({ onOpen }: { onOpen: (id: string) => void }) {
  const api = useApi()
  const projects = useQuery(() => unwrap(api.GET('/api/project')), [api])
  const [creating, setCreating] = useState(false)
  const [deleting, setDeleting] = useState<Schemas['Project'] | null>(null)

  async function create(form: FormData) {
    const project = await unwrap(
      api.POST('/api/project', {
        body: {
          name: textField(form, 'name'),
          description: textField(form, 'description'),
          system_prompt: textField(form, 'system_prompt'),
          role_ids: [], // roles are added on the project's page, with search
        },
      }),
    )
    onOpen(project.id) // the next step is adding roles, agents and resources, which happens inside the project
  }

  async function remove(project: Schemas['Project']) {
    await unwrap(api.DELETE('/api/project/{project_id}', { params: { path: { project_id: project.id } } }))
    projects.reload()
  }

  return (
    <>
      <PageHeader
        title="Projects"
        description="A project is a team of agents working toward one goal."
        action={<AddButton label="New project" onClick={() => setCreating(true)} />}
      />
      <Async query={projects}>
        {(list) =>
          list.length === 0 ? (
            <EmptyState>
              <p>No projects yet.</p>
              <AddButton label="Create the first project" onClick={() => setCreating(true)} />
            </EmptyState>
          ) : (
            <ul className="rows">
              {list.map((project) => (
                <li key={project.id} className="row">
                  <button type="button" className="row-main row-button" onClick={() => onOpen(project.id)}>
                    <span className="row-title">{project.name}</span>
                    <span className="row-desc">{project.description}</span>
                  </button>
                  <span className="row-meta">
                    {plural(project.roles.length, 'role')}, {plural(project.team.length, 'agent')}
                  </span>
                  <DeleteButton label={`Delete ${project.name}`} onClick={() => setDeleting(project)} />
                </li>
              ))}
            </ul>
          )
        }
      </Async>

      {creating && (
        <FormModal title="New project" submitLabel="Create project" onSubmit={create} onClose={() => setCreating(false)}>
          <Field label="Name">
            <input name="name" required data-autofocus />
          </Field>
          <Field label="Goal" hint="What the team is working toward, in a sentence or two.">
            <textarea name="description" rows={2} required />
          </Field>
          <Field label="Team instructions" hint="Given to every agent in the project, before its own role.">
            <textarea name="system_prompt" rows={5} required />
          </Field>
        </FormModal>
      )}
      {deleting &&
        (deleting.team.length > 0 ? (
          // The API refuses to delete a project with agents. Say so up front rather than offer a button that fails.
          <Modal title={`${deleting.name} still has agents`} onClose={() => setDeleting(null)}>
            <p className="confirm-text">
              Delete its {plural(deleting.team.length, 'agent')} first, then the project can be deleted.
            </p>
            <div className="form-actions">
              <button type="button" className="button" onClick={() => setDeleting(null)} data-autofocus>
                Got it
              </button>
            </div>
          </Modal>
        ) : (
          <ConfirmDialog
            title={`Delete ${deleting.name}?`}
            confirmLabel="Delete project"
            onConfirm={() => remove(deleting)}
            onClose={() => setDeleting(null)}
          >
            <p>Its context scopes are deleted too. Its roles and resources stay available to other projects.</p>
          </ConfirmDialog>
        ))}
    </>
  )
}
