/**
 * Typed client for the agent team API.
 *
 * `schema.d.ts` is generated from the API's OpenAPI schema by `npm run generate`; don't edit it by hand.
 */
import createClient, { type ClientOptions } from 'openapi-fetch'
import type { components, paths } from './schema'

export type { components, paths }

/** Request and response bodies of the API, e.g. `Schemas['Project']`. */
export type Schemas = components['schemas']

/**
 * Create a client for the API. Without a `baseUrl` it calls the API on the same origin, which in development
 * is the Vite dev server forwarding `/api` to the Python server. Pass `fetch` to stub requests in tests.
 */
export function createApiClient(options: ClientOptions = {}) {
  return createClient<paths>(options)
}

export type ApiClient = ReturnType<typeof createApiClient>
