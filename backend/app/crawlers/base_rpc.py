import asyncio
import logging
import httpx
from datetime import datetime, timedelta
from app.config import get_settings
from app.crawlers import http_client

logger = logging.getLogger("agentscore.crawlers.base_rpc")

# Known DeFi protocols on Base
DEFI_PROTOCOLS = {
    "0x2626664c2603336e57b271c5c0b26f421741e481": "Uniswap V3",
    "0x4752ba5dbc23f44d87826276bf6fd6b1c372ad24": "Uniswap V2",
    "0x3154cf16ccdb4c6d922629664174b904d80f2c35": "Aerodrome",
    "0x18cd499e3d7ed42feba981ac9236a278e4cdc2ee": "Moonwell",
    "0xd9aa57f44857cd3e6b0406173cf0aba2b9525f94": "Compound",
    "0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2": "Aave V3",
    "0x6cdebe940bc0f26850285caca097c11c33103e47": "Curve",
}

USDC_BASE = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"


# ── RPC helper ────────────────────────────────────────────────────────────────
async def _rpc_post(client: httpx.AsyncClient, rpc_url: str, method: str, params: list):
    """JSON-RPC call with error handling."""
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    r = await client.post(rpc_url, json=payload)
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise RuntimeError(f"RPC error [{method}]: {data['error']}")
    return data["result"]


# ── Alchemy paginated transfers ───────────────────────────────────────────────
async def _get_all_transfers(client: httpx.AsyncClient, rpc_url: str, wallet: str) -> list:
    """Fetch ALL outgoing transfers with pageKey pagination."""
    all_transfers = []
    page_key = None

    # Base does NOT support "internal" category
    is_eth = "eth-mainnet" in rpc_url
    categories = ["external", "internal", "erc20", "erc721", "erc1155"] if is_eth \
        else ["external", "erc20", "erc721", "erc1155"]

    while True:
        params: dict = {
            "fromBlock": "0x0",
            "toBlock": "latest",
            "fromAddress": wallet,
            "withMetadata": True,
            "excludeZeroValue": False,
            "category": categories,
            "maxCount": "0x3e8",
        }
        if page_key:
            params["pageKey"] = page_key

        result = await _rpc_post(client, rpc_url, "alchemy_getAssetTransfers", [params])
        transfers = result.get("transfers", [])
        all_transfers.extend(transfers)
        page_key = result.get("pageKey")
        if not page_key:
            break

    return all_transfers


# ── Balance helpers ───────────────────────────────────────────────────────────
async def _get_eth_balance(client: httpx.AsyncClient, rpc_url: str, wallet: str) -> float:
    res = await _rpc_post(client, rpc_url, "eth_getBalance", [wallet, "latest"])
    return int(res, 16) / 1e18


async def _get_token_balances(client: httpx.AsyncClient, rpc_url: str, wallet: str) -> list:
    res = await _rpc_post(client, rpc_url, "alchemy_getTokenBalances", [wallet, "erc20"])
    return res.get("tokenBalances", [])


async def _get_nft_count(wallet: str) -> int:
    settings = get_settings()
    base_key = settings.ALCHEMY_BASE_KEY 
    nft_url = f"https://base-mainnet.g.alchemy.com/nft/v3/{base_key}/getNFTsForOwner"
    try:
        async with http_client(timeout=20) as c:
            r = await c.get(nft_url, params={"owner": wallet, "withMetadata": "false", "pageSize": "1"})
            r.raise_for_status()
            return r.json().get("totalCount", 0)
    except Exception as e:
        logger.warning(f"[Alchemy] NFT count failed: {e}")
        return 0


# ── Feature computation from transfers ────────────────────────────────────────
def _compute_transfer_features(transfers: list) -> dict:
    """Compute features from a list of Alchemy transfers."""
    if not transfers:
        return {
            "wallet_age_days": 0,
            "tx_count_total": 0,
            "tx_count_90d": 0,
            "last_seen_at_days": 999,
            "unique_counterparties_90d": 0,
            "defi_protocol_count": 0,
            "defi_protocols_used": [],
            "contract_deploy_count": 0,
            "activity_streak_days": 0,
        }

    now = datetime.utcnow()
    cutoff = now - timedelta(days=90)

    # Parse timestamps
    for t in transfers:
        try:
            t["_ts"] = datetime.fromisoformat(
                t["metadata"]["blockTimestamp"].rstrip("Z")
            )
        except Exception:
            t["_ts"] = now

    timestamps = [t["_ts"] for t in transfers]
    recent_txns = [t for t in transfers if t["_ts"] >= cutoff]

    # Unique counterparties in 90d
    counterparties = {
        t["to"].lower() for t in recent_txns if t.get("to")
    }

    # DeFi protocol detection
    defi_hit = {
        DEFI_PROTOCOLS[t["to"].lower()]
        for t in transfers
        if t.get("to") and t["to"].lower() in DEFI_PROTOCOLS
    }

    # Contract deployments (tx with no "to")
    deploys = [t for t in transfers if not t.get("to")]

    # Activity streak (max consecutive days)
    active_days = sorted({ts.date() for ts in timestamps})
    streak = max_streak = 1
    for i in range(1, len(active_days)):
        if (active_days[i] - active_days[i - 1]).days == 1:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 1

    return {
        "wallet_age_days": (now - min(timestamps)).days,
        "tx_count_total": len(transfers),
        "tx_count_90d": len(recent_txns),
        "last_seen_at_days": (now - max(timestamps)).days,
        "unique_counterparties_90d": len(counterparties),
        "defi_protocol_count": len(defi_hit),
        "defi_protocols_used": list(defi_hit),
        "contract_deploy_count": len(deploys),
        "activity_streak_days": max_streak if len(active_days) > 1 else 0,
    }


def _compute_balance_features(token_balances: list, eth_bal: float) -> dict:
    """Compute balance-related features."""
    usdc_raw = next(
        (t["tokenBalance"] for t in token_balances
         if t["contractAddress"].lower() == USDC_BASE),
        "0x0",
    )
    return {
        "balance_eth": round(eth_bal, 6),
        "balance_usdc": int(usdc_raw, 16) / 1e6,
        "erc20_token_count": len(token_balances),
    }


# ── Main Extractor ────────────────────────────────────────────────────────────
async def get_wallet_data(wallet_address: str) -> dict:
    """
    Collect comprehensive onchain data for a wallet from Base and ETH mainnet.
    Uses separate Alchemy keys for Base and ETH, with full pagination.
    """
    settings = get_settings()
    wallet = wallet_address.lower()

    if not wallet.startswith("0x"):
        logger.info(f"[Alchemy] Skipped — {wallet} is not an EVM address")
        return {
            "wallet_age_days": 0, "tx_count_total": 0, "tx_count_90d": 0,
            "last_seen_at_days": 999, "activity_streak_days": 0,
            "defi_protocol_count": 0, "defi_protocols_used": [],
            "balance_eth": 0.0, "balance_usdc": 0.0, "erc20_token_count": 0,
            "nft_count": 0, "cross_chain_count": 0,
            "unique_counterparties_90d": 0, "contract_deploy_count": 0,
            "raw_transfers": [],
        }

    base_rpc = settings.ALCHEMY_BASE_RPC
    eth_rpc = settings.ALCHEMY_ETH_RPC

    logger.info(f"[Alchemy] Extracting features for {wallet}")

    async with http_client(timeout=30) as client:
        # Run all data fetches in parallel
        (
            base_transfers,
            eth_transfers,
            eth_balance,
            token_balances,
            nft_count,
        ) = await asyncio.gather(
            _get_all_transfers(client, base_rpc, wallet),
            _get_all_transfers(client, eth_rpc, wallet),
            _get_eth_balance(client, base_rpc, wallet),
            _get_token_balances(client, base_rpc, wallet),
            _get_nft_count(wallet),
            return_exceptions=True,
        )

        # Handle any exceptions from gather
        if isinstance(base_transfers, Exception):
            logger.error(f"[Alchemy] Base transfers failed: {base_transfers}")
            base_transfers = []
        if isinstance(eth_transfers, Exception):
            logger.error(f"[Alchemy] ETH transfers failed: {eth_transfers}")
            eth_transfers = []
        if isinstance(eth_balance, Exception):
            logger.error(f"[Alchemy] ETH balance failed: {eth_balance}")
            eth_balance = 0.0
        if isinstance(token_balances, Exception):
            logger.error(f"[Alchemy] Token balances failed: {token_balances}")
            token_balances = []
        if isinstance(nft_count, Exception):
            logger.error(f"[Alchemy] NFT count failed: {nft_count}")
            nft_count = 0

    # Compute features
    eth_features = _compute_transfer_features(eth_transfers)
    base_features = _compute_transfer_features(base_transfers)
    bal_features = _compute_balance_features(token_balances, eth_balance)

    cross_chain_count = sum([
        1 if base_transfers else 0,
        1 if eth_transfers else 0,
    ])

    features = {
        # Time / Activity — wallet_age from ETH (oldest history)
        "wallet_age_days": max(eth_features["wallet_age_days"], base_features["wallet_age_days"]),
        "last_seen_at_days": min(eth_features["last_seen_at_days"], base_features["last_seen_at_days"]),
        "activity_streak_days": base_features["activity_streak_days"],

        # Transaction volume
        "tx_count_total": eth_features["tx_count_total"] + base_features["tx_count_total"],
        "tx_count_90d": base_features["tx_count_90d"],

        # DeFi
        "defi_protocol_count": base_features["defi_protocol_count"],
        "defi_protocols_used": base_features["defi_protocols_used"],

        # Balances
        "balance_eth": bal_features["balance_eth"],
        "balance_usdc": bal_features["balance_usdc"],
        "erc20_token_count": bal_features["erc20_token_count"],

        # Assets
        "nft_count": nft_count,

        # Network
        "cross_chain_count": cross_chain_count,
        "unique_counterparties_90d": base_features["unique_counterparties_90d"],

        # Builder signal
        "contract_deploy_count": base_features["contract_deploy_count"],

        # Raw transfers for transaction storage + LLM analysis (last 100)
        "raw_transfers": [
            {
                "hash": t.get("hash", ""),
                "from": t.get("from", ""),
                "to": t.get("to", ""),
                "value": t.get("value"),
                "asset": t.get("asset", ""),
                "category": t.get("category", ""),
                "blockNum": t.get("blockNum", ""),
                "timestamp": t.get("metadata", {}).get("blockTimestamp", ""),
            }
            for t in (base_transfers[-100:] if isinstance(base_transfers, list) else [])
        ],
    }

    # Log summary
    logger.info(
        f"[Alchemy] Features extracted:\n"
        f"  wallet_age_days       = {features['wallet_age_days']}\n"
        f"  tx_count_total        = {features['tx_count_total']}\n"
        f"  tx_count_90d          = {features['tx_count_90d']}\n"
        f"  last_seen_at_days     = {features['last_seen_at_days']}\n"
        f"  activity_streak_days  = {features['activity_streak_days']}\n"
        f"  balance_eth           = {features['balance_eth']}\n"
        f"  balance_usdc          = {features['balance_usdc']}\n"
        f"  erc20_token_count     = {features['erc20_token_count']}\n"
        f"  nft_count             = {features['nft_count']}\n"
        f"  defi_protocol_count   = {features['defi_protocol_count']}\n"
        f"  defi_protocols_used   = {features['defi_protocols_used']}\n"
        f"  cross_chain_count     = {features['cross_chain_count']}\n"
        f"  unique_cps_90d        = {features['unique_counterparties_90d']}\n"
        f"  contract_deploys      = {features['contract_deploy_count']}"
    )

    return features
