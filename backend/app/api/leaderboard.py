from fastapi import APIRouter
from typing import Optional
from app.services.supabase import anon_client

router = APIRouter()


@router.get("/leaderboard")
async def get_leaderboard(tier: Optional[str] = None, limit: int = 100):
    """Get top agents by score."""
    query = (
        anon_client.table("scores")
        .select("wallet_address, score, tier, collateral_requirement, max_loan_usdc, rationale, scored_at, agents(agent_name, platform)")
        .order("score", desc=True)
        .limit(limit)
    )

    if tier:
        query = query.eq("tier", tier)

    result = query.execute()
    entries = result.data or []

    # Flatten agent data
    for entry in entries:
        agent_info = entry.pop("agents", None)
        if agent_info:
            entry["agent_name"] = agent_info.get("agent_name")
            entry["platform"] = agent_info.get("platform")
        else:
            entry["agent_name"] = None
            entry["platform"] = None

    return {"leaderboard": entries, "total": len(entries)}


@router.get("/stats")
async def get_stats():
    """Get aggregate statistics."""
    # Total agents
    agents_result = anon_client.table("agents").select("id", count="exact").execute()
    total_agents = agents_result.count or 0

    # Scored agents
    scores_result = anon_client.table("scores").select("wallet_address", count="exact").execute()
    scored_agents = scores_result.count or 0

    # Tier distribution
    all_scores = anon_client.table("scores").select("tier, score").execute()
    scores_data = all_scores.data or []

    tier_dist = {"S": 0, "A": 0, "B": 0, "C": 0, "D": 0}
    total_score = 0
    for s in scores_data:
        t = s.get("tier", "D")
        tier_dist[t] = tier_dist.get(t, 0) + 1
        total_score += s.get("score", 0)

    avg_score = total_score / len(scores_data) if scores_data else 0

    # Platform distribution
    platform_result = anon_client.table("agents").select("platform").execute()
    platform_dist = {}
    for a in (platform_result.data or []):
        p = a.get("platform", "unknown")
        platform_dist[p] = platform_dist.get(p, 0) + 1

    # Anomaly count
    anomaly_result = (
        anon_client.table("scores")
        .select("id", count="exact")
        .eq("is_anomaly", True)
        .execute()
    )
    anomaly_count = anomaly_result.count or 0

    return {
        "total_agents": total_agents,
        "scored_agents": scored_agents,
        "tier_distribution": tier_dist,
        "platform_distribution": platform_dist,
        "anomaly_count": anomaly_count,
        "avg_score": round(avg_score, 1),
    }
