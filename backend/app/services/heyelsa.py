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


def _safe_float(value, default: float = 0.0) -> float:
    """Safely convert any value to float."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        mapping = {"high": 80.0, "medium": 50.0, "low": 20.0, "none": 0.0, "very high": 95.0, "very low": 10.0}
        lower = value.strip().lower()
        if lower in mapping:
            return mapping[lower]
        try:
            return float(lower)
        except ValueError:
            return default
    return default


def _safe_int(value, default: int = 0) -> int:
    """Safely convert any value to int."""
    try:
        return int(_safe_float(value, float(default)))
    except (ValueError, TypeError):
        return default


async def analyze_wallet(wallet_address: str) -> dict:
    """
    Call HeyElsa x402 API to get DeFi enrichment data for a wallet.

    x402 protocol: call → 402 with payment requirements → sign EIP-3009
    authorization (off-chain, gasless) → retry with signed proof → server
    settles the USDC transfer and returns data.

    Each endpoint is wrapped in try/except so one failure doesn't lose
    data from other endpoints.
    """
    settings = get_settings()
    combined_data = {"heyelsa_available": False}

    # Skip if HeyElsa is disabled via flag
    if not settings.HEYELSA_ENABLED:
        logger.info("[HeyElsa] Skipped — HEYELSA_ENABLED=false in .env")
        return combined_data

    # Skip if wallet not configured for payments
    if not settings.HEYELSA_WALLET_PRIVATE_KEY or not settings.HEYELSA_WALLET_ADDRESS:
        logger.info("[HeyElsa] Skipped — no payment wallet configured. TVL will use on-chain estimate.")
        return combined_data

    x402_client, account = _build_x402_client()

    # ── Endpoint 1: analyze_wallet ($0.02) ─────────────────────
    try:
        analysis = await _call_x402_endpoint(
            x402_client,
            f"{settings.HEYELSA_BASE_URL}/api/analyze_wallet",
            {"wallet_address": wallet_address},
        )
        if analysis and isinstance(analysis, dict):
            # Log raw response keys for debugging
            logger.info(f"[HeyElsa] analyze_wallet response keys: {list(analysis.keys())}")

            # Extract from nested "analysis" key if present
            analysis_inner = analysis.get("analysis", analysis)
            if not isinstance(analysis_inner, dict):
                analysis_inner = analysis

            portfolio_metrics = analysis_inner.get("portfolio_metrics", {}) if isinstance(analysis_inner, dict) else {}
            activity_metrics = analysis_inner.get("activity_metrics", {}) if isinstance(analysis_inner, dict) else {}
            risk_metrics = analysis_inner.get("risk_metrics", {}) if isinstance(analysis_inner, dict) else {}

            if not isinstance(portfolio_metrics, dict):
                portfolio_metrics = {}
            if not isinstance(activity_metrics, dict):
                activity_metrics = {}
            if not isinstance(risk_metrics, dict):
                risk_metrics = {}

            combined_data.update({
                "heyelsa_available": True,
                "risk_score": risk_metrics.get("concentration_risk") or analysis.get("risk_score") or analysis.get("riskScore") or 0,
                "defi_activity_score": activity_metrics.get("total_transactions") or analysis.get("defi_activity") or 0,
                "diversification_score": risk_metrics.get("diversification_score") or 0,
                "protocol_list": activity_metrics.get("active_protocols") if isinstance(activity_metrics.get("active_protocols"), list) else analysis.get("protocols") or [],
                "wallet_label": analysis.get("label") or analysis.get("wallet_type") or "",
                "chain_count": portfolio_metrics.get("chain_count") or 0,
                "token_count_heyelsa": portfolio_metrics.get("token_count") or 0,
            })
            combined_data["tvl_usd"] = portfolio_metrics.get("total_value_usd") or analysis.get("tvl_usd") or 0
            logger.info(f"[HeyElsa] Analysis retrieved: risk={combined_data.get('risk_score')}, diversification={combined_data.get('diversification_score')}, tvl={combined_data.get('tvl_usd')}")
        elif analysis is not None:
            logger.warning(f"[HeyElsa] analyze_wallet returned non-dict: type={type(analysis).__name__}, value={str(analysis)[:200]}")
    except Exception as e:
        logger.error(f"[HeyElsa] analyze_wallet processing crashed: {e}")
        logger.error(traceback.format_exc())

    # ── Endpoint 2: get_transaction_history ($0.003) ───────────
    # API returns: {"success":true, "transactions": {"transactions": [...]}}
    #              (double-nested — "transactions" key contains a dict with inner "transactions" list)
    try:
        tx_history = await _call_x402_endpoint(
            x402_client,
            f"{settings.HEYELSA_BASE_URL}/api/get_transaction_history",
            {"wallet_address": wallet_address, "limit": 20},
        )
        if tx_history and isinstance(tx_history, dict):
            logger.info(f"[HeyElsa] tx_history response keys: {list(tx_history.keys())}")
            raw_tx = tx_history.get("transactions") or tx_history.get("history") or []

            # Handle double-nesting: {"transactions": {"transactions": [...]}}
            if isinstance(raw_tx, dict):
                logger.info(f"[HeyElsa] transactions is a dict with keys: {list(raw_tx.keys())} — extracting inner list")
                transactions = raw_tx.get("transactions") or raw_tx.get("history") or list(raw_tx.values())[0] if raw_tx else []
                if not isinstance(transactions, list):
                    transactions = []
            elif isinstance(raw_tx, list):
                transactions = raw_tx
            else:
                logger.warning(f"[HeyElsa] transactions is {type(raw_tx).__name__}, not list/dict")
                transactions = []

            if transactions:
                sample = transactions[0]
                logger.info(f"[HeyElsa] TX sample type={type(sample).__name__}, value={str(sample)[:200]}")
            combined_data["transaction_history"] = transactions
            combined_data["heyelsa_available"] = True
            logger.info(f"[HeyElsa] Transaction history: {len(transactions)} txs")
    except Exception as e:
        logger.error(f"[HeyElsa] get_transaction_history processing crashed: {e}")
        logger.error(traceback.format_exc())

    # ── Endpoint 3: get_pnl_report ($0.015) ────────────────────
    # API returns: {"success":true, "pnl_report": {"overall_metrics": {...}, "top_gainers":[], ...}}
    # overall_metrics keys: total_realized_pnl_usd, total_fees_paid_usd, net_pnl_usd,
    #                       profitable_tokens, loss_tokens, win_rate_percent
    try:
        pnl = await _call_x402_endpoint(
            x402_client,
            f"{settings.HEYELSA_BASE_URL}/api/get_pnl_report",
            {"wallet_address": wallet_address, "time_period": "90_days"},
        )
        if pnl and isinstance(pnl, dict):
            logger.info(f"[HeyElsa] pnl response keys: {list(pnl.keys())}")

            # Extract pnl_report (actual key from API)
            pnl_data = pnl.get("pnl_report") or pnl.get("pnl") or pnl.get("report") or pnl
            if not isinstance(pnl_data, dict):
                pnl_data = pnl

            # Extract overall_metrics (nested inside pnl_report)
            metrics = pnl_data.get("overall_metrics", {}) if isinstance(pnl_data, dict) else {}
            if not isinstance(metrics, dict):
                metrics = {}
            logger.info(f"[HeyElsa] pnl overall_metrics: {metrics}")

            # Map actual API field names to our internal names
            total_pnl = _safe_float(
                metrics.get("net_pnl_usd")
                or metrics.get("total_pnl")
                or pnl_data.get("total_pnl_usd")
                or pnl_data.get("net_pnl_usd")
            )
            realized_pnl = _safe_float(
                metrics.get("total_realized_pnl_usd")
                or metrics.get("realized_pnl")
                or pnl_data.get("realized_pnl_usd")
            )
            win_rate_raw = metrics.get("win_rate_percent") or metrics.get("win_rate") or pnl_data.get("win_rate")
            # Handle "NaN" string from API
            win_rate = 0.0
            if win_rate_raw is not None and str(win_rate_raw).lower() != "nan":
                win_rate = _safe_float(win_rate_raw) / 100.0 if _safe_float(win_rate_raw) > 1 else _safe_float(win_rate_raw)

            profitable_count = _safe_int(metrics.get("profitable_tokens") or metrics.get("profitable_trades") or pnl_data.get("profitable_trades"))
            loss_count = _safe_int(metrics.get("loss_tokens") or pnl_data.get("loss_tokens"))
            total_trades = profitable_count + loss_count

            # Get position data for tokens_traded
            all_positions = pnl_data.get("all_positions", [])
            top_gainers = pnl_data.get("top_gainers", [])
            top_losers = pnl_data.get("top_losers", [])
            tokens_traded = []
            for pos_list in [all_positions, top_gainers, top_losers]:
                if isinstance(pos_list, list):
                    for pos in pos_list:
                        if isinstance(pos, dict):
                            symbol = pos.get("symbol") or pos.get("token")
                            if symbol and symbol not in tokens_traded:
                                tokens_traded.append(symbol)

            combined_data.update({
                "heyelsa_available": True,
                "pnl_report": pnl_data,
                "total_pnl_usd": total_pnl,
                "realized_pnl_usd": realized_pnl,
                "unrealized_pnl_usd": _safe_float(metrics.get("unrealized_pnl") or pnl_data.get("unrealized_pnl_usd")),
                "win_rate": win_rate,
                "total_trades": total_trades,
                "profitable_trades": profitable_count,
                "avg_trade_size_usd": _safe_float(metrics.get("avg_trade_size") or pnl_data.get("avg_trade_size_usd")),
                "largest_win_usd": _safe_float(metrics.get("largest_win") or pnl_data.get("largest_win_usd")),
                "largest_loss_usd": _safe_float(metrics.get("largest_loss") or pnl_data.get("largest_loss_usd")),
                "total_fees_usd": _safe_float(metrics.get("total_fees_paid_usd")),
                "tokens_traded": tokens_traded,
            })
            logger.info(f"[HeyElsa] PnL report: total_pnl=${total_pnl}, realized=${realized_pnl}, win_rate={win_rate}, trades={total_trades}, tokens={tokens_traded}")
        elif pnl is not None:
            logger.warning(f"[HeyElsa] pnl returned non-dict: type={type(pnl).__name__}, value={str(pnl)[:200]}")
    except Exception as e:
        logger.error(f"[HeyElsa] get_pnl_report processing crashed: {e}")
        logger.error(traceback.format_exc())

    # ── Endpoint 4: get_stake_balances ($0.005) ─────────────────
    # API returns: {"success":true, "stake_balances": [...]}
    try:
        stakes = await _call_x402_endpoint(
            x402_client,
            f"{settings.HEYELSA_BASE_URL}/api/get_stake_balances",
            {"wallet_address": wallet_address},
        )
        if stakes and isinstance(stakes, dict):
            logger.info(f"[HeyElsa] stakes response keys: {list(stakes.keys())}")
            stake_list = stakes.get("stake_balances") or stakes.get("stakes") or stakes.get("balances") or []
            if isinstance(stake_list, list) and stake_list:
                staking_total = sum(_safe_float(s.get("balance_usd") or s.get("value_usd")) for s in stake_list if isinstance(s, dict))
                combined_data["staking_positions"] = stake_list
                combined_data["staking_balance_usd"] = staking_total
                combined_data["heyelsa_available"] = True
                logger.info(f"[HeyElsa] Staking balances: ${staking_total:.2f}, {len(stake_list)} positions")
            else:
                logger.info(f"[HeyElsa] No staking positions found")
        elif stakes is not None:
            logger.warning(f"[HeyElsa] stakes returned non-dict: type={type(stakes).__name__}, value={str(stakes)[:200]}")
    except Exception as e:
        logger.error(f"[HeyElsa] get_stake_balances processing crashed: {e}")
        logger.error(traceback.format_exc())

    if not combined_data.get("heyelsa_available"):
        logger.info("[HeyElsa] x402 payment required but not completed. TVL will use on-chain estimate.")
    else:
        logger.info(f"[HeyElsa] Final combined_data keys: {[k for k in combined_data.keys() if combined_data[k]]}")

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
                data = resp.json()
                logger.info(f"[HeyElsa] {url} response type: {type(data).__name__}")
                return data
            else:
                logger.warning(f"[HeyElsa] {url} failed: HTTP {resp.status_code} — {resp.text[:300]}")

    except Exception as e:
        logger.error(f"[HeyElsa] {url} failed: {e}")
        logger.error(f"[HeyElsa] Traceback:\n{traceback.format_exc()}")

    return None
