import logging
from fastapi import APIRouter, HTTPException
from app.services.supabase import anon_client
from app.crawlers.base_rpc import _get_all_transfers, _rpc_post
from app.crawlers import http_client
from app.config import get_settings

logger = logging.getLogger("agentscore.api.enrichment")
router = APIRouter()


async def _fetch_alchemy_transfers(wallet: str, page: int, page_size: int) -> dict:
    """Fetch transactions directly from Alchemy when DB has none."""
    settings = get_settings()
    wallet_lower = wallet.lower()

    try:
        async with http_client(timeout=30) as client:
            result = await _rpc_post(
                client,
                settings.ALCHEMY_BASE_RPC,
                "alchemy_getAssetTransfers",
                [{
                    "fromBlock": "0x0",
                    "toBlock": "latest",
                    "fromAddress": wallet_lower,
                    "withMetadata": True,
                    "excludeZeroValue": False,
                    "category": ["external", "erc20", "erc721", "erc1155"],
                    "maxCount": "0x64",  # 100
                }],
            )

        transfers = result.get("transfers", [])

        # Also fetch incoming transfers
        async with http_client(timeout=30) as client:
            result_in = await _rpc_post(
                client,
                settings.ALCHEMY_BASE_RPC,
                "alchemy_getAssetTransfers",
                [{
                    "fromBlock": "0x0",
                    "toBlock": "latest",
                    "toAddress": wallet_lower,
                    "withMetadata": True,
                    "excludeZeroValue": False,
                    "category": ["external", "erc20", "erc721", "erc1155"],
                    "maxCount": "0x64",
                }],
            )

        incoming = result_in.get("transfers", [])
        for t in incoming:
            t["_incoming"] = True
        all_transfers = transfers + incoming

        # Sort by timestamp descending
        all_transfers.sort(
            key=lambda t: t.get("metadata", {}).get("blockTimestamp", ""),
            reverse=True,
        )

        total = len(all_transfers)

        # Paginate
        start = (page - 1) * page_size
        page_transfers = all_transfers[start:start + page_size]

        # Format for the frontend TransactionTable
        formatted = []
        for t in page_transfers:
            ts = t.get("metadata", {}).get("blockTimestamp", "")
            is_incoming = t.get("_incoming", False)
            formatted.append({
                "tx_hash": t.get("hash", ""),
                "from_address": t.get("from", ""),
                "to_address": t.get("to", ""),
                "value_raw": str(t.get("value") or "0"),
                "value_usd": 0,
                "token_symbol": t.get("asset") or "",
                "tx_type": t.get("category", ""),
                "chain": "base",
                "timestamp": ts,
                "is_incoming": is_incoming,
                "protocol_name": None,
            })

        return {
            "transactions": formatted,
            "page": page,
            "page_size": page_size,
            "total": total,
            "source": "alchemy_live",
        }

    except Exception as e:
        logger.error(f"[Enrichment] Alchemy live fetch failed: {e}")
        return {"transactions": [], "page": page, "page_size": page_size, "total": 0}


@router.get("/{wallet_address}/transactions")
async def get_transactions(wallet_address: str, page: int = 1, page_size: int = 20):
    """Get paginated transaction history. Falls back to live Alchemy fetch if DB is empty."""
    offset = (page - 1) * page_size

    # Try DB first
    count_result = (
        anon_client.table("agent_transactions")
        .select("id", count="exact")
        .eq("wallet_address", wallet_address)
        .execute()
    )

    db_count = count_result.count or 0

    if db_count > 0:
        result = (
            anon_client.table("agent_transactions")
            .select("*")
            .eq("wallet_address", wallet_address)
            .order("timestamp", desc=True)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        return {
            "transactions": result.data or [],
            "page": page,
            "page_size": page_size,
            "total": db_count,
            "source": "database",
        }

    # No DB data — fetch live from Alchemy
    logger.info(f"[Enrichment] No DB transactions for {wallet_address}, fetching from Alchemy")
    return await _fetch_alchemy_transfers(wallet_address, page, page_size)


@router.get("/{wallet_address}/pnl")
async def get_pnl(wallet_address: str):
    """Get latest PnL report for an agent wallet."""
    result = (
        anon_client.table("agent_pnl")
        .select("*")
        .eq("wallet_address", wallet_address)
        .order("snapshot_at", desc=True)
        .limit(1)
        .execute()
    )

    if not result.data:
        return {"pnl": None}

    return {"pnl": result.data[0]}


@router.get("/{wallet_address}/positions")
async def get_positions(wallet_address: str):
    """Get current token + DeFi positions for an agent wallet."""
    result = (
        anon_client.table("agent_positions")
        .select("*")
        .eq("wallet_address", wallet_address)
        .order("snapshot_at", desc=True)
        .execute()
    )

    positions = result.data or []

    # Group by type
    tokens = [p for p in positions if p.get("position_type") == "token"]
    defi = [p for p in positions if p.get("position_type") == "defi"]
    staking = [p for p in positions if p.get("position_type") == "staking"]

    return {
        "positions": positions,
        "tokens": tokens,
        "defi": defi,
        "staking": staking,
        "total_count": len(positions),
    }
