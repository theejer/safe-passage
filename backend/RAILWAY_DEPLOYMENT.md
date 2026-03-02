# SafePassage Backend: Railway Deployment Guide

**Status:** Production-Ready for Railway Deployment  
**Last Updated:** March 3, 2026  
**Backend Framework:** Flask 3.1.0 | **Server:** Gunicorn | **Database:** PostgreSQL

---

## Table of Contents

1. [Pre-Deployment Requirements](#pre-deployment-requirements)
2. [Railway Project Setup](#railway-project-setup)
3. [Environment Variables](#environment-variables)
4. [Deployment Steps](#deployment-steps)
5. [Post-Deployment Verification](#post-deployment-verification)
6. [Troubleshooting](#troubleshooting)
7. [Monitoring & Logs](#monitoring--logs)
8. [Scaling & Advanced Configuration](#scaling--advanced-configuration)

---

## Pre-Deployment Requirements

### 1. Prerequisites

- ✅ **Railway Account** - Sign up at [railway.app](https://railway.app)
- ✅ **GitHub Repository** - Your `dlweek_project` pushed to GitHub
  - Railway will pull code from your GitHub repository
  - Ensure `.git/config` has correct GitHub remote URL
- ✅ **OpenAI API Key** - For itinerary risk analysis (PREVENTION pillar)
  - Obtain from [api.openai.com](https://platform.openai.com/api-keys)
  - **Note:** Risk analysis will fail without this key; consider stubbing it for initial deploy

### 2. Local Verification (Optional but Recommended)

Before deploying to Railway, test the Docker build locally:

```bash
# Navigate to project root
cd c:\JR's Cache\dlweek_project

# Build the Docker image
docker build -t safepassage-backend:latest ./backend

# Create a test .env file (replace with real PostgreSQL URI)
cat > .env.test << EOF
APP_CONFIG=development
SQLALCHEMY_DATABASE_URI=postgresql://user:password@localhost:5432/safepassage
OPENAI_API_KEY=sk-your-test-key
CORS_ORIGINS=http://localhost:8081,http://localhost:3000
EOF

# Run container with test environment
docker run --env-file .env.test -p 5000:5000 safepassage-backend:latest

# Test health endpoint (in another terminal)
curl http://localhost:5000/health
# Expected response: {"status": "ok", "server": "up", "database": "up"}
```

---

## Railway Project Setup

### Step 1: Create Railway Project

1. Log in to [Railway Dashboard](https://railway.app)
2. Click **"New Project"** button
3. Select **"Deploy from GitHub repo"**
4. Connect GitHub account if not already connected
5. Find and select `dlweek_project` repository
6. Click **"Deploy Now"**

### Step 2: Add PostgreSQL Database

Railway will auto-detect the `railway.json` plugin reference and create a PostgreSQL instance.

**Alternative (Manual):**
1. Click **"Add Service"** in your Railway project
2. Search for and select **"PostgreSQL"**
3. Click **"Create"**

Railway will:
- Provision a managed PostgreSQL instance
- Auto-generate connection credentials
- Set `${{DATABASE_URL}}` environment variable

### Step 3: Configure Backend Service

Once build completes:

1. Click on the **Backend** service in your Railway project
2. Go to **"Settings"** tab
3. Verify:
   - **Build Command:** Empty (will use Dockerfile)
   - **Start Command:** Empty (will use docker-entrypoint.sh from Dockerfile)
   - **Port:** 5000 (auto-detected from Dockerfile)

---

## Environment Variables

### Critical Variables (Must Set)

Set these in your Railway Backend service **Variables** tab:

#### 1. Application Configuration
```
APP_CONFIG=production
```

#### 2. Database Connection (Auto-Populated)
Railway automatically sets `DATABASE_URL`. Reference it as:
```
SQLALCHEMY_DATABASE_URI=${{DATABASE_URL}}
```

#### 3. OpenAI API Key (Required for PREVENTION Pillar)
```
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxx
```

**Note:** If you don't have an OpenAI key:
- The backend starts, but itinerary risk analysis will fail
- User can create trips, but risk assessment returns 500 error
- Obtain key from [platform.openai.com/api-keys](https://platform.openai.com/api-keys) and update

#### 4. CORS Configuration
```
CORS_ORIGINS=https://your-frontend.railway.app,https://your-domain.com
```

Replace `your-frontend.railway.app` with your actual frontend Railway app URL.

**Important:** If frontend and backend are deployed together in Railway:
- Frontend URL follows pattern: `https://your-project.railway.app`
- Use exact URL that users see in browser
- Comma-separated for multiple origins

### Optional Variables

#### Heartbeat Monitoring (CURE Pillar)
```
ENABLE_HEARTBEAT_SCHEDULER=0
HEARTBEAT_WATCHDOG_INTERVAL_MINUTES=5
HEARTBEAT_WATCHDOG_KEY=your-secret-key
```

**Default:** Disabled (`0`)  
**Recommendation:** Keep disabled initially; enable via Railway Cron job for distributed scheduling

#### Telegram Bot (Emergency Alerts - MITIGATION)
```
TELEGRAM_BOT_ENABLED=0
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
```

**Default:** Disabled  
**Recommendation:** Skip on initial deployment

#### Other Services (Optional)
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
```

These are stubbed/optional and not required for core functionality.

---

## Deployment Steps

### Step 1: Push Code to GitHub

Ensure all changes are committed and on your main branch:

```bash
cd c:\JR's Cache\dlweek_project
git add .
git commit -m "feat: Add Railway deployment configuration"
git push origin main
```

### Step 2: Railway Auto-Deploy

Railway automatically:
1. Detects code change on main branch
2. Builds Docker image using `Dockerfile`
3. Initializes PostgreSQL database (via `docker-entrypoint.sh`)
4. Deploys container to Railway infrastructure
5. Runs health checks

**Build Log Location:**
- Railway Dashboard → Backend Service → "Deployments" tab

### Step 3: Monitor Initial Deployment

Watch the deployment logs for:

1. **Database Initialization:**
   ```
   [INFO] Starting SafePassage database initialization...
   [INFO] Database schema already initialized, skipping setup
   OR
   [INFO] Database schema not found, initializing...
   [INFO] ✓ Database schema applied successfully
   ```

2. **PostgreSQL Readiness:**
   ```
   [INFO] Step 2: Waiting for PostgreSQL readiness...
   [INFO] ✓ PostgreSQL is ready
   ```

3. **Server Startup:**
   ```
   [INFO] Step 3: Starting Gunicorn WSGI server...
   [INFO] Running in production mode
   ```

4. **Health Check Success:**
   ```
   [2026-03-03 10:15:45] Checking health...
   [2026-03-03 10:15:46] ✓ Application health check passed
   ```

If you see errors, proceed to [Troubleshooting](#troubleshooting).

---

## Post-Deployment Verification

### 1. Test Health Endpoint

```bash
# Get your backend service URL from Railway dashboard
# Format: https://safepassage-backend-production.railway.app

curl https://safepassage-backend-production.railway.app/health

# Expected response (200 OK):
{
  "status": "ok",
  "server": "up",
  "database": "up"
}
```

### 2. Test User Registration (Happy Path)

```bash
curl -X POST https://safepassage-backend-production.railway.app/users/register \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Test User",
    "phone": "+919876543210",
    "email": "test@example.com"
  }'

# Expected response (201 Created):
{
  "id": "uuid...",
  "full_name": "Test User",
  "phone": "+919876543210",
  "created_at": "2026-03-03T10:15:45Z"
}
```

### 3. Test Trip Creation

```bash
# Get a user ID from the response above
USER_ID="uuid..."

curl -X POST https://safepassage-backend-production.railway.app/users/${USER_ID}/trips \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Bihar Safety Test Trip",
    "start_date": "2026-03-10",
    "end_date": "2026-03-15",
    "destination_country": "India"
  }'

# Expected response (201 Created):
{
  "id": "trip-uuid...",
  "title": "Bihar Safety Test Trip",
  ...
}
```

### 4. Verify Database Persistence

```bash
# Repeat the user lookup (should return the previously created user)
curl https://safepassage-backend-production.railway.app/users/${USER_ID}

# Should return 200 OK with user data
```

---

## Troubleshooting

### Issue 1: Deployment Stuck on Building

**Symptoms:**
- Deployment hangs in "Building" state for >15 minutes
- Build logs are empty or stopped

**Solutions:**
1. **Check Railway logs:**
   - Railway Dashboard → Deployments → "View Logs"
   - Look for Docker build errors
2. **Rebuild manually:**
   - Dashboard → Service Settings → "Redeploy"
3. **Check file sizes:**
   - Ensure `__pycache__/` and `.venv/` are in `.dockerignore`
   - Large dependencies should use `--no-cache-dir` in pip install (already done)

### Issue 2: Health Check Failing (502 Bad Gateway)

**Symptoms:**
- Deployment succeeds but returns 502 errors
- Health check logs show "Connection refused"

**Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| **App crashed during startup** | Check logs for exception messages, typically related to database connection |
| **Database not ready** | Verify PostgreSQL service is running in Railway; wait 30 seconds and retry |
| **SQLALCHEMY_DATABASE_URI missing** | Ensure `SQLALCHEMY_DATABASE_URI=${{DATABASE_URL}}` is set in environment variables |
| **Port binding failure** | Verify no other process using port 5000 (shouldn't happen in container, but check logs anyway) |

**View detailed logs:**
```
Railway Dashboard → Backend Service → Logs tab
Look for errors from wsgi.py or app/__init__.py
```

### Issue 3: Database Initialization Failed

**Symptoms:**
- `[ERROR] Failed to apply database schema`
- `[ERROR] PostgreSQL not ready after 30 attempts`

**Solutions:**

1. **PostgreSQL service not created:**
   - Go to Railway dashboard
   - Verify PostgreSQL service exists under "Services"
   - If missing, click "Add Service" and select PostgreSQL

2. **Database URI malformed:**
   - Check `SQLALCHEMY_DATABASE_URI` value in variables
   - Should be: `postgresql://user:password@host:5432/railway`
   - Railway's `${{DATABASE_URL}}` auto-fills this correctly

3. **Network connectivity issue:**
   - Ensure both Backend and PostgreSQL services are in the same Railway project
   - Railway auto-connects them if in same project
   - Try redeploying the backend service

4. **Manual schema application (emergency workaround):**
   - Go to PostgreSQL service → "Database" tab
   - Click "Open Database" (connects to pgAdmin or similar)
   - Copy-paste contents of `contracts/db/schema_outline.sql`
   - Execute the SQL

### Issue 4: OpenAI API Key Rejected (Risk Analysis Fails)

**Symptoms:**
- Health check passes (database OK)
- POST `/trips/:trip_id/itinerary/upload` returns 401 or 403
- Logs show "Invalid API key" or "Unauthorized"

**Solutions:**

1. **Verify API key format:**
   - Should start with `sk-proj-` (newer format) or `sk-` (older)
   - Check [platform.openai.com/api-keys](https://platform.openai.com/api-keys) for current key

2. **Regenerate API key:**
   - If key was created >90 days ago, it may be revoked
   - Create new key in OpenAI dashboard
   - Update `OPENAI_API_KEY` in Railway variables

3. **Check API key permissions:**
   - Ensure key has "Chat Completions" API access
   - Some restricted keys may not have access to all models

4. **Temporary bypass (development only):**
   - Set `OPENAI_API_KEY=stub-for-testing`
   - Risk analysis will skip silently
   - Remove before production use

### Issue 5: CORS Errors from Frontend

**Symptoms:**
- Frontend makes request to backend
- Errors like "Access to XMLHttpRequest blocked by CORS policy"
- Preflight OPTIONS request returns 403 or 405

**Solutions:**

1. **Verify CORS_ORIGINS set correctly:**
   ```
   CORS_ORIGINS=https://your-frontend.railway.app,https://localhost:8081
   ```
   - Use exact URLs users see in browser
   - Include scheme (https://), not just domain

2. **Check frontend URL:**
   - Go to frontend Railway service dashboard
   - Copy the provided URL (format: `https://project-name.railway.app`)
   - Paste exact URL into CORS_ORIGINS

3. **Restart backend service after changing CORS_ORIGINS:**
   - Railway Dashboard → Backend Service → Redeploy

### Issue 6: Container Exits Immediately (Status: Failed)

**Symptoms:**
- Deployment shows "Failed" status
- Container exits after a few seconds
- No error in logs

**Common Causes:**

1. **Missing required environment variable:**
   - Check for: `APP_CONFIG`, `SQLALCHEMY_DATABASE_URI`
   - Both must be set

2. **Python dependency conflict:**
   - Check `requirements.txt` for conflicting versions
   - Try updating to latest compatible versions

3. **File permissions issue:**
   - Verify `docker-entrypoint.sh` is executable
   - Dockerfile includes: `RUN chmod +x docker-entrypoint.sh`

4. **Workaround:**
   - Manually test Docker build locally first (see Pre-Deployment section)
   - Fix issues locally before pushing to Railway

---

## Monitoring & Logs

### Railway Dashboard Logs

**Real-time logs:**
- Railway Dashboard → Backend Service → Logs tab
- Shows all stdout/stderr output from running container
- Color-coded by log level (errors in red)

**Search logs:**
- Use browser Ctrl+F to search for keywords
- Look for: "ERROR", "Exception", "FAILED", "connection"

### Health Monitoring

Railway automatically monitors:
- **CPU Usage** - If >80% sustained, consider adding more resources
- **Memory Usage** - If >512MB, may indicate memory leak
- **Response Time** - If >10s, check database query performance
- **Error Rate** - If >1% requests fail, investigate logs

### Key Metrics to Watch

1. **Request Latency:**
   - Heartbeat POST: should be <200ms
   - Itinerary upload: should be <5s (depends on PDF size)
   - Database queries: should be <100ms

2. **Database Connections:**
   - Monitor active connections in Railway PostgreSQL dashboard
   - Default pool size is 20; increase if needed

3. **Error Rates:**
   - Spike in 5xx errors → check application logs
   - Spike in 4xx errors → check frontend CORS/auth
   - Spike in 503 Service Unavailable → check database

### Log Analysis Examples

**Successful request:**
```
[2026-03-03 10:15:46] GET /health HTTP/1.1 200 45
[2026-03-03 10:15:47] POST /users/register HTTP/1.1 201 234
```

**Database connection error:**
```
[ERROR] psycopg2.OperationalError: could not connect to server
[ERROR] SQLALCHEMY_DATABASE_URI connection failed
```

**OpenAI API error:**
```
[ERROR] openai.error.AuthenticationError: Invalid API key
```

---

## Scaling & Advanced Configuration

### Single-Instance (Current)

**Recommended for:**
- Initial launch / MVP
- <1000 daily active users
- Risk analysis demand <10 requests/min

**Current configuration:**
- Gunicorn: 2 workers
- Timeout: 120 seconds
- PostgreSQL: Shared pool (20 connections)

### Scaling to Multi-Instance

**When to scale:**
- CPU sustained >70%
- Response latency >1s
- >10,000 daily active users

**Steps:**

1. **Add Railway replicates:**
   - Railway Dashboard → Backend Service → "Add Replica"
   - Sets up load balancing automatically

2. **Increase database pool size:**
   - In `app/config.py`, increase `SQLALCHEMY_POOL_SIZE`
   - Default: 20, scale to 40-50 per additional instance

3. **Enable heartbeat scheduler via Cron:**
   - Currently disabled (uses in-process APScheduler)
   - For multi-instance, use Railway Cron:
     ```
     ENABLE_HEARTBEAT_SCHEDULER=0  # Disable in-process
     ```
   - Create Railway Cron job that calls `/internal/heartbeat-watchdog`

### Database Optimization

**For production, consider:**

1. **Index heartbeat queries:**
   ```sql
   CREATE INDEX idx_heartbeats_trip_timestamp ON heartbeats(trip_id, timestamp DESC);
   CREATE INDEX idx_heartbeats_user_timestamp ON heartbeats(user_id, timestamp DESC);
   ```

2. **Archive old heartbeats:**
   ```sql
   -- Move heartbeats older than 90 days to archive table
   INSERT INTO heartbeats_archive SELECT * FROM heartbeats WHERE timestamp < now() - interval '90 days';
   DELETE FROM heartbeats WHERE timestamp < now() - interval '90 days';
   ```

3. **Increase shared_buffers (PostgreSQL):**
   - Railway PostgreSQL: Requires database plan upgrade

---

## Summary

| Phase | Status | Notes |
|-------|--------|-------|
| **Pre-Deployment** | ✅ Ready | Dockerfile and configs included |
| **Build & Deploy** | ✅ Automated | Railway auto-builds and deploys on push to main |
| **Database Init** | ✅ Automated | Schema applies on first boot, skipped on subsequent boots |
| **Security** | ✅ Ready | No hardcoded secrets; all config via env vars |
| **Health Checks** | ✅ Enabled | /health endpoint for container orchestration |
| **Monitoring** | ✅ Available | Railway dashboard provides logs and metrics |
| **Production Ready** | ✅ Yes | Tested architecture, proper error handling, CORS configured |

---

## Next Steps

1. **Set Environment Variables:**
   - Railway Backend Service → Variables tab
   - Add: `APP_CONFIG=production`, `OPENAI_API_KEY=...`, `CORS_ORIGINS=...`

2. **Verify Deployment:**
   - Test health endpoint: `curl <backend-url>/health`
   - Create test user and trip via API

3. **Connect Frontend:**
   - Update frontend API base URL to Railway backend URL
   - Ensure CORS_ORIGINS includes frontend Railway URL

4. **Monitor:**
   - Watch Railway logs for errors
   - Set up Telegram/email alerts for failures (Railway supports webhooks)

---

## Support & Questions

For issues beyond this guide:

- **Railway Docs:** https://docs.railway.app/
- **Flask Docs:** https://flask.palletsprojects.com/
- **PostgreSQL Docs:** https://www.postgresql.org/docs/
- **Gunicorn Docs:** https://docs.gunicorn.org/

---

**Happy deploying! 🚀**
