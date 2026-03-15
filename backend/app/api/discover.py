import asyncio
import logging
from fastapi import APIRouter, BackgroundTasks

from app.crawlers import virtuals, olas, fetchai
from app.services.supabase import service_client

router = APIRouter()
logger = logging.getLogger("agentscore.api.discover")


@router.get("/discover/{platform_name}")
async def discover_platform_agents(
    platform_name: str,
    page: int = 1,
    page_size: int = 50,
    background_tasks: BackgroundTasks = None,
):
    """Fetch agents LIVE from a platform API for browsing."""
    crawler_map = {
        "virtuals": virtuals.list_agents,
        "olas": olas.list_agents,
        "fetch": fetchai.list_agents,
    }

    crawler_fn = crawler_map.get(platform_name)
    if not crawler_fn:
        return {
            "error": f"Platform '{platform_name}' not supported",
            "agents": [],
            "page": page,
            "page_size": page_size,
            "total": 0,
            "total_pages": 0,
            "platform": platform_name,
        }

    result = await crawler_fn(page=page, page_size=page_size)

    # Enrich with cached scores from Supabase
    result["agents"] = await _enrich_with_scores(result.get("agents", []))

    # Background: cache discovered agents in DB
    if background_tasks:
        background_tasks.add_task(_cache_discovered_agents, result.get("agents", []))

    return result


@router.get("/discover")
async def discover_all_platforms(page: int = 1, page_size: int = 20):
    """Fetch agents from ALL platforms in parallel."""
    results = await asyncio.gather(
        virtuals.list_agents(page=page, page_size=page_size),
        olas.list_agents(page=page, page_size=page_size),
        fetchai.list_agents(page=page, page_size=page_size),
        return_exceptions=True,
    )

    all_agents = []
    platform_totals = {}

    for r in results:
        if isinstance(r, Exception):
            logger.error(f"[Discover] Platform fetch failed: {r}")
            continue
        all_agents.extend(r.get("agents", []))
        platform_totals[r.get("platform", "unknown")] = r.get("total", 0)

    # Enrich with cached scores
    all_agents = await _enrich_with_scores(all_agents)

    return {
        "agents": all_agents,
        "page": page,
        "page_size": page_size,
        "platform_totals": platform_totals,
    }



async def _enrich_with_scores(agents: list) -> list:
    """Ensure cached scores are not sent to the frontend.
    
    This ensures that the directory listing does not reveal pre-computed
    scores, forcing the user to click into the agent profile to view them.
    """
    for agent in agents:
        agent["score"] = None
        agent["tier"] = None

    return agents



async def _cache_discovered_agents(agents: list):
    """Background task: upsert discovered agents into DB."""
    cached = 0
    for agent in agents:
        wallet = agent.get("wallet_address", "")
        if not wallet or not wallet.startswith("0x"):
            continue
        try:
            service_client.table("agents").upsert(
                {
                    "wallet_address": wallet,
                    "agent_name": agent.get("agent_name", ""),
                    "platform": agent.get("platform", "unknown"),
                    "platform_agent_id": agent.get("platform_agent_id", wallet),
                    "description": agent.get("description", ""),
                    "is_active": agent.get("is_active", True),
                    "metadata": {
                        "mcap_usd": agent.get("mcap_usd"),
                        "holder_count": agent.get("holder_count"),
                        "image_url": agent.get("image_url"),
                        "chain": agent.get("chain"),
                    },
                },
                on_conflict="wallet_address",
            ).execute()
            cached += 1
        except Exception:
            pass
    if cached:
        logger.info(f"[Discover] Cached {cached} agents to DB")
