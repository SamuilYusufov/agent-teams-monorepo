import { createApiClient, type ApiClient } from '@agent-team/api-client'
import { useState } from 'react'
import { ApiProvider } from './api/ApiProvider'
import { SideTabs } from './components/SideTabs'
import { AgentsTab } from './features/agents/AgentsTab'
import { ProjectsTab } from './features/projects/ProjectsTab'
import { ResourcesTab } from './features/resources/ResourcesTab'
import { RolesTab } from './features/roles/RolesTab'
import { ScopesTab } from './features/scopes/ScopesTab'

const defaultClient = createApiClient()

// `as const` keeps the IDs as literal types, so `TabId` is 'projects' | 'roles' | … and typos don't compile.
const TABS = [
  { id: 'projects', label: 'Projects' },
  { id: 'roles', label: 'Roles' },
  { id: 'scopes', label: 'Scopes' },
  { id: 'resources', label: 'Resources' },
  { id: 'agents', label: 'Agents' },
] as const

type TabId = (typeof TABS)[number]['id']

export default function App({ client = defaultClient }: { client?: ApiClient }) {
  const [tab, setTab] = useState<TabId>('projects')

  return (
    <ApiProvider client={client}>
      <div className="shell">
        <SideTabs tabs={TABS} active={tab} onChange={setTab} />
        <main className="panel" role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`} tabIndex={0}>
          {tab === 'projects' && <ProjectsTab />}
          {tab === 'roles' && <RolesTab />}
          {tab === 'scopes' && <ScopesTab />}
          {tab === 'resources' && <ResourcesTab />}
          {tab === 'agents' && <AgentsTab />}
        </main>
      </div>
    </ApiProvider>
  )
}
