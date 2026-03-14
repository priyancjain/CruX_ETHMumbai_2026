-- ============================================================
-- AgentScore: HeyElsa Enrichment Migration
-- Run in Supabase SQL Editor:
-- https://supabase.com/dashboard/project/vvxhbyfqxmyfigczwqsk/sql/new
-- ============================================================

-- ── Table: agent_transactions ──────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_transactions (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id        uuid REFERENCES agents(id) ON DELETE CASCADE,
  wallet_address  text NOT NULL,
  tx_hash         text NOT NULL,
  block_number    bigint,
  chain           text DEFAULT 'base',
  from_address    text,
  to_address      text,
  value_raw       text,
  value_usd       numeric,
  token_symbol    text,
  token_address   text,
  tx_type         text,
  protocol_name   text,
  gas_used        numeric,
  tx_fee_usd      numeric,
  is_incoming     boolean DEFAULT false,
  timestamp       timestamptz NOT NULL,
  raw_data        jsonb,
  created_at      timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_agent_tx_wallet ON agent_transactions(wallet_address);
CREATE INDEX IF NOT EXISTS idx_agent_tx_time   ON agent_transactions(timestamp DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_tx_unique ON agent_transactions(wallet_address, tx_hash);

-- ── Table: agent_pnl ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_pnl (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id           uuid REFERENCES agents(id) ON DELETE CASCADE,
  wallet_address     text NOT NULL,
  total_pnl_usd      numeric DEFAULT 0,
  realized_pnl_usd   numeric DEFAULT 0,
  unrealized_pnl_usd numeric DEFAULT 0,
  win_rate           float8 DEFAULT 0,
  total_trades       integer DEFAULT 0,
  profitable_trades  integer DEFAULT 0,
  avg_trade_size_usd numeric DEFAULT 0,
  largest_win_usd    numeric DEFAULT 0,
  largest_loss_usd   numeric DEFAULT 0,
  tokens_traded      jsonb DEFAULT '[]',
  period_days        integer DEFAULT 90,
  raw_data           jsonb,
  snapshot_at        timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_pnl_wallet ON agent_pnl(wallet_address);
CREATE INDEX IF NOT EXISTS idx_pnl_time   ON agent_pnl(snapshot_at DESC);

-- ── Table: agent_positions ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_positions (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id        uuid REFERENCES agents(id) ON DELETE CASCADE,
  wallet_address  text NOT NULL,
  position_type   text NOT NULL CHECK (position_type IN ('token','defi','staking','nft')),
  token_symbol    text,
  token_address   text,
  protocol_name   text,
  chain           text DEFAULT 'base',
  balance_raw     text,
  balance_usd     numeric DEFAULT 0,
  apy             float8,
  raw_data        jsonb,
  snapshot_at     timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_positions_wallet ON agent_positions(wallet_address);
CREATE INDEX IF NOT EXISTS idx_positions_time   ON agent_positions(snapshot_at DESC);

-- ── Row Level Security ─────────────────────────────────────────
ALTER TABLE agent_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_pnl          ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_positions    ENABLE ROW LEVEL SECURITY;

CREATE POLICY "public_read_transactions"   ON agent_transactions  FOR SELECT USING (true);
CREATE POLICY "public_read_pnl"            ON agent_pnl           FOR SELECT USING (true);
CREATE POLICY "public_read_positions"      ON agent_positions     FOR SELECT USING (true);

CREATE POLICY "service_write_transactions" ON agent_transactions  FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "service_write_pnl"          ON agent_pnl           FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "service_write_positions"    ON agent_positions     FOR ALL USING (auth.role() = 'service_role');

-- ── Extend agent_features with HeyElsa columns ────────────────
ALTER TABLE agent_features ADD COLUMN IF NOT EXISTS heyelsa_risk_score    float8  DEFAULT 0;
ALTER TABLE agent_features ADD COLUMN IF NOT EXISTS heyelsa_defi_activity float8  DEFAULT 0;
ALTER TABLE agent_features ADD COLUMN IF NOT EXISTS heyelsa_wallet_label  text    DEFAULT '';
ALTER TABLE agent_features ADD COLUMN IF NOT EXISTS total_pnl_usd        numeric DEFAULT 0;
ALTER TABLE agent_features ADD COLUMN IF NOT EXISTS win_rate             float8  DEFAULT 0;
ALTER TABLE agent_features ADD COLUMN IF NOT EXISTS total_trades         integer DEFAULT 0;
ALTER TABLE agent_features ADD COLUMN IF NOT EXISTS avg_trade_size_usd   numeric DEFAULT 0;
ALTER TABLE agent_features ADD COLUMN IF NOT EXISTS staking_balance_usd  numeric DEFAULT 0;
ALTER TABLE agent_features ADD COLUMN IF NOT EXISTS token_diversity      integer DEFAULT 0;
