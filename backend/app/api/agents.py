from fastapi import APIRouter, HTTPException
from typing import Optional
from app.services.supabase import anon_client

router = APIRouter()


@router.get("")
async def list_agents(
    platform: Optional[str] = None,
    tier: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = 1,
    page_size: int = 50,
):
    """List agents with optional filters, joined with latest score."""
    query = anon_client.table("agents").select("*, scores(score, tier, scored_at)")

    if platform:
        query = query.eq("platform", platform)
    if is_active is not None:
        query = query.eq("is_active", is_active)

    offset = (page - 1) * page_size
    query = query.range(offset, offset + page_size - 1).order("created_at", desc=True)

    result = query.execute()
    agents = result.data or []

    # Flatten latest score into agent
    for agent in agents:
        scores = agent.pop("scores", [])
        if scores:
            latest = scores[0]
            agent["score"] = latest.get("score")
            agent["tier"] = latest.get("tier")
        else:
            agent["score"] = None
            agent["tier"] = None

    # Filter by tier if requested (post-query since it's in joined table)
    if tier:
        agents = [a for a in agents if a.get("tier") == tier]

    return {
        "agents": agents,
        "page": page,
        "page_size": page_size,
        "total": len(agents),
    }


@router.get("/{wallet_address}")
async def get_agent(wallet_address: str):
    """Get full agent profile with latest score and features."""
    # Get agent
    agent_result = (
        anon_client.table("agents")
        .select("*")
        .eq("wallet_address", wallet_address)
        .limit(1)
        .execute()
    )

    if not agent_result.data:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent = agent_result.data[0]

    # Get latest score
    score_result = (
        anon_client.table("scores")
        .select("*")
        .eq("wallet_address", wallet_address)
        .order("scored_at", desc=True)
        .limit(1)
        .execute()
    )

    # Get features
    features_result = (
        anon_client.table("agent_features")
        .select("*")
        .eq("agent_id", agent["id"])
        .limit(1)
        .execute()
    )

    # Get PnL data
    pnl_result = (
        anon_client.table("agent_pnl")
        .select("*")
        .eq("wallet_address", wallet_address)
        .order("snapshot_at", desc=True)
        .limit(1)
        .execute()
    )

    # Get pending request if any
    request_result = (
        anon_client.table("score_requests")
        .select("id, status, created_at")
        .eq("wallet_address", wallet_address)
        .in_("status", ["pending", "processing"])
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    return {
        "agent": agent,
        "latest_score": score_result.data[0] if score_result.data else None,
        "features": features_result.data[0] if features_result.data else None,
        "pnl": pnl_result.data[0] if pnl_result.data else None,
        "pending_request": request_result.data[0] if request_result.data else None,
    }
