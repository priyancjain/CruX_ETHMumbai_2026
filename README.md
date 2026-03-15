# 0xTrust  — Universal Credit Rating for AI Agents

> **CIBIL for AI Agents** — Cross-platform ML-powered credit scoring protocol for autonomous agents using onchain behaviour from Virtuals, ElizaOS, Olas, Fetch.ai and more, enabling undercollateralised DeFi lending on Base.

**Hackathon:** ETH Mumbai 2026 | **Team:** CruX

---

## Live Demo

| Service | URL |
|---------|-----|
| **Frontend** | [https://agentscore-frontend.onrender.com](https://agentscore-frontend.onrender.com) |
| **Backend API** | [https://agentscore-api.onrender.com](https://agentscore-api.onrender.com) |
| **Health Check** | [https://agentscore-api.onrender.com/health](https://agentscore-api.onrender.com/health) |
| **API Docs** | [https://agentscore-api.onrender.com/docs](https://agentscore-api.onrender.com/docs) |

> **Note:** Hosted on Render free tier. First request may take 30-60 seconds (cold start). Subsequent requests are fast.

---

## The Problem

**40,000+ autonomous AI agents** operate onchain across platforms like Virtuals, Olas, Fetch.ai, and ElizaOS — trading tokens, providing liquidity, deploying contracts, and managing treasuries. Yet:

1. **No Credit Identity** — Traditional credit scoring (CIBIL, Equifax) doesn't exist for AI agents
2. **Over-Collateralization Trap** — DeFi protocols require 150-200% collateral from everyone equally, regardless of track record
3. **Fragmented Reputation** — Agent reputation is siloed across individual platforms with no unified view
4. **No Risk Assessment** — Lenders can't distinguish a battle-tested profitable agent from a brand-new wallet

## The Solution

**0xTrust** reads any agent wallet from **10 external platforms**, aggregates their onchain behaviour into a **33-signal feature vector**, scores them **0-1000** using a deterministic base score + GPT-5.2 qualitative adjustment, and enables **undercollateralized DeFi lending** on Base.

### Day-1 Coverage
- **Virtuals:** 21,171+ agents
- **Olas:** 9,000+ agents
- **Fetch.ai:** 10,000+ agents
- **ElizaOS / ERC-8004:** Identity + reputation registry
- **Total scorable on Day 1: 21,000+ agents with onchain wallets**

---

## How to Use

### 1. Search & Score an Agent

Open the frontend and enter any EVM wallet address in the **"Score by Wallet ID"** field. Click **SCORE**.

The platform will:
- Queue a scoring request
- Show live pipeline progress ("Fetching On-Chain Data...", "Running Anomaly Detection...", etc.)
- Auto-navigate to the agent profile when scoring completes (~30-60 seconds)

You can also **search by agent name/description** using the search tab on the landing page.

### 2. View Agent Profile

The agent profile page shows:
- **Credit Score** (0-1000) with animated count-up and tier badge (S/A/B/C/D)
- **Collateral Requirement** — percentage required for lending
- **Max Liquidity** — maximum USDC loan available
- **ENSIP-25 Verification** — onchain identity status
- **Underwriting Rationale** — GPT-5.2's reasoning for the score
- **Bullish Factors** (green) and **Risk Indicators** (red)
- **Feature Radar Chart** — 12-axis visualization of normalized signals
- **Score History** — past scores timeline

### 3. Analyze Transaction Behavior (Analysis Tab)

- AI-generated summary of the agent's trading personality
- Activity profile classification (active_trader, defi_user, holder, dormant, mixed)
- Behavioral patterns detected by ML
- Risk indicators and notable transactions
- Protocol engagement breakdown

### 4. Check Loan Eligibility (DeFi Lender Portal)

- Enter desired loan amount (USDC) and duration (days)
- Click **CHECK ELIGIBILITY** to see max loan, interest rate, and LTV
- Connect your wallet via RainbowKit (MetaMask, Coinbase, WalletConnect)
- Sign an EIP-712 message (gas-less) to authorize the loan
- Receive loan approval with terms

### 5. Explore Leaderboard & Platforms

- **Leaderboard** — Top agents ranked by credit score, filterable by tier
- **Platforms** — Browse coverage stats for each AI agent platform

---

## Architecture

```
┌──────────────────┐     ┌───────────────────┐     ┌──────────────────────┐     ┌───────────┐
│  Next.js 14      │────>│  FastAPI API       │────>│ LangGraph Pipeline   │────>│ Supabase  │
│  Frontend        │<────│  + Embedded Worker │<────│ (10-node scoring)    │<────│ PostgreSQL│
└──────┬───────────┘     └──────┬─────────────┘     └────────┬─────────────┘     └───────────┘
       │                        │                            │
   wagmi v2 / viem v2     Platform Crawlers           GPT-5.2 + IsolationForest
   RainbowKit v2          (5 platforms)               (scoring + anomaly detection)
       │                        │
   Base Chain (8453)       Alchemy RPC                Supabase Realtime
   Base Sepolia (84532)    (ETH + Base mainnet)       (live score updates)
```

### Data Flow

```
User enters wallet address
    |
    v
POST /score {wallet_address}
    |
    v
Backend queues scoring request (Supabase score_requests table)
    |
    v
Embedded worker picks up request
    |
    v
LangGraph 10-Node Pipeline:
    Node 1: Fetch platforms (Virtuals, Olas, Fetch.ai, ElizaOS) — parallel
    Node 2: Fetch onchain data (Alchemy + HeyElsa x402) — parallel
    Node 3: Fetch ERC-8004 identity + reputation
    Node 4: Fetch ENS + ENSIP-25 verification
    Node 5: Aggregate 33-signal feature vector + store to DB
    Node 6: Run IsolationForest anomaly detection
    Node 6.5: LLM transaction behavior analysis (GPT-5.2)
    Node 7: Deterministic base score + GPT-5.2 qualitative adjustment
    Node 8: Save score to Supabase
    Node 9: Anchor score onchain (Base Sepolia) + ENS subname
    |
    v
Supabase Realtime triggers INSERT event
    |
    v
Frontend auto-navigates to /agent/{wallet} with score
```

---

## Scoring Methodology

### Two-Phase Scoring System

**Phase 1: Deterministic Base Score (0-1000)**

A weighted formula computes a base score from raw metrics — no LLM involved:

| Signal | Max Points | Thresholds |
|--------|-----------|------------|
| Wallet Age | 80 pts | 0d=0, 30d=20, 90d=40, 365d=60, 730d+=80 |
| TX Count (90d) | 100 pts | 0=0, 10=25, 50=50, 200=80, 500+=100 |
| TX Count (total) | 60 pts | 0=0, 50=15, 200=30, 1000=50, 5000+=60 |
| Last Seen | 80 pts | >30d=0, 30d=20, 7d=40, 1d=60, today=80 |
| Activity Streak | 50 pts | 0=0, 3d=10, 7d=20, 14d=35, 30d+=50 |
| Unique Counterparties (90d) | 60 pts | 0=0, 5=15, 15=30, 30=45, 50+=60 |
| DeFi Protocols | 80 pts | 0=0, 1=20, 3=40, 5=60, 7+=80 |
| Balance (ETH+USDC) | 70 pts | $0=0, $100=15, $1K=30, $10K=50, $50K+=70 |
| TVL | 80 pts | $0=0, $1K=20, $10K=40, $100K=65, $500K+=80 |
| Cross Chain | 40 pts | 1=0, 2=20, 3+=40 |
| Platform Count | 40 pts | 1=0, 2=20, 3+=40 |
| NFT Count | 30 pts | 0=0, 5=10, 20=20, 50+=30 |
| Contract Deploys | 40 pts | 0=0, 1=10, 3=25, 5+=40 |
| ERC-8004 Reputation | 60 pts | 0=0, 3=15, 5=30, 8=50, 10=60 |
| ENSIP-25 Verified | 30 pts | false=0, true=30 |
| Financial Performance | 100 pts | PnL + win_rate + staking + trade volume |
| Anomaly Penalty | -200 pts | is_anomaly=true: -200 |

**Phase 2: GPT-5.2 Qualitative Adjustment (+/- 75 points)**

GPT-5.2 receives the base score, all raw metrics, and the LLM transaction analysis. It can adjust the score by at most +/- 75 points and must justify any deviation in its rationale.

### Scoring Tiers

| Tier | Score | Collateral | Max Loan | Benchmark |
|------|-------|-----------|----------|-----------|
| **S** | 900-1000 | 30% | $500,000 USDC | wallet >= 730d, tx_90d >= 500, TVL >= $500K |
| **A** | 750-899 | 75% | $100,000 USDC | wallet >= 365d, tx_90d >= 200, TVL >= $100K |
| **B** | 600-749 | 120% | $25,000 USDC | wallet >= 90d, tx_90d >= 50, TVL >= $10K |
| **C** | 450-599 | 150% | $5,000 USDC | wallet >= 30d, tx_90d >= 10, some DeFi |
| **D** | 0-449 | 200% | $1,000 USDC | New wallet, minimal activity |

**Anomaly Cap:** If IsolationForest flags `is_anomaly=true`, score is hard-capped at 599 (Tier C).

---

## 33-Signal Feature Vector

Aggregated from 5 platform crawlers + Alchemy RPC + HeyElsa x402 + ENS + ML:

| # | Signal | Source |
|---|--------|--------|
| 1 | wallet_age_days | Alchemy (first tx timestamp) |
| 2 | tx_count_90d | Alchemy getAssetTransfers |
| 3 | tx_count_total | Alchemy eth_getTransactionCount |
| 4 | last_seen_at_days | Alchemy (last tx timestamp) |
| 5 | activity_streak_days | Alchemy (consecutive active days) |
| 6 | unique_counterparties_90d | Alchemy (unique addresses in 90d) |
| 7 | contract_deploy_count | Alchemy (contract creation txs) |
| 8 | tvl_usd | HeyElsa x402 / Alchemy estimate |
| 9 | balance_eth | Alchemy eth_getBalance |
| 10 | balance_usdc | Alchemy ERC-20 balanceOf (USDC on Base) |
| 11 | erc20_token_count | Alchemy getTokenBalances |
| 12 | defi_protocol_count | Alchemy + HeyElsa |
| 13 | nft_count | Alchemy getNFTs |
| 14 | erc8004_reputation | ERC-8004 Reputation Registry (0-10) |
| 15 | erc8004_job_count | ERC-8004 Registry |
| 16 | ensip25_verified | ENS text record (ETH mainnet) |
| 17 | cross_chain_count | Alchemy multi-chain detection |
| 18 | platform_count | All crawlers |
| 19 | platforms_list | All crawlers |
| 20 | virtuals_mcap_usd | Virtuals REST API |
| 21 | virtuals_holder_count | Virtuals REST API |
| 22 | olas_job_count | Olas GraphQL Subgraph |
| 23 | fetch_active_services | Fetch.ai Agentverse API |
| 24 | heyelsa_risk_score | HeyElsa x402 |
| 25 | heyelsa_diversification | HeyElsa x402 |
| 26 | total_pnl_usd | HeyElsa PnL |
| 27 | win_rate | HeyElsa PnL |
| 28 | total_trades | HeyElsa PnL |
| 29 | avg_trade_size_usd | HeyElsa PnL |
| 30 | staking_balance_usd | HeyElsa Staking |
| 31 | token_diversity | HeyElsa Portfolio |
| 32 | anomaly_score | IsolationForest (scikit-learn) |
| 33 | is_anomaly | IsolationForest (boolean) |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI (Python 3.11), pydantic-settings, httpx |
| **Scoring** | LangGraph 0.2, OpenAI GPT-5.2, scikit-learn IsolationForest |
| **Database** | Supabase (PostgreSQL 15 + Realtime + RLS) |
| **Frontend** | Next.js 14 (App Router), TypeScript, Tailwind CSS |
| **Wallet** | wagmi v2, viem v2, RainbowKit v2 |
| **UI** | shadcn/ui, Recharts, Framer Motion |
| **Blockchain** | Base mainnet (8453), Base Sepolia (84532) |
| **Standards** | ERC-8004 (Agent Identity), ENSIP-25 (Agent Registration), x402 (Micropayments) |
| **RPC** | Alchemy (Base + ETH mainnet) |
| **DeFi API** | HeyElsa x402 (USDC micropayment per API call) |
| **Hosting** | Render (free tier) |

---

## API Reference

### Score Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/score` | Request credit scoring for a wallet |
| `GET` | `/score/{wallet}` | Get latest valid score |
| `GET` | `/score/{wallet}/history` | Get all past scores |
| `POST` | `/score/sync` | Synchronous scoring (admin, requires X-Service-Key) |

### Agent Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/agents` | List agents (filterable by platform, tier, is_active) |
| `GET` | `/agents/{wallet}` | Full agent profile + score + features |
| `GET` | `/agents/search?q=...` | Search agents by name/description |

### Leaderboard & Stats

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/leaderboard?tier=S&limit=100` | Top agents by score |
| `GET` | `/stats` | Aggregate statistics (counts, distributions) |

### Platform Discovery

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/platforms` | All supported platforms with agent counts |
| `GET` | `/platforms/{name}/agents` | Agents on a specific platform |
| `GET` | `/discover` | Live fetch from all platform APIs |
| `GET` | `/discover/{platform}` | Live fetch from single platform |

### Enrichment Data

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/enrichment/{wallet}/transactions` | Paginated transaction history |
| `GET` | `/enrichment/{wallet}/pnl` | PnL report |
| `GET` | `/enrichment/{wallet}/positions` | Token & DeFi positions |
| `GET` | `/enrichment/{wallet}/trends` | Daily transaction trends (30d) |
| `GET` | `/enrichment/{wallet}/stats` | Trading performance stats |
| `GET` | `/enrichment/{wallet}/activity` | Activity heatmap (90d) |
| `GET` | `/enrichment/{wallet}/analysis` | LLM transaction analysis |

### Lending

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/lender/eligibility` | Check loan eligibility by score |
| `POST` | `/lender/apply` | Submit loan application |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | API health + Supabase connectivity |

---

## Platform Crawlers

| Platform | Type | Coverage | What We Read |
|----------|------|----------|-------------|
| **Virtuals** | REST API | 21,171+ agents | Name, market cap, holder count, wallet |
| **Olas** | GraphQL Subgraph | 9,000+ agents | Service ID, job count, creation date |
| **Fetch.ai** | Agentverse API | 10,000+ agents | Agent address, interactions, rating |
| **ElizaOS** | ERC-8004 Contract | On-chain registry | Agent ID, reputation (0-10), feedback count |
| **Base RPC** | Alchemy APIs | Any EVM wallet | Balances, txs, NFTs, DeFi protocols, cross-chain |

---

## Local Development

### Prerequisites
- Python 3.11+
- Node.js 20+
- Supabase project (schema deployed)
- API keys: OpenAI, Alchemy

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # Fill in credentials
uvicorn main:app --reload       # API at http://localhost:8000
```

The embedded worker starts automatically with the API server.

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local  # Fill in credentials
npm run dev                       # UI at http://localhost:3000
```

### Environment Variables

**Backend (.env)**
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key
ALCHEMY_API_KEY=your-alchemy-key
ALCHEMY_BASE_KEY=your-alchemy-key
ALCHEMY_BASE_RPC=https://base-mainnet.g.alchemy.com/v2/your-key
ALCHEMY_ETH_RPC=https://eth-mainnet.g.alchemy.com/v2/your-key
OPENAI_API_KEY=your-openai-key
OPENAI_MODEL=gpt-5.2
```

**Frontend (.env.local)**
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

---

## Deployment (Render Free Tier)

The app runs as **2 services** on Render:

| Service | Type | Root Directory | Runtime |
|---------|------|---------------|---------|
| `agentscore-api` | Web Service | `backend` | Docker |
| `agentscore-frontend` | Web Service | `frontend` | Node |

The backend embeds the scoring worker directly into the FastAPI lifespan (no separate background worker needed on free tier).

See [DEPLOYMENT.md](DEPLOYMENT.md) for full step-by-step deployment guide.

---

## Project Structure

```
agentscore/
├── backend/
│   ├── main.py                     # FastAPI entry + embedded worker
│   ├── worker.py                   # Background scoring worker
│   ├── Dockerfile                  # Docker config for Render
│   ├── requirements.txt
│   └── app/
│       ├── config.py               # pydantic-settings config
│       ├── api/
│       │   ├── score.py            # POST /score, GET /score/{wallet}
│       │   ├── agents.py           # Agent listing + search
│       │   ├── leaderboard.py      # Leaderboard + stats
│       │   ├── platforms.py        # Platform browser
│       │   ├── discover.py         # Live platform discovery
│       │   ├── enrichment.py       # Transaction + PnL + positions
│       │   ├── lender.py           # Loan eligibility + application
│       │   └── health.py           # Health check
│       ├── crawlers/
│       │   ├── virtuals.py         # Virtuals REST API crawler
│       │   ├── olas.py             # Olas GraphQL subgraph
│       │   ├── fetchai.py          # Fetch.ai Agentverse API
│       │   ├── elizaos.py          # ERC-8004 identity + reputation
│       │   └── base_rpc.py         # Alchemy Base + ETH RPC
│       ├── pipeline/
│       │   ├── graph.py            # LangGraph DAG definition (10 nodes)
│       │   ├── nodes.py            # All node implementations + base score
│       │   ├── state.py            # AgentScoreState TypedDict
│       │   └── prompt.py           # GPT-5.2 scoring prompts
│       └── services/
│           ├── supabase.py         # Anon + service_role clients
│           ├── features.py         # 33-signal feature aggregation
│           ├── anomaly.py          # IsolationForest pre-trained model
│           ├── ensip25.py          # ENS + ENSIP-25 verification
│           ├── heyelsa.py          # HeyElsa x402 DeFi enrichment
│           ├── heyelsa_storage.py  # Store transactions/PnL/positions
│           ├── onchain_anchor.py   # Score hash → Base Sepolia
│           └── ens_subnames.py     # Gasless ENS subnames (NameStone)
│
├── frontend/
│   ├── app/
│   │   ├── layout.tsx              # Root layout + providers
│   │   ├── page.tsx                # Landing + search + discovery
│   │   ├── agent/[wallet]/page.tsx # Agent profile + score dashboard
│   │   ├── leaderboard/page.tsx    # Top agents ranked
│   │   └── platforms/page.tsx      # Platform coverage explorer
│   ├── components/
│   │   ├── ScoreCard.tsx           # Animated score + tier + rationale
│   │   ├── FeatureRadar.tsx        # 12-axis radar chart
│   │   ├── AgentCard.tsx           # Agent grid card
│   │   ├── AIAnalysis.tsx          # LLM behavioral analysis
│   │   ├── LenderPortal.tsx        # Loan eligibility + EIP-712 signing
│   │   ├── TransactionTable.tsx    # Paginated transaction history
│   │   ├── TransactionCharts.tsx   # Pie + line charts
│   │   ├── ScoreHistory.tsx        # Score timeline
│   │   ├── PlatformBadge.tsx       # Platform name/icon badge
│   │   ├── PlatformTabs.tsx        # Platform filter tabs
│   │   ├── ConnectWallet.tsx       # RainbowKit connect button
│   │   └── providers.tsx           # wagmi + RainbowKit + React Query
│   └── lib/
│       ├── api.ts                  # FastAPI client wrapper
│       ├── supabase.ts             # Supabase browser client
│       └── wagmi.ts                # wagmi config (Base chains)
│
├── contracts/                      # Score anchor contract (Base Sepolia)
├── supabase/
│   └── schema.sql                  # Full DB schema (5 tables + RLS)
├── DEPLOYMENT.md                   # Render deployment guide
└── CLAUDE.md                       # Full build specification
```

---

## Database Schema

5 core tables in Supabase PostgreSQL:

| Table | Purpose |
|-------|---------|
| `agents` | Agent profiles (wallet, platform, name, metadata) |
| `scores` | Credit scores (0-1000, tier, collateral, rationale, expiry) |
| `agent_features` | 33-field feature vectors per agent |
| `score_requests` | Scoring queue with priority + retry tracking |
| `platform_crawl_log` | Crawler audit trail |

All tables have **Row Level Security** enabled:
- Public read (anon key)
- Service role write (backend only)
- **Realtime** enabled on `agents`, `scores`, `score_requests`

---

## Key Features

- **Cross-Platform Scoring** — Reads agents from 5+ platforms without requiring registration
- **Deterministic + AI Hybrid** — Base score from weighted formula, refined by GPT-5.2
- **Real-Time Updates** — Supabase Realtime pushes score results to frontend instantly
- **Anomaly Detection** — Pre-trained IsolationForest flags suspicious wallets
- **LLM Transaction Analysis** — GPT-5.2 analyzes last 50 transactions for behavioral patterns
- **DeFi Lending Portal** — Check loan eligibility, connect wallet, sign EIP-712, get approved
- **Onchain Anchoring** — Score hash written to Base Sepolia + ENS subname via NameStone
- **ENSIP-25 Verification** — Checks ENS text records for agent identity verification
- **Graceful Degradation** — Pipeline continues even if individual data sources fail

---

*0xTrust  — ETH Mumbai 2026 — Team CruX*
