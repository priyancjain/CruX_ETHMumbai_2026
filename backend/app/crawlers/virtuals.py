import logging
from app.crawlers import http_client

logger = logging.getLogger("agentscore.crawlers.virtuals")

VIRTUALS_API = "https://api.virtuals.io/api/virtuals"


async def fetch_agent(wallet_address: str) -> dict:
    """Fetch agent data from Virtuals protocol by wallet address."""
    try:
        wallet_lower = wallet_address.lower()
        async with http_client(timeout=30) as client:
            # Search first 5 pages (500 agents) for hackathon speed
            for page in range(1, 6):
                resp = await client.get(
                    VIRTUALS_API,
                    params={
                        "pagination[page]": page,
                        "pagination[pageSize]": 100,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                agents = data.get("data", [])
                if not agents:
                    break

                for agent in agents:
                    sentient_wallet = (agent.get("sentientWalletAddress") or "").lower()
                    agent_wallet = (agent.get("walletAddress") or "").lower()

                    if wallet_lower in (sentient_wallet, agent_wallet):
                        # Derive virtuals_level from API fields (level, tier, or infer from mcap)
                        raw_level = agent.get("level") or agent.get("tier") or agent.get("agentLevel") or 0
                        if not raw_level:
                            # Infer level from market cap tiers
                            mcap = float(agent.get("mcapInVirtual", 0) or 0)
                            if mcap >= 1_000_000:
                                raw_level = 5
                            elif mcap >= 100_000:
                                raw_level = 4
                            elif mcap >= 10_000:
                                raw_level = 3
                            elif mcap >= 1_000:
                                raw_level = 2
                            elif mcap > 0:
                                raw_level = 1
                            else:
                                raw_level = 0

                        result = {
                            "found": True,
                            "agent_name": agent.get("name", ""),
                            "description": agent.get("description", ""),
                            "mcap_usd": float(agent.get("mcapInVirtual", 0)),
                            "holder_count": int(agent.get("holderCount", 0)),
                            "agent_id": str(agent.get("id", "")),
                            "virtual_id": agent.get("virtualId", ""),
                            "platform_agent_id": str(agent.get("id", "")),
                            "chain": agent.get("chain", "BASE"),
                            "status": agent.get("status", ""),
                            "is_active": agent.get("status") == "AVAILABLE",
                            "virtuals_level": int(raw_level),
                        }
                        logger.info(
                            f"[Virtuals] FOUND agent on page {page}:\n"
                            f"           name       = {result['agent_name']}\n"
                            f"           mcap_usd   = {result['mcap_usd']}\n"
                            f"           holders    = {result['holder_count']}\n"
                            f"           agent_id   = {result['agent_id']}\n"
                            f"           chain      = {result['chain']}\n"
                            f"           status     = {result['status']}"
                        )
                        return result

        logger.info(f"[Virtuals] Agent NOT found for {wallet_address} (searched 5 pages)")
        return {"found": False}
    except Exception as e:
        logger.error(f"[Virtuals] Crawler FAILED for {wallet_address}: {e}")
        return {"found": False}


async def list_agents(page: int = 1, page_size: int = 100) -> dict:
    """Fetch paginated list of Virtuals agents for browsing."""
    try:
        async with http_client(timeout=30) as client:
            resp = await client.get(
                VIRTUALS_API,
                params={
                    "pagination[page]": page,
                    "pagination[pageSize]": min(page_size, 100),
                },
            )
            resp.raise_for_status()
            data = resp.json()

            agents_raw = data.get("data", [])
            pagination = data.get("meta", {}).get("pagination", {})

            agents = []
            for a in agents_raw:
                wallet = a.get("sentientWalletAddress") or a.get("walletAddress")
                if not wallet:
                    continue
                agents.append({
                    "wallet_address": wallet,
                    "agent_name": a.get("name", ""),
                    "description": (a.get("description") or "")[:200],
                    "platform": "virtuals",
                    "platform_agent_id": str(a.get("id", "")),
                    "mcap_usd": float(a.get("mcapInVirtual", 0)),
                    "holder_count": int(a.get("holderCount", 0)),
                    "image_url": (a.get("image") or {}).get("url", ""),
                    "is_active": a.get("status") == "AVAILABLE",
                    "chain": a.get("chain", "BASE"),
                    "score": None,
                    "tier": None,
                })

            logger.info(f"[Virtuals] list_agents page={page} → {len(agents)} agents")
            return {
                "agents": agents,
                "page": page,
                "page_size": page_size,
                "total": pagination.get("total", len(agents)),
                "total_pages": pagination.get("pageCount", 1),
                "platform": "virtuals",
            }
    except Exception as e:
        logger.error(f"[Virtuals] list_agents FAILED: {e}")
        return {
            "agents": [], "page": page, "page_size": page_size,
            "total": 0, "total_pages": 0, "platform": "virtuals",
        }
