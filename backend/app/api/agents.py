from fastapi import APIRouter, HTTPException
from typing import Optional
from app.services.supabase import anon_client, service_client

router = APIRouter()



@router.get("/search")
async def search_agents(q: str, limit: int = 30):
    """
    Full-text search across agent name, description and platform.
    Falls back to a case-insensitive ILIKE on each column because
    Supabase free-tier text-search index may not be configured.
    """
    if not q or len(q.strip()) < 2:
        return {"agents": [], "total": 0, "query": q}

    pattern = f"%{q.strip()}%"

    # Search by agent_name
    by_name = (
        service_client.table("agents")
        .select("*")
        .ilike("agent_name", pattern)
        .limit(limit)
        .execute()
    )

    # Search by description
    by_desc = (
        service_client.table("agents")
        .select("*")
        .ilike("description", pattern)
        .limit(limit)
        .execute()
    )

    # Search by platform
    by_platform = (
        service_client.table("agents")
        .select("*")
        .ilike("platform", pattern)
        .limit(limit)
        .execute()
    )

    # Merge & deduplicate by wallet_address
    seen = set()
    merged = []
    for row in (by_name.data or []) + (by_desc.data or []) + (by_platform.data or []):
        w = row.get("wallet_address", "")
        if not w:
            continue
        w_low = w.lower()
        if w_low not in seen:
            seen.add(w_low)
            merged.append(row)

    # Return the merged agents without preemptively fetching cached scores
    result_agents = []
    for agent in merged:
        w = agent.get("wallet_address", "")
        
        # Flatten metadata subfields if present
        meta = agent.get("metadata") or {}
        
        agent_obj = {
            "wallet_address": w,
            "agent_name": agent.get("agent_name", ""),
            "description": agent.get("description", ""),
            "platform": agent.get("platform", ""),
            "score": None,  # Always hide score on the card overview per user request
            "tier": None,
            "image_url": meta.get("image_url", ""),
            "mcap_usd": meta.get("mcap_usd"),
            "holder_count": meta.get("holder_count"),
            "chain": meta.get("chain", ""),
            "is_evm_wallet": w.startswith("0x"),
        }
            
        result_agents.append(agent_obj)

    return {"agents": result_agents, "total": len(result_agents), "query": q}


@router.get("")
async def list_agents(
    platform: Optional[str] = None,
    tier: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = 1,
    page_size: int = 50,
):
    """List agents with optional filters, without joining cached scores."""
    # Do not join the scores table so we don't leak cached scores
    query = anon_client.table("agents").select("*")

    if platform:
        query = query.eq("platform", platform)
    if is_active is not None:
        query = query.eq("is_active", is_active)

    offset = (page - 1) * page_size
    query = query.range(offset, offset + page_size - 1).order("created_at", desc=True)

    result = query.execute()
    agents = result.data or []

    # Ensure score and tier are null so the frontend shows "NOT YET SCORED"
    for agent in agents:
        agent["score"] = None
        agent["tier"] = None

    # Filter by tier if requested (post-query since it's in joined table)
    if tier:
        agents = [a for a in agents if a.get("tier") == tier]

    return {
        "page": page,
        "page_size": page_size,
        "agents": agents,
        "total": len(agents),
    }


@router.get("/{wallet_address}")
async def get_agent(wallet_address: str):
    """Get full agent profile with latest score and features."""
    # Normalise address for lookups
    w_low = wallet_address.lower()

    # Get agent via ILIKE to handle case-insensitive match on wallet_address
    agent_result = (
        anon_client.table("agents")
        .select("*")
        .ilike("wallet_address", w_low)
        .limit(1)
        .execute()
    )

    if not agent_result.data:
        # Check if there is a pending scoring request before throwing 404
        request_result = (
            anon_client.table("score_requests")
            .select("id, status, created_at")
            .ilike("wallet_address", w_low)
            .in_("status", ["pending", "processing"])
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if request_result.data:
            # Return a stub profile to the frontend to show "Scoring in Progress"
            return {
                "agent": {
                    "wallet_address": wallet_address,
                    "agent_name": f"Agent-{wallet_address[:8]}",
                    "platform": "unknown",
                    "is_active": True,
                },
                "latest_score": None,
                "features": None,
                "pnl": None,
                "pending_request": request_result.data[0],
            }
        raise HTTPException(status_code=404, detail="Agent not found")

    agent = agent_result.data[0]
    actual_wallet = agent["wallet_address"]

    # Get latest score (normalized address)
    score_result = (
        anon_client.table("scores")
        .select("*")
        .eq("wallet_address", actual_wallet.lower())
        .order("scored_at", desc=True)
        .limit(1)
        .execute()
    )
    
    # Fallback to literal case if lowercased match failed
    if not score_result.data:
         score_result = (
            anon_client.table("scores")
            .select("*")
            .eq("wallet_address", actual_wallet)
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

    # Get PnL data (normalised)
    pnl_result = (
        anon_client.table("agent_pnl")
        .select("*")
        .ilike("wallet_address", w_low)
        .order("snapshot_at", desc=True)
        .limit(1)
        .execute()
    )

    # Get pending request if any
    request_result = (
        anon_client.table("score_requests")
        .select("id, status, created_at")
        .ilike("wallet_address", w_low)
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

