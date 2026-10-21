# ExpiryCare — urgent PBL demo guide

## Important truth about the current integration

- The guidance chatbot now works without an API key using a local, deterministic knowledge base. It is **not generative AI** unless a provider key is configured. Optional live providers: Google Gemini (`GEMINI_API_KEY`, with free-tier quotas/eligibility subject to Google) or OpenAI (`OPENAI_API_KEY`). It labels the offline mode in its response.
- Label scanning now attempts local Tesseract OCR without an API key, and falls back to manual entry if the image is unreadable. OCR can misread dates; verify all fields against the package. The machine running the backend needs the Tesseract OCR executable installed, plus the Python packages in `backend/requirements.txt`.
- Barcode lookup uses the public Open Food Facts API and requires internet access. A barcode does not prove an expiry date.
- Firestore is **not active unless** a Firebase project and service-account/Application Default Credentials are configured. Without those credentials, the backend's in-memory development store is not durable and data is lost when the server restarts.
- The existing main frontend's product, account, and retail prototype data still uses browser `localStorage`. Do not claim that those screens are fully backed by Firestore. The backend REST routes exist, but the current frontend is not end-to-end integrated for every CRUD operation.

## Run locally on Windows

1. Install Python 3.10+ if not already installed.
2. Open Command Prompt in the extracted `ExpiryCare_Complete_Integration` folder.
3. Create and activate a virtual environment:
   ```bat
   py -m venv .venv
   .venv\Scripts\activate
   ```
4. Install backend packages:
   ```bat
   py -m pip install -r backend\requirements.txt
   ```
5. Install the Tesseract OCR Windows application separately and ensure its install directory is on PATH. If it is not on PATH, set `pytesseract.pytesseract.tesseract_cmd` in `backend/services/label_service.py` to the installed `tesseract.exe` path.
6. Start the backend from the project root:
   ```bat
   py -m backend.app
   ```
7. Open `http://127.0.0.1:5000/` in your browser. Use Flask to serve the frontend rather than opening HTML files directly.
8. Check `http://127.0.0.1:5000/api/health` before the demo.

## Demo checklist

- Open Healthcare Guidance and ask: “What if the expiry date is missing?” Confirm the answer says **offline knowledge base** when no AI key is set.
- Try “Is expired milk safe to drink?” and “Can a barcode tell me the expiry date?”
- For label scanning, use a sharp, well-lit label image with large printed text. Confirm the extracted values manually. If it fails, use manual entry and explain OCR limitations.
- Try barcode lookup only with internet access.
- Show the dashboard/inventory as a browser-local prototype; do not describe it as Firestore-backed until Firebase credentials and frontend API integration are completed and tested.

## Optional Gemini setup

If you already have a Google AI Studio API key, put it in `backend/.env` as `GEMINI_API_KEY=...` and set `GEMINI_MODEL` if needed. Do not share or commit the key. The provider may enforce quotas or change availability; the offline chatbot still works without it.

## Firebase setup is an external prerequisite

To use real Firestore, create/choose a Firebase project, enable Cloud Firestore, create a service account with least-privilege access, securely place its JSON key outside source control, set `FIRESTORE_ENABLED=true` and `GOOGLE_APPLICATION_CREDENTIALS` to that file path, and verify the backend health/configuration. Never upload the service-account key to GitHub or include it in the ZIP.
