import logging
from app.services.supabase import service_client

logger = logging.getLogger("agentscore.services.features")


def aggregate_features(
    wallet_address: str,
    virtuals_data: dict,
    elizaos_data: dict,
    olas_data: dict,
    fetch_data: dict,
    erc8004_data: dict,
    onchain_data: dict,
    ens_data: dict,
    heyelsa_data: dict,
) -> dict:
    """
    Merge ALL data sources into the 22-field feature vector.

    Data flow:
      - Virtuals API → agent_name, mcap_usd, holder_count (NOT onchain wallet data)
      - Alchemy RPC  → wallet_age_days, tx_count_90d, tx_count_total, balance_eth,
                        balance_usdc, defi_protocol_count, nft_count, failed_tx_ratio
      - HeyElsa x402 → tvl_usd, defi_positions, risk assessment
      - ERC-8004     → reputation_score, job_count
      - ENS/ENSIP-25 → ens_name, ensip25_verified
      - Olas         → service_count, job_count
      - Fetch.ai     → agent_address, active_services
    """
    # ── Count platforms the agent appears on ───────────────────────────
    platforms_list = []
    if virtuals_data.get("found"):
        platforms_list.append("virtuals")
    if olas_data.get("found"):
        platforms_list.append("olas")
    if fetch_data.get("found"):
        platforms_list.append("fetch")
    if elizaos_data.get("found"):
        platforms_list.append("elizaos")
    if erc8004_data.get("found"):
        if "erc8004" not in platforms_list:
            platforms_list.append("erc8004")

    platform_count = max(len(platforms_list), 1)

    # ── Cross-chain count ──────────────────────────────────────────────
    # base_rpc now returns cross_chain_count directly (Base + ETH)
    cross_chain = int(onchain_data.get("cross_chain_count", 1))
    # Olas on Gnosis chain
    if olas_data.get("found") and olas_data.get("gnosis_found"):
        cross_chain += 1

    # ── TVL: prefer HeyElsa data, fallback to computed balance ─────────
    tvl_usd = float(heyelsa_data.get("tvl_usd", 0) or 0)
    if tvl_usd == 0:
        # Estimate TVL from balances (rough approximation)
        eth_price_approx = 3000  # Rough ETH price for estimation
        tvl_usd = (
            float(onchain_data.get("balance_eth", 0)) * eth_price_approx
            + float(onchain_data.get("balance_usdc", 0))
        )

    # ── DeFi protocol count: augment with HeyElsa protocols ───────────
    defi_protocol_count = int(onchain_data.get("defi_protocol_count", 0))
    heyelsa_protocols = heyelsa_data.get("protocol_list", [])
    if heyelsa_protocols:
        defi_protocol_count = max(defi_protocol_count, len(heyelsa_protocols))

    # ── Build feature vector ──────────────────────────────────────────
    features = {
        # Onchain signals (from Alchemy)
        "wallet_age_days": int(onchain_data.get("wallet_age_days", 0)),
        "tx_count_90d": int(onchain_data.get("tx_count_90d", 0)),
        "tx_count_total": int(onchain_data.get("tx_count_total", 0)),
        "last_seen_at_days": int(onchain_data.get("last_seen_at_days", 999)),
        "activity_streak_days": int(onchain_data.get("activity_streak_days", 0)),
        "unique_counterparties_90d": int(onchain_data.get("unique_counterparties_90d", 0)),
        "contract_deploy_count": int(onchain_data.get("contract_deploy_count", 0)),
        "tvl_usd": round(tvl_usd, 2),
        "balance_eth": round(float(onchain_data.get("balance_eth", 0)), 6),
        "balance_usdc": round(float(onchain_data.get("balance_usdc", 0)), 2),
        "erc20_token_count": int(onchain_data.get("erc20_token_count", 0)),
        "defi_protocol_count": defi_protocol_count,
        "defi_protocols_used": onchain_data.get("defi_protocols_used", []),
        "nft_count": int(onchain_data.get("nft_count", 0)),
        # ERC-8004 signals
        "erc8004_reputation": float(erc8004_data.get("reputation_score", 0) or 0),
        "erc8004_job_count": int(
            erc8004_data.get("feedback_count", 0)
            or erc8004_data.get("job_count", 0)
            or olas_data.get("job_count", 0)
            or 0
        ),
        # Identity signals
        "ensip25_verified": bool(ens_data.get("ensip25_verified", False)),
        "cross_chain_count": cross_chain,
        "tee_secured": False,  # From Freysa/ERC-8004 metadata
        "platform_count": platform_count,
        "platforms_list": platforms_list,
        # Virtuals signals (from Virtuals API only)
        "virtuals_mcap_usd": round(float(virtuals_data.get("mcap_usd", 0) or 0), 2),
        "virtuals_holder_count": int(virtuals_data.get("holder_count", 0) or 0),
        # Olas signals
        "olas_job_count": int(olas_data.get("job_count", 0) or 0),
        "olas_service_id": olas_data.get("service_id") or olas_data.get("agent_id"),
        # Fetch.ai signals
        "fetch_active_services": int(fetch_data.get("active_services", 0) or 0),
        "fetch_agent_address": fetch_data.get("agent_address"),
        # HeyElsa enrichment
        "heyelsa_risk_score": float(heyelsa_data.get("risk_score", 0) or 0),
        "heyelsa_defi_activity": float(heyelsa_data.get("defi_activity_score", 0) or 0),
        # Anomaly — defaults, set by run_anomaly node later
        "anomaly_score": 0.0,
        "is_anomaly": False,
        # Risk flags — set by GPT-o3 later
        "risk_flags_count": 0,
    }

    logger.info(
        f"[Features] Aggregated for {wallet_address}: "
        f"wallet_age={features['wallet_age_days']}d, "
        f"tx_90d={features['tx_count_90d']}, "
        f"tx_total={features['tx_count_total']}, "
        f"last_seen={features['last_seen_at_days']}d, "
        f"streak={features['activity_streak_days']}d, "
        f"counterparties_90d={features['unique_counterparties_90d']}, "
        f"balance_eth={features['balance_eth']}, "
        f"balance_usdc={features['balance_usdc']}, "
        f"tvl={features['tvl_usd']}, "
        f"defi_protocols={features['defi_protocol_count']}, "
        f"nfts={features['nft_count']}, "
        f"erc20_tokens={features['erc20_token_count']}, "
        f"contract_deploys={features['contract_deploy_count']}, "
        f"platforms={features['platforms_list']}, "
        f"cross_chain={features['cross_chain_count']}"
    )

    return features


def upsert_features(agent_id: str, features: dict) -> None:
    """Upsert feature vector to agent_features table."""
    try:
        row = {
            "agent_id": agent_id,
            "wallet_age_days": features.get("wallet_age_days", 0),
            "tx_count_90d": features.get("tx_count_90d", 0),
            "tx_count_total": features.get("tx_count_total", 0),
            "tvl_usd": features.get("tvl_usd", 0),
            "balance_eth": features.get("balance_eth", 0),
            "balance_usdc": features.get("balance_usdc", 0),
            "defi_protocol_count": features.get("defi_protocol_count", 0),
            "nft_count": features.get("nft_count", 0),
            "erc8004_reputation": features.get("erc8004_reputation", 0),
            "erc8004_job_count": features.get("erc8004_job_count", 0),
            "ensip25_verified": features.get("ensip25_verified", False),
            "cross_chain_count": features.get("cross_chain_count", 1),
            "tee_secured": features.get("tee_secured", False),
            "platform_count": features.get("platform_count", 1),
            "platforms_list": features.get("platforms_list", []),
            "virtuals_mcap_usd": features.get("virtuals_mcap_usd", 0),
            "virtuals_holder_count": features.get("virtuals_holder_count", 0),
            "olas_job_count": features.get("olas_job_count", 0),
            "olas_service_id": features.get("olas_service_id"),
            "fetch_agent_address": features.get("fetch_agent_address"),
        }
        service_client.table("agent_features").upsert(
            row, on_conflict="agent_id"
        ).execute()
        logger.info(f"[Features] Upserted features for agent_id={agent_id}")
    except Exception as e:
        logger.warning(f"Failed to upsert features: {e}")
