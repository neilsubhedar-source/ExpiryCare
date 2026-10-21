# ExpiryCare Verification Report — Current ZIP

**Status:** Partial verification only. The full Flask pytest suite was **not run** in the editing environment because Flask was not installed and package downloads were unavailable. Do not present this as a full passing test report.

## Smoke tests actually run

- Python syntax compilation (`python -m compileall -q backend`): passed.
- JavaScript syntax checks (`node --check` for `app.js`, `retail-intelligence.js`, and `retail-catalog.js`): passed.
- Retail rule and transfer lifecycle tests (`node frontend/tests/test_retail_rules.js`): passed.
- Offline chatbot service smoke test for an expired-milk question: passed; returned HTTP-style service status 200 and `mode=offline_knowledge_base`.
- Local Tesseract OCR smoke test on a generated sample label containing `EXP: 2027-05-21`: passed; extracted `expiryDate=2027-05-21`.

## Important tests to run on the team's laptop

From the extracted project root, after installing `backend/requirements.txt`, run:

```bash
python -m pytest backend/tests -v
```

Resolve any failures before claiming the backend test suite passes. The local smoke tests do not prove that every route, login flow, database operation, deployment, or browser workflow is correct.

## Current known limitations

- Live Firestore requires a Firebase project and valid credentials. Without them, backend persistence is an in-memory development store and is lost when the process restarts.
- Main frontend inventory/account/retail state still uses browser `localStorage`; not all CRUD actions call backend endpoints.
- Chatbot works without credentials through a deterministic offline knowledge base. This is not a generative AI model. Live AI requires a valid provider key (Google Gemini or OpenAI).
- Label scan uses local Tesseract OCR when available; OCR can misread values and every extracted date must be verified manually.
- Barcode lookup depends on internet access and the Open Food Facts service.

## Additional regression checks performed after the original report

- Chatbot direct-service smoke checks for “Is expired milk safe to drink?”, “What if the expiry date is missing?”, and “Can a barcode tell me the expiry date?” returned status 200 in offline knowledge-base mode.
- Regression found and fixed: the exact phrasing “What if the expiry date is missing?” previously missed the dedicated missing-date rule. Added matching phrases and confirmed the answer now advises treating the date as unknown.
- Regression found and fixed: OCR could incorrectly report the manufacturing date as the expiry date when a product name contained “Expiry” (e.g. “ExpiryCare Demo Product”). Date extraction now requires a date associated with the relevant label and avoids choosing an unrelated earlier date. A generated sample label with MFG `2026-01-15` and EXP `2027-05-21` returned those two distinct dates correctly.
- All frontend JavaScript files passed `node --check`.
- `node frontend/tests/test_retail_rules.js` passed both retail rules and transfer lifecycle smoke tests.
- `python -m compileall -q backend` passed.
- Full Flask API / health endpoint and browser form workflow could not be executed in this environment: Flask and Flask-CORS are not installed, package installation is blocked by unavailable network access, and the browser automation environment blocks local-page navigation. Do not treat these as passed tests.
