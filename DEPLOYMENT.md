# AgentScore — Deployment Guide (Railway)

## Architecture

```
Railway Project: AgentScore
├── Service: api        (FastAPI)    → https://<api>.up.railway.app
├── Service: worker     (worker.py)  → no public URL
└── Service: frontend   (Next.js)    → https://<frontend>.up.railway.app
```

- **Supabase** stays on Supabase Cloud (already hosted)
- **Railway** hosts all 3 application services
- $5 free trial credits, no credit card needed

---

## Prerequisites

- [GitHub](https://github.com) account
- [Railway](https://railway.com) account (sign up with GitHub)
- [Supabase](https://supabase.com) project already set up with schema
- API keys: OpenAI, Alchemy

---

## Step 1: Push Code to GitHub

```bash
cd agentscore
git init
git add .
git commit -m "Initial commit"

# Create repo on GitHub (using GitHub CLI)
gh repo create agentscore --public --source=. --push

# Or manually: create repo on github.com, then:
git remote add origin https://github.com/<your-username>/agentscore.git
git push -u origin main
```

Make sure `.gitignore` excludes:
```
venv/
__pycache__/
.env
.env.local
node_modules/
.next/
*.pyc
```

---

## Step 2: Create Railway Project

1. Go to [railway.com](https://railway.com) → **Login with GitHub**
2. Click **New Project → Empty Project**
3. Name it `agentscore`

---

## Step 3: Deploy FastAPI API

1. In Railway dashboard → **New → GitHub Repo** → select your `agentscore` repo
2. Configure:
   - **Service Name**: `api`
   - **Root Directory**: `agentscore/backend`
   - **Builder**: Dockerfile (auto-detected from `backend/Dockerfile`)
3. **Add Environment Variables** (click on the service → Variables tab):

   ```env
   # Supabase
   SUPABASE_URL=https://vvxhbyfqxmyfigczwqsk.supabase.co
   SUPABASE_ANON_KEY=<your-anon-key>
   SUPABASE_SERVICE_KEY=<your-service-role-key>

   # Alchemy
   ALCHEMY_API_KEY=<your-alchemy-key>
   ALCHEMY_BASE_KEY=<your-alchemy-key>
   ALCHEMY_BASE_RPC=https://base-mainnet.g.alchemy.com/v2/<your-key>
   ALCHEMY_ETH_RPC=https://eth-mainnet.g.alchemy.com/v2/<your-key>

   # OpenAI
   OPENAI_API_KEY=<your-openai-key>
   OPENAI_MODEL=o3

   # Port
   PORT=8000
   ```

4. Go to **Settings → Networking → Generate Domain**
5. Copy the URL (e.g. `https://api-production-xxxx.up.railway.app`)
6. **Deploy** — wait for build to complete

### Verify API
```bash
curl https://api-production-xxxx.up.railway.app/health
# Expected: {"status": "ok", ...}
```

---

## Step 4: Deploy Worker

1. In Railway dashboard → **New → GitHub Repo** → same repo
2. Configure:
   - **Service Name**: `worker`
   - **Root Directory**: `agentscore/backend`
   - **Dockerfile Path**: `Dockerfile.worker`
3. **Add same environment variables** as the API service (copy from API service)
4. **DO NOT generate a domain** — worker has no public URL
5. **Deploy**

### Verify Worker
Check **Logs** tab in Railway dashboard → should see:
```
AgentScore Worker started. Polling for score requests...
```

---

## Step 5: Deploy Next.js Frontend

1. In Railway dashboard → **New → GitHub Repo** → same repo
2. Configure:
   - **Service Name**: `frontend`
   - **Root Directory**: `agentscore/frontend`
   - **Builder**: Nixpacks (auto-detects Next.js)
3. **Add Environment Variables**:

   ```env
   NEXT_PUBLIC_API_URL=https://api-production-xxxx.up.railway.app
   NEXT_PUBLIC_SUPABASE_URL=https://vvxhbyfqxmyfigczwqsk.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=<your-anon-key>
   NODE_VERSION=20
   ```

   > Replace `api-production-xxxx` with the actual API URL from Step 3.

4. **Settings → Networking → Generate Domain**
5. **Deploy**

### Verify Frontend
Open `https://frontend-production-xxxx.up.railway.app` in browser → landing page should load.

---

## Step 6: End-to-End Test

1. Open frontend URL
2. Enter a wallet address (e.g. a Virtuals agent wallet)
3. Click score → should see "Scoring in progress..."
4. Check **worker logs** in Railway → pipeline should run through all 10 nodes
5. Score should appear on the agent page automatically (via Supabase Realtime)
6. Check **Transactions tab** → should show Alchemy-sourced transactions

---

## Dockerfiles

### `backend/Dockerfile` (API)
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `backend/Dockerfile.worker` (Worker)
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "worker.py"]
```

---

## Environment Variables Reference

### Backend (API + Worker share these)

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_ANON_KEY` | Yes | Supabase anonymous/public key |
| `SUPABASE_SERVICE_KEY` | Yes | Supabase service role key (writes) |
| `ALCHEMY_API_KEY` | Yes | Alchemy API key |
| `ALCHEMY_BASE_KEY` | Yes | Alchemy Base chain key |
| `ALCHEMY_BASE_RPC` | Yes | Alchemy Base RPC URL |
| `ALCHEMY_ETH_RPC` | Yes | Alchemy ETH mainnet RPC URL |
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `OPENAI_MODEL` | No | Model name (default: `o3`) |
| `PORT` | Yes | Server port (set to `8000`) |
| `HEYELSA_ENABLED` | No | Enable HeyElsa x402 (default: `true`) |
| `NAMESTONE_API_KEY` | No | NameStone API key for ENS subnames |
| `ENS_DOMAIN` | No | Parent ENS domain (e.g. `agentscore.eth`) |
| `SCORE_ANCHOR_ADDRESS` | No | Base Sepolia anchor contract |
| `SCORE_ANCHOR_PRIVATE_KEY` | No | Private key for onchain anchoring |

### Frontend

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Yes | Backend API URL from Railway |
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Yes | Supabase anonymous key |
| `NODE_VERSION` | No | Node.js version (default: `20`) |

---

## Troubleshooting

### API returns 500
- Check Railway logs for the `api` service
- Verify all env vars are set (especially `SUPABASE_SERVICE_KEY`)

### Worker not processing requests
- Check Railway logs for `worker` service
- Ensure `score_requests` table has pending rows
- Verify env vars match the API service

### Frontend shows "API request failed"
- Verify `NEXT_PUBLIC_API_URL` points to the correct Railway API URL
- Check browser DevTools → Network tab for failed requests
- Ensure API service is running and healthy

### Cold starts (slow first request)
- Railway trial plan may sleep services after inactivity
- First request takes ~10-30s to wake up
- Upgrade to paid plan ($5/mo per service) for always-on

---

## Cost Estimate

| Plan | Cost | Notes |
|------|------|-------|
| Trial | $5 free | ~1 week of light usage for 3 services |
| Hobby | $5/mo | Per service, always-on, no sleep |
| Pro | $20/mo | Team features, more resources |

For a hackathon demo, the **free $5 trial** is sufficient.
