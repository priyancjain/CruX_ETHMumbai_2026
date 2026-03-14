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
    """Attach cached scores to agents from Supabase."""
    wallet_addresses = [
        a["wallet_address"] for a in agents
        if a.get("wallet_address") and a["wallet_address"].startswith("0x")
    ]
    if not wallet_addresses:
        return agents

    cached_scores = {}
    try:
        scores_result = (
            service_client.table("scores")
            .select("wallet_address, score, tier")
            .in_("wallet_address", wallet_addresses[:100])
            .order("scored_at", desc=True)
            .execute()
        )
        for s in (scores_result.data or []):
            w = s["wallet_address"]
            if w not in cached_scores:
                cached_scores[w] = {"score": s["score"], "tier": s["tier"]}
    except Exception as e:
        logger.warning(f"Failed to fetch cached scores: {e}")

    for agent in agents:
        w = agent.get("wallet_address", "")
        if w in cached_scores:
            agent["score"] = cached_scores[w]["score"]
            agent["tier"] = cached_scores[w]["tier"]

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
