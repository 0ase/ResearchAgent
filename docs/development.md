# Development guide

## Services

Run the FastAPI service and Next.js app in separate terminals:

```powershell
& .\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
npm --prefix web run dev -- --hostname 127.0.0.1 --port 3000
```

The frontend reads `NEXT_PUBLIC_API_BASE_URL` and defaults to `http://127.0.0.1:8000`. Keep `CORS_ORIGINS` aligned with the browser URL.

## Configuration and storage

The first-run dialog writes `DEEPSEEK_API_KEY` to the project-root `.env` file. It can also be replaced from Settings. The key is never returned by the settings API, logged, or stored in SQLite.

`RESEARCH_RUNNER_MODE=demo` is deterministic and network-free. SQLite is created automatically at `DATABASE_PATH`; startup applies numbered migrations. Generated databases, cached papers, figures, virtual environments, and frontend build artifacts are ignored by Git.

## API contract

The backend is the source of truth for OpenAPI:

```powershell
npm --prefix web run api:export
npm --prefix web run api:generate
npm --prefix web run api:check
```

Generated files are `web/openapi.json` and `web/lib/api/schema.d.ts`.

## Verification

```powershell
& .\.venv\Scripts\python.exe -m pytest backend/tests -q
& .\.venv\Scripts\python.exe -m compileall -q backend
npm --prefix web run lint
npm --prefix web run typecheck
npm --prefix web run test -- --run
npm --prefix web run build
npm --prefix web run test:e2e
```

For a local browser test stack, run `scripts/start_dev.ps1`. When Playwright's bundled browser is unavailable, the project configuration uses an installed Chrome executable.

Both start scripts use `.venv\Scripts\python.exe` by default. CI or advanced local setups may set `RESEARCH_AGENT_PYTHON` to another Python executable with the project dependencies installed.

## Common issues

- `409 ACTIVE_TASK_EXISTS`: only one task may be active; open or cancel it before starting another.
- `RESULT_NOT_READY`: the task is still running or has not published its result.
- Missing replay/evidence panels on older history is expected when stored capability flags are false.
- Provider warnings in Demo mode are intentional fixtures; the report still completes with a partial warning.
- If a forced stop leaves a SQLite lock, stop the backend and remove only the configured database and its matching `-wal`/`-shm` files.
