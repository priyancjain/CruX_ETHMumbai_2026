import logging
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

    # ── Endpoint 2: analyze_wallet ───────────────────────────────
    analysis = await _call_x402_endpoint(
        x402_client,
        f"{settings.HEYELSA_BASE_URL}/api/analyze_wallet",
        {"wallet_address": wallet_address},
    )
    if analysis:
        combined_data.update({
            "heyelsa_available": True,
            "risk_score": analysis.get("risk_score") or analysis.get("riskScore") or 0,
            "defi_activity_score": analysis.get("defi_activity") or analysis.get("activity_score") or 0,
            "protocol_list": analysis.get("protocols") or analysis.get("protocol_list") or [],
            "wallet_label": analysis.get("label") or analysis.get("wallet_type") or "",
        })
        if not combined_data.get("tvl_usd"):
            combined_data["tvl_usd"] = analysis.get("tvl_usd") or analysis.get("total_value") or 0
        logger.info(f"[HeyElsa] Analysis retrieved: risk_score={combined_data.get('risk_score')}")

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
        async with x402HttpxClient(x402_client) as client:
            resp = await client.post(url, json=body)
            await resp.aread()
            logger.info(f"[HeyElsa] {url} → HTTP {resp.status_code}")

            if resp.is_success:
                return resp.json()
            else:
                logger.warning(f"[HeyElsa] {url} failed: HTTP {resp.status_code} — {resp.text[:300]}")

    except Exception as e:
        logger.error(f"[HeyElsa] {url} failed: {e}")

    return None
