# Agent team

Teams of Claude agents working on shared projects: a Python REST API and MCP server, and a React frontend.

A polyglot monorepo. [Turborepo](https://turborepo.com) runs tasks across all projects; Python dependencies are
managed by [uv](https://docs.astral.sh/uv/), JavaScript dependencies by npm workspaces.

## Layout

```
apps/
  api/            Python: FastAPI REST API + team MCP server (uv)
  web/            TypeScript: React frontend (Vite)
packages/
  api-client/     TypeScript client generated from the API's OpenAPI schema
package.json      npm workspaces and the root scripts
turbo.json        Turborepo tasks
pyproject.toml    uv workspace and the shared Ruff config
```

Every project has a `package.json` with its tasks (`dev`, `build`, `test`, `lint`, `typecheck`, ...). The Python
project's scripts call `uv`, so Turborepo runs both languages the same way.

## Setup

Prerequisites: [uv](https://docs.astral.sh/uv/) and Node 24 (pinned in `.node-version`). With
[fnm](https://github.com/Schniz/fnm), add `eval "$(fnm env --use-on-cd --shell zsh)"` to `~/.zshrc` to switch
to the pinned version automatically.

```sh
uv sync --all-packages   # Python dependencies, into .venv
npm install              # JavaScript dependencies
npm run generate         # API client types from the API's OpenAPI schema
```

## Commands

Run from the repo root; Turborepo runs the task in every project that has it, in dependency order, and caches
the results.

| Command             | Does                                                                 |
| ------------------- | -------------------------------------------------------------------- |
| `npm run dev`       | API on http://127.0.0.1:8000 and frontend on http://localhost:5173  |
| `npm run check`     | `lint`, `typecheck` and `test` everywhere                            |
| `npm run build`     | Production build of the frontend                                     |
| `npm run generate`  | Regenerate the API client after changing the API                     |

Run a task in one project with `--filter`, e.g. `npx turbo run test --filter=@agent-team/api`.

The frontend's dev server forwards `/api` and `/mcp` to the API, so the frontend calls the API on its own origin.

## How the API and the frontend stay in sync

1. `apps/api`'s `openapi` task exports the API's OpenAPI schema to `apps/api/openapi.json`.
2. `packages/api-client`'s `generate` task turns it into TypeScript types (`src/schema.d.ts`).
3. `apps/web` calls the API through the typed client: `createApiClient().GET('/api/project')`.

`build`, `typecheck`, `test` and `dev` depend on `generate`, so the types are always up to date. Commit the
generated `openapi.json` and `schema.d.ts`: API changes then show up as type changes in code review.

## API configuration

Environment variables for `apps/api`, passed through by Turborepo:

| Variable                         | Purpose                                                                  |
| -------------------------------- | ------------------------------------------------------------------------ |
| `ANTHROPIC_API_KEY`              | Anthropic credentials                                                    |
| `ANTHROPIC_ENVIRONMENT_ID`       | Managed Agents environment the agent sessions run in (required)          |
| `AGENTS_DB_PATH`                 | SQLite database, `agents.db` by default                                  |
| `MCP_PUBLIC_URL`, `MCP_SECRET`   | Public URL of `/mcp/` and the key signing the agents' MCP URLs           |

## Adding projects

- **TypeScript package or app**: create it under `packages/` or `apps/` with a `package.json`; npm workspaces and
  Turborepo pick it up. Depend on it from another workspace with `"@agent-team/<name>": "*"`.
- **Python package**: create it with its own `pyproject.toml` under `packages/` or `apps/`, add it to `members` in
  the root `pyproject.toml`, and give it a `package.json` whose scripts call `uv` so Turborepo can run its tasks.
