// Example API data for tests.
import type { Schemas } from '@agent-team/api-client'

export const resources: Schemas['Resource'][] = [
  { id: 'res-brief', name: 'Mission brief', type: 'text', storage: 'in_place', content: 'Land.', anthropic_file_id: null },
  { id: 'res-maps', name: 'Moon maps', type: 'url', storage: 'in_place', content: 'https://moon.test', anthropic_file_id: null },
  { id: 'res-log', name: 'Flight log', type: 'text', storage: 'in_place', content: 'T-10', anthropic_file_id: null },
]

export const roles: Schemas['AgentRole'][] = [
  { id: 'role-pilot', name: 'Pilot', description: 'Flies the lander.', task_examples: [], source_examples: [], context_scope: 'scope-pilot' },
  { id: 'role-geo', name: 'Geologist', description: 'Studies rocks.', task_examples: [], source_examples: [], context_scope: 'scope-geo' },
]

export const project: Schemas['Project'] = {
  id: 'proj-apollo',
  name: 'Apollo',
  description: 'Go to the moon.',
  system_prompt: 'Work together.',
  team: [],
  roles: ['role-pilot'],
  main_scope: 'scope-main',
  context_scopes: ['scope-main'],
}

export const agent: Schemas['AgentWorker'] = {
  id: 'agent-ada',
  anthropic_id: 'agent_123',
  name: 'Ada',
  project: 'proj-apollo',
  role: 'role-pilot',
  context_scope: null,
}
