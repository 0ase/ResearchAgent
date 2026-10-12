## Windows: double-click startup

After installing the BIGONE Conda environment, backend dependencies and frontend
dependencies, double-click **启动B1GONE.bat** in the project root. The launcher
starts the FastAPI backend on port 3000 and the current React frontend on port
5173, waits for both services, and opens http://127.0.0.1:5173/.

Keep the launcher window open. Press Enter or Q to stop its two services;
Ctrl+C also exits. Output is saved under `logs/launcher-*.log`. The launcher
does not automatically install dependencies or terminate services started in
other terminals. If a port is occupied, stop that service in its original
terminal before retrying.

Optional commands from the project root:

```powershell
.\启动B1GONE.bat -Observe    # Same backend, with full usage/retrieval observation
.\启动B1GONE.bat -Stop       # Stop services owned by the launcher
.\启动B1GONE.bat -CheckOnly  # Check dependencies without starting services
```

If Conda/npm are not found when double-clicking, run the BAT with explicit paths:

```powershell
.\启动B1GONE.bat -CondaPath "D:\anaconda\condabin\conda.bat" -NpmPath "D:\nodejs\npm.cmd"
```

The normal launcher uses `backend.main:app`; `-Observe` selects
`evaluation.observed_app:app`. Backend reload is disabled for daily use. The
existing development command below remains available.

## How to start manually

```powershell
conda activate BIGONE
pip install -r requirements.txt
Copy-Item .env.example .env
```

Fill the API keys and contact email in `.env`, then open two terminals.

For Agent model calls, configure either `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`
with a key accepted by `BASE_URL`. If both are configured, `OPENAI_API_KEY` takes
precedence. Empty or whitespace-only values count as unconfigured. Embeddings
continue to use the separate `DASHSCOPE_API_KEY`.

Backend:

```powershell
cd D:\BIGONE
powershell -ExecutionPolicy Bypass -File scripts/start_backend.ps1 -Reload
```

The launcher selects the `BIGONE` Conda environment even when the terminal is in
`base`. It listens on port 3000 and watches only backend source files. Stop an
existing backend with Ctrl+C before starting this command. For a run without
automatic reload, omit `-Reload`.

Alternatively, activate `BIGONE` first and run
`python -m uvicorn backend.main:app --host 127.0.0.1 --port 3000 --reload --reload-dir backend`.

Current React frontend:

```powershell
cd D:\BIGONE\web
npm ci  # First setup only
npm run dev
```

Open http://127.0.0.1:5173/ for real research. Adding `?demo=1` uses simulated
research data. See [the frontend guide](web/README.md) for usage and checks.

Legacy Streamlit frontend:

```powershell
conda activate BIGONE
cd D:\BIGONE
python -m streamlit run frontend/streamlit_app.py
```

The frontend connects to `http://127.0.0.1:3000` by default. If the backend runs on another
port, set `BACKEND_URL` in the frontend terminal before starting Streamlit:

```powershell
$env:BACKEND_URL = "http://127.0.0.1:8000"
python -m streamlit run frontend/streamlit_app.py
```

Set `BACKEND_URL` to the port used by Uvicorn. Restart Streamlit after changing
this configuration; an existing process retains the environment it loaded at startup.

## Homepage metrics belong to this checkout

The homepage reads `web/public/metrics/summary.json`, generated from this
checkout's local logs, database and observation records. All of those local
inputs and the generated snapshot are Git-ignored: cloning the repository or
downloading its source does not include the developer's measurements. A fresh
checkout shows that no statistics are available until its user generates a
snapshot. `?demo=1` research does not populate real metrics.

After real research, use the BIGONE environment to generate the local snapshot:

```powershell
python -m evaluation.update_metrics
# If real quality annotations exist:
python -m evaluation.update_metrics --labels evaluation/labels.jsonl
```

Then click the homepage refresh button. `-Observe` records complete usage and
retrieval IDs; quality scores still require independent annotations. See
[the evaluation guide](evaluation/README.md).

Building the frontend copies any snapshot then present in `web/public` into
`web/dist`. Distributing that built directory or deploying it as a static site
therefore exposes the included build-time snapshot. Updating `web/public` later
does not update an already-built `dist`; rebuild it to publish new readings.
Official benchmark results should be separately identified with their test set,
version and evaluation method, rather than presented as each user's local runs.

## Backend error tracing

HTTP responses include `X-Request-ID`; HTTP and SSE errors return a stable error
code and `error_id`. Structured logs with exception chains are written to
`logs/backend.log` with automatic rotation. See
[the backend error-handling guide](backend/ERROR_HANDLING.md) for error codes,
log lookup, configuration and development conventions.

Run backend regression tests:

```powershell
python -m pytest backend/tests -q
```

## Search and screening

Research retrieves 80–100 deduplicated candidates and orders them by topic overlap,
metadata completeness and available citation/venue information. Screening processes
five papers per call with a 6,000-token budget and stops when the requested number
passes the main relevance gates. Missing scores are retried in smaller groups;
65–69-point supplemental papers are considered only after candidates are exhausted.
See
[the search and screening guide](backend/SEARCH_AND_SCREENING.md) for criteria,
configuration, candidate-count failures and how selected evidence reaches the report.
