import { createApiClient, type ApiClient, type Schemas } from '@agent-team/api-client'
import { useEffect, useState } from 'react'

const defaultClient = createApiClient()

type State =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'loaded'; projects: Schemas['Project'][] }

export default function App({ client = defaultClient }: { client?: ApiClient }) {
  const [state, setState] = useState<State>({ status: 'loading' })

  useEffect(() => {
    client
      .GET('/api/project')
      .then(({ data, error }) =>
        setState(error ? { status: 'error', message: 'Could not load projects.' } : { status: 'loaded', projects: data }),
      )
      .catch(() => setState({ status: 'error', message: 'The API is not reachable. Is it running?' }))
  }, [client])

  return (
    <main>
      <h1>Agent team</h1>
      {state.status === 'loading' && <p>Loading projects…</p>}
      {state.status === 'error' && <p role="alert">{state.message}</p>}
      {state.status === 'loaded' &&
        (state.projects.length === 0 ? (
          <p>No projects yet.</p>
        ) : (
          <ul>
            {state.projects.map((project) => (
              <li key={project.id}>
                <strong>{project.name}</strong>: {project.description}
              </li>
            ))}
          </ul>
        ))}
    </main>
  )
}
