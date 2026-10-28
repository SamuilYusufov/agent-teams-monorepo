import type { Schemas } from '@agent-team/api-client'
import { useState } from 'react'
import { useApi } from '../../api/context'
import { unwrap } from '../../api/errors'
import { useQuery } from '../../api/useQuery'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { AddButton, Async, DeleteButton, EmptyState, PageHeader } from '../../components/layout'
import { ResourceFormModal } from './ResourceFormModal'

export function ResourcesTab() {
  const api = useApi()
  const resources = useQuery(() => unwrap(api.GET('/api/resource')), [api])
  const [creating, setCreating] = useState(false)
  const [deleting, setDeleting] = useState<Schemas['Resource'] | null>(null)

  return (
    <>
      <PageHeader
        title="Resources"
        description="Texts, links and files agents can use as context. Add them to projects and roles to share them."
        action={<AddButton label="New resource" onClick={() => setCreating(true)} />}
      />
      <Async query={resources}>
        {(list) =>
          list.length === 0 ? (
            <EmptyState>
              <p>No resources yet.</p>
              <AddButton label="Create the first resource" onClick={() => setCreating(true)} />
            </EmptyState>
          ) : (
            <ul className="rows">
              {list.map((resource) => (
                <li key={resource.id} className="row">
                  <div className="row-main">
                    <span className="row-title">{resource.name}</span>
                    <span className="row-desc">
                      {resource.storage === 'in_place' ? resource.content : `Files API: ${resource.anthropic_file_id}`}
                    </span>
                  </div>
                  <span className="tag">{resource.type}</span>
                  <DeleteButton label={`Delete ${resource.name}`} onClick={() => setDeleting(resource)} />
                </li>
              ))}
            </ul>
          )
        }
      </Async>

      {creating && <ResourceFormModal onCreated={resources.reload} onClose={() => setCreating(false)} />}
      {deleting && (
        <ConfirmDialog
          title={`Delete ${deleting.name}?`}
          confirmLabel="Delete resource"
          onConfirm={async () => {
            await unwrap(api.DELETE('/api/resource/{resource_id}', { params: { path: { resource_id: deleting.id } } }))
            resources.reload()
          }}
          onClose={() => setDeleting(null)}
        >
          <p>It will be removed from every project, role and agent that uses it.</p>
        </ConfirmDialog>
      )}
    </>
  )
}
