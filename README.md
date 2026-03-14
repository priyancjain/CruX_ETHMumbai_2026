# AgentScore — CIBIL for AI Agents

> Universal credit scoring protocol for autonomous AI agents. Aggregates onchain behaviour from Virtuals, ElizaOS, Olas, Fetch.ai and more, scores agents 0–1000 using GPT-o3 via LangGraph, and enables undercollateralised DeFi lending on Base.

**Hackathon:** ETH Mumbai 2026

---

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐     ┌──────────┐
│  Next.js 14  │────▶│  FastAPI API  │────▶│ LangGraph (9     │────▶│ Supabase │
│  Frontend    │◀────│  + Worker     │◀────│ node pipeline)   │◀────│ Postgres │
└──────┬───────┘     └──────┬───────┘     └────────┬─────────┘     └──────────┘
       │                    │                      │
   wagmi/viem          Platform Crawlers      GPT-o3 + IsolationForest
   RainbowKit          (5 platforms)          (scoring + anomaly)
       │                    │
   Base Chain          Alchemy RPC
                       (ETH + Base)
```

---

## What's Built

### Backend (FastAPI + Python 3.11)

| Component | Status | Details |
|-----------|--------|---------|
| FastAPI app + CORS | Done | `main.py` — all routers registered, lifespan handler |
| Background worker | Done | `worker.py` — polls `score_requests`, retry logic (max 3 attempts) |
| Config (pydantic-settings) | Done | `app/config.py` — loads all env vars |
| Supabase clients | Done | `app/services/supabase.py` — anon + service_role clients |
| Health endpoint | Done | `GET /health` — Supabase connectivity check |

### API Routes

| Endpoint | Status | File |
|----------|--------|------|
| `POST /score` | Done | `app/api/score.py` — queues scoring request |
| `GET /score/{wallet}` | Done | Returns latest valid (unexpired) score |
| `GET /score/{wallet}/history` | Done | All scores ordered by date |
| `POST /score/sync` | Done | Service-key protected synchronous scoring |
| `GET /agents` | Done | `app/api/agents.py` — filterable agent list |
| `GET /agents/{wallet}` | Done | Full agent profile + latest score + features |
| `GET /leaderboard` | Done | `app/api/leaderboard.py` — top agents by score |
| `GET /stats` | Done | Aggregate stats (counts, distributions) |
| `GET /platforms` | Done | `app/api/platforms.py` — platform list |
| `GET /platforms/{name}/agents` | Done | Agents filtered by platform |
| `GET /discover/{platform}` | Done | `app/api/discover.py` — live fetch from external APIs |

### Platform Crawlers

| Platform | Status | Source | File |
|----------|--------|--------|------|
| Virtuals | Done | REST API (21k+ agents) | `app/crawlers/virtuals.py` |
| Olas | Done | GraphQL subgraph (ETH + Gnosis) | `app/crawlers/olas.py` |
| Fetch.ai | Done | Agentverse API | `app/crawlers/fetchai.py` |
| ElizaOS / ERC-8004 | Done | ERC-721 + Reputation registry | `app/crawlers/elizaos.py` |
| Base onchain | Done | Alchemy RPC (transfers, balances, NFTs) | `app/crawlers/base_rpc.py` |
| Talus | Not built | — | — |
| Wayfinder | Not built | — | — |
| Freysa | Not built | — | — |
| AgentLayer | Not built | — | — |
| Sentient | Not built | — | — |

### LangGraph Scoring Pipeline (9 Nodes)

All 9 nodes are implemented in `app/pipeline/nodes.py`:

1. **fetch_platforms** — Parallel calls to Virtuals, Olas, Fetch.ai, ElizaOS crawlers
2. **fetch_onchain** — Alchemy RPC for wallet data + HeyElsa DeFi enrichment
3. **fetch_erc8004** — ERC-8004 Identity + Reputation registry reads
4. **fetch_ens_ensip25** — ENS reverse resolution + ENSIP-25 text record verification
5. **aggregate_features** — Merges all data into 25-field feature vector, upserts to Supabase
6. **run_anomaly** — IsolationForest on 7 numeric features (contamination=5%)
7. **run_gpt_o3** — OpenAI o3 scoring with structured JSON output
8. **save_score** — Inserts score record into Supabase
9. **anchor_onchain** — Score hash anchoring to Base (skips gracefully if no contract/gas)

Pipeline graph: `app/pipeline/graph.py` | State: `app/pipeline/state.py` | Prompts: `app/pipeline/prompt.py`

### Services

| Service | Status | File |
|---------|--------|------|
| Feature aggregation (25 signals) | Done | `app/services/features.py` |
| Anomaly detection (IsolationForest) | Done | `app/services/anomaly.py` |
| ENSIP-25 verification | Done | `app/services/ensip25.py` |
| HeyElsa x402 micropayments | Done | `app/services/heyelsa.py` |

### Frontend (Next.js 14 + TypeScript)

| Component | Status | File |
|-----------|--------|------|
| Landing page (hero + wallet search + discovery) | Done | `app/page.tsx` |
| Agent profile page | Done | `app/agent/[wallet]/page.tsx` |
| Leaderboard page | Done | `app/leaderboard/page.tsx` |
| Platforms page | Done | `app/platforms/page.tsx` |
| ScoreCard (animated counter + tier badge) | Done | `components/ScoreCard.tsx` |
| FeatureRadar (9-axis Recharts radar) | Done | `components/FeatureRadar.tsx` |
| ScoreHistory timeline | Done | `components/ScoreHistory.tsx` |
| AgentCard (grid card) | Done | `components/AgentCard.tsx` |
| PlatformBadge | Done | `components/PlatformBadge.tsx` |
| PlatformTabs (tab selector) | Done | `components/PlatformTabs.tsx` |
| Providers (wagmi + RainbowKit + React Query) | Done | `components/providers.tsx` |
| Supabase Realtime (live score updates) | Done | `app/agent/[wallet]/page.tsx` |
| Wagmi + RainbowKit (Base + Base Sepolia) | Done | `lib/wagmi.ts` |
| API client wrapper | Done | `lib/api.ts` |

### Database (Supabase PostgreSQL)

| Table | Status |
|-------|--------|
| `agents` | Done — wallet, platform, metadata, indexes |
| `scores` | Done — 0-1000 score, tier, collateral, 7-day expiry |
| `agent_features` | Done — 25 feature fields |
| `score_requests` | Done — queue with priority + retry tracking |
| `platform_crawl_log` | Done — audit trail |
| Row Level Security | Done — public read, service-role write |
| Realtime | Done — enabled on agents, scores, score_requests |

---

## What's NOT Built

| Component | Priority | Description |
|-----------|----------|-------------|
| **AgentScoreAnchor.sol** | P0 | Solidity contract for score hash anchoring on Base Sepolia/mainnet. `contracts/` directory is empty. Pipeline node 9 exists but has no contract to call. |
| **5 additional crawlers** | P1 | Talus, Wayfinder, Freysa, AgentLayer, Sentient. Schema supports them; no crawler code exists. |
| **TEE detection** | P2 | `tee_secured` is always `false` in feature aggregation. Needs Freysa/ERC-8004 metadata integration. |
| **Unit tests** | P1 | No test files anywhere in the codebase. |
| **Integration tests** | P1 | No end-to-end pipeline tests (mock OpenAI needed). |
| **Docker / docker-compose** | P2 | No containerization. |
| **CI/CD pipeline** | P2 | No GitHub Actions or deployment configs. |
| **Deployment configs** | P2 | No Railway/Render/Vercel configuration files. |

---

## Scoring Logic

### 25-Signal Feature Vector

Aggregated from 5 crawlers + Alchemy RPC + HeyElsa + ENS:

| Signal | Weight | Source |
|--------|--------|--------|
| wallet_age_days | HIGH | Alchemy ETH |
| tx_count_90d | HIGH | Alchemy Base |
| tvl_usd | HIGH | HeyElsa / estimated |
| defi_protocol_count | HIGH | Alchemy Base |
| erc8004_reputation (0-10) | HIGH | ERC-8004 contract |
| erc8004_job_count | HIGH | ERC-8004 contract |
| anomaly_score | HIGH | IsolationForest |
| is_anomaly | HIGH | IsolationForest |
| ensip25_verified | MEDIUM | ENS ETH mainnet |
| cross_chain_count | MEDIUM | Alchemy multi-chain |
| platform_count | MEDIUM | All crawlers |
| tee_secured | MEDIUM | Not yet implemented |
| olas_job_count | MEDIUM | Olas subgraph |
| tx_count_total | LOW | Alchemy ETH |
| balance_eth | LOW | Alchemy Base |
| balance_usdc | LOW | Alchemy Base |
| nft_count | LOW | Alchemy Base |
| virtuals_mcap_usd | LOW | Virtuals API |
| virtuals_holder_count | LOW | Virtuals API |

### Scoring Tiers

| Tier | Score | Collateral | Max Loan |
|------|-------|-----------|----------|
| S | 900–1000 | 30% | $500,000 USDC |
| A | 750–899 | 75% | $100,000 USDC |
| B | 600–749 | 120% | $25,000 USDC |
| C | 450–599 | 150% | $5,000 USDC |
| D | 0–449 | 200% | $1,000 USDC |

**Anomaly cap:** If IsolationForest flags `is_anomaly=true`, the score is capped at 599 (Tier C max).

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, Python 3.11, pydantic-settings |
| Scoring | LangGraph 0.2, OpenAI o3, scikit-learn IsolationForest |
| Database | Supabase (PostgreSQL 15 + Realtime + RLS) |
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS |
| Wallet | wagmi v2, viem v2, RainbowKit v2 |
| UI | shadcn/ui, Recharts, Framer Motion |
| Blockchain | Base mainnet (8453), Base Sepolia (84532) |
| Standards | ERC-8004, ENSIP-25, x402 |
| RPC | Alchemy (Base + ETH mainnet) |
| DeFi API | HeyElsa x402 (USDC micropayments) |

---

## Quick Start

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env            # fill in credentials
uvicorn main:app --reload       # API at http://localhost:8000
python worker.py                # start background scorer (separate terminal)
```

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local  # fill in credentials
npm run dev                       # UI at http://localhost:3000
```

### Database

Run `supabase/schema.sql` in the [Supabase SQL Editor](https://supabase.com/dashboard/project/vvxhbyfqxmyfigczwqsk/sql/new), then enable Realtime on `agents`, `scores`, and `score_requests`.

---

## Project Structure

```
agentscore/
├── backend/
│   ├── main.py                    # FastAPI entry point
│   ├── worker.py                  # Background scoring worker
│   ├── requirements.txt
│   └── app/
│       ├── config.py              # Environment config
│       ├── api/                   # Route handlers (6 modules)
│       ├── crawlers/              # Platform data fetchers (5 crawlers)
│       ├── pipeline/              # LangGraph scoring (9-node graph)
│       ├── services/              # Business logic (features, anomaly, ENS, HeyElsa)
│       └── models/                # Pydantic models
├── frontend/
│   ├── app/                       # Next.js pages (landing, agent profile, leaderboard)
│   ├── components/                # React components (ScoreCard, FeatureRadar, etc.)
│   └── lib/                       # Utilities (Supabase, wagmi, API client)
├── contracts/                     # (empty — AgentScoreAnchor.sol not yet built)
└── supabase/
    └── schema.sql                 # Full database schema
```

---

## Completion Status

**Overall: ~85-90% complete for hackathon demo.**

- All core scoring infrastructure is operational
- 5 of 10 platform crawlers are built (covering the largest agent ecosystems)
- Full frontend with real-time score updates
- Smart contract anchoring is the main missing piece
- Graceful degradation — pipeline continues even if individual data sources fail

---

*AgentScore — ETH Mumbai 2026*
