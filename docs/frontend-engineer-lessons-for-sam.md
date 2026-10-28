# Frontend engineer lessons for Sam

A running notebook of the frontend skills, judgement calls and best practices used to build `apps/web`. Each
lesson points at real code in this repo, says what was done, and, more importantly, **why**. New lessons are
added as the UI grows.

> How to read this: skim the headings first. When you open a file in `apps/web/src`, come back and read the
> lessons that mention it. Code beats prose: every example here is in the codebase.

---

## Map of the code

```
apps/web/src/
  App.tsx                      the shell: side tabs + the panel for the active tab
  index.css                    design tokens and all styles
  api/                         talking to the backend (no UI here)
    context.ts, ApiProvider    hands the API client to every component
    errors.ts                  unwrap() and describeError(): one way to handle failures
    useQuery.ts                load data, with loading / error / loaded states
    useAction.ts               run a change (create, delete…) and track busy / error
    scopes.ts                  add/remove the difference between two resource lists
  components/                  generic building blocks, know nothing about projects or agents
    Modal, FormModal, ConfirmDialog, SideTabs, ResourceChecklist, layout.tsx, icons.tsx
  features/                    one folder per tab, the actual product
    projects/ roles/ scopes/ resources/ agents/
  test/                        fake API, sample data, jsdom setup
```

**Lesson 0: split by responsibility, then by feature.** `api/` knows HTTP but not HTML. `components/` knows
HTML but not the domain. `features/` combines both. When something breaks, the folder tells you where to look.
When a second screen needs a dialog, it reuses `components/Modal` instead of copying it.

---

## 1. Start from the data, not the screens

Before drawing anything I read `apps/api/routers/*.py` and the services. Three findings shaped the UI:

1. **There is no "list all scopes" endpoint.** Every scope belongs to a project (main + custom scopes) or a role.
   So `features/scopes/ScopesTab.tsx` collects them from projects and roles (`loadScopes`). A UI built only
   from the brief would have assumed `GET /api/scope` exists.
2. **An agent's "context" is not a list of resources. It's a pointer to a scope.** The API's rule: no scope
   means "resources shared by the project and the role"; otherwise it's one of the project's scopes. The user
   just wants to tick checkboxes. `AgentContextDrawer.tsx` translates between the two:
   - load: compute the current selection with the *same rule the API uses* (`loadContext`);
   - save: if the agent has a scope nobody else uses, edit it in place; otherwise create a new scope and
     point the agent at it. Editing a shared scope would silently change *other agents'* context.
3. **Business rules the API enforces** (a project with agents can't be deleted, main scopes can't be deleted,
   agents need a role from their project). The UI shows these *before* the user hits the error (see §8).

**Why:** the UI is a view of the data model. If you design screens first, you discover the mismatch when wiring
the API and end up with hacks. Hiding the model's complexity ("scopes") behind the user's mental model
("which resources can Ada see?") is a large part of frontend work.

---

## 2. Components: small, composable, props down, events up

A React component is a function from props to UI. Data flows **down** as props; changes flow **up** as callback
props (`onClose`, `onCreated`, `onChange`).

```tsx
// features/projects/ProjectDetail.tsx
<ProjectRoles {...loaded} onChange={data.reload} />
```

`ProjectRoles` doesn't know how the page loads data. It just says "something changed" and the parent decides
to reload. That keeps each component understandable on its own.

**Composition over configuration.** `FormModal` doesn't know about projects: it takes `children` (the fields)
and an `onSubmit`. The same component powers the project, role, resource, agent and scope forms:

```tsx
<FormModal title="New role" submitLabel="Create role" onSubmit={create} onClose={() => setCreating(false)}>
  <Field label="Name"><input name="name" required data-autofocus /></Field>
  …
</FormModal>
```

**Reuse when the second use appears, not before.** `AgentList` was extracted because both the Agents tab and
the project page list agents. `ResourceChecklist` is used in four places. Nothing was made generic "just in
case".

---

## 3. State: keep as little as possible, derive the rest

The most common React bug is two pieces of state that should agree but don't. Rule: **if you can compute it from
props or other state, don't store it.**

```tsx
// ProjectDetail.tsx: search results are computed on every render, not stored
const query = search.trim().toLowerCase()
const matches = query ? roles.filter((role) => !project.roles.includes(role.id) && …) : []
```

```tsx
// ResourceFormModal.tsx: only files can be Anthropic-managed, so derive it
const effectiveStorage = type === 'file' ? storage : 'in_place'
```

If `matches` were state, you'd need to update it whenever `search`, `roles` *or* `project` changed, and you'd
eventually forget one.

**Never mutate state; replace it.** React decides whether to re-render by checking if the value is a *new*
object. Changing a `Set` in place looks like no change at all:

```tsx
// ResourceChecklist.tsx
const next = new Set(selected) // copy
next.has(id) ? next.delete(id) : next.add(id)
onChange(next)                 // new object → React re-renders
```

**Resetting state: use `key`.** When you open a different project, every bit of state in the old page (search
text, open dialogs) should go. Instead of resetting each one by hand, give the component a `key`; a new key
means React throws the old instance away:

```tsx
// ProjectsTab.tsx
if (openId) return <ProjectDetail key={openId} projectId={openId} onBack={…} />
```

Same trick in `AgentFormModal`: `<select key={projectId} …>` starts the role list over when the project changes.

**Reset dependent state in the event, not in an effect.** In `NewScopeModal`, changing the project clears the
selected resources *in the same handler*. A `useEffect` that "watches" the project would first render the wrong
combination (new project + old resources) and then fix it.

**Seed state from data only once it has loaded.** `ContextForm` in `AgentContextDrawer.tsx` is only mounted
after the data arrives, so `useState(() => new Set(initial))` gets real data. If it were mounted earlier, the
initial value would be empty and never update.

---

## 4. Model async state so impossible states can't happen

A beginner writes `const [loading, setLoading] = useState(true); const [error, setError] = useState(); const
[data, setData] = useState()`. Now "loading *and* error *and* data" is representable, and every render has to
guess which one wins.

```ts
// api/useQuery.ts: a discriminated union, exactly one state at a time
export type QueryState<T> =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'loaded'; data: T }
```

TypeScript enforces it: you can only read `.data` after checking `status === 'loaded'`. The `Async` component
(`components/layout.tsx`) renders all three states the same way across the app, so no screen forgets its error
state. The original `App.tsx` already did this; I kept the pattern and generalised it.

---

## 5. Fetching data

**Race conditions.** If you switch projects quickly, the response for project A may arrive *after* project B's.
`useQuery` ignores stale responses:

```ts
useEffect(() => {
  let current = true
  load().then((data) => current && setState({ status: 'loaded', data }), …)
  return () => { current = false } // cleanup runs when deps change or the component unmounts
}, [...deps, version])
```

**Parallel requests.** Independent requests go out together with `Promise.all`. Four sequential 50 ms requests
take 200 ms; in parallel, 50 ms. See `loadProject` in `ProjectDetail.tsx`: it waits for the project first
(because it needs `main_scope`), then fires the rest at once.

**Reload after a change.** After any create/delete, the screen calls `reload()`. It's simple and always
correct, at the cost of a few extra requests. The project page deliberately loads everything in *one* query so
all three sections stay consistent.

**Judgement call: no data library yet.** The industry standard is TanStack Query (shared cache, retries,
refetch on window focus, optimistic updates). For five screens, a 40-line hook is easier to understand and
teaches what those libraries do. Switch when you notice: the same data fetched in many places, or wanting
instant UI updates before the server answers.

---

## 6. Errors: one path, actionable messages

openapi-fetch returns `{ data, error }` instead of throwing, which makes it easy to forget the error.
`unwrap()` (`api/errors.ts`) turns every failure into a thrown error, so one `try/catch` handles all of them.
`describeError()` turns them into messages:

| Failure | Message |
| --- | --- |
| API said 404/409 | The API's own `detail`, e.g. "Role … is still assigned to agents" |
| 422 validation | "Some fields are missing or invalid." |
| Network down (`TypeError`) | "The API is not reachable. Is it running?" |

**Rules for error UI:**
- Say what happened and what to do. No "Oops!", no apologies, no vague "Something went wrong" unless it truly
  is unknown.
- Show the error *where the action happened*: inside the dialog, under the search box.
- **Keep the user's input.** `FormModal` only closes on success; on failure the form stays filled in.
- `role="alert"` makes screen readers announce the error.
- Loading errors offer **Try again** (`Async`).

---

## 7. Forms

**Use the platform.** A real `<form>` gives you Enter-to-submit and `required` validation with no code.
`FormModal` reads values with `new FormData(form)` instead of tracking every keystroke in state:

```tsx
async function handleSubmit(event) {
  event.preventDefault()                         // otherwise the browser reloads the page
  const form = new FormData(event.currentTarget)
  if (await run(() => onSubmit(form))) onClose()
}
```

**Controlled vs uncontrolled.** "Uncontrolled" inputs (the DOM holds the value, you read it on submit) are
the default here. An input is *controlled* (`value` + `onChange` in React state) only when its value changes
other parts of the form: resource **type** decides which fields appear; agent **project** decides which roles
are listed. That's the rule: store in state what affects rendering.

**While saving:** the submit button is disabled and says "Saving…", which prevents double-submits. Labels say
what happens ("Create project", not "Submit"), and the same verb carries through.

**Labels:** `<Field>` wraps the input inside `<label>`, so clicking the label focuses the input and screen
readers announce it. Placeholders are not labels; they vanish when you type.

---

## 8. Destructive actions and preventing errors

Every delete goes through `ConfirmDialog`:
- The title **names the thing**: "Delete Apollo?", not "Are you sure?".
- The body says **what will happen**: "Its context scopes are deleted too. Its roles and resources stay."
- The button says **the action**: "Delete project", not "OK". It's red; Cancel is quiet.
- **Focus starts on Cancel**, so a reflexive Enter doesn't delete anything.

**Confirm only when it's destructive or cascades.** Removing a role from a project is one click to undo, so it
has no confirmation. Removing a *resource* from a project also strips it from every agent's context, so it
asks. Too many confirmations train people to click through them blindly.

**Prevent rather than report.** The API refuses to delete a project that still has agents. We know that from
`project.team`, so instead of a Delete button that fails, the dialog explains: "Delete its 2 agents first."
Likewise the Scopes tab only shows a delete button on *custom* scopes, and "New agent" is disabled with an
explanation when the project has no roles.

---

## 9. Accessibility is part of "done"

Not a separate pass: it falls out of using the right elements.

- **Buttons are `<button>`.** Clickable rows are buttons (`row-button`), not `<div onClick>`. A div can't be
  reached with Tab or activated with Enter.
- **Icon-only buttons need a name:** `aria-label="Delete Apollo"` (`DeleteButton`). Without it, a screen
  reader says "button". The icons themselves are `aria-hidden`.
- **Tabs follow the WAI-ARIA tabs pattern** (`components/SideTabs.tsx`): `role="tablist"/"tab"/"tabpanel"`,
  `aria-selected`, arrow keys move between tabs, and only the active tab is in the Tab order ("roving
  tabindex"). Keyboard users press Tab once to reach the tabs, not five times.
- **Native `<dialog>` with `showModal()`** traps focus, closes on Escape, makes the page behind it inert, and
  returns focus to the button that opened it. Building that by hand is hundreds of lines.
- **`aria-live="polite"`** on the role search results: screen readers announce new results as you type.
- **Visible focus:** `:focus-visible` shows the outline for keyboard users only.
- **Reduced motion:** dialog animations are turned off under `prefers-reduced-motion`.

**A bug the tests caught:** I first used React's `autoFocus` to focus Cancel. React focuses the element when it
mounts, but at that moment the `<dialog>` isn't open yet, so nothing can take focus. Then `showModal()` focused
the first button, the ✕. Fix: mark the element with `data-autofocus` and focus it in `Modal` *after*
`showModal()`. Lesson: test focus behaviour; it's invisible when you click with a mouse.

---

## 10. The typed API contract: fix problems at the source

The frontend's types are generated from the API's OpenAPI schema (`npm run generate`). When I wrote the UI,
TypeScript said `project.id` might be `undefined`. The API always sends it, but Pydantic documents fields with a
default (`id = Field(default_factory=uuid4)`) as optional.

Options were: (a) sprinkle `!` or `as` casts in the frontend, or (b) fix the schema. I chose (b): one line per
response model in `apps/api/models/*.py`:

```python
model_config = ConfigDict(json_schema_serialization_defaults_required=True)
```

Then regenerated `openapi.json` and `schema.d.ts`. All 246 API tests still pass, and every client now gets
correct types. **Why:** casts silence the compiler everywhere, including the day a field really does go missing.
Fixing the contract keeps the types honest.

(Related quirk: openapi-typescript treats request fields with defaults, like `role_ids: []`, as required, so
the frontend sends `role_ids: []` explicitly.)

---

## 11. CSS that scales

**Design tokens.** Every color, font and radius is a CSS variable at the top of `index.css`. Dark mode is just
a second set of values in `@media (prefers-color-scheme: dark)`; no component CSS changes.

**A type scale.** Sizes come from a ratio (1.25): `--step--1` … `--step-3`. A few sizes used consistently look
designed; many arbitrary sizes look messy.

**Layout with grid.** The shell is `grid-template-columns: 14rem minmax(0, 1fr)`. Each list row is a 3-column
grid (content, meta, action). `minmax(0, 1fr)` lets long text shrink and truncate instead of overflowing.

**Responsive.** Under 720px the rail becomes a row of tabs at the top; under 480px, row counts hide so
descriptions have room. I checked this at a real phone width (390px).

**Keep specificity flat.** Single-class selectors (`.row`, `.button`) with modifiers (`.button-danger`), so
styles don't fight each other.

**Lists, not cards.** Rows separated by hairlines scan faster than a grid of boxes, and they're what most
modern CSS kits *don't* default to.

---

## 12. Design: decide on purpose

Process used (from the frontend-design skill):
1. Write a small plan: palette (5–6 named colors), typefaces and their roles, layout sketch, one principle.
2. Check it against generic defaults ("would I produce this for any app?") and revise what's generic.
3. **Spend boldness in one place.** Here: the side rail, where the active tab is shaped like a folder tab
   joined to the page (the `::before`/`::after` inverted corners on `.tab[aria-selected='true']`).
   Everything else is quiet.
4. Motion only responds to the user: the drawer slides in because you opened it. Nothing animates on its own.

**Copy is design.** Use the user's words ("Resources Ada can see", not "context scope resources"). Use
sentence case. Make empty states invitations ("No roles yet." + a create button). Name actions consistently.

---

## 13. Testing like a user

Tests live in `src/App.test.tsx` and use React Testing Library:

- **Query by role and name**, the way a user (or screen reader) finds things:
  `screen.getByRole('button', { name: 'Delete Apollo' })`. If a test can't find a button by its name, a blind
  user can't either. Accessibility and testability reinforce each other.
- **`user-event`** types and clicks like a person, including focus and keyboard events.
- **Fake the network, not the components.** `test/fakeApi.ts` answers requests by `"METHOD /path"` and records
  them, so tests assert *what the UI sent*:
  ```ts
  expect(api.called('POST /api/project')[0].body).toEqual({ name: 'Gemini', … })
  ```
  The components run for real; only the server is pretend.
- **Test behaviour, not implementation:** "asks before deleting and only deletes after confirming", not "sets
  `deleting` state".
- jsdom (the fake browser in tests) lacks `<dialog>.showModal()`, so `test/setup.ts` adds a tiny stand-in.

Writing tests surfaced two problems: the autofocus bug (§9) and ambiguous button names (`/Apollo/` matched both
"Apollo" and "Delete Apollo", fixed with `/^Apollo/`).

---

## 14. Look at it in a real browser

Tests check behaviour; they don't check that it *looks* right. I ran the API with a scratch database, seeded
realistic data, and took screenshots with headless Chrome (desktop, dark mode, phone width, each dialog). That
caught a project's custom scope being listed above its main scope, and cramped rows on phones. Neither would
fail a test.

**Use realistic content.** "Spring launch: Ship the new onboarding flow…" shows truncation and wrapping
problems that "Test 1" hides.

---

## 15. Deliberately not done yet (and when to do it)

| Not yet | Why it waited | Do it when |
| --- | --- | --- |
| URL routing (`/projects/:id`) | Adds a dependency and concepts; tabs in state are enough to start | You want refresh/back button/shareable links to keep your place, which will be soon |
| TanStack Query | See §5 | Same data in many places, or want instant updates |
| Editing projects/roles (PUT) | Not in this round's brief | Next round: reuse `FormModal` with default values |
| Toast notifications ("Project deleted") | The list updating is feedback enough for now | Actions whose result isn't visible on screen |
| Optimistic updates | Reload is simple and correct | Actions feel slow on a real network |
| Self-hosted fonts | Google Fonts link is fine for development | Shipping to users (privacy, offline, speed) |

Knowing what to leave out, and writing down why, is as much a skill as building.
