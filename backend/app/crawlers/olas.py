import httpx
import logging
from app.config import get_settings
from app.crawlers import http_client

logger = logging.getLogger("agentscore.crawlers.olas")


def _get_urls():
    settings = get_settings()
    api_key = settings.GRAPH_API_KEY
    base = f"https://gateway.thegraph.com/api/{api_key}/subgraphs/id"
    return {
        "eth_registry": f"{base}/89VhY3d7w6Ran1C86wkchzYNEG3rLBgWvyDUZMEFyjtQ",
        "gnosis_registry": f"{base}/HHRBjVWFT2bV7eNSRqbCNDtUVnLPt911hcp8mSe4z6KG",
        "tokenomics": f"{base}/9TqoWrLbxZA43iH7MnSqJ8igj6tRT43PFAUisxGvJK2U",
    }


async def _gql_post(client: httpx.AsyncClient, url: str, query: str) -> dict:
    resp = await client.post(
        url,
        json={"query": query},
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()
    if "errors" in result:
        logger.warning(f"GraphQL errors: {result['errors']}")
        return {}
    return result.get("data", {})


async def fetch_agent(wallet_address: str) -> dict:
    """Fetch agent data from Olas protocol via The Graph subgraphs."""
    try:
        urls = _get_urls()
        wallet_lower = wallet_address.lower()

        async with http_client() as client:
            # Query both ETH mainnet and Gnosis Chain registries
            query = """
            {
                services(where: {multisig: "%s"}, first: 10) {
                    id
                    multisig
                    agentIds
                    creationTimestamp
                }
                agentRegistrations(first: 100) {
                    agentId
                    serviceId
                    registrationTimestamp
                }
            }
            """ % wallet_lower

            # Try ETH mainnet first
            data = await _gql_post(client, urls["eth_registry"], query)
            services = data.get("services", [])

            # If not found on ETH, try Gnosis Chain
            if not services:
                data = await _gql_post(client, urls["gnosis_registry"], query)
                services = data.get("services", [])

            if not services:
                # Also check if wallet is an agent owner
                owner_query = """
                {
                    services(where: {owner: "%s"}, first: 10) {
                        id
                        multisig
                        agentIds
                        creationTimestamp
                    }
                }
                """ % wallet_lower

                data = await _gql_post(client, urls["eth_registry"], owner_query)
                services = data.get("services", [])

                if not services:
                    data = await _gql_post(client, urls["gnosis_registry"], owner_query)
                    services = data.get("services", [])

            if not services:
                logger.info(f"[Olas] Agent NOT found for {wallet_address}")
                return {"found": False}

            service = services[0]
            agent_ids = service.get("agentIds", [])

            # Get performance data if available
            tx_count = 0
            if agent_ids:
                perf_query = """
                {
                    agentPerformances(where: {id_in: [%s]}) {
                        id
                        txCount
                    }
                }
                """ % ",".join(f'"{aid}"' for aid in agent_ids)
                perf_data = await _gql_post(client, urls["eth_registry"], perf_query)
                perfs = perf_data.get("agentPerformances", [])
                tx_count = sum(int(p.get("txCount", 0)) for p in perfs)

            # Get dev incentives
            total_reward = 0
            incentive_query = """
            {
                devIncentives(where: {owner: "%s"}, first: 100) {
                    reward
                    topUp
                }
            }
            """ % wallet_lower
            inc_data = await _gql_post(client, urls["tokenomics"], incentive_query)
            incentives = inc_data.get("devIncentives", [])
            total_reward = sum(int(i.get("reward", 0)) for i in incentives)

            result = {
                "found": True,
                "agent_id": str(agent_ids[0]) if agent_ids else service["id"],
                "service_id": service["id"],
                "service_count": len(services),
                "job_count": tx_count,
                "co_agent_ids": agent_ids,
                "multisig": service.get("multisig", ""),
                "total_reward": total_reward,
                "created_at": service.get("creationTimestamp", ""),
            }
            logger.info(
                f"[Olas] FOUND agent:\n"
                f"       agent_id      = {result['agent_id']}\n"
                f"       service_id    = {result['service_id']}\n"
                f"       service_count = {result['service_count']}\n"
                f"       job_count     = {result['job_count']}\n"
                f"       total_reward  = {result['total_reward']}\n"
                f"       multisig      = {result['multisig']}"
            )
            return result

    except Exception as e:
        logger.error(f"[Olas] Crawler FAILED for {wallet_address}: {e}")
        return {"found": False}


async def list_agents(page: int = 1, page_size: int = 50) -> dict:
    """Fetch paginated list of Olas services from Gnosis Chain subgraph."""
    try:
        urls = _get_urls()
        skip = (page - 1) * page_size
        first = min(page_size, 100)

        query = """
        {
            services(first: %d, skip: %d, orderBy: creationTimestamp, orderDirection: desc) {
                id
                multisig
                agentIds
                creationTimestamp
            }
        }
        """ % (first, skip)

        async with http_client() as client:
            # Gnosis Chain has 9K+ services vs 48 on ETH
            data = await _gql_post(client, urls["gnosis_registry"], query)
            services = data.get("services", [])

            agents = []
            for svc in services:
                wallet = svc.get("multisig")
                if not wallet:
                    continue
                agent_ids = svc.get("agentIds", [])
                agents.append({
                    "wallet_address": wallet,
                    "agent_name": f"Olas Service #{svc['id']}",
                    "description": f"Service with {len(agent_ids)} agent(s) on Gnosis Chain",
                    "platform": "olas",
                    "platform_agent_id": svc["id"],
                    "service_id": svc["id"],
                    "agent_ids": agent_ids,
                    "is_active": True,
                    "image_url": "",
                    "chain": "gnosis",
                    "created_at": svc.get("creationTimestamp", ""),
                    "score": None,
                    "tier": None,
                })

            logger.info(f"[Olas] list_agents page={page} → {len(agents)} services")
            return {
                "agents": agents,
                "page": page,
                "page_size": page_size,
                "total": len(agents),
                "total_pages": -1,
                "platform": "olas",
            }
    except Exception as e:
        logger.error(f"[Olas] list_agents FAILED: {e}")
        return {
            "agents": [], "page": page, "page_size": page_size,
            "total": 0, "total_pages": 0, "platform": "olas",
        }
