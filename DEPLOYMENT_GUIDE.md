# Deployment Guide

**Stack**: Flask backend on Render → PostgreSQL on Render → React frontend on Vercel

---

## Overview

```
GitHub Repo
    │
    ├── Backend (Flask)  →  Render Web Service  ←── PostgreSQL (Render)
    │
    └── Frontend (React) →  Vercel
                              └── VITE_API_URL points to Render backend URL
```

Both platforms have free tiers. Total cost: **$0**.

---

## Prerequisites

- GitHub account with this project pushed to a repository
- [Render account](https://render.com) (sign up free)
- [Vercel account](https://vercel.com) (sign up free)
- Your project is already configured — `render.yaml` and `frontend/vercel.json` exist

---

## Step 1 — Push to GitHub

If you haven't already:

```bash
git add .
git commit -m "Ready for deployment"
git push origin main
```

Make sure these files are **not** in `.gitignore`:
- `render.yaml`
- `requirements.txt`
- `frontend/vercel.json`
- `frontend/package.json`

And make sure these **are** in `.gitignore` (never commit these):
```
.env
intelligent_env/
intelligent_env1/
__pycache__/
*.pyc
frontend/node_modules/
frontend/dist/
```

---

## Step 2 — Create the PostgreSQL Database on Render

1. Go to [render.com/dashboard](https://dashboard.render.com)
2. Click **New** → **PostgreSQL**
3. Fill in:
   - **Name**: `interview-intelligence-db`
   - **Database**: leave default
   - **User**: leave default
   - **Region**: Oregon (US West) — same region as your web service
   - **Plan**: Free
4. Click **Create Database**
5. Wait ~1 minute for it to provision
6. On the database page, copy the **Internal Database URL** — you will need it in Step 3

> **Important**: Use the **Internal URL** (not External URL) when both database and web service are on Render. It looks like:
> `postgresql://user:password@dpg-xxxx-a/interview_intelligence_db`

---

## Step 3 — Deploy the Backend on Render

### Option A — Blueprint (Recommended, uses render.yaml)

1. Go to Render Dashboard → **New** → **Blueprint**
2. Connect your GitHub repo
3. Render will detect `render.yaml` automatically
4. It will show you a preview of what it will create — confirm it
5. Click **Apply**

Render will create the web service and link it to your database automatically.

### Option B — Manual

If Blueprint doesn't work:

1. **New** → **Web Service**
2. Connect your GitHub repo
3. Set:
   - **Name**: `interview-intelligence-system`
   - **Region**: Oregon
   - **Branch**: `main`
   - **Root Directory**: *(leave blank — app.py is at root)*
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
   - **Plan**: Free

4. Go to **Environment** tab and add these variables:

| Key | Value |
|-----|-------|
| `DATABASE_URL` | Paste the Internal Database URL from Step 2 |
| `FLASK_ENV` | `production` |
| `SECRET_KEY` | Any long random string (e.g. `openssl rand -hex 32`) |
| `PYTHON_VERSION` | `3.12.8` |

5. Click **Create Web Service**

---

### Watch the Build Logs

The first build will take **5–10 minutes** because `sentence-transformers` downloads the `all-MiniLM-L6-v2` model. This is normal. You will see lines like:

```
Downloading all-MiniLM-L6-v2...
100%|████████| 22.7M/22.7M
```

Once the build finishes, Render gives you a URL like:
```
https://interview-intelligence-system.onrender.com
```

Copy this URL — you need it for the frontend.

---

### Verify the Backend is Running

Open in your browser:
```
https://your-app-name.onrender.com/api/health/
```

You should see:
```json
{"status": "healthy", "database": "connected"}
```

If you see a database error, double-check the `DATABASE_URL` environment variable is set to the **Internal** URL.

---

## Step 4 — Deploy the Frontend on Vercel

1. Go to [vercel.com/new](https://vercel.com/new)
2. Click **Import** → connect your GitHub repo
3. On the configure screen:
   - **Framework Preset**: Vite (Vercel usually detects this automatically)
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Expand **Environment Variables** and add:

| Key | Value |
|-----|-------|
| `VITE_API_URL` | `https://your-app-name.onrender.com` |

   Replace `your-app-name` with your actual Render service name. No trailing slash.

5. Click **Deploy**

Vercel builds in ~1 minute and gives you a URL like:
```
https://interview-intelligence-system.vercel.app
```

---

## Step 5 — Connect Frontend to Backend (CORS)

The Flask app needs to allow requests from your Vercel URL. Check `main.py` — it should already have CORS configured. If you see errors in the browser console like `CORS policy blocked`, open `main.py` and update:

```python
from flask_cors import CORS
# ...
CORS(app, origins=["https://your-app.vercel.app", "http://localhost:5173"])
```

After changing this, commit and push — Render redeploys automatically.

---

## Step 6 — Test the Full Deployment

1. Open your Vercel URL in the browser
2. Select a company (e.g. Amazon)
3. Click **Run Analysis**
4. Wait 1–2 minutes for scraping to complete
5. Insights should appear

If the page loads but analysis fails, open browser DevTools → Network tab to see which API call is failing.

---

## Environment Variables Reference

### Render (Backend)

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | Internal PostgreSQL URL from Render |
| `FLASK_ENV` | Yes | Set to `production` |
| `SECRET_KEY` | Yes | Any long random string |
| `PYTHON_VERSION` | Yes | `3.12.8` |
| `REQUEST_DELAY` | No | Seconds between scraping requests (default: 1) |
| `MAX_RETRIES` | No | Max scraping retries (default: 2) |

### Vercel (Frontend)

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_API_URL` | Yes | Full URL of your Render backend (no trailing slash) |

---

## Redeployment

Both platforms redeploy automatically when you push to `main`.

- **Render**: Triggers a new build on every push. Backend redeploys in ~3 minutes (faster after first build since pip cache is warmed).
- **Vercel**: Triggers a new build on every push. Frontend redeploys in ~1 minute.

To manually trigger a redeploy without a code change:
- **Render**: Dashboard → your service → **Manual Deploy** → Deploy latest commit
- **Vercel**: Dashboard → your project → **Deployments** → **Redeploy**

---

## Common Issues and Fixes

### Backend won't start — `ModuleNotFoundError`
The build command didn't install packages. Check that `requirements.txt` is at the **root** of the repo (not inside a subfolder).

### `database connection refused` error
You set the **External** database URL instead of the **Internal** one. On Render, services in the same region communicate over the internal URL. Go to Render → your database → copy the **Internal Database URL**.

### Frontend shows a blank page
The `VITE_API_URL` environment variable on Vercel is missing or has a trailing slash. It must exactly match `https://your-app.onrender.com` with no `/` at the end. After fixing it, redeploy on Vercel.

### `CORS` errors in browser console
Your Render backend URL isn't in the allowed origins list. Update `main.py` to include your Vercel URL in the CORS config and push.

### Render service sleeps after 15 minutes (Free tier)
Free Render web services spin down after 15 minutes of inactivity. The first request after sleep takes ~30 seconds to wake up. This is a free tier limitation. To avoid it, upgrade to the $7/month Starter plan, or use [UptimeRobot](https://uptimerobot.com) to ping your `/api/health/` endpoint every 10 minutes for free.

### `sentence-transformers` model not found at runtime
The model downloads once on first inference, not at build time. The first "Run Analysis" after a cold start will be slower (~30s extra). Subsequent runs are fast because the model stays loaded in memory.

### Build fails with memory error
`sentence-transformers` installation can exhaust RAM on free tier during build. If this happens, Render will show `Killed` in the build log. Upgrade to the Starter plan (512 MB → 2 GB RAM) or reduce dependencies.

---

## Checking Logs

**Render backend logs**:
Dashboard → your web service → **Logs** tab. Filter by `ERROR` to see only failures.

**Vercel frontend logs**:
Dashboard → your project → **Functions** tab (for serverless) or check the browser DevTools console — the frontend is static so most errors show up there.

---

## Updating Environment Variables After Deployment

- **Render**: Dashboard → your service → **Environment** → edit → **Save Changes** → service restarts automatically
- **Vercel**: Dashboard → your project → **Settings** → **Environment Variables** → edit → **Redeploy**
