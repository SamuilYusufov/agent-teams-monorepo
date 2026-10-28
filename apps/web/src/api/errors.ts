/** Turning API responses and failures into data or into messages people can act on. */

/** The API answered, but with an error status. `message` is the API's explanation. */
export class ApiError extends Error {}

type ApiResult<T> = { data?: T; error?: unknown; response: Response }

/**
 * Wait for an openapi-fetch request and return its data, or throw an `ApiError` for an error status.
 * openapi-fetch returns `{ data, error }` instead of throwing, which is easy to forget to check; with `unwrap`
 * every failure ends up in one `catch`.
 */
export async function unwrap<T>(request: Promise<ApiResult<T>>): Promise<T> {
  const { data, error, response } = await request
  if (!response.ok) throw new ApiError(detailOf(error) ?? `The request failed with status ${response.status}.`)
  return data as T
}

/** A message for any error thrown while talking to the API. */
export function describeError(error: unknown): string {
  if (error instanceof ApiError) return error.message
  // fetch() throws a TypeError when it can't reach the server at all.
  if (error instanceof TypeError) return 'The API is not reachable. Is it running?'
  return 'Something unexpected went wrong. Try again.'
}

function detailOf(error: unknown): string | undefined {
  if (!error || typeof error !== 'object' || !('detail' in error)) return undefined
  const { detail } = error
  if (typeof detail === 'string') return detail // 404 and 409: the API explains what went wrong
  if (Array.isArray(detail)) return 'Some fields are missing or invalid.' // 422: request validation failed
  return undefined
}
