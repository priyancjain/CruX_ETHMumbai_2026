from fastapi import APIRouter, HTTPException
from app.services.supabase import anon_client

router = APIRouter()


@router.get("/{wallet_address}/transactions")
async def get_transactions(wallet_address: str, page: int = 1, page_size: int = 20):
    """Get paginated transaction history for an agent wallet."""
    offset = (page - 1) * page_size

    result = (
        anon_client.table("agent_transactions")
        .select("*")
        .eq("wallet_address", wallet_address)
        .order("timestamp", desc=True)
        .range(offset, offset + page_size - 1)
        .execute()
    )

    count_result = (
        anon_client.table("agent_transactions")
        .select("id", count="exact")
        .eq("wallet_address", wallet_address)
        .execute()
    )

    return {
        "transactions": result.data or [],
        "page": page,
        "page_size": page_size,
        "total": count_result.count or 0,
    }


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
