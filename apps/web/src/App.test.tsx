import { createApiClient } from '@agent-team/api-client'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App'

function clientReturning(response: Response | Error) {
  return createApiClient({
    baseUrl: 'http://api.test',
    fetch: async () => {
      if (response instanceof Error) throw response
      return response
    },
  })
}

const project = {
  id: '6f1c2c1e-3b8f-4c7a-9a52-1f6d3c1b2a10',
  name: 'Apollo',
  description: 'Go to the moon.',
  system_prompt: 'Work together.',
  team: [],
  roles: [],
  main_scope: '0b7d6a54-2b44-4b8e-8a8e-2f3c4d5e6f70',
  context_scopes: ['0b7d6a54-2b44-4b8e-8a8e-2f3c4d5e6f70'],
}

describe('App', () => {
  it('lists the projects from the API', async () => {
    render(<App client={clientReturning(Response.json([project]))} />)
    expect(await screen.findByText('Apollo')).toBeInTheDocument()
  })

  it('says when there are no projects', async () => {
    render(<App client={clientReturning(Response.json([]))} />)
    expect(await screen.findByText('No projects yet.')).toBeInTheDocument()
  })

  it('says when the API is not reachable', async () => {
    render(<App client={clientReturning(new TypeError('Failed to fetch'))} />)
    expect(await screen.findByRole('alert')).toHaveTextContent('not reachable')
  })
})
