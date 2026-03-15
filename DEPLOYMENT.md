# AgentScore — Deployment Guide (Render Free Tier)

## Architecture

```
Render Dashboard
├── Web Service: agentscore-api       (FastAPI + embedded worker)  → https://agentscore-api.onrender.com
└── Web Service: agentscore-frontend  (Next.js)                   → https://agentscore-frontend.onrender.com

Supabase Cloud (already hosted — no changes needed)
```

> **Why 2 services instead of 3?**
> Render free tier does not support Background Workers. So we embed the worker
> loop directly into the FastAPI process (runs as an asyncio background task
> during app lifespan). This keeps everything on the free tier.

---

## Prerequisites

- [GitHub](https://github.com) account with code pushed
- [Render](https://render.com) account (sign up with GitHub — free)
- [Supabase](https://supabase.com) project already running with schema
- API keys ready: OpenAI, Alchemy

---

## Step 1: Embed Worker into FastAPI

Render free tier has no background worker support. We run the worker polling
loop as a background task inside the FastAPI lifespan.

### Modify `backend/main.py`

Add the worker loop to the `lifespan` function:

```python
import asyncio
from worker import process_next_request, recover_stale_requests

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AgentScore API ready")

    # Start embedded worker as background task
    async def worker_loop():
        logger.info("Embedded worker started. Polling for score requests...")
        try:
            await recover_stale_requests()
        except Exception as e:
            logger.warning(f"Could not recover stale requests: {e}")
        while True:
            try:
                processed = await process_next_request()
                if not processed:
                    await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Worker error: {e}")
                await asyncio.sleep(2)

    worker_task = asyncio.create_task(worker_loop())
    yield
    worker_task.cancel()
    logger.info("AgentScore API shutting down")
```

This means one service handles both the API and worker polling.

---

## Step 2: Create Dockerfile

Create `backend/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 10000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
```

> **Note:** Render free tier uses port `10000` by default. Set `PORT=10000` in env vars.

---

## Step 3: Push to GitHub

```bash
cd agentscore
git init
git add .
git commit -m "Initial commit"

# Using GitHub CLI:
gh repo create agentscore --public --source=. --push

# Or manually:
git remote add origin https://github.com/<your-username>/agentscore.git
git push -u origin main
```

Ensure `.gitignore` has:
```
venv/
__pycache__/
.env
.env.local
node_modules/
.next/
*.pyc
.DS_Store
```

---

## Step 4: Deploy Backend on Render

1. Go to [render.com](https://render.com) → **Login with GitHub**
2. Click **New → Web Service**
3. Connect your GitHub repo
4. Configure:

| Setting | Value |
|---------|-------|
| **Name** | `agentscore-api` |
| **Root Directory** | `agentscore/backend` |
| **Runtime** | Docker |
| **Instance Type** | Free |

5. **Add Environment Variables** (Environment tab):

```
SUPABASE_URL=https://vvxhbyfqxmyfigczwqsk.supabase.co
SUPABASE_ANON_KEY=<your-anon-key>
SUPABASE_SERVICE_KEY=<your-service-role-key>
ALCHEMY_API_KEY=<your-alchemy-key>
ALCHEMY_BASE_KEY=<your-alchemy-key>
ALCHEMY_BASE_RPC=https://base-mainnet.g.alchemy.com/v2/<your-key>
ALCHEMY_ETH_RPC=https://eth-mainnet.g.alchemy.com/v2/<your-key>
OPENAI_API_KEY=<your-openai-key>
OPENAI_MODEL=gpt-4o
HEYELSA_ENABLED=true
NAMESTONE_API_KEY=<your-namestone-api-key>
PORT=10000
```

6. Click **Deploy**
7. Wait for build (~3-5 min)
8. Copy the service URL: `https://agentscore-api.onrender.com`

### Verify
```bash
curl https://agentscore-api.onrender.com/health
# Expected: {"status": "ok", ...}
```

Check Render logs — should see both:
```
AgentScore API ready
Embedded worker started. Polling for score requests...
```

---

## Step 5: Deploy Frontend on Render

1. **New → Web Service**
2. Connect same GitHub repo
3. Configure:

| Setting | Value |
|---------|-------|
| **Name** | `agentscore-frontend` |
| **Root Directory** | `agentscore/frontend` |
| **Runtime** | Node |
| **Build Command** | `npm install && npm run build` |
| **Start Command** | `npm start` |
| **Instance Type** | Free |

4. **Add Environment Variables**:

```
NEXT_PUBLIC_API_URL=https://agentscore-api.onrender.com
NEXT_PUBLIC_SUPABASE_URL=https://vvxhbyfqxmyfigczwqsk.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<your-anon-key>
NODE_VERSION=20
PORT=10000
```

> Replace `agentscore-api.onrender.com` with the actual API URL from Step 4.

5. Click **Deploy**
6. Wait for build (~3-5 min)

### Verify
Open `https://agentscore-frontend.onrender.com` → landing page should load.

---

## Step 6: End-to-End Test

1. Open frontend URL in browser
2. Enter a wallet address (e.g. `0x598b4A32958e76A16B2471e67C0B2eF28e1Ba47d`)
3. Click search/score → should see "Scoring in progress..."
4. Check **Render logs** for `agentscore-api` → pipeline should run all 10 nodes
5. Score appears on agent page automatically (Supabase Realtime)
6. Click **Transactions tab** → should show Alchemy-sourced transactions
7. **Transaction Analysis Card** should appear below the score card

---

## Environment Variables Reference

### Backend (`agentscore-api`)

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_ANON_KEY` | Yes | Supabase public key |
| `SUPABASE_SERVICE_KEY` | Yes | Supabase service role key |
| `ALCHEMY_API_KEY` | Yes | Alchemy API key |
| `ALCHEMY_BASE_KEY` | Yes | Alchemy Base chain key |
| `ALCHEMY_BASE_RPC` | Yes | Alchemy Base RPC endpoint |
| `ALCHEMY_ETH_RPC` | Yes | Alchemy ETH mainnet RPC endpoint |
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `OPENAI_MODEL` | No | Default: `o3` |
| `PORT` | Yes | `10000` (Render default) |
| `HEYELSA_ENABLED` | No | Default: `true` |
| `NAMESTONE_API_KEY` | No | For ENS subnames |
| `SCORE_ANCHOR_ADDRESS` | No | Base Sepolia anchor contract |
| `SCORE_ANCHOR_PRIVATE_KEY` | No | For onchain anchoring |

### Frontend (`agentscore-frontend`)

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Yes | Backend URL from Render |
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Yes | Supabase public key |
| `NODE_VERSION` | No | Default: `20` |
| `PORT` | Yes | `10000` (Render default) |

---

## Troubleshooting

### API returns 500 / Application Error
- Check Render logs for the `agentscore-api` service
- Verify `SUPABASE_SERVICE_KEY` is correct (get from Supabase → Settings → API → service_role)
- Ensure `OPENAI_API_KEY` is valid and has credits

### Worker not processing requests
- Check Render logs — look for "Embedded worker started"
- If missing, the `main.py` lifespan changes weren't applied
- Check `score_requests` table in Supabase for pending rows

### Frontend shows "API request failed"
- Verify `NEXT_PUBLIC_API_URL` matches the Render API URL exactly
- Check browser DevTools → Network tab for CORS errors
- Ensure API service is awake (free tier sleeps after 15 min inactivity)

### Slow first load (30-60 seconds)
- **This is normal on Render free tier** — services sleep after 15 min of no traffic
- First request wakes the service ("cold start")
- Subsequent requests are fast
- For always-on: upgrade to Starter ($7/mo per service)

### Build fails on Render
- Check that `requirements.txt` has no Windows-only packages
- Remove `pycryptodome` if it causes C compilation errors (replace with `pycryptodome==3.20.0`)
- For frontend: ensure `package-lock.json` is committed

---

## Cost

| Tier | Cost | Services | Notes |
|------|------|----------|-------|
| **Free** | $0 | 2 web services | Sleeps after 15 min, 750 hrs/mo |
| Starter | $7/mo each | Always-on | No cold starts |

**Free tier is perfect for hackathon demos.** The 750 free hours/month is shared
across all services (2 services × 24h × 31 days = 1488 hrs needed, so services
will sleep when inactive to stay within limits — which is fine for a demo).
