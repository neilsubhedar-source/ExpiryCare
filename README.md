# ExpiryCare — Smart Expiry Tracker & Healthcare Website (Student Prototype)

**Demo readiness note:** This is a student prototype. See [PBL_DEMO_GUIDE.md](PBL_DEMO_GUIDE.md) for verified limits and setup. The offline chatbot and local OCR have smoke-tested successfully in the current editing environment; the full Flask pytest suite could not be run here because Flask dependencies were not installed and package download access was unavailable.
---

## 1. Project Overview

**Important:** The current frontend is not fully connected to Firestore. Inventory/account/retail prototype state in `frontend/js/app.js` and retail scripts uses browser `localStorage`. Backend REST routes are present, but full end-to-end CRUD wiring and live Firestore credentials remain setup/integration work. Do not describe this ZIP as fully production-ready.

**ExpiryCare** is a student prototype for a smart expiration tracking platform and healthcare website designed for consumers, households, healthcare practitioners, and retail store managers.

### Core Capabilities
- **Personal Inventory Management**: Track expiry dates, purchase dates, manufacturing dates, shelf life, and batch codes across medicine, grocery, personal care, and other household essentials.
- **Precision Expiry Intelligence**: Zero off-by-one status classifications:
  - `expired` (< 0 days remaining)
  - `expiring-soon` (0 to 30 days remaining)
  - `active` (> 30 days remaining)
  - `estimated-expiry` (calculated from manufacturing date + verified shelf-life evidence)
  - `expiry-unknown` / `unidentified` (transparent indicators for unverified items)
- **Healthcare Guidance Chatbot**: Practical, cautious guidance on product storage, expiration safety, and review reminders with medical disclaimers.
- **Product Scanner & Vision Integration**: Barcode lookup (via Open Food Facts) and OCR label photo inspection for dates and batch numbers.
- **Retail Intelligence (FEFO & Transfers)**: Multi-branch lot tracking, First Expired First Out prioritization, at-risk batch calculations (<= 7 days), surplus-driven clearance discounts, and an atomic 5-stage inter-branch transfer workflow.
- **Public Store Catalog**: Customer-facing real-time product availability excluding unverified, expired, or reserved stock.

---

## 2. Verified Architecture

The repository is organized into frontend and backend layers. The current frontend/backend connection is partial, as noted above; this folder layout alone does not mean every screen is integrated.

```text
ExpiryCare_Complete_Integration/
├── frontend/             # HTML/CSS/JS prototype UI
│   ├── index.html        # Landing page
│   ├── dashboard.html    # User analytics dashboard
│   ├── inventory.html    # Personal inventory table
│   ├── add-product.html  # Scanner and item creation
│   ├── alerts.html       # Expiry alerts
│   ├── retail-intelligence.html  # Retail manager portal
│   ├── retail-catalog.html       # Public store availability
│   ├── css/styles.css    # Unified styles
│   └── js/app.js         # Frontend controller
├── backend/              # Production-grade Python / Flask API layer
│   ├── app.py            # Application factory & runner
│   ├── wsgi.py           # Gunicorn production entry point
│   ├── requirements.txt  # Dependencies
│   ├── .env.example      # Environment template
│   ├── config/           # Base, Dev, Prod, Test configurations
│   ├── middleware/       # JWT/Firebase Auth & Error Handlers
│   ├── repositories/     # Firestore database operations
│   ├── services/         # Domain business logic & expiry math
│   ├── routes/           # REST API Blueprints (/api/*)
│   ├── utils/            # Precision date math, validators, responses
│   └── tests/            # Automated pytest suite
├── firebase/             # Production Firestore security rules & composite indexes
│   ├── firestore.rules
│   ├── firestore.indexes.json
│   └── README.md
├── docs/                 # Engineering documentation & reports
│   ├── ARCHITECTURE.md
│   ├── FRONTEND_FEATURE_INVENTORY.md
│   ├── API_CONTRACT.md
│   ├── DATABASE_SCHEMA.md
│   ├── SETUP.md
│   ├── DEPLOYMENT.md
│   ├── TEST_REPORT.md
│   └── FRONTEND_INTEGRITY_REPORT.md
└── README.md             # This document
```

---

## 3. Technology Stack

- **Backend**: Python 3.10+, Flask 3.x, Gunicorn, RESTful JSON API
- **Database**: Firestore repository layer is implemented; live Firestore requires external Firebase credentials. Without them, the backend uses a non-persistent in-memory development store.
- **Authentication**: Salted PBKDF2-SHA256 password hashing, standard HMAC-SHA256 JWT tokens, and Google Firebase ID token verification
- **Testing**: pytest test suite included; not all tests were executable in the current editing environment.
- **Frontend**: HTML5, CSS3, vanilla JavaScript (two files intentionally adjusted for API/chatbot fixes)

---

## 4. Prerequisites

1. **Python 3.10 or newer** installed on your system.
2. **pip** (Python package installer).
3. A modern web browser.

---

## 5. Quickstart: Run Backend Locally (Beginner Friendly)

### Step 1: Open a Terminal in the extracted project root
```bash
cd ExpiryCare_Complete_Integration
```

### Step 2: Create and Activate a Virtual Environment
- **Windows (PowerShell)**:
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
- **macOS / Linux**:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### Step 3: Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### Step 4: Configure Environment Variables
Copy `.env.example` to `.env`:
- **Windows**: `Copy-Item backend/.env.example backend/.env`
- **macOS/Linux**: `cp backend/.env.example backend/.env`

*(No external credentials are required to start developing or running tests; the system automatically runs with an in-memory document store out of the box!)*

### Step 5: Run the Automated Test Suite
```bash
pytest backend/tests -v
```
**Review the test output; do not assume all tests pass until you run them locally.**

### Step 6: Start the Backend Server from the project root
```bash
python -m backend.app
```
The server will start on: **`http://127.0.0.1:5000`**  
Verify health by visiting: **`http://127.0.0.1:5000/api/health`**

---

## 6. Run the Frontend Locally

You can also let Flask serve the frontend from `http://127.0.0.1:5000/` (recommended). Alternatively, in a **new terminal window**, navigate to `frontend/` and start a local static server:

```bash
cd ExpiryCare_Complete_Integration/frontend
python -m http.server 8000
```

Open your browser and navigate to:
👉 **`http://localhost:8000`**

---

## 7. Connecting Frontend to Backend

- The frontend chooses a same-origin `/api` endpoint when Flask serves the pages. When using a local static server on port 8000/5500, it points to `http://127.0.0.1:5000/api`. For a separately deployed frontend, set `window.EXPIRYCARE_API_BASE` before `js/app.js`.
- Only the chatbot and label-analysis workflows currently call the Flask API from the main frontend. Do not assume all inventory/account/retail CRUD operations are connected to Firestore.
- For production deployments, see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for how a simple Vercel/Netlify rewrite proxies `/api/*` to Render with zero modifications to frontend code!

---

## 8. Firebase Configuration (When Connecting Live Firestore)

1. Create a project in the [Firebase Console](https://console.firebase.google.com/).
2. Enable **Cloud Firestore** in production mode.
3. Download your service account private key JSON from:
   **Project Settings** ⚙️ > **Service accounts** > **Generate new private key**.
4. In your `backend/.env`, set:
   ```env
   FIRESTORE_ENABLED=true
   GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
   FIREBASE_PROJECT_ID=your-project-id
   ```
5. Deploy security rules and indexes using Firebase CLI:
   ```bash
   firebase deploy --only firestore:rules,firestore:indexes
   ```
   *(See [firebase/README.md](firebase/README.md) for complete details).*

---

## 9. Production Deployment

- **Backend**: Deploy on Render or Railway using Gunicorn command:
  ```bash
  gunicorn --bind 0.0.0.0:$PORT wsgi:app
  ```
- **Frontend**: Deploy on Vercel, Netlify, or Cloudflare Pages as a static site.
- See the complete step-by-step walkthrough in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

---

## 10. Common Errors & Troubleshooting

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| `CORS error in browser` | Frontend origin not in `CORS_ORIGINS` | Add your frontend origin (e.g. `http://localhost:8000`) to `CORS_ORIGINS` in `.env`. |
| Chatbot answers from offline knowledge base | `OPENAI_API_KEY` is not set or provider unavailable | Expected: it still gives conservative, deterministic guidance and labels offline mode. It is not generative AI without a provider key. |
| `503 Firestore initialization failed` | Invalid path in `GOOGLE_APPLICATION_CREDENTIALS` | Ensure the path points to a valid JSON key file, or leave `FIRESTORE_ENABLED=false` for local mode. |
| `401 Unauthorized` | Missing or expired token | Log in via `/api/auth/login` and include `Authorization: Bearer <token>` in request headers. |
| `ModuleNotFoundError` | Virtual environment not active | Activate virtualenv (`.\venv\Scripts\Activate.ps1` or `source venv/bin/activate`) before running commands. |

---

## 11. Complete Documentation Index

- 📘 [System Architecture](docs/ARCHITECTURE.md)
- 📋 [Frontend Feature Inventory](docs/FRONTEND_FEATURE_INVENTORY.md)
- 🔌 [REST API Contract](docs/API_CONTRACT.md)
- 🗄️ [Firestore Database Schema](docs/DATABASE_SCHEMA.md)
- 🛠️ [Local Setup Guide](docs/SETUP.md)
- 🚀 [Production Deployment Guide](docs/DEPLOYMENT.md)
- 🧪 [Automated Test Report / limitations](docs/TEST_REPORT.md)
- 🔒 [Frontend Integrity Notes](docs/FRONTEND_INTEGRITY_REPORT.md)
