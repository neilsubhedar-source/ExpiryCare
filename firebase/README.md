# Firebase Firestore Configuration & Setup Guide

This directory contains the Firebase Cloud Firestore security rules and index definitions for **ExpiryCare**.

---

## 1. Firebase Project Setup

1. Open the [Firebase Console](https://console.firebase.google.com/).
2. Click **Add project** and enter a name (e.g. `expirycare-production`).
3. Under **Build**, select **Firestore Database** and click **Create database**.
4. Choose a region close to your primary users (e.g. `nam5 (us-central)` or `asia-south1`).
5. Choose **Start in production mode**.

---

## 2. Generating Service Account Credentials (Server-Side)

1. In the Firebase Console, click the Gear icon ⚙️ > **Project settings**.
2. Navigate to the **Service accounts** tab.
3. Select **Firebase Admin SDK** (Python).
4. Click **Generate new private key**, then click **Generate key**.
5. Save the downloaded JSON file securely on your server (e.g. `/etc/secrets/service-account.json`).
6. **NEVER commit this JSON file to version control or put it in public directories.**
7. In your backend `.env`, set:
   ```env
   FIRESTORE_ENABLED=true
   GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
   FIREBASE_PROJECT_ID=your-project-id
   ```

---

## 3. Deploying Firestore Rules & Indexes via Firebase CLI

If you have the Firebase CLI installed (`npm install -g firebase-tools`):

1. Log in:
   ```bash
   firebase login
   ```
2. Initialize project in this directory:
   ```bash
   firebase use --add your-firebase-project-id
   ```
3. Deploy rules and indexes:
   ```bash
   firebase deploy --only firestore:rules,firestore:indexes
   ```

---

## 4. Collection Structure Summary

| Collection | Description | Document ID | Ownership Field |
| :--- | :--- | :--- | :--- |
| `users` | User accounts, profiles, notification preferences | `user_<uid>` | Document ID |
| `products` | Personal inventory items and tracking dates | `product_<timestamp>` | `userId` |
| `retail_branches` | Store locations | `br-<code_suffix>` | Public read |
| `retail_products` | Retail catalog items & pricing | `p-<name>` | Public read |
| `retail_batches` | Inventory lots with expiry & stock | `ba-<code_suffix>` | Public read |
| `retail_clearance` | Clearance recommendations & approval status | `cl-<batchId>` | Manager access |
| `retail_transfers` | Inter-branch transfer requests & lifecycle states | `tr-<timestamp>` | Manager access |
| `retail_events` | Immutable audit log of stock movements | `ev-<timestamp>` | Manager access |
