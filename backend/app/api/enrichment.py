import json
import logging
from fastapi import APIRouter, HTTPException
from app.services.supabase import anon_client, service_client
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
            
            from_addr = t.get("from", "")
            to_addr = t.get("to", "")
            
            # The "peer" is whoever isn't the wallet we are looking at
            wallet_low = wallet.lower()
            peer = from_addr if is_incoming else to_addr
            
            formatted.append({
                "tx_hash": t.get("hash", ""),
                "from_address": from_addr,
                "to_address": to_addr,
                "peer_address": peer,
                "value_raw": str(t.get("value") or "0"),
                "value_usd": 0, # Stays 0 for live fallback unless we add price fetch
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

    # Calculate token shares for pie chart
    total_val = sum(float(t.get("balance_usd") or 0) for t in tokens)
    token_shares = []
    if total_val > 0:
        # Top 5 + Others
        sorted_tokens = sorted(tokens, key=lambda x: float(x.get("balance_usd") or 0), reverse=True)
        for t in sorted_tokens[:5]:
            token_shares.append({
                "name": t.get("token_symbol", "??"),
                "value": float(t.get("balance_usd") or 0)
            })
        others = sum(float(t.get("balance_usd") or 0) for t in sorted_tokens[5:])
        if others > 0:
            token_shares.append({"name": "Others", "value": others})

    return {
        "positions": positions,
        "tokens": tokens,
        "defi": defi,
        "staking": staking,
        "token_shares": token_shares,
        "total_count": len(positions),
    }



@router.get("/{wallet_address}/trends")
async def get_wallet_trends(wallet_address: str):
    """Get aggregated daily transaction trends for charting."""
    from collections import defaultdict
    
    # Try DB aggregation
    result = (
        anon_client.table("agent_transactions")
        .select("timestamp")
        .eq("wallet_address", wallet_address)
        .order("timestamp", desc=True)
        .limit(500)
        .execute()
    )

    data = result.data or []
    
    # If no DB data, fall back to Alchemy
    if not data:
        live = await _fetch_alchemy_transfers(wallet_address, 1, 100)
        data = live.get("transactions", [])

    counts = defaultdict(int)
    for t in data:
        ts = t.get("timestamp")
        if not ts: continue
        day = ts.split("T")[0]
        counts[day] += 1
    
    sorted_days = sorted(counts.items())
    trend = [{"date": d, "count": c} for d, c in sorted_days]
    
    return {"trend": trend[-30:]}


@router.get("/{wallet_address}/pnl/history")
async def get_pnl_history(wallet_address: str):
    """Get historical PnL snapshots for equity curve charting."""
    result = (
        anon_client.table("agent_pnl")
        .select("total_pnl_usd, snapshot_at")
        .eq("wallet_address", wallet_address)
        .order("snapshot_at", desc=False)
        .execute()
    )
    
    history = []
    for row in (result.data or []):
        history.append({
            "date": row["snapshot_at"].split("T")[0],
            "value": float(row["total_pnl_usd"] or 0)
        })
        
    return {"history": history}


@router.get("/{wallet_address}/stats")
async def get_trading_stats(wallet_address: str):
    """Get high-level trading performance statistics."""
    result = (
        anon_client.table("agent_pnl")
        .select("*")
        .eq("wallet_address", wallet_address)
        .order("snapshot_at", desc=True)
        .limit(1)
        .execute()
    )
    
    if not result.data:
        return {
            "win_rate": 0,
            "total_trades": 0,
            "profitable_trades": 0,
            "loss_making_trades": 0,
            "avg_return_usd": 0,
            "largest_win_usd": 0,
            "largest_loss_usd": 0
        }
        
    pnl = result.data[0]
    total = pnl.get("total_trades", 0)
    wins = pnl.get("profitable_trades", 0)
    losses = total - wins if total > wins else 0
    
    return {
        "win_rate": pnl.get("win_rate", 0),
        "total_trades": total,
        "profitable_trades": wins,
        "loss_making_trades": losses,
        "avg_return_usd": pnl.get("avg_trade_size_usd", 0),
        "largest_win_usd": pnl.get("largest_win_usd", 0),
        "largest_loss_usd": pnl.get("largest_loss_usd", 0),
        "realized_pnl": pnl.get("realized_pnl_usd", 0)
    }


@router.get("/{wallet_address}/activity")
async def get_activity_heatmap(wallet_address: str):
    """Get historical activity heatmap data (last 90 days)."""
    from collections import defaultdict
    
    result = (
        anon_client.table("agent_transactions")
        .select("timestamp")
        .eq("wallet_address", wallet_address)
        .order("timestamp", desc=True)
        .limit(1000)
        .execute()
    )
    
    data = result.data or []
    
    # Fallback to Alchemy if DB is empty
    if not data:
        live = await _fetch_alchemy_transfers(wallet_address, 1, 200)
        data = live.get("transactions", [])
    
    activity = defaultdict(int)
    for tx in data:
        ts = tx.get("timestamp")
        if not ts: continue
        day = ts.split("T")[0]
        activity[day] += 1
        
    heatmap = [{"date": d, "count": c} for d, c in activity.items()]
    return {"activity": heatmap}


@router.get("/{wallet_address}/analysis")
async def get_agent_analysis(wallet_address: str):
    """Retrieve the deep LLM analysis stored in the latest score."""
    logger.info(f"[Enrichment] Fetching analysis for {wallet_address}")
    
    # Use service_client to ensure we bypass any RLS for this specific detail
    try:
        result = (
            service_client.table("scores")
            .select("raw_features, rationale, scored_at")
            .ilike("wallet_address", wallet_address)
            .order("scored_at", desc=True)
            .limit(1)
            .execute()
        )
    except Exception as e:
        logger.error(f"[Enrichment] Database error fetching analysis: {e}")
        return {"analysis": None}
    
    if not result.data:
        logger.warning(f"[Enrichment] No score found for {wallet_address}")
        return {"analysis": None}
        
    score_data = result.data[0]
    raw = score_data.get("raw_features") or {}
    
    # Handle both string and dict formats for raw_features
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except:
            raw = {}
            
    analysis = raw.get("tx_analysis", {})
    
    # If tx_analysis doesn't have a summary, fallback to the rationale
    if not analysis.get("summary") and score_data.get("rationale"):
        logger.info(f"[Enrichment] Falling back to rationale for {wallet_address}")
        analysis["summary"] = score_data["rationale"]
        
    if not analysis.get("summary"):
        logger.warning(f"[Enrichment] No summary or rationale found for {wallet_address}")
    else:
        logger.info(f"[Enrichment] Returning analysis for {wallet_address} (Scored at: {score_data.get('scored_at')})")
        
    return {"analysis": analysis}
