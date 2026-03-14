# AgentScore Backend

## 1. Project Overview
The AgentScore backend is the core engine for generating credit scores for autonomous AI agents across various platforms (Virtuals, ElizaOS, Olas, Fetch.ai, ERC-8004). It handles data ingestion via blockchain crawlers, ML processing via LangGraph and GPT-o3, background asynchronous job queues, and exposing a clean REST API for the frontend and third-party integrations.

## 2. Tech Stack
* **Framework**: FastAPI (Python 3.10+) 
* **Database**: PostgreSQL (via Supabase) with `supabase-py`
* **Workflow / AI**: LangGraph, Langchain, Scikit-learn, OpenAI (GPT-o3-mini)
* **Web3 Integration**: `web3.py`, `eth-abi`, Alchemy APIs
* **Background Jobs**: Custom Python asynchronous worker polling (`worker.py`)
* **Data parsing**: Pydantic schemas

## 3. Folder Structure
```text
/backend
 ├── main.py          # FastAPI application entry point, routers, CORS setup
 ├── worker.py        # Async background worker polling Supabase for scoring jobs
 ├── requirements.txt # Python dependencies
 └── /app
      ├── /api        # Fast API router controllers (score.py, agents.py, leaderboard.py, health.py)
      ├── /models     # Pydantic schemas for request/response validation
      ├── /services   # Core business logic (scoring.py orchestrator, supabase.py DB wrappers, anomaly.py)
      ├── /pipeline   # LangGraph DAG definition (graph.py, nodes.py, state.py, prompt.py)
      ├── /crawlers   # External data ingestion (base_rpc.py, virtuals.py, olas.py, fetchai.py, elizaos.py)
      └── config.py   # Global Pydantic settings loading from .env
```

## 4. API Endpoints Overview
*(See `api_spec.md` for detailed request/response schemas)*

* **Scores**:
  * `POST /v1/score` - Queue a background scoring request
  * `GET /v1/score/{wallet}` - Retrieve the latest score
  * `GET /v1/score/{wallet}/history` - Retrieve score history (limit 10)
  * `GET /v1/score/request/{id}` - Poll queuing status
* **Agents**:
  * `GET /v1/agents` - List all agents (paginated, platform filter)
  * `GET /v1/agents/{wallet}` - Detail single agent
  * `POST /v1/agents` - Upsert agent metadata
* **Leaderboard**:
  * `GET /v1/leaderboard` - Ranked agents from materialized view
  * `GET /v1/stats` - Platform-wide aggregates

## 5. Database Schema
The database uses PostgreSQL via Supabase.

1. **`agents`**
   * `wallet_address` (PK, string, lowercase)
   * `name` (string)
   * `platform` (string)
   * `ens_name` (string)
   * `avatar_url` (string)
   * `created_at` (timestamp)
2. **`score_requests`**
   * `id` (PK, UUID)
   * `wallet_address` (FK string)
   * `status` (string: pending, processing, completed, failed)
   * `score_id` (FK UUID, nullable)
   * `error` (text)
   * Fields: `priority`, `requested_by`, `attempts`, `created_at`, `updated_at`, `completed_at`
3. **`scores`**
   * `id` (PK, UUID)
   * `wallet_address` (FK string)
   * `score` (int, 0-1000)
   * `tier` (string: S, A, B, C, D)
   * `rationale` (text, from GPT-o3)
   * `key_factors`, `risk_flags` (jsonb array)
   * `is_anomaly` (boolean)
   * `pipeline_error` (text)
   * Fields: `platform`, `agent_id`, `model_used`, `anomaly_score`, `ensip25_verified`, `onchain_tx_hash`, `started_at`, `created_at`
4. **`agent_features`**
   * `wallet_address` (PK)
   * `features` (JSONB) - Normalized 22 signals
   * `raw_data` (JSONB) - Scraped raw blockchain/API data
   * Fields: `platform`, `agent_id`, `anomaly_score`, `is_anomaly`, `scored_at`, `pipeline_error`
5. **`leaderboard_view`**
   * Materialized view compiling the highest latest scores per agent.

## 6. Business Logic & ML Pipeline
Scoring logic is decoupled into a clear pipeline via `LangGraph` (`app/pipeline/graph.py`):
1. **Initialize State**: Start pipeline for a given wallet.
2. **Crawlers**: Fetch on-chain Base RPC metrics, then call Virtuals, Olas, Fetch.ai, ERC-8004 APIs sequentially to collect raw signals.
3. **ENSIP-25 Check**: Verify agent reputation anchors.
4. **Compute Features**: Normalize raw metrics into exactly 22 floating-point signals. Execute IsolationForest anomaly detection (`anomaly.py`).
5. **GPT Score**: Pass normalized features and platform context into `prompt.py`, where GPT-o3-mini returns a structured JSON mapping 0-1000 score, tier, strengths, and risks.

## 7. Authentication and Authorization
The API endpoints are generally unauthenticated for reading scores. 
Rate-limiting and authorization (e.g., API Keys) should be applied at an API Gateway level or implemented inside FastAPI dependencies for POST write endpoints if exposed to the public. 
Database access uses Supabase with strong RLS (Row Level Security) and Service Role keys.

## 8. External Integrations
* **OpenAI API**: GPT-o3-mini for qualitative model reasoning.
* **Alchemy**: Base and Ethereum JSON-RPC nodes to fetch balances, TX counts.
* **Supabase**: PostgreSQL host and Realtime data socket backend.
* **The Graph Protocol**: Subgraph querying.
* **HeyElsa (x402)**: External LLM payer verification limits.

## 9. Environment Variables
* `openai_api_key`, `openai_model`
* `supabase_url`, `supabase_anon_key`, `supabase_service_key`
* `alchemy_api_key`, `alchemy_base_rpc`, `alchemy_eth_rpc`
* `erc8004_registry`, `virtual_token_base`
* `worker_poll_interval`, `worker_max_concurrent`

## 10. Data Flow
**Scoring Sequence**:
1. Request hits `POST /v1/score`. FastAPI checks cache, inserts `pending` row into `score_requests`, returns `202 Accepted` + UUID.
2. `worker.py` (running loop) spots `pending` job, updates to `processing`.
3. Worker invokes `services.scoring.score_agent`.
4. `score_agent` triggers `run_scoring_pipeline` (LangGraph).
5. LangGraph node cascade hits 3rd-party APIs, transforms data, pings OpenAI.
6. `score_agent` receives final state, UPSERTS `agent_features`, INSERTS `scores`.
7. Worker updates `score_requests` to `completed`.
8. Frontend listens to Supabase Realtime channel for `scores` table insert and updates UI.

## 11. Error Handling
* Pydantic catches schema validation errors heavily resulting in `422 Unprocessable Entity`.
* Standard internal issues raise `HTTPException(500)`.
* Failed background pipeline tasks mark the request as `failed` inside `score_requests`, preserving the stack trace in the `error` column for debugging.

## 12. Deployment Instructions
1. Install Python 3.10+
2. `pip install -r requirements.txt`
3. Populate `.env` with required keys.
4. Execute DB migrations in Supabase to build the schemas.
5. In Terminal 1, run API: `python -m uvicorn main:app --host 0.0.0.0 --port 8000`
6. In Terminal 2, run Worker: `python worker.py`

## 13. Rebuild Instructions
*(Refer to `backend_architecture.md` for a deeper architectural rebuild breakdown).*
1. Initialize a FastAPI project and configure `pydantic-settings`.
2. Map the 5 database schemas (tables/views) in Supabase.
3. Build the LangGraph pipeline separating crawling, transformation, and AI grading.
4. Construct `main.py` routing layer pointing to `services/`.
5. Write `worker.py` utilizing `asyncio.Semaphore` to poll and rate-limit DB consumption.
