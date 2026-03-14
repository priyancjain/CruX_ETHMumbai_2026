from fastapi import APIRouter
from app.services.supabase import anon_client

router = APIRouter()

SUPPORTED_PLATFORMS = [
    {"name": "virtuals", "display_name": "Virtuals Protocol", "chain": "Base", "total_agents": 21171},
    {"name": "olas", "display_name": "Olas (Autonolas)", "chain": "ETH / Gnosis", "total_agents": 9000},
    {"name": "fetch", "display_name": "Fetch.ai", "chain": "Fetch Network", "total_agents": 10000},
    {"name": "elizaos", "display_name": "ElizaOS", "chain": "Multi-chain", "total_agents": 0},
    {"name": "erc8004", "display_name": "ERC-8004 Registry", "chain": "Multi-chain", "total_agents": 0},
    {"name": "talus", "display_name": "Talus", "chain": "Talus", "total_agents": 0},
    {"name": "wayfinder", "display_name": "Wayfinder", "chain": "ETH", "total_agents": 0},
    {"name": "freysa", "display_name": "Freysa", "chain": "ETH", "total_agents": 0},
    {"name": "agentlayer", "display_name": "AgentLayer", "chain": "Multi-chain", "total_agents": 0},
    {"name": "sentient", "display_name": "Sentient", "chain": "Multi-chain", "total_agents": 0},
]


@router.get("")
async def list_platforms():
    """List all supported platforms with agent counts in our DB."""
    # Get counts from our DB
    result = anon_client.table("agents").select("platform").execute()
    db_counts = {}
    for a in (result.data or []):
        p = a.get("platform", "")
        db_counts[p] = db_counts.get(p, 0) + 1

    platforms = []
    for p in SUPPORTED_PLATFORMS:
        platforms.append({
            **p,
            "indexed_agents": db_counts.get(p["name"], 0),
        })

    return {"platforms": platforms}


@router.get("/{platform_name}/agents")
async def get_platform_agents(platform_name: str, page: int = 1, page_size: int = 50):
    """Get agents for a specific platform."""
    offset = (page - 1) * page_size
    result = (
        anon_client.table("agents")
        .select("*, scores(score, tier)")
        .eq("platform", platform_name)
        .range(offset, offset + page_size - 1)
        .order("created_at", desc=True)
        .execute()
    )

    agents = result.data or []
    for agent in agents:
        scores = agent.pop("scores", [])
        if scores:
            agent["score"] = scores[0].get("score")
            agent["tier"] = scores[0].get("tier")
        else:
            agent["score"] = None
            agent["tier"] = None

    return {
        "platform": platform_name,
        "agents": agents,
        "page": page,
        "page_size": page_size,
    }
