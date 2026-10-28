import type { ApiClient } from '@agent-team/api-client'
import { unwrap } from './errors'

/** Make the scope contain exactly `wanted`, adding and removing only the resources that changed. */
export async function setScopeResources(api: ApiClient, scopeId: string, current: string[], wanted: string[]) {
  const toAdd = wanted.filter((id) => !current.includes(id))
  const toRemove = current.filter((id) => !wanted.includes(id))
  const path = (resourceId: string) => ({ params: { path: { scope_id: scopeId, resource_id: resourceId } } })
  await Promise.all([
    ...toAdd.map((id) => unwrap(api.PUT('/api/scope/{scope_id}/resources/{resource_id}', path(id)))),
    ...toRemove.map((id) => unwrap(api.DELETE('/api/scope/{scope_id}/resources/{resource_id}', path(id)))),
  ])
}
