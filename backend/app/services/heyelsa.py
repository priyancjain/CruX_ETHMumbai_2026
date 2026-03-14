import logging
import traceback
from eth_account import Account
from x402 import x402Client
from x402.http.clients import x402HttpxClient
from x402.mechanisms.evm import EthAccountSigner
from x402.mechanisms.evm.exact.register import register_exact_evm_client
from app.config import get_settings

logger = logging.getLogger("agentscore.services.heyelsa")


def _build_x402_client() -> tuple[x402Client, Account]:
    """Build x402 client with EVM signer from settings."""
    settings = get_settings()
    account = Account.from_key(settings.HEYELSA_WALLET_PRIVATE_KEY)
    client = x402Client()
    register_exact_evm_client(client, EthAccountSigner(account))
    return client, account


async def analyze_wallet(wallet_address: str) -> dict:
    """
    Call HeyElsa x402 API to get DeFi enrichment data for a wallet.

    x402 protocol: call → 402 with payment requirements → sign EIP-3009
    authorization (off-chain, gasless) → retry with signed proof → server
    settles the USDC transfer and returns data.
    """
    settings = get_settings()
    combined_data = {"heyelsa_available": False}

    # Skip if wallet not configured for payments
    if not settings.HEYELSA_WALLET_PRIVATE_KEY or not settings.HEYELSA_WALLET_ADDRESS:
        logger.info("[HeyElsa] Skipped — no payment wallet configured. TVL will use on-chain estimate.")
        return combined_data

    x402_client, account = _build_x402_client()

    # ── Endpoint 1: get_portfolio ────────────────────────────────
    portfolio = await _call_x402_endpoint(
        x402_client,
        f"{settings.HEYELSA_BASE_URL}/api/get_portfolio",
        {"wallet_address": wallet_address},
    )
    if portfolio:
        combined_data.update({
            "heyelsa_available": True,
            "tvl_usd": portfolio.get("tvl_usd") or portfolio.get("total_value_usd") or portfolio.get("totalValue") or 0,
            "token_positions": portfolio.get("tokens") or portfolio.get("positions") or [],
            "defi_positions": portfolio.get("defi") or portfolio.get("defi_positions") or [],
        })
        logger.info(f"[HeyElsa] Portfolio retrieved: tvl_usd={combined_data.get('tvl_usd')}")

    # ── Endpoint 2: analyze_wallet ($0.02) ───────────────────────
    analysis = await _call_x402_endpoint(
        x402_client,
        f"{settings.HEYELSA_BASE_URL}/api/analyze_wallet",
        {"wallet_address": wallet_address},
    )
    if analysis:
        # Extract from nested "analysis" key if present
        analysis_inner = analysis.get("analysis", analysis)
        portfolio_metrics = analysis_inner.get("portfolio_metrics", {})
        activity_metrics = analysis_inner.get("activity_metrics", {})
        risk_metrics = analysis_inner.get("risk_metrics", {})

        combined_data.update({
            "heyelsa_available": True,
            "risk_score": risk_metrics.get("concentration_risk") or analysis.get("risk_score") or analysis.get("riskScore") or 0,
            "defi_activity_score": activity_metrics.get("total_transactions") or analysis.get("defi_activity") or 0,
            "diversification_score": risk_metrics.get("diversification_score") or 0,
            "protocol_list": activity_metrics.get("active_protocols") or analysis.get("protocols") or [],
            "wallet_label": analysis.get("label") or analysis.get("wallet_type") or "",
            "chain_count": portfolio_metrics.get("chain_count") or 0,
            "token_count_heyelsa": portfolio_metrics.get("token_count") or 0,
        })
        if not combined_data.get("tvl_usd"):
            combined_data["tvl_usd"] = portfolio_metrics.get("total_value_usd") or analysis.get("tvl_usd") or 0
        logger.info(f"[HeyElsa] Analysis retrieved: risk={combined_data.get('risk_score')}, diversification={combined_data.get('diversification_score')}")

    # ── Endpoint 3: get_transaction_history ($0.003) ───────────
    tx_history = await _call_x402_endpoint(
        x402_client,
        f"{settings.HEYELSA_BASE_URL}/api/get_transaction_history",
        {"wallet_address": wallet_address, "limit": 20},
    )
    if tx_history:
        transactions = tx_history.get("transactions") or tx_history.get("history") or []
        combined_data["transaction_history"] = transactions
        combined_data["heyelsa_available"] = True
        logger.info(f"[HeyElsa] Transaction history: {len(transactions)} txs")

    # ── Endpoint 4: get_pnl_report ($0.015) ────────────────────
    pnl = await _call_x402_endpoint(
        x402_client,
        f"{settings.HEYELSA_BASE_URL}/api/get_pnl_report",
        {"wallet_address": wallet_address, "time_period": "90_days"},
    )
    if pnl:
        pnl_data = pnl.get("pnl") or pnl.get("report") or pnl
        combined_data.update({
            "heyelsa_available": True,
            "pnl_report": pnl_data,
            "total_pnl_usd": float(pnl_data.get("total_pnl") or pnl_data.get("total_pnl_usd") or 0),
            "realized_pnl_usd": float(pnl_data.get("realized_pnl") or pnl_data.get("realized_pnl_usd") or 0),
            "unrealized_pnl_usd": float(pnl_data.get("unrealized_pnl") or pnl_data.get("unrealized_pnl_usd") or 0),
            "win_rate": float(pnl_data.get("win_rate") or 0),
            "total_trades": int(pnl_data.get("total_trades") or 0),
            "profitable_trades": int(pnl_data.get("profitable_trades") or 0),
            "avg_trade_size_usd": float(pnl_data.get("avg_trade_size") or pnl_data.get("avg_trade_size_usd") or 0),
            "largest_win_usd": float(pnl_data.get("largest_win") or pnl_data.get("largest_win_usd") or 0),
            "largest_loss_usd": float(pnl_data.get("largest_loss") or pnl_data.get("largest_loss_usd") or 0),
            "tokens_traded": pnl_data.get("tokens_traded") or [],
        })
        logger.info(f"[HeyElsa] PnL report: total_pnl=${combined_data.get('total_pnl_usd')}, win_rate={combined_data.get('win_rate')}")

    # ── Endpoint 5 (conditional): get_stake_balances ($0.005) ──
    # Only call if portfolio shows staking-related positions
    has_staking = False
    for pos in combined_data.get("defi_positions", []):
        if isinstance(pos, dict) and "stak" in str(pos).lower():
            has_staking = True
            break
    for pos in combined_data.get("token_positions", []):
        if isinstance(pos, dict) and "stak" in str(pos).lower():
            has_staking = True
            break

    if has_staking:
        stakes = await _call_x402_endpoint(
            x402_client,
            f"{settings.HEYELSA_BASE_URL}/api/get_stake_balances",
            {"wallet_address": wallet_address},
        )
        if stakes:
            stake_list = stakes.get("stakes") or stakes.get("balances") or []
            staking_total = sum(float(s.get("balance_usd") or s.get("value_usd") or 0) for s in stake_list)
            combined_data["staking_positions"] = stake_list
            combined_data["staking_balance_usd"] = staking_total
            combined_data["heyelsa_available"] = True
            logger.info(f"[HeyElsa] Staking balances: ${staking_total:.2f}")

    if not combined_data.get("heyelsa_available"):
        logger.info("[HeyElsa] x402 payment required but not completed. TVL will use on-chain estimate.")

    return combined_data


async def _call_x402_endpoint(x402_client: x402Client, url: str, body: dict) -> dict | None:
    """
    Call a HeyElsa x402 endpoint using the x402 SDK.
    The SDK handles: 402 detection → EIP-3009 signing → base64 header → retry.
    Returns parsed JSON response or None on failure.
    """
    try:
        async with x402HttpxClient(x402_client, timeout=60) as client:
            resp = await client.post(url, json=body)
            await resp.aread()
            logger.info(f"[HeyElsa] {url} → HTTP {resp.status_code}")

            if resp.is_success:
                return resp.json()
            else:
                logger.warning(f"[HeyElsa] {url} failed: HTTP {resp.status_code} — {resp.text[:300]}")

    except Exception as e:
        logger.error(f"[HeyElsa] {url} failed: {e}")
        logger.error(f"[HeyElsa] Traceback:\n{traceback.format_exc()}")

    return None
