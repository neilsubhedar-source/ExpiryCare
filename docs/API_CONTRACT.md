# ExpiryCare REST API Specification & Contract

All endpoints communicate using JSON over HTTP/HTTPS.
Base URL (local development): `http://127.0.0.1:5000/api`
Base URL (production): `https://<your-render-or-custom-domain>/api`

---

## 1. System Endpoints

### `GET /api/health`
- **Auth**: None
- **Description**: Verifies service availability, persistence mode, and external AI configuration.
- **Response 200**:
  ```json
  {
    "status": "ok",
    "service": "ExpiryCare API",
    "version": "2.0.0",
    "persistence": "connected-google-cloud-firestore | in-memory-document-store-unless-firestore-configured",
    "ai": "live-provider-configured | not-configured-unless-provider-key-present",
    "timestamp": "2026-10-20T00:00:00Z"
  }
  ```

---

## 2. Authentication Endpoints

### `POST /api/auth/register`
- **Auth**: None
- **Request Body**:
  ```json
  {
    "name": "Jane Doe",
    "email": "jane@example.com",
    "password": "SecurePassword123"
  }
  ```
- **Response 201**:
  ```json
  {
    "success": true,
    "message": "Registration successful",
    "data": {
      "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "user": {
        "id": "user_a1b2c3d4",
        "name": "Jane Doe",
        "email": "jane@example.com",
        "settings": { "alertThresholds": [3], "defaultSort": "expiry-date" }
      }
    }
  }
  ```
- **Error 400**: Duplicate email, invalid email, or short password.

### `POST /api/auth/login`
- **Auth**: None
- **Request Body**:
  ```json
  {
    "email": "jane@example.com",
    "password": "SecurePassword123"
  }
  ```
- **Response 200**:
  ```json
  {
    "success": true,
    "message": "Login successful",
    "data": {
      "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "user": {
        "id": "user_a1b2c3d4",
        "name": "Jane Doe",
        "email": "jane@example.com",
        "settings": { "alertThresholds": [3], "defaultSort": "expiry-date" }
      }
    }
  }
  ```
- **Error 401**: Incorrect email or password.

### `GET /api/auth/profile`
- **Auth**: Required (`Authorization: Bearer <token>`)
- **Response 200**:
  ```json
  {
    "success": true,
    "data": {
      "id": "user_a1b2c3d4",
      "name": "Jane Doe",
      "email": "jane@example.com",
      "settings": { "alertThresholds": [3], "defaultSort": "expiry-date" }
    }
  }
  ```

### `PUT /api/auth/profile`
- **Auth**: Required (`Authorization: Bearer <token>`)
- **Request Body**:
  ```json
  {
    "name": "Jane Smith",
    "email": "janesmith@example.com"
  }
  ```
- **Response 200**: Updated profile object.

### `PUT /api/auth/settings`
- **Auth**: Required (`Authorization: Bearer <token>`)
- **Request Body**:
  ```json
  {
    "alertThresholds": [1, 3, 7, 14],
    "defaultSort": "expiry-date"
  }
  ```
- **Response 200**: Updated settings object.

---

## 3. Personal Inventory Endpoints

### `GET /api/products`
- **Auth**: Required (`Authorization: Bearer <token>`)
- **Query Parameters**:
  - `category` (optional): `medicine` | `grocery` | `personal-care` | `other` | `all`
  - `search` (optional): search text in name, notes, or batchNumber
  - `sortBy` (optional): `expiry-date` (default) | `name` | `date-added`
- **Response 200**:
  ```json
  {
    "success": true,
    "count": 2,
    "data": [
      {
        "id": "product_1792435000",
        "userId": "user_a1b2c3d4",
        "name": "Paracetamol 500mg",
        "category": "medicine",
        "quantity": 1,
        "purchaseDate": "2026-08-01",
        "expiryDate": "2026-10-23",
        "daysRemaining": 3,
        "status": "expiring-soon",
        "statusLabel": "Expiring Soon",
        "statusClass": "status-badge-expiring",
        "batchNumber": "LOT-441",
        "notes": "Take with water"
      }
    ]
  }
  ```

### `POST /api/products`
- **Auth**: Required (`Authorization: Bearer <token>`)
- **Request Body**:
  ```json
  {
    "name": "Paracetamol 500mg",
    "category": "medicine",
    "quantity": 1,
    "purchaseDate": "2026-08-01",
    "expiryDate": "2026-10-23",
    "manufacturingDate": "2026-01-01",
    "verifiedShelfLifeDays": null,
    "shelfLifeSource": "",
    "batchNumber": "LOT-441",
    "notes": "Take with water",
    "barcode": "8901234567890"
  }
  ```
- **Response 201**: Returns created product enriched with live status.

### `GET /api/products/<id>`
- **Auth**: Required (`Authorization: Bearer <token>`)
- **Response 200**: Single product matching ID and authenticated user.
- **Error 404**: Not found or belongs to another user.

### `PUT /api/products/<id>` & `PATCH /api/products/<id>`
- **Auth**: Required (`Authorization: Bearer <token>`)
- **Request Body**: Partial or full product fields to update.
- **Response 200**: Updated enriched product.

### `DELETE /api/products/<id>`
- **Auth**: Required (`Authorization: Bearer <token>`)
- **Response 200**: `{ "success": true, "message": "Product deleted successfully" }`

### `POST /api/products/demo`
- **Auth**: Required (`Authorization: Bearer <token>`)
- **Response 200**: Seeds 10 standard demo products if user inventory is empty.
- **Error 400**: Inventory already contains products.

---

## 4. Intelligence & Scanner Endpoints

### `GET /api/products/barcode/<barcode>`
- **Auth**: None (or optional)
- **Description**: Query Open Food Facts product database.
- **Response 200**:
  ```json
  {
    "success": true,
    "data": {
      "barcode": "5449000000996",
      "name": "Coca-Cola Zero Sugar",
      "brands": "Coca-Cola",
      "categories": "Beverages, Carbonated drinks",
      "quantity": "330 ml",
      "suggestedCategory": "grocery"
    }
  }
  ```
- **Error 400**: Barcode is not 8–14 digits.
- **Error 404**: Product not found in database.

### `POST /api/products/analyze-label`
- **Auth**: None (matches frontend `callExpiryCareApi`)
- **Request Body**:
  ```json
  {
    "imageName": "sample.jpg",
    "imageType": "image/jpeg",
    "imageData": "data:image/jpeg;base64,..."
  }
  ```
- **Response 200 (Live provider or offline knowledge base):**
  ```json
  {
    "name": "Aspirin 100mg",
    "category": "medicine",
    "manufacturingDate": "2026-01-15",
    "expiryDate": "2027-01-15",
    "batchNumber": "B-902",
    "warnings": ["Confirm dates against packaging"]
  }
  ```
- **Response 503 (When Provider Unconfigured)**:
  ```json
  {
    "error": "OCR/vision provider is not configured; enter label values manually"
  }
  ```

### `POST /api/guidance/chat`
- **Auth**: None (matches frontend `callExpiryCareApi`)
- **Request Body**:
  ```json
  {
    "message": "What should I do if an eye drop has expired?"
  }
  ```
- **Response 200 (Live provider or offline knowledge base):**
  ```json
  {
    "reply": "Expired eye drops should never be used because preservatives degrade...",
    "disclaimer": "Informational only; not a safety certification or professional medical advice."
  }
  ```
- **Response 200 (Offline mode):** returns a deterministic, conservative answer with `mode: "offline_knowledge_base"` and a disclaimer. This fallback is not generative AI. A live provider key is optional. Invalid/missing messages return HTTP 400.

---

## 5. Dashboard & Alerts Endpoints

### `GET /api/dashboard/summary`
- **Auth**: Required (`Authorization: Bearer <token>`)
- **Response 200**:
  ```json
  {
    "success": true,
    "data": {
      "counts": {
        "total": 10,
        "active": 5,
        "expiringSoon": 3,
        "expired": 2,
        "unknown": 0
      },
      "categoryCounts": { "medicine": 4, "grocery": 3, "personal-care": 2, "other": 1 },
      "timeline": {
        "expiredCount": 2,
        "next7DaysCount": 2,
        "next14DaysCount": 1,
        "next30DaysCount": 0,
        "safeCount": 5,
        "unknownCount": 0
      },
      "insights": [
        { "type": "danger", "message": "You have 2 expired product(s)..." }
      ]
    }
  }
  ```

### `GET /api/alerts`
- **Auth**: Required (`Authorization: Bearer <token>`)
- **Response 200**: Returns list of products triggering active alert thresholds.

---

## 6. Retail Intelligence Endpoints

### `GET /api/retail/summary`
- **Description**: Multi-branch operational overview.

### `GET /api/retail/branches`
- **Description**: List of store locations.

### `GET /api/retail/batches`
- **Description**: Inventory batches sorted in FEFO order.

### `GET /api/retail/clearance`
- **Description**: Generated clearance discount suggestions.

### `POST /api/retail/clearance/<id>/review`
- **Request Body**: `{ "status": "Approved" | "Rejected" }`

### `GET /api/retail/transfers`
- **Description**: Transfer records and workflow status.

### `POST /api/retail/transfers`
- **Request Body**: `{ "batchId": "ba-milk-a", "destinationId": "br-c", "qty": 10 }`

### `POST /api/retail/transfers/<id>/transition`
- **Request Body**: `{ "action": "Approve" | "Dispatch" | "Receive" | "Complete" | "Cancel" | "Rejected" }`

### `GET /api/retail/catalog`
- **Description**: Public store availability view with stock classifications.
