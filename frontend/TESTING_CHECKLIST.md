# ExpiryCare Testing Checklist

## Automated checks run in the current editing environment
- [x] Python bytecode compilation for backend files — passed.
- [x] JavaScript syntax checks for `app.js`, `retail-intelligence.js`, and `retail-catalog.js` — passed.
- [x] Offline chatbot smoke tests for common expiry questions — passed.
- [x] Local Tesseract OCR smoke test on a generated sample label (`EXP: 2027-05-21`) — passed.
- [x] Existing retail rule JavaScript test was retained in the project; run it locally with Node to reconfirm.

## Not verified here
- [ ] Full Flask pytest suite (Flask was unavailable in the editing environment and package downloads could not be reached). Run `python -m pytest backend/tests -v` after installing `backend/requirements.txt`.
- [ ] Full browser click-through of registration/login, product CRUD, dashboard, alerts, profile, scanner, and responsive navigation.
- [ ] Real camera permissions and live Open Food Facts requests.
- [ ] OCR on actual photos from the team's phone; extracted dates must be manually verified.
- [ ] Firestore persistence with a real Firebase project and credentials.
- [ ] End-to-end API wiring for inventory/account/retail CRUD. Those main frontend flows currently use localStorage.

## Safety and demo notes
- The offline chatbot is a deterministic knowledge base, not a generative AI model.
- Do not claim Firestore persistence until configured and verified.
- Do not treat barcode lookup or OCR output as proof that a product is safe.
