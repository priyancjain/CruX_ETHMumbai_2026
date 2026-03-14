import logging
from datetime import datetime, timezone
from web3 import Web3
from app.config import get_settings

logger = logging.getLogger("agentscore.services.onchain_anchor")

# ABI for AgentScoreAnchor contract (only the functions we call)
ANCHOR_ABI = [
    {
        "inputs": [
            {"name": "wallet", "type": "address"},
            {"name": "score", "type": "uint256"},
            {"name": "tier", "type": "string"},
            {"name": "scoredAt", "type": "uint256"},
        ],
        "name": "anchorScore",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"name": "wallet", "type": "address"},
            {"name": "score", "type": "uint256"},
            {"name": "scoredAt", "type": "uint256"},
        ],
        "name": "verifyScore",
        "outputs": [{"name": "valid", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "totalAnchored",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]


async def anchor_score_onchain(
    wallet_address: str,
    score: int,
    tier: str,
    scored_at: datetime | None = None,
) -> str | None:
    """
    Anchor a credit score on Base Sepolia via AgentScoreAnchor contract.

    Returns the transaction hash on success, or None if anchoring is
    unavailable (no contract address, no private key, insufficient gas).
    """
    settings = get_settings()

    contract_address = settings.SCORE_ANCHOR_ADDRESS
    private_key = settings.SCORE_ANCHOR_PRIVATE_KEY

    if not contract_address or not private_key:
        logger.info("[Anchor] Skipped — SCORE_ANCHOR_ADDRESS or SCORE_ANCHOR_PRIVATE_KEY not configured")
        return None

    try:
        w3 = Web3(Web3.HTTPProvider(settings.BASE_SEPOLIA_RPC))

        if not w3.is_connected():
            logger.error("[Anchor] Cannot connect to Base Sepolia RPC")
            return None

        contract = w3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=ANCHOR_ABI,
        )

        account = w3.eth.account.from_key(private_key)
        checksum_wallet = Web3.to_checksum_address(wallet_address)

        # Convert scored_at to unix timestamp
        if scored_at is None:
            scored_at = datetime.now(timezone.utc)
        if isinstance(scored_at, datetime):
            scored_at_unix = int(scored_at.timestamp())
        else:
            scored_at_unix = int(scored_at)

        # Check gas balance
        balance = w3.eth.get_balance(account.address)
        if balance < w3.to_wei(0.0001, "ether"):
            logger.warning(
                f"[Anchor] Insufficient gas on {account.address}: "
                f"{w3.from_wei(balance, 'ether')} ETH. Need ~0.0001 ETH on Base Sepolia."
            )
            return None

        # Build transaction
        nonce = w3.eth.get_transaction_count(account.address)

        tx = contract.functions.anchorScore(
            checksum_wallet,
            score,
            tier,
            scored_at_unix,
        ).build_transaction({
            "from": account.address,
            "nonce": nonce,
            "gas": 150000,
            "maxFeePerGas": w3.to_wei(0.1, "gwei"),
            "maxPriorityFeePerGas": w3.to_wei(0.05, "gwei"),
            "chainId": settings.BASE_SEPOLIA_CHAIN_ID,
        })

        # Sign and send
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_hex = tx_hash.hex()

        logger.info(f"[Anchor] TX sent: {tx_hex}")

        # Wait for receipt (up to 30 seconds)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)

        if receipt["status"] == 1:
            logger.info(
                f"[Anchor] Score anchored on Base Sepolia!\n"
                f"  TX Hash : {tx_hex}\n"
                f"  Block   : {receipt['blockNumber']}\n"
                f"  Gas Used: {receipt['gasUsed']}\n"
                f"  Wallet  : {wallet_address}\n"
                f"  Score   : {score} (Tier {tier})"
            )
            return tx_hex
        else:
            logger.error(f"[Anchor] TX reverted: {tx_hex}")
            return None

    except Exception as e:
        logger.error(f"[Anchor] Failed to anchor score: {e}")
        return None
