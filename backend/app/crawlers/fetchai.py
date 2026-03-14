import logging
from app.crawlers import http_client

logger = logging.getLogger("agentscore.crawlers.fetchai")

AGENTVERSE_SEARCH_URL = "https://agentverse.ai/v1/search/agents"


async def fetch_agent(wallet_address: str) -> dict:
    """
    Search Fetch.ai Agentverse for agents potentially linked to a wallet.

    Note: Fetch.ai uses agent1q... addresses, NOT EVM wallets.
    This is a best-effort search matching wallet in agent metadata/description.
    """
    try:
        wallet_lower = wallet_address.lower()
        async with http_client(timeout=30) as client:
            # Search by wallet address substring in agent data
            resp = await client.post(
                AGENTVERSE_SEARCH_URL,
                json={"limit": 100, "offset": 0},
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "AgentScore/1.0",
                },
            )
            resp.raise_for_status()
            data = resp.json()

            agents = data.get("agents", [])
            for agent in agents:
                # Check description, metadata for wallet reference
                description = (agent.get("description") or "").lower()
                name = (agent.get("name") or "").lower()
                readme = (agent.get("readme") or "").lower()

                if wallet_lower in description or wallet_lower in readme:
                    metadata = agent.get("metadata", {})
                    result = {
                        "found": True,
                        "agent_address": agent.get("address", ""),
                        "agent_name": agent.get("name", ""),
                        "description": agent.get("description", ""),
                        "total_interactions": metadata.get("totalInteractions", 0),
                        "recent_interactions": metadata.get("recentInteractions", 0),
                        "rating": metadata.get("rating", 0),
                        "active_services": len(agent.get("protocols", [])),
                        "status": agent.get("status", ""),
                        "category": agent.get("category", ""),
                    }
                    logger.info(
                        f"[Fetch.ai] FOUND agent:\n"
                        f"           name            = {result['agent_name']}\n"
                        f"           agent_address   = {result['agent_address']}\n"
                        f"           interactions    = {result['total_interactions']}\n"
                        f"           active_services = {result['active_services']}\n"
                        f"           rating          = {result['rating']}"
                    )
                    return result

        logger.info(f"[Fetch.ai] Agent NOT found for {wallet_address} (searched {len(agents)} agents)")
        return {"found": False}
    except Exception as e:
        logger.error(f"[Fetch.ai] Crawler FAILED for {wallet_address}: {e}")
        return {"found": False}


async def list_agents(page: int = 1, page_size: int = 20) -> dict:
    """Fetch paginated list of Fetch.ai agents from Agentverse."""
    try:
        offset = (page - 1) * page_size
        async with http_client(timeout=30) as client:
            resp = await client.post(
                AGENTVERSE_SEARCH_URL,
                json={"limit": page_size, "offset": offset},
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "AgentScore/1.0",
                },
            )
            resp.raise_for_status()
            data = resp.json()

            agents_raw = data.get("agents", [])
            agents = []
            for a in agents_raw:
                agents.append({
                    "wallet_address": a.get("address", ""),
                    "agent_name": a.get("name", ""),
                    "description": (a.get("description") or "")[:200],
                    "platform": "fetch",
                    "platform_agent_id": a.get("address", ""),
                    "is_active": a.get("status", "") == "active",
                    "image_url": "",
                    "category": a.get("category", ""),
                    "protocols_count": len(a.get("protocols", [])),
                    "chain": "fetch",
                    "is_evm_wallet": False,
                    "score": None,
                    "tier": None,
                })

            total = data.get("total", len(agents))
            logger.info(f"[Fetch.ai] list_agents page={page} → {len(agents)} agents")
            return {
                "agents": agents,
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": max(1, (total + page_size - 1) // page_size) if total > 0 else 1,
                "platform": "fetch",
            }
    except Exception as e:
        logger.error(f"[Fetch.ai] list_agents FAILED: {e}")
        return {
            "agents": [], "page": page, "page_size": page_size,
            "total": 0, "total_pages": 0, "platform": "fetch",
        }
