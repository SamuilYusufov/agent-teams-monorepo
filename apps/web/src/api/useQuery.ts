import { useCallback, useEffect, useState, type DependencyList } from 'react'
import { describeError } from './errors'

/** Where a request for data is: still loading, failed, or done. Exactly one of these at a time. */
export type QueryState<T> =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'loaded'; data: T }

export type Query<T> = QueryState<T> & {
  /** Load the data again, e.g. after changing it. The current data stays on screen until the new data arrives. */
  reload: () => void
}

/**
 * Load data when the component mounts and whenever `deps` change.
 *
 * Deliberately small. When the app grows, a library like TanStack Query adds caching shared between components,
 * retries and refetching on focus.
 */
export function useQuery<T>(load: () => Promise<T>, deps: DependencyList): Query<T> {
  const [state, setState] = useState<QueryState<T>>({ status: 'loading' })
  const [version, setVersion] = useState(0)

  useEffect(() => {
    // If deps change or the component unmounts before the response arrives, ignore that stale response.
    let current = true
    load().then(
      (data) => current && setState({ status: 'loaded', data }),
      (error: unknown) => current && setState({ status: 'error', message: describeError(error) }),
    )
    return () => {
      current = false
    }
    // `load` is a new function on every render; callers list what it depends on in `deps` instead.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, version])

  const reload = useCallback(() => setVersion((v) => v + 1), [])
  return { ...state, reload }
}
