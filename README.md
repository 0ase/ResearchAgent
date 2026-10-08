## How to start

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

Frontend:

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
