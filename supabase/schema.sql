-- AgentScore — Supabase Schema
-- Run in Supabase SQL Editor: https://supabase.com/dashboard/project/vvxhbyfqxmyfigczwqsk/sql/new

-- ── Table: agents ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agents (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  wallet_address    text UNIQUE NOT NULL,
  ens_name          text,
  platform          text NOT NULL CHECK (platform IN (
                      'virtuals','elizaos','olas','fetch','erc8004',
                      'talus','wayfinder','freysa','agentlayer','sentient'
                    )),
  platform_agent_id text NOT NULL,
  agent_name        text,
  description       text,
  agent_type        text,
  is_active         boolean DEFAULT true,
  metadata          jsonb,
  created_at        timestamptz DEFAULT now(),
  last_seen_at      timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_agents_wallet   ON agents(wallet_address);
CREATE INDEX IF NOT EXISTS idx_agents_platform ON agents(platform);
CREATE INDEX IF NOT EXISTS idx_agents_active   ON agents(is_active);

-- ── Table: scores ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS scores (
  id                     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id               uuid REFERENCES agents(id) ON DELETE CASCADE,
  wallet_address         text NOT NULL,
  score                  integer NOT NULL CHECK (score BETWEEN 0 AND 1000),
  tier                   text NOT NULL CHECK (tier IN ('S','A','B','C','D')),
  collateral_requirement integer NOT NULL,
  max_loan_usdc          numeric NOT NULL,
  rationale              text NOT NULL,
  key_factors            jsonb NOT NULL DEFAULT '[]',
  risk_flags             jsonb NOT NULL DEFAULT '[]',
  raw_features           jsonb NOT NULL DEFAULT '{}',
  model_used             text DEFAULT 'o3',
  anomaly_score          float8,
  is_anomaly             boolean DEFAULT false,
  onchain_tx_hash        text,
  scored_at              timestamptz DEFAULT now(),
  expires_at             timestamptz DEFAULT now() + interval '7 days'
);
CREATE INDEX IF NOT EXISTS idx_scores_wallet    ON scores(wallet_address);
CREATE INDEX IF NOT EXISTS idx_scores_tier      ON scores(tier);
CREATE INDEX IF NOT EXISTS idx_scores_expires   ON scores(expires_at);
CREATE INDEX IF NOT EXISTS idx_scores_scored_at ON scores(scored_at DESC);

-- ── Table: agent_features ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_features (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id             uuid REFERENCES agents(id) ON DELETE CASCADE,
  wallet_age_days      integer DEFAULT 0,
  tx_count_90d         integer DEFAULT 0,
  tx_count_total       integer DEFAULT 0,
  tvl_usd              numeric DEFAULT 0,
  balance_eth          numeric DEFAULT 0,
  balance_usdc         numeric DEFAULT 0,
  defi_protocol_count  integer DEFAULT 0,
  nft_count            integer DEFAULT 0,
  erc8004_reputation   float8 DEFAULT 0,
  erc8004_job_count    integer DEFAULT 0,
  ensip25_verified     boolean DEFAULT false,
  cross_chain_count    integer DEFAULT 1,
  tee_secured          boolean DEFAULT false,
  platform_count       integer DEFAULT 1,
  platforms_list       jsonb DEFAULT '[]',
  virtuals_mcap_usd    numeric DEFAULT 0,
  virtuals_holder_count integer DEFAULT 0,
  olas_service_id      integer,
  olas_job_count       integer DEFAULT 0,
  fetch_agent_address  text,
  last_updated_at      timestamptz DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_features_agent ON agent_features(agent_id);

-- ── Table: score_requests (replaces Redis queue) ───────────────────────────
CREATE TABLE IF NOT EXISTS score_requests (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  wallet_address  text NOT NULL,
  requested_by    text,
  status          text NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending','processing','complete','failed')),
  priority        integer DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),
  attempts        integer DEFAULT 0,
  error_message   text,
  result_score_id uuid REFERENCES scores(id),
  created_at      timestamptz DEFAULT now(),
  started_at      timestamptz,
  completed_at    timestamptz
);
CREATE INDEX IF NOT EXISTS idx_requests_status   ON score_requests(status, priority, created_at);
CREATE INDEX IF NOT EXISTS idx_requests_wallet   ON score_requests(wallet_address);

-- ── Table: platform_crawl_log ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS platform_crawl_log (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  platform       text NOT NULL,
  agents_fetched integer DEFAULT 0,
  agents_new     integer DEFAULT 0,
  status         text DEFAULT 'success' CHECK (status IN ('success','partial','failed')),
  error          text,
  crawled_at     timestamptz DEFAULT now()
);

-- ── Row Level Security ─────────────────────────────────────────────────────
ALTER TABLE agents           ENABLE ROW LEVEL SECURITY;
ALTER TABLE scores           ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_features   ENABLE ROW LEVEL SECURITY;
ALTER TABLE score_requests   ENABLE ROW LEVEL SECURITY;
ALTER TABLE platform_crawl_log ENABLE ROW LEVEL SECURITY;

-- Public read (anon key can read all tables)
CREATE POLICY "public_read_agents"     ON agents           FOR SELECT USING (true);
CREATE POLICY "public_read_scores"     ON scores           FOR SELECT USING (true);
CREATE POLICY "public_read_features"   ON agent_features   FOR SELECT USING (true);
CREATE POLICY "public_read_requests"   ON score_requests   FOR SELECT USING (true);
CREATE POLICY "public_read_crawl_log"  ON platform_crawl_log FOR SELECT USING (true);

-- Service role can write (backend only uses service key)
CREATE POLICY "service_write_agents"   ON agents           FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "service_write_scores"   ON scores           FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "service_write_features" ON agent_features   FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "service_write_requests" ON score_requests   FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "service_write_crawl"    ON platform_crawl_log FOR ALL USING (auth.role() = 'service_role');

-- ── Anon can INSERT score_requests (so frontend can queue scores) ──────────
CREATE POLICY "anon_insert_requests"   ON score_requests   FOR INSERT WITH CHECK (true);
