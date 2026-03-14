import json
import logging
import httpx
from web3 import Web3
from app.config import get_settings
from app.crawlers import http_client

logger = logging.getLogger("agentscore.services.heyelsa")

# USDC on Base
USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
USDC_TRANSFER_ABI = [
    {
        "inputs": [
            {"name": "to", "type": "address"},
            {"name": "amount", "type": "uint256"},
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]


async def analyze_wallet(wallet_address: str) -> dict:
    """
    Call HeyElsa x402 API to get DeFi enrichment data for a wallet.
    Uses the x402 payment protocol:
      1. Call endpoint → may return 402 with payment details
      2. Pay USDC on Base
      3. Retry with X-Payment header containing tx proof

    Calls TWO endpoints for comprehensive data:
      - /api/get_portfolio ($0.01) — portfolio positions, TVL, token holdings
      - /api/analyze_wallet ($0.02) — behavioral analysis, risk assessment, DeFi activity

    Falls back gracefully — pipeline continues with partial/empty data.
    """
    settings = get_settings()
    combined_data = {}

    # ── Endpoint 1: get_portfolio (cheaper, portfolio overview) ────────
    portfolio = await _call_x402_endpoint(
        f"{settings.HEYELSA_BASE_URL}/api/get_portfolio",
        {"wallet_address": wallet_address},
    )
    if portfolio:
        combined_data.update({
            "tvl_usd": portfolio.get("tvl_usd") or portfolio.get("total_value_usd") or portfolio.get("totalValue") or 0,
            "token_positions": portfolio.get("tokens") or portfolio.get("positions") or [],
            "defi_positions": portfolio.get("defi") or portfolio.get("defi_positions") or [],
            "portfolio_raw": portfolio,
        })
        logger.info(f"[HeyElsa] Portfolio data retrieved: tvl_usd={combined_data.get('tvl_usd')}")

    # ── Endpoint 2: analyze_wallet (richer behavioral analysis) ────────
    analysis = await _call_x402_endpoint(
        f"{settings.HEYELSA_BASE_URL}/api/analyze_wallet",
        {"wallet_address": wallet_address},
    )
    if analysis:
        combined_data.update({
            "risk_score": analysis.get("risk_score") or analysis.get("riskScore") or 0,
            "defi_activity_score": analysis.get("defi_activity") or analysis.get("activity_score") or 0,
            "protocol_list": analysis.get("protocols") or analysis.get("protocol_list") or [],
            "wallet_label": analysis.get("label") or analysis.get("wallet_type") or "",
            "analysis_raw": analysis,
        })
        # If portfolio didn't give TVL, try from analysis
        if not combined_data.get("tvl_usd"):
            combined_data["tvl_usd"] = analysis.get("tvl_usd") or analysis.get("total_value") or 0
        logger.info(f"[HeyElsa] Analysis data retrieved: risk_score={combined_data.get('risk_score')}")

    if not combined_data:
        logger.warning(f"[HeyElsa] No data retrieved for {wallet_address}")

    return combined_data


async def _call_x402_endpoint(url: str, body: dict) -> dict | None:
    """
    Call a HeyElsa x402 endpoint with automatic payment handling.
    Returns parsed JSON response or None on failure.
    """
    settings = get_settings()

    try:
        async with http_client(timeout=60) as client:
            # Step 1: Initial call
            resp = await client.post(url, json=body)
            logger.info(f"[HeyElsa] {url} returned status {resp.status_code}")

            if resp.status_code == 200:
                return resp.json()

            if resp.status_code == 402:
                # x402 Payment Required
                payment_info = resp.json()
                logger.info(f"[HeyElsa] x402 payment required: {json.dumps(payment_info)[:200]}")

                # Extract payment details — handle various response formats
                payment_address = (
                    payment_info.get("payment_address")
                    or payment_info.get("paymentAddress")
                    or payment_info.get("accepts", [{}])[0].get("address", "")
                    if isinstance(payment_info.get("accepts"), list) and payment_info.get("accepts")
                    else payment_info.get("payment_address", "")
                )
                amount = float(
                    payment_info.get("amount")
                    or payment_info.get("maxAmountRequired")
                    or payment_info.get("price")
                    or 0.01
                )

                if not payment_address:
                    logger.error("[HeyElsa] No payment address in 402 response")
                    return None

                # Step 2: Pay USDC on Base
                tx_hash = _pay_usdc_on_base(to=payment_address, amount_usdc=amount)

                if tx_hash:
                    # Step 3: Retry with payment proof
                    retry_resp = await client.post(
                        url,
                        json=body,
                        headers={
                            "X-Payment": json.dumps({
                                "txHash": tx_hash,
                                "amount": str(amount),
                                "from": settings.HEYELSA_WALLET_ADDRESS,
                                "chainId": 8453,
                            })
                        },
                    )
                    logger.info(f"[HeyElsa] Retry after payment returned {retry_resp.status_code}")
                    if retry_resp.status_code == 200:
                        return retry_resp.json()
                    else:
                        logger.error(f"[HeyElsa] Retry failed: {retry_resp.text[:200]}")
                else:
                    logger.error("[HeyElsa] Payment failed, cannot retry")

            else:
                logger.warning(f"[HeyElsa] Unexpected status {resp.status_code}: {resp.text[:200]}")

    except Exception as e:
        logger.error(f"[HeyElsa] {url} call failed: {e}")

    return None


def _pay_usdc_on_base(to: str, amount_usdc: float) -> str | None:
    """Transfer USDC on Base using web3.py. Returns tx hash or None."""
    try:
        settings = get_settings()
        if not settings.HEYELSA_WALLET_PRIVATE_KEY:
            logger.warning("[HeyElsa] No wallet private key configured for x402 payments")
            return None

        w3 = Web3(Web3.HTTPProvider(settings.ALCHEMY_BASE_RPC))

        usdc = w3.eth.contract(
            address=Web3.to_checksum_address(USDC_BASE), abi=USDC_TRANSFER_ABI
        )
        amount_wei = int(amount_usdc * 1e6)  # USDC has 6 decimals

        from_addr = Web3.to_checksum_address(settings.HEYELSA_WALLET_ADDRESS)
        to_addr = Web3.to_checksum_address(to)

        tx = usdc.functions.transfer(to_addr, amount_wei).build_transaction(
            {
                "from": from_addr,
                "nonce": w3.eth.get_transaction_count(from_addr),
                "gas": 100000,
                "gasPrice": w3.eth.gas_price,
                "chainId": 8453,
            }
        )

        signed = w3.eth.account.sign_transaction(
            tx, settings.HEYELSA_WALLET_PRIVATE_KEY
        )
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
        logger.info(f"[HeyElsa] USDC payment sent: {tx_hash.hex()}, status={receipt.get('status')}")
        return tx_hash.hex()

    except Exception as e:
        logger.warning(f"[HeyElsa] USDC payment failed: {e}")
        return None
