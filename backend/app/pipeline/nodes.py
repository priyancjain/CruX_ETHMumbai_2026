import asyncio
import json
import logging
from openai import OpenAI
from app.config import get_settings
from app.pipeline.state import AgentScoreState
from app.pipeline.prompt import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE, ANOMALY_WARNING
from app.crawlers import virtuals, olas, fetchai, elizaos, base_rpc
from app.services.ensip25 import check_ensip25
from app.services.anomaly import run_anomaly_detection
from app.services.features import aggregate_features, upsert_features
from app.services.heyelsa import analyze_wallet
from app.services.supabase import service_client, anon_client
from app.services.onchain_anchor import anchor_score_onchain

logger = logging.getLogger("agentscore.pipeline")


# ── NODE 1: Fetch Platform Data ─────────────────────────────────────────────
async def fetch_platforms(state: AgentScoreState) -> dict:
    """Fetch agent data from all supported platforms in parallel."""
    wallet = state["wallet_address"]
    logger.info(f"\n{'='*60}")
    logger.info(f"  NODE 1: PLATFORM CRAWLERS — {wallet}")
    logger.info(f"{'='*60}")

    results = await asyncio.gather(
        virtuals.fetch_agent(wallet),
        elizaos.fetch_agent(wallet),
        olas.fetch_agent(wallet),
        fetchai.fetch_agent(wallet),
        return_exceptions=True,
    )

    data = {
        "virtuals_data": results[0] if not isinstance(results[0], Exception) else {"found": False},
        "elizaos_data": results[1] if not isinstance(results[1], Exception) else {"found": False},
        "olas_data": results[2] if not isinstance(results[2], Exception) else {"found": False},
        "fetch_data": results[3] if not isinstance(results[3], Exception) else {"found": False},
    }

    # Summary table
    names = ["Virtuals", "ERC-8004/ElizaOS", "Olas", "Fetch.ai"]
    logger.info(f"\n  {'Platform':<20} {'Status':<10} {'Details'}")
    logger.info(f"  {'-'*55}")
    for name, result in zip(names, results):
        if isinstance(result, Exception):
            logger.info(f"  {name:<20} {'ERROR':<10} {str(result)[:40]}")
        elif result.get("found"):
            detail = result.get("agent_name") or result.get("agent_id") or "found"
            logger.info(f"  {name:<20} {'FOUND':<10} {detail}")
        else:
            logger.info(f"  {name:<20} {'—':<10}")

    return data


# ── NODE 2: Fetch Onchain Data ──────────────────────────────────────────────
async def fetch_onchain(state: AgentScoreState) -> dict:
    """
    Fetch wallet data from Base and ETH mainnet via Alchemy + HeyElsa x402.

    Alchemy provides: wallet_age_days, tx_count_90d, tx_count_total, balance_eth,
                      balance_usdc, defi_protocol_count, nft_count, activity_streak_days,
                      unique_counterparties_90d, contract_deploy_count, cross_chain_count,
                      last_seen_at_days, erc20_token_count, defi_protocols_used
    HeyElsa provides: tvl_usd, defi_positions, risk assessment, protocol list
    """
    wallet = state["wallet_address"]
    logger.info(f"\n{'='*60}")
    logger.info(f"  NODE 2: ONCHAIN DATA (Alchemy + HeyElsa) — {wallet}")
    logger.info(f"{'='*60}")

    # Run Alchemy + HeyElsa in parallel for speed
    onchain_result, heyelsa_result = await asyncio.gather(
        base_rpc.get_wallet_data(wallet),
        analyze_wallet(wallet),
        return_exceptions=True,
    )

    onchain = onchain_result if not isinstance(onchain_result, Exception) else {}
    heyelsa = heyelsa_result if not isinstance(heyelsa_result, Exception) else {}

    if isinstance(onchain_result, Exception):
        logger.error(f"[Node 2] Alchemy data fetch failed: {onchain_result}")
    else:
        logger.info(
            f"[Node 2] Alchemy data: tx_total={onchain.get('tx_count_total')}, "
            f"tx_90d={onchain.get('tx_count_90d')}, "
            f"wallet_age={onchain.get('wallet_age_days')}d, "
            f"last_seen={onchain.get('last_seen_at_days')}d, "
            f"streak={onchain.get('activity_streak_days')}d, "
            f"balance_eth={onchain.get('balance_eth')}, "
            f"balance_usdc={onchain.get('balance_usdc')}, "
            f"nfts={onchain.get('nft_count')}, "
            f"defi_protocols={onchain.get('defi_protocol_count')}, "
            f"counterparties_90d={onchain.get('unique_counterparties_90d')}, "
            f"contract_deploys={onchain.get('contract_deploy_count')}, "
            f"cross_chain={onchain.get('cross_chain_count')}"
        )

    if isinstance(heyelsa_result, Exception):
        logger.error(f"[Node 2] HeyElsa data fetch failed: {heyelsa_result}")
    elif heyelsa:
        logger.info(f"[Node 2] HeyElsa data: tvl={heyelsa.get('tvl_usd')}, risk={heyelsa.get('risk_score')}")
    else:
        logger.warning(f"[Node 2] HeyElsa returned empty data (x402 payment may have failed)")

    return {
        "onchain_data": onchain,
        "heyelsa_data": heyelsa,
    }


# ── NODE 3: Fetch ERC-8004 Data ─────────────────────────────────────────────
async def fetch_erc8004(state: AgentScoreState) -> dict:
    """Check ERC-8004 Identity + Reputation registries."""
    wallet = state["wallet_address"]
    logger.info(f"\n{'='*60}")
    logger.info(f"  NODE 3: ERC-8004 IDENTITY + REPUTATION — {wallet}")
    logger.info(f"{'='*60}")

    # elizaos crawler already queries ERC-8004
    erc8004_data = state.get("elizaos_data", {})
    if not erc8004_data.get("found"):
        erc8004_data = await elizaos.fetch_agent(wallet)

    if erc8004_data.get("found"):
        logger.info(
            f"  ERC-8004 agent_id    = {erc8004_data.get('agent_id')}\n"
            f"  ERC-8004 reputation  = {erc8004_data.get('reputation_score')}\n"
            f"  ERC-8004 feedback    = {erc8004_data.get('feedback_count')}\n"
            f"  ERC-8004 chain       = {erc8004_data.get('chain')}"
        )
    else:
        logger.info("  ERC-8004: No agent identity found")

    return {"erc8004_data": erc8004_data}


# ── NODE 4: Fetch ENS + ENSIP-25 ────────────────────────────────────────────
async def fetch_ens_ensip25(state: AgentScoreState) -> dict:
    """
    Reverse resolve wallet → ENS name, then verify ENSIP-25.
    Needs agentId from Node 3 (ERC-8004) for text record key construction.
    """
    wallet = state["wallet_address"]
    logger.info(f"\n{'='*60}")
    logger.info(f"  NODE 4: ENS + ENSIP-25 VERIFICATION — {wallet}")
    logger.info(f"{'='*60}")

    # Get agentId from ERC-8004 data (set in Node 3)
    agent_id = state.get("erc8004_data", {}).get("agent_id")

    ens_data = await check_ensip25(wallet, agent_id)

    logger.info(
        f"  ENS name          = {ens_data.get('ens_name') or '—'}\n"
        f"  ENSIP-25 verified = {ens_data.get('ensip25_verified', False)}"
    )

    return {"ens_data": ens_data}


# ── NODE 5: Aggregate Features ──────────────────────────────────────────────
async def node_aggregate_features(state: AgentScoreState) -> dict:
    """Merge all data sources into 22-field feature vector."""
    wallet = state["wallet_address"]
    logger.info(f"\n{'='*60}")
    logger.info(f"  NODE 5: FEATURE AGGREGATION — {wallet}")
    logger.info(f"{'='*60}")

    features = aggregate_features(
        wallet_address=wallet,
        virtuals_data=state.get("virtuals_data", {}),
        elizaos_data=state.get("elizaos_data", {}),
        olas_data=state.get("olas_data", {}),
        fetch_data=state.get("fetch_data", {}),
        erc8004_data=state.get("erc8004_data", {}),
        onchain_data=state.get("onchain_data", {}),
        ens_data=state.get("ens_data", {}),
        heyelsa_data=state.get("heyelsa_data", {}),
    )

    # Print full feature extraction table with sources
    logger.info(f"\n  {'#':<4} {'Feature':<24} {'Value':<16} {'Source'}")
    logger.info(f"  {'-'*65}")
    feature_rows = [
        ("1",  "wallet_age_days",           features.get("wallet_age_days", 0),           "Alchemy"),
        ("2",  "tx_count_90d",              features.get("tx_count_90d", 0),              "Alchemy"),
        ("3",  "tx_count_total",            features.get("tx_count_total", 0),            "Alchemy"),
        ("4",  "last_seen_at_days",         features.get("last_seen_at_days", 999),       "Alchemy"),
        ("5",  "activity_streak_days",      features.get("activity_streak_days", 0),      "Alchemy"),
        ("6",  "unique_counterparties_90d", features.get("unique_counterparties_90d", 0), "Alchemy"),
        ("7",  "contract_deploy_count",     features.get("contract_deploy_count", 0),     "Alchemy"),
        ("8",  "tvl_usd",                   features.get("tvl_usd", 0),                  "HeyElsa / Alchemy"),
        ("9",  "balance_eth",               features.get("balance_eth", 0),               "Alchemy"),
        ("10", "balance_usdc",              features.get("balance_usdc", 0),              "Alchemy"),
        ("11", "erc20_token_count",         features.get("erc20_token_count", 0),         "Alchemy"),
        ("12", "defi_protocol_count",       features.get("defi_protocol_count", 0),       "Alchemy / HeyElsa"),
        ("13", "nft_count",                 features.get("nft_count", 0),                 "Alchemy NFT API"),
        ("14", "erc8004_reputation",        features.get("erc8004_reputation", 0),        "ERC-8004 Registry"),
        ("15", "erc8004_job_count",         features.get("erc8004_job_count", 0),         "ERC-8004 / Olas"),
        ("16", "ensip25_verified",          features.get("ensip25_verified", False),       "ENS (ETH mainnet)"),
        ("17", "cross_chain_count",         features.get("cross_chain_count", 1),         "Alchemy multi-chain"),
        ("18", "platform_count",            features.get("platform_count", 1),            "All crawlers"),
        ("19", "platforms_list",            features.get("platforms_list", []),            "All crawlers"),
        ("20", "virtuals_mcap_usd",         features.get("virtuals_mcap_usd", 0),         "Virtuals API"),
        ("21", "virtuals_holder_count",     features.get("virtuals_holder_count", 0),     "Virtuals API"),
        ("22", "olas_job_count",            features.get("olas_job_count", 0),             "Olas Subgraph"),
        ("23", "fetch_active_services",     features.get("fetch_active_services", 0),     "Fetch.ai Agentverse"),
        ("24", "anomaly_score",             features.get("anomaly_score", 0),              "IsolationForest"),
        ("25", "is_anomaly",                features.get("is_anomaly", False),             "IsolationForest"),
    ]
    for num, name, value, source in feature_rows:
        logger.info(f"  {num:<4} {name:<24} {str(value):<16} {source}")

    # Ensure/upsert agent record in DB
    agent_name = (
        state.get("virtuals_data", {}).get("agent_name")
        or state.get("fetch_data", {}).get("agent_name")
        or f"Agent-{wallet[:8]}"
    )
    platform = "erc8004"
    platform_agent_id = str(state.get("erc8004_data", {}).get("agent_id", wallet))
    if state.get("virtuals_data", {}).get("found"):
        platform = "virtuals"
        platform_agent_id = state["virtuals_data"].get("platform_agent_id", wallet)
    elif state.get("olas_data", {}).get("found"):
        platform = "olas"
        platform_agent_id = str(state["olas_data"].get("agent_id", wallet))
    elif state.get("fetch_data", {}).get("found"):
        platform = "fetch"
        platform_agent_id = state["fetch_data"].get("agent_address", wallet)

    try:
        agent_row = {
            "wallet_address": wallet,
            "agent_name": agent_name,
            "platform": platform,
            "platform_agent_id": platform_agent_id,
            "ens_name": state.get("ens_data", {}).get("ens_name"),
            "is_active": True,
        }
        result = service_client.table("agents").upsert(
            agent_row, on_conflict="wallet_address"
        ).execute()

        if result.data:
            agent_id = result.data[0]["id"]
            upsert_features(agent_id, features)
    except Exception as e:
        logger.warning(f"Failed to upsert agent/features: {e}")

    return {"features": features}


# ── NODE 6: Run Anomaly Detection ───────────────────────────────────────────
async def run_anomaly(state: AgentScoreState) -> dict:
    """Run IsolationForest anomaly detection."""
    logger.info(f"\n{'='*60}")
    logger.info(f"  NODE 6: ANOMALY DETECTION (IsolationForest)")
    logger.info(f"{'='*60}")

    features = state.get("features", {})

    # Get historical features for training
    historical = []
    try:
        result = anon_client.table("agent_features").select("*").limit(500).execute()
        historical = result.data or []
    except Exception:
        pass

    anomaly_result = run_anomaly_detection(features, historical)

    # Update features with anomaly result
    features["anomaly_score"] = anomaly_result["anomaly_score"]
    features["is_anomaly"] = anomaly_result["is_anomaly"]

    logger.info(
        f"  Historical samples  = {len(historical)}\n"
        f"  Anomaly score       = {anomaly_result['anomaly_score']}\n"
        f"  Is anomaly          = {anomaly_result['is_anomaly']}"
    )
    if anomaly_result["is_anomaly"]:
        logger.warning("  ⚠ ANOMALY DETECTED — score will be capped at Tier C (max 599)")

    return {
        "anomaly_result": anomaly_result,
        "features": features,
    }


# ── NODE 7: Run GPT-o3 Scoring ──────────────────────────────────────────────
async def run_gpt_o3(state: AgentScoreState) -> dict:
    """Call OpenAI o3 to generate credit score."""
    logger.info(f"\n{'='*60}")
    logger.info(f"  NODE 7: GPT-o3 CREDIT SCORING")
    logger.info(f"{'='*60}")

    settings = get_settings()
    features = state.get("features", {})
    anomaly = state.get("anomaly_result", {})

    # Build prompt
    system = SYSTEM_PROMPT
    if anomaly.get("is_anomaly"):
        system += ANOMALY_WARNING

    user_prompt = USER_PROMPT_TEMPLATE.format(
        wallet_address=state["wallet_address"],
        platforms_list=", ".join(features.get("platforms_list", [])) or "unknown",
        wallet_age_days=features.get("wallet_age_days", 0),
        tx_count_90d=features.get("tx_count_90d", 0),
        tx_count_total=features.get("tx_count_total", 0),
        last_seen_at_days=features.get("last_seen_at_days", 999),
        activity_streak_days=features.get("activity_streak_days", 0),
        unique_counterparties_90d=features.get("unique_counterparties_90d", 0),
        contract_deploy_count=features.get("contract_deploy_count", 0),
        tvl_usd=features.get("tvl_usd", 0),
        tvl_source=features.get("tvl_source", "onchain_estimate"),
        balance_eth=features.get("balance_eth", 0),
        balance_usdc=features.get("balance_usdc", 0),
        erc20_token_count=features.get("erc20_token_count", 0),
        defi_protocol_count=features.get("defi_protocol_count", 0),
        defi_protocols_used=", ".join(features.get("defi_protocols_used", [])) or "none",
        nft_count=features.get("nft_count", 0),
        cross_chain_count=features.get("cross_chain_count", 1),
        has_erc8004_profile=features.get("has_erc8004_profile", False),
        erc8004_reputation=features.get("erc8004_reputation", 0),
        erc8004_job_count=features.get("erc8004_job_count", 0),
        ensip25_verified=features.get("ensip25_verified", False),
        tee_secured=features.get("tee_secured", False),
        platform_count=features.get("platform_count", 1),
        virtuals_mcap_usd=features.get("virtuals_mcap_usd", 0),
        virtuals_holder_count=features.get("virtuals_holder_count", 0),
        olas_job_count=features.get("olas_job_count", 0),
        heyelsa_available=features.get("heyelsa_available", False),
        anomaly_score=features.get("anomaly_score", 0),
        is_anomaly=features.get("is_anomaly", False),
    )

    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ],
        max_completion_tokens=settings.OPENAI_MAX_TOKENS,
    )

    raw_text = response.choices[0].message.content.strip()

    # Parse JSON from response (handle markdown code blocks)
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    gpt_response = json.loads(raw_text)

    # Validate tier/score consistency
    score = gpt_response["score"]
    tier = gpt_response["tier"]
    expected_tier = _score_to_tier(score)
    if tier != expected_tier:
        logger.warning(f"GPT returned tier {tier} but score {score} maps to {expected_tier}. Correcting.")
        gpt_response["tier"] = expected_tier
        gpt_response["collateral_requirement"] = _tier_collateral(expected_tier)
        gpt_response["max_loan_usdc"] = _tier_max_loan(expected_tier)

    # Enforce anomaly cap
    if anomaly.get("is_anomaly") and score > 599:
        logger.warning(f"Anomaly detected but score {score} > 599. Capping at 599.")
        gpt_response["score"] = 599
        gpt_response["tier"] = "C"
        gpt_response["collateral_requirement"] = 150
        gpt_response["max_loan_usdc"] = 5000

    logger.info(
        f"\n  GPT-o3 RESULT:\n"
        f"  {'Score':<20} = {gpt_response.get('score')}\n"
        f"  {'Tier':<20} = {gpt_response.get('tier')}\n"
        f"  {'Collateral':<20} = {gpt_response.get('collateral_requirement')}%\n"
        f"  {'Max Loan':<20} = ${gpt_response.get('max_loan_usdc'):,.0f} USDC\n"
        f"  {'Rationale':<20} = {gpt_response.get('rationale', '')[:100]}...\n"
        f"  {'Key Factors':<20} = {gpt_response.get('key_factors', [])}\n"
        f"  {'Risk Flags':<20} = {gpt_response.get('risk_flags', [])}"
    )

    return {"gpt_response": gpt_response}


# ── NODE 8: Save Score ──────────────────────────────────────────────────────
async def save_score(state: AgentScoreState) -> dict:
    """Save score to Supabase scores table."""
    logger.info(f"\n{'='*60}")
    logger.info(f"  NODE 8: SAVING SCORE TO SUPABASE")
    logger.info(f"{'='*60}")

    gpt = state.get("gpt_response", {})
    features = state.get("features", {})
    wallet = state["wallet_address"]

    # Get agent_id
    agent_id = None
    try:
        result = anon_client.table("agents").select("id").eq(
            "wallet_address", wallet
        ).limit(1).execute()
        if result.data:
            agent_id = result.data[0]["id"]
    except Exception:
        pass

    score_row = {
        "agent_id": agent_id,
        "wallet_address": wallet,
        "score": gpt["score"],
        "tier": gpt["tier"],
        "collateral_requirement": gpt["collateral_requirement"],
        "max_loan_usdc": gpt["max_loan_usdc"],
        "rationale": gpt["rationale"],
        "key_factors": gpt.get("key_factors", []),
        "risk_flags": gpt.get("risk_flags", []),
        "raw_features": features,
        "model_used": "o3",
        "anomaly_score": features.get("anomaly_score", 0),
        "is_anomaly": features.get("is_anomaly", False),
    }

    result = service_client.table("scores").insert(score_row).execute()
    score_id = result.data[0]["id"] if result.data else None

    logger.info(f"  Score saved: id={score_id}, score={gpt['score']}, tier={gpt['tier']}")

    return {"score_id": score_id}


# ── NODE 9: Anchor Onchain (Optional) ───────────────────────────────────────
async def anchor_onchain(state: AgentScoreState) -> dict:
    """
    Anchor score hash on Base Sepolia via AgentScoreAnchor contract.
    Skips gracefully if contract not deployed or no gas.
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"  NODE 9: ONCHAIN ANCHOR (Base Sepolia)")
    logger.info(f"{'='*60}")

    score_id = state.get("score_id")
    if not score_id:
        logger.info("  Skipped: no score_id to anchor")
        return {}

    gpt = state.get("gpt_response", {})
    wallet = state["wallet_address"]
    score = gpt.get("score", 0)
    tier = gpt.get("tier", "D")

    tx_hash = await anchor_score_onchain(
        wallet_address=wallet,
        score=score,
        tier=tier,
    )

    if tx_hash:
        # Update the scores row with the on-chain tx hash
        try:
            service_client.table("scores").update({
                "onchain_tx_hash": tx_hash,
            }).eq("id", score_id).execute()
            logger.info(f"  Updated score {score_id} with onchain_tx_hash={tx_hash}")
        except Exception as e:
            logger.warning(f"  Failed to update score with tx_hash: {e}")
    else:
        logger.info(
            f"  Score {score_id} saved to Supabase only (no on-chain anchor).\n"
            f"  To enable: deploy AgentScoreAnchor.sol, fund wallet with Base Sepolia ETH,\n"
            f"  and set SCORE_ANCHOR_ADDRESS + SCORE_ANCHOR_PRIVATE_KEY in .env"
        )

    return {}


# ── Helper functions ─────────────────────────────────────────────────────────
def _score_to_tier(score: int) -> str:
    if score >= 900:
        return "S"
    if score >= 750:
        return "A"
    if score >= 600:
        return "B"
    if score >= 450:
        return "C"
    return "D"


def _tier_collateral(tier: str) -> int:
    return {"S": 30, "A": 75, "B": 120, "C": 150, "D": 200}.get(tier, 200)


def _tier_max_loan(tier: str) -> float:
    return {"S": 500000, "A": 100000, "B": 25000, "C": 5000, "D": 1000}.get(tier, 1000)
