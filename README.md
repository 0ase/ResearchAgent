## How to start

```powershell
conda activate BIGONE
pip install -r requirements.txt
Copy-Item .env.example .env
```

Fill the API keys and contact email in `.env`, then open two terminals.

Backend:

```powershell
conda activate BIGONE
cd D:\BIGONE
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Frontend:

```powershell
conda activate BIGONE
cd D:\BIGONE
streamlit run frontend/streamlit_app.py
```
