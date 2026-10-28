import type { ApiClient } from '@agent-team/api-client'
import type { ReactNode } from 'react'
import { ApiContext } from './context'

/** Makes `client` available to every component below through `useApi()`. Tests pass a fake client. */
export function ApiProvider({ client, children }: { client: ApiClient; children: ReactNode }) {
  return <ApiContext value={client}>{children}</ApiContext>
}
