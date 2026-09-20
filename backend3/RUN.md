# Judge Demo

Run from the repository root. Before starting, ensure `.env` contains `OPENROUTER_API_KEY` and `CONCEPTBRIDGE_DEMO_MODE=false`.

```powershell
.\venv\Scripts\python.exe scripts\seed_demo.py; .\venv\Scripts\python.exe -m uvicorn demo.conceptbridge.api:app --host 127.0.0.1 --port 8000
```

Open the judge demo at http://127.0.0.1:8000/docs.
