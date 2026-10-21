# ExpiryCare API and Integration Guide

## Current architecture

The main UI is a static HTML/CSS/JavaScript prototype. Inventory, account, and retail prototype records still use browser `localStorage`; these screens are not fully wired to backend CRUD endpoints. The active Flask backend is the top-level `backend/` folder. Do not run the older duplicate scaffold formerly located at `frontend/backend/`.

## Run locally

From the extracted project root, follow `PBL_DEMO_GUIDE.md`. On Windows, the short path is:

```powershell
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
py -m backend.app
```

Open `http://127.0.0.1:5000/` and check `http://127.0.0.1:5000/api/health`. The app serves the frontend and API from one origin. The frontend can also use a local static server on common ports such as 8000 or 5500.

## `POST /api/guidance/chat`

Request: `{"message":"What if the expiry date is missing?"}`.

- With `GEMINI_API_KEY`, the backend tries Google Gemini; with `OPENAI_API_KEY`, it can use OpenAI as an alternative. Google AI Studio free-tier quotas/eligibility can vary.
- Without a key, or when providers are unavailable, it returns HTTP 200 with `mode: "offline_knowledge_base"` and a deterministic, conservative answer. This fallback is not generative AI and must not be presented as such.
- All responses include a healthcare disclaimer. The assistant cannot certify product safety.

## `POST /api/products/analyze-label`

Request JSON: `{"imageName":"label.jpg","imageType":"image/jpeg","imageData":"data:image/jpeg;base64,..."}`. The backend attempts configured vision if `OPENAI_API_KEY` is set, then local Tesseract OCR. If no readable text is found, it asks for manual entry. OCR may misread dates: verify all values against the physical package. The backend host needs Tesseract installed as an operating-system executable and the Python packages in `backend/requirements.txt`.

## Barcode lookup

`GET /api/products/barcode/<digits>` uses Open Food Facts and requires internet access. It can identify supported food products but does not reliably provide an expiry date.

## Firestore and security

Live Firestore is only enabled after configuring a Firebase project, Firestore database, and valid service-account/Application Default Credentials, then setting `FIRESTORE_ENABLED=true`. Without that, the backend uses a non-persistent in-memory development store. Do not commit credentials or put provider keys in frontend code. The existing frontend localStorage flows are not a secure multi-user data store.
