import type { Schemas } from '@agent-team/api-client'
import { useState } from 'react'
import { useApi } from '../../api/context'
import { unwrap } from '../../api/errors'
import { useQuery } from '../../api/useQuery'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { FormModal } from '../../components/FormModal'
import { AddButton, Async, DeleteButton, EmptyState, Field, PageHeader } from '../../components/layout'
import { linesField, plural, textField } from '../../lib/format'

export function RolesTab() {
  const api = useApi()
  const roles = useQuery(() => unwrap(api.GET('/api/role')), [api])
  const [creating, setCreating] = useState(false)
  const [deleting, setDeleting] = useState<Schemas['AgentRole'] | null>(null)

  async function create(form: FormData) {
    await unwrap(
      api.POST('/api/role', {
        body: {
          name: textField(form, 'name'),
          description: textField(form, 'description'),
          task_examples: linesField(form, 'task_examples'),
          source_examples: linesField(form, 'source_examples'),
          resource_ids: [], // resources are picked in the Scopes tab
        },
      }),
    )
    roles.reload()
  }

  return (
    <>
      <PageHeader
        title="Roles"
        description="Job descriptions agents can take on. Any project can use a role."
        action={<AddButton label="New role" onClick={() => setCreating(true)} />}
      />
      <Async query={roles}>
        {(list) =>
          list.length === 0 ? (
            <EmptyState>
              <p>No roles yet.</p>
              <AddButton label="Create the first role" onClick={() => setCreating(true)} />
            </EmptyState>
          ) : (
            <ul className="rows">
              {list.map((role) => (
                <li key={role.id} className="row">
                  <div className="row-main">
                    <span className="row-title">{role.name}</span>
                    <span className="row-desc">{role.description}</span>
                  </div>
                  <span className="row-meta">
                    {plural(role.task_examples.length, 'task example')}, {plural(role.source_examples.length, 'source')}
                  </span>
                  <DeleteButton label={`Delete ${role.name}`} onClick={() => setDeleting(role)} />
                </li>
              ))}
            </ul>
          )
        }
      </Async>

      {creating && (
        <FormModal title="New role" submitLabel="Create role" onSubmit={create} onClose={() => setCreating(false)}>
          <Field label="Name">
            <input name="name" required data-autofocus placeholder="Researcher" />
          </Field>
          <Field label="Description">
            <textarea name="description" rows={3} required />
          </Field>
          <Field label="Task examples" hint="Optional. One per line.">
            <textarea name="task_examples" rows={3} />
          </Field>
          <Field label="Source examples" hint="Optional. Sources agents should ground their work in, one per line.">
            <textarea name="source_examples" rows={3} />
          </Field>
        </FormModal>
      )}
      {deleting && (
        <ConfirmDialog
          title={`Delete ${deleting.name}?`}
          confirmLabel="Delete role"
          onConfirm={async () => {
            await unwrap(api.DELETE('/api/role/{role_id}', { params: { path: { role_id: deleting.id } } }))
            roles.reload()
          }}
          onClose={() => setDeleting(null)}
        >
          <p>Its context scope is deleted with it. A role can't be deleted while agents have it.</p>
        </ConfirmDialog>
      )}
    </>
  )
}
