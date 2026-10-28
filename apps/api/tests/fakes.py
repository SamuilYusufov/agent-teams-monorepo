"""In-memory stand-in for the parts of AsyncAnthropic's Managed Agents API the services use."""
from itertools import count
from types import SimpleNamespace


class _AsyncPage:
    def __init__(self, items):
        self._items = items

    def __aiter__(self):
        return self._iterate()

    async def _iterate(self):
        for item in self._items:
            yield item


class _Agents:
    def __init__(self, fake: FakeAnthropic):
        self._fake = fake

    async def create(self, *, name, model, system, mcp_servers=(), tools=()):
        agent = SimpleNamespace(
            id=f"agent_{next(self._fake._ids)}",
            name=name,
            model=model,
            system=system,
            version=1,
            mcp_servers=list(mcp_servers),
            tools=list(tools),
        )
        self._fake.agents[agent.id] = agent
        return agent

    async def retrieve(self, agent_id):
        return self._fake.agents[agent_id]

    async def archive(self, agent_id):
        self._fake.archived_agents.append(agent_id)


class _Events:
    def __init__(self, fake: FakeAnthropic):
        self._fake = fake

    async def send(self, session_id, *, events):
        for event in events:
            self._fake.sent.append((session_id, event))


class _Sessions:
    def __init__(self, fake: FakeAnthropic):
        self._fake = fake
        self.events = _Events(fake)

    async def create(self, **kwargs):
        session = SimpleNamespace(
            id=f"sesn_{next(self._fake._ids)}",
            agent_id=kwargs["agent"]["id"],
            status="idle",
            title=kwargs.get("title"),
            archived=False,
            params=kwargs,
        )
        self._fake.sessions[session.id] = session
        return session

    def list(self, *, agent_id, include_archived=False, statuses=None, limit=None):
        sessions = [
            session
            for session in self._fake.sessions.values()
            if session.agent_id == agent_id
            and (include_archived or not session.archived)
            and (statuses is None or session.status in statuses)
        ]
        return _AsyncPage(sessions[:limit] if limit else sessions)

    async def archive(self, session_id):
        self._fake.sessions[session_id].archived = True


class FakeAnthropic:
    def __init__(self):
        self._ids = count(1)
        self.agents: dict[str, SimpleNamespace] = {}
        self.archived_agents: list[str] = []
        self.sessions: dict[str, SimpleNamespace] = {}
        self.sent: list[tuple[str, dict]] = []
        self.beta = SimpleNamespace(agents=_Agents(self), sessions=_Sessions(self))

    def live_sessions(self, agent_id: str) -> list[SimpleNamespace]:
        return [s for s in self.sessions.values() if s.agent_id == agent_id and not s.archived]

    def texts_sent_to(self, session_id: str) -> list[str]:
        return [event["content"][0]["text"] for sid, event in self.sent if sid == session_id]
