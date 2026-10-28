import { createApiClient } from '@agent-team/api-client'

type Request = { body: unknown; url: URL }
/** A fixed response body, a function computing one, or a `Response` for errors. `undefined` answers 204. */
type Route = unknown

/**
 * An API client answering from `routes`, keyed by "METHOD /path", e.g. "GET /api/project". Records every request
 * in `calls`, so tests can check what the UI sent. Routes can be functions, to keep state between requests.
 */
export function fakeApi(routes: Record<string, Route>) {
  const calls: { key: string; body: unknown }[] = []
  const client = createApiClient({
    baseUrl: 'http://api.test',
    fetch: async (request: globalThis.Request) => {
      const url = new URL(request.url)
      const key = `${request.method} ${url.pathname}`
      const text = await request.text()
      const body: unknown = text ? JSON.parse(text) : undefined
      calls.push({ key, body })
      if (!(key in routes)) return Response.json({ detail: `No fake route for ${key}` }, { status: 404 })
      const route = routes[key]
      const result = typeof route === 'function' ? (route as (r: Request) => unknown)({ body, url }) : route
      if (result instanceof Response) return result
      if (result === undefined) return new Response(null, { status: 204 })
      return Response.json(result)
    },
  })
  return { client, calls, called: (key: string) => calls.filter((call) => call.key === key) }
}
