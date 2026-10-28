import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import App from './App'
import { agent, project, resources, roles } from './test/data'
import { fakeApi } from './test/fakeApi'

describe('App', () => {
  it('lists the projects from the API', async () => {
    const { client } = fakeApi({ 'GET /api/project': [project] })
    render(<App client={client} />)
    expect(await screen.findByText('Apollo')).toBeInTheDocument()
  })

  it('says when there are no projects', async () => {
    const { client } = fakeApi({ 'GET /api/project': [] })
    render(<App client={client} />)
    expect(await screen.findByText('No projects yet.')).toBeInTheDocument()
  })

  it('says when the API is not reachable', async () => {
    const { client } = fakeApi({
      'GET /api/project': () => {
        throw new TypeError('Failed to fetch')
      },
    })
    render(<App client={client} />)
    expect(await screen.findByRole('alert')).toHaveTextContent('not reachable')
  })
})

describe('side tabs', () => {
  it('switch sections by click and with the arrow keys', async () => {
    const user = userEvent.setup()
    const { client } = fakeApi({ 'GET /api/project': [], 'GET /api/role': roles, 'GET /api/resource': [] })
    render(<App client={client} />)

    await user.click(screen.getByRole('tab', { name: 'Roles' }))
    expect(screen.getByRole('tab', { name: 'Roles' })).toHaveAttribute('aria-selected', 'true')
    expect(await screen.findByRole('heading', { level: 1, name: 'Roles' })).toBeInTheDocument()

    await user.keyboard('{ArrowDown}{ArrowDown}')
    expect(screen.getByRole('tab', { name: 'Resources' })).toHaveFocus()
    expect(await screen.findByRole('heading', { level: 1, name: 'Resources' })).toBeInTheDocument()
  })
})

describe('projects', () => {
  it('creates a project with the + button and opens it', async () => {
    const user = userEvent.setup()
    const created = { ...project, id: 'proj-new', name: 'Gemini', roles: [] }
    const api = fakeApi({
      'GET /api/project': [],
      'POST /api/project': created,
      'GET /api/project/proj-new': created,
      'GET /api/role': roles,
      'GET /api/agent': [],
      'GET /api/scope/scope-main/resources': [],
      'GET /api/resource': resources,
    })
    render(<App client={api.client} />)

    await user.click(await screen.findByRole('button', { name: 'New project' }))
    const dialog = screen.getByRole('dialog', { name: 'New project' })
    await user.type(within(dialog).getByLabelText('Name'), 'Gemini')
    await user.type(within(dialog).getByLabelText(/Goal/), 'Orbit.')
    await user.type(within(dialog).getByLabelText(/Team instructions/), 'Be careful.')
    await user.click(within(dialog).getByRole('button', { name: 'Create project' }))

    expect(await screen.findByRole('heading', { level: 1, name: 'Gemini' })).toBeInTheDocument()
    expect(api.called('POST /api/project')[0].body).toEqual({
      name: 'Gemini',
      description: 'Orbit.',
      system_prompt: 'Be careful.',
      role_ids: [],
    })
  })

  it('asks before deleting a project, and only deletes after confirming', async () => {
    const user = userEvent.setup()
    const api = fakeApi({ 'GET /api/project': [project], 'DELETE /api/project/proj-apollo': undefined })
    render(<App client={api.client} />)

    await user.click(await screen.findByRole('button', { name: 'Delete Apollo' }))
    const dialog = screen.getByRole('dialog', { name: 'Delete Apollo?' })
    expect(within(dialog).getByRole('button', { name: 'Cancel' })).toHaveFocus()
    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }))
    expect(api.called('DELETE /api/project/proj-apollo')).toHaveLength(0)

    await user.click(screen.getByRole('button', { name: 'Delete Apollo' }))
    await user.click(screen.getByRole('button', { name: 'Delete project' }))
    await waitFor(() => expect(api.called('DELETE /api/project/proj-apollo')).toHaveLength(1))
  })

  it('explains instead of deleting a project that still has agents', async () => {
    const user = userEvent.setup()
    const { client } = fakeApi({ 'GET /api/project': [{ ...project, team: [agent.id] }] })
    render(<App client={client} />)

    await user.click(await screen.findByRole('button', { name: 'Delete Apollo' }))
    expect(screen.getByRole('dialog', { name: 'Apollo still has agents' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Delete project' })).not.toBeInTheDocument()
  })

  it('finds a role by searching and adds it to the project', async () => {
    const user = userEvent.setup()
    let current = project
    const api = fakeApi({
      'GET /api/project': [project],
      'GET /api/project/proj-apollo': () => current,
      'PUT /api/project/proj-apollo/roles/role-geo': () => (current = { ...project, roles: [...project.roles, 'role-geo'] }),
      'GET /api/role': roles,
      'GET /api/agent': [],
      'GET /api/scope/scope-main/resources': [],
      'GET /api/resource': resources,
    })
    render(<App client={api.client} />)

    await user.click(await screen.findByRole('button', { name: /^Apollo/ }))
    await user.type(await screen.findByRole('searchbox', { name: 'Search roles to add' }), 'rock')
    await user.click(screen.getByRole('button', { name: /Geologist/ }))

    expect(await screen.findByRole('button', { name: 'Remove Geologist from Apollo' })).toBeInTheDocument()
    expect(api.called('PUT /api/project/proj-apollo/roles/role-geo')).toHaveLength(1)
  })
})

describe('agent context', () => {
  const routes = {
    'GET /api/agent': [agent],
    'GET /api/project': [project],
    'GET /api/role': roles,
    'GET /api/project/proj-apollo': project,
    'GET /api/role/role-pilot': roles[0],
    'GET /api/scope/scope-main/resources': resources,
    // The pilot role's scope shares two resources with the project, so those make up Ada's default context.
    'GET /api/scope/scope-pilot': { id: 'scope-pilot', resources: ['res-brief', 'res-log', 'res-elsewhere'] },
  }

  it('starts from the default context and saves the picked resources as a new scope', async () => {
    const user = userEvent.setup()
    const api = fakeApi({
      ...routes,
      'POST /api/project/proj-apollo/scopes': { id: 'scope-ada', resources: ['res-brief', 'res-maps', 'res-log'] },
      'PUT /api/agent/agent-ada/scope': { ...agent, context_scope: 'scope-ada' },
    })
    render(<App client={api.client} />)

    await user.click(screen.getByRole('tab', { name: 'Agents' }))
    await user.click(await screen.findByRole('button', { name: /^Ada/ }))
    const drawer = screen.getByRole('dialog', { name: 'Ada' })
    expect(await within(drawer).findByRole('checkbox', { name: /Mission brief/ })).toBeChecked()
    expect(within(drawer).getByRole('checkbox', { name: /Moon maps/ })).not.toBeChecked()
    expect(within(drawer).getByRole('button', { name: 'Save context' })).toBeDisabled()

    await user.click(within(drawer).getByRole('checkbox', { name: /Moon maps/ }))
    await user.click(within(drawer).getByRole('button', { name: 'Save context' }))

    await waitFor(() => expect(api.called('PUT /api/agent/agent-ada/scope')).toHaveLength(1))
    expect(api.called('POST /api/project/proj-apollo/scopes')[0].body).toEqual({
      resource_ids: ['res-brief', 'res-maps', 'res-log'],
    })
    expect(api.called('PUT /api/agent/agent-ada/scope')[0].body).toEqual({ context_scope: 'scope-ada' })
  })

  it("edits the agent's own scope in place", async () => {
    const user = userEvent.setup()
    const pinned = { ...agent, context_scope: 'scope-ada' }
    const api = fakeApi({
      ...routes,
      'GET /api/agent': [pinned],
      'GET /api/project/proj-apollo': { ...project, context_scopes: ['scope-main', 'scope-ada'] },
      'GET /api/scope/scope-ada': { id: 'scope-ada', resources: ['res-brief'] },
      'DELETE /api/scope/scope-ada/resources/res-brief': { id: 'scope-ada', resources: [] },
    })
    render(<App client={api.client} />)

    await user.click(screen.getByRole('tab', { name: 'Agents' }))
    await user.click(await screen.findByRole('button', { name: /^Ada/ }))
    await user.click(await screen.findByRole('checkbox', { name: /Mission brief/ }))
    await user.click(screen.getByRole('button', { name: 'Save context' }))

    await waitFor(() => expect(api.called('DELETE /api/scope/scope-ada/resources/res-brief')).toHaveLength(1))
    expect(api.called('POST /api/project/proj-apollo/scopes')).toHaveLength(0)
  })
})
