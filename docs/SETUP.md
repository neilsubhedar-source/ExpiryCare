# ExpiryCare Setup Guide

For the most current setup steps and PBL limitations, follow [`../PBL_DEMO_GUIDE.md`](../PBL_DEMO_GUIDE.md). The canonical Flask backend is the top-level `backend/` folder; do not run the older optional scaffold under `frontend/backend/`.

## Quick setup (Windows)

From the extracted `ExpiryCare_Complete_Integration` project root:

```powershell
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
py -m backend.app
```

Open `http://127.0.0.1:5000/` and check `http://127.0.0.1:5000/api/health`.

## Automated tests

After dependencies are installed, run from the project root:

```powershell
py -m pytest backend\tests -v
```

The current editing environment could not run the full Flask test suite, so verify the output on the team's laptop. Do not claim all tests pass until they have actually run.

## Storage and AI notes

- Firestore requires a Firebase project and valid credentials. Without them, the backend uses a non-persistent in-memory development store.
- The main frontend inventory/account/retail flows still use `localStorage` and are not fully wired to backend CRUD endpoints.
- Chatbot works with an offline deterministic knowledge base if no OpenAI API key is configured.
- Label scanning uses local Tesseract OCR when available and needs manual verification.
