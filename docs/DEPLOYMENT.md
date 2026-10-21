# ExpiryCare Production Deployment Guide

This guide details how to deploy the ExpiryCare Backend and Frontend to production environments.

---

## 1. Hosting Architecture Options

The application supports two primary deployment topologies:

```text
Topology A: Decoupled (Recommended for High Scalability)
├── Backend  -> Render / Railway / Google Cloud Run (Python 3 + Gunicorn)
├── Frontend -> Vercel / Netlify / Cloudflare Pages (Global CDN Static Hosting)
└── Database -> Google Cloud Firestore (Managed NoSQL Database)

Topology B: Unified (Simplest Single-Service Hosting)
├── Web Service -> Render / Railway (Serves both Flask REST API and static frontend)
└── Database    -> Google Cloud Firestore
```

---

## 2. Deploying the Backend on Render

### Step 2.1: Prepare Repository
Push the project to your GitHub/GitLab repository.

### Step 2.2: Create a New Web Service on Render
1. Log in to [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** > **Web Service**.
3. Select your repository.
4. Set the following parameters:
   - **Name**: `expirycare-api`
   - **Root Directory**: `backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT wsgi:app`
   - **Plan**: Free or Starter

### Step 2.3: Configure Environment Variables on Render
Under the **Environment** tab, add the following variables:

| Variable Name | Value | Description |
| :--- | :--- | :--- |
| `FLASK_ENV` | `production` | Enables production caching and disables debug mode |
| `SECRET_KEY` | `(generate a 32+ char random string)` | Signs JWT tokens securely |
| `CORS_ORIGINS` | `https://your-frontend.vercel.app` | Allow only your production frontend domain |
| `FIRESTORE_ENABLED` | `true` | Connects to live Firebase Firestore |
| `FIREBASE_PROJECT_ID` | `your-firebase-project-id` | Your Google Cloud project ID |
| `GOOGLE_APPLICATION_CREDENTIALS` | `/etc/secrets/service-account.json` | Path to Render secret file |

### Step 2.4: Attach Firebase Secret File
1. On Render, click **Secret Files**.
2. Add a new file named `service-account.json`.
3. Paste the contents of your Google Cloud Firebase service account key.
4. Save changes and trigger deploy.

---

## 3. Deploying the Frontend on Vercel

### Step 3.1: Connect Frontend Folder
1. Log in to [Vercel](https://vercel.com/).
2. Click **Add New...** > **Project**.
3. Set **Root Directory** to `frontend`.
4. Framework Preset: **Other** (Static HTML).

### Step 3.2: Connecting Frontend to Public Backend Without Changing Code
To connect the frontend to the deployed backend without modifying any original frontend files, use a standard reverse-proxy rewrite in `vercel.json`:

Create `frontend/vercel.json` (or place in root):
```json
{
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://expirycare-api.onrender.com/api/:path*"
    }
  ]
}
```
This proxies all client-side calls to `/api/*` directly to your production Render backend over HTTPS with automatic same-origin CORS compliance!

---

## 4. Production Health Verification

Once both services are deployed:
1. Verify backend health:
   ```bash
   curl -I https://expirycare-api.onrender.com/api/health
   ```
   Must return HTTP 200 with JSON payload.
2. Open your public frontend URL in the browser.
3. Test personal inventory registration and product addition.
4. Verify documents are written to the live Google Cloud Firestore console!
