import type { Schemas } from '@agent-team/api-client'
import { useState } from 'react'
import { useApi } from '../../api/context'
import { unwrap } from '../../api/errors'
import { FormModal } from '../../components/FormModal'
import { Field } from '../../components/layout'
import { textField } from '../../lib/format'

type ResourceType = Schemas['ResourceCreate']['type']
type Storage = Schemas['ResourceCreate']['storage']

const CONTENT_LABELS: Record<ResourceType, string> = { text: 'Text', url: 'URL', file: 'File contents' }

/** Form to create a resource. `onCreated` gets the new resource, e.g. to add it to a project right away. */
export function ResourceFormModal({
  onCreated,
  onClose,
  submitLabel = 'Create resource',
}: {
  onCreated: (resource: Schemas['Resource']) => Promise<unknown> | void
  onClose: () => void
  submitLabel?: string
}) {
  const api = useApi()
  // These two are state, not just form values, because they change which other fields are shown.
  const [type, setType] = useState<ResourceType>('text')
  const [storage, setStorage] = useState<Storage>('in_place')
  // Only files can live in Anthropic's storage. Deriving this instead of storing it keeps the two consistent.
  const effectiveStorage = type === 'file' ? storage : 'in_place'

  async function submit(form: FormData) {
    const resource = await unwrap(
      api.POST('/api/resource', {
        body: {
          name: textField(form, 'name'),
          type,
          storage: effectiveStorage,
          content: effectiveStorage === 'in_place' ? textField(form, 'content') : null,
          anthropic_file_id: effectiveStorage === 'anthropic_managed' ? textField(form, 'file_id') : null,
        },
      }),
    )
    await onCreated(resource)
  }

  return (
    <FormModal title="New resource" submitLabel={submitLabel} onSubmit={submit} onClose={onClose}>
      <Field label="Name">
        <input name="name" required data-autofocus />
      </Field>
      <Field label="Type">
        <select value={type} onChange={(e) => setType(e.target.value as ResourceType)}>
          <option value="text">Text</option>
          <option value="url">URL</option>
          <option value="file">File</option>
        </select>
      </Field>
      {type === 'file' && (
        <fieldset className="radio-group">
          <legend className="field-label">Stored</legend>
          <label className="check">
            <input
              type="radio"
              name="storage"
              checked={storage === 'in_place'}
              onChange={() => setStorage('in_place')}
            />
            Here, with its contents pasted below
          </label>
          <label className="check">
            <input
              type="radio"
              name="storage"
              checked={storage === 'anthropic_managed'}
              onChange={() => setStorage('anthropic_managed')}
            />
            Uploaded to Anthropic through the Files API
          </label>
        </fieldset>
      )}
      {effectiveStorage === 'in_place' ? (
        <Field label={CONTENT_LABELS[type]}>
          {type === 'url' ? (
            <input name="content" type="url" required placeholder="https://" />
          ) : (
            <textarea name="content" rows={6} required />
          )}
        </Field>
      ) : (
        <Field label="Files API ID" hint="The ID Anthropic returned when you uploaded the file.">
          <input name="file_id" required placeholder="file_…" />
        </Field>
      )}
    </FormModal>
  )
}
