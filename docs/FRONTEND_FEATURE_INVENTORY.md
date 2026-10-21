# Frontend Feature Inventory & Integration Contract

This inventory documents all pre-existing frontend features discovered in the ExpiryCare codebase, their UI triggers, data expectations, and corresponding backend integrations.

---

## 1. Feature Classification Matrix

| Feature | Location | Type | Backend Endpoint | Status |
| :--- | :--- | :--- | :--- | :--- |
| **System Health Check** | System | Backend-Required | `GET /api/health` | Implemented |
| **User Registration** | `register.html` | Backend-Required | `POST /api/auth/register` | Implemented |
| **User Login** | `login.html` | Backend-Required | `POST /api/auth/login` | Implemented |
| **User Profile Management** | `profile.html` | Backend-Required | `GET/PUT /api/auth/profile` | Implemented |
| **Notification Preferences** | `profile.html`, `alerts.html` | Backend-Required | `GET/PUT /api/auth/settings` | Implemented |
| **Forgot Password** | `forgot-password.html` | Backend-Required | `POST /api/auth/forgot-password` | Implemented |
| **Personal Inventory List** | `inventory.html` | Backend-Required | `GET /api/products` | Implemented |
| **Add Product** | `add-product.html` | Backend-Required | `POST /api/products` | Implemented |
| **Product Details & Evidence**| `product-details.html` | Backend-Required | `GET /api/products/<id>` | Implemented |
| **Edit Product** | `edit-product.html` | Backend-Required | `PUT/PATCH /api/products/<id>` | Implemented |
| **Delete Product** | `inventory.html`, `product-details.html`| Backend-Required | `DELETE /api/products/<id>` | Implemented |
| **Load Demo Data** | `dashboard.html` | Backend-Required | `POST /api/products/demo` | Implemented |
| **Dashboard Statistics** | `dashboard.html` | Backend-Required | `GET /api/dashboard/summary` | Implemented |
| **Alert Feeds** | `alerts.html` | Backend-Required | `GET /api/alerts` | Implemented |
| **Barcode Lookup** | `add-product.html` | External-Dependent | `GET /api/products/barcode/<code>` | Implemented & Proxied |
| **Barcode Camera Scan** | `add-product.html` | Frontend-Only | Browser `BarcodeDetector` | Preserved |
| **Label OCR / Vision Analysis**| `add-product.html` | External-Dependent | `POST /api/products/analyze-label` | Implemented (503 Fallback) |
| **Healthcare Guidance Chat** | `healthcare-guidance.html`| External-Dependent | `POST /api/guidance/chat` | Implemented (503 Fallback) |
| **Retail Summary & FEFO** | `retail-intelligence.html`| Backend-Required | `GET /api/retail/summary`, `/batches` | Implemented |
| **Retail Clearance Workflow**| `retail-intelligence.html`| Backend-Required | `GET/POST /api/retail/clearance` | Implemented |
| **Retail Transfers Workflow**| `retail-intelligence.html`| Backend-Required | `GET/POST /api/retail/transfers` | Implemented |
| **Retail Demo Seeding** | `retail-intelligence.html`| Backend-Required | `POST /api/retail/demo/seed` | Implemented |
| **Customer Store Catalog** | `retail-catalog.html` | Backend-Required | `GET /api/retail/catalog` | Implemented |
| **About Step Walkthrough** | `about.html` | Frontend-Only | DOM event handlers | Preserved |
| **Landing Navigation / UI** | `index.html` | Frontend-Only | CSS animations & anchors | Preserved |

---

## 2. Detailed Feature Contract

### 2.1 User Authentication (`register.html`, `login.html`)
- **Action**: User fills name, email, password, and submits.
- **Input Format**: `{ "name": "...", "email": "...", "password": "..." }`
- **Backend Responsibility**: Validate email format, verify password minimum length (8 chars), check for duplicates, hash password with PBKDF2-SHA256, create record in Firestore, generate signed JWT token.
- **Expected Success Response**: HTTP 200/201 `{ "success": true, "data": { "token": "...", "user": { "id": "...", "email": "..." } } }`
- **Expected Error Response**: HTTP 400/401 `{ "success": false, "error": "Descriptive message" }`

### 2.2 Personal Inventory CRUD (`add-product.html`, `edit-product.html`, `inventory.html`)
- **Action**: User manages personal medicines, groceries, personal care, or other items.
- **Fields Supported**:
  - `name`: string (defaults to "Unidentified Product" if empty on add)
  - `category`: `medicine` | `grocery` | `personal-care` | `other`
  - `quantity`: positive integer >= 1
  - `purchaseDate`: optional `YYYY-MM-DD`
  - `expiryDate`: optional `YYYY-MM-DD`
  - `manufacturingDate`: optional `YYYY-MM-DD`
  - `verifiedShelfLifeDays`: optional integer > 0
  - `shelfLifeSource`: optional string
  - `batchNumber`: optional string
  - `notes`: optional string
  - `barcode`: optional string
- **Date Boundary Validation**: Expiry date must not precede purchase date.
- **Status Classification Output**:
  - `expired`: days < 0
  - `expiring-soon`: 0 <= days <= 30
  - `active`: days > 30
  - `unidentified`: name missing or "Unidentified Product"
  - `estimated-expiry`: calculated from mfg date + shelf life
  - `expiry-unknown`: missing expiry date

### 2.3 Product Label Analysis (`add-product.html`)
- **Trigger**: Click "Analyze with AI / OCR".
- **Payload**: `{ "imageName": "photo.jpg", "imageType": "image/jpeg", "imageData": "data:image/jpeg;base64,..." }`
- **Response**:
  - When configured: HTTP 200 with extracted `{ name, category, manufacturingDate, expiryDate, batchNumber }`.
  - Without a live vision key, the backend attempts local Tesseract OCR; unreadable images return an error that prompts manual entry. Verify extracted dates manually.
- **Frontend Behavior**: Frontend displays status message without crashing, allowing manual entry.

### 2.4 Healthcare Guidance Chatbot (`healthcare-guidance.html`)
- **Trigger**: Submit question in chatbot form.
- **Payload**: `{ "message": "Can I use expired eye drops?" }`
- **Response**:
  - HTTP 200 with a live provider response when configured, or `mode: "offline_knowledge_base"` with deterministic guidance when not configured. The offline fallback is not generative AI.
- **Frontend Behavior**: Frontend renders guidance reply or educational fallback message.

### 2.5 Retail Intelligence & Store Availability (`retail-intelligence.html`, `retail-catalog.html`)
- **Batches**: FEFO ordered, verified expiry, at-risk unit calculations (<= 7 days).
- **Clearance**: Computes demand surplus against 14-day window; 25% discount for <= 6 days, 15% for <= 14 days. Provides Approve/Reject review.
- **Transfers**: Complete lifecycle: `Requested` -> `Approved` (reserves stock) -> `Dispatched` (deducts stock) -> `Received` (adds destination stock) -> `Completed`. Blocks duplicate pending transfers and invalid transitions.
- **Customer Catalog**: Excludes unverified and expired batches from sellable inventory; groups stock into Out of stock (0), Low stock (1-5), and In stock (>5).
