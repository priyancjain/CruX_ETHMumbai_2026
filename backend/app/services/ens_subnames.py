"""
ENS Subname Service — Gasless offchain subnames via NameStone API.

Creates subnames like `agent123.agentscore.eth` for scored agents with:
  - ENSIP-25 text record: agent-registration[<erc7930>][<agentId>] = "1"
  - Score text records: agentscore.score, agentscore.tier, agentscore.collateral
  - Address resolution: subname → agent wallet address

Uses NameStone API (CCIP-Read / ERC-3668) — zero gas, instant, free.
Same approach Coinbase used for 2M+ *.base.eth subnames.
"""

import re
import logging
import httpx
from app.config import get_settings
from app.crawlers import http_client

logger = logging.getLogger("agentscore.services.ens_subnames")

# ERC-7930 encoded address of ERC-8004 Identity Registry
ERC7930_REGISTRY = "0x000100000101148004a169fb4a3325136eb29fa0ceb6d2e539a432"

NAMESTONE_BASE_URL = "https://namestone.com/api/public_v1"


def _sanitize_label(name: str) -> str:
    """
    Convert agent name to a valid ENS subdomain label.
    Rules: lowercase, alphanumeric + hyphens, no leading/trailing hyphens,
           max 63 chars, no consecutive hyphens.
    """
    label = name.lower().strip()
    # Replace spaces and underscores with hyphens
    label = re.sub(r"[\s_]+", "-", label)
    # Remove non-alphanumeric except hyphens
    label = re.sub(r"[^a-z0-9\-]", "", label)
    # Collapse consecutive hyphens
    label = re.sub(r"-{2,}", "-", label)
    # Strip leading/trailing hyphens
    label = label.strip("-")
    # Truncate to 63 chars (DNS label limit)
    label = label[:63].rstrip("-")
    return label or "agent"


async def create_agent_subname(
    wallet_address: str,
    score: int,
    tier: str,
    collateral_requirement: int,
    agent_name: str | None = None,
    agent_id: str = "0",
) -> dict:
    """
    Create a gasless ENS subname for a scored agent via NameStone API.

    Creates: {label}.agentscore.eth → wallet_address
    Sets text records:
      - agent-registration[<erc7930>][<agentId>] = "1"  (ENSIP-25)
      - agentscore.score = "820"
      - agentscore.tier = "A"
      - agentscore.collateral = "75"
      - description = "AI Agent — AgentScore A-tier (820/1000)"

    Returns: { subname, success, error? }
    """
    settings = get_settings()

    if not settings.NAMESTONE_API_KEY:
        logger.info("[ENS Subnames] Skipped — NAMESTONE_API_KEY not set")
        return {"subname": None, "success": False, "error": "NAMESTONE_API_KEY not configured"}

    if not settings.ENS_DOMAIN:
        logger.info("[ENS Subnames] Skipped — ENS_DOMAIN not set")
        return {"subname": None, "success": False, "error": "ENS_DOMAIN not configured"}

    domain = settings.ENS_DOMAIN  # e.g. "agentscore.eth"

    # Generate label from agent name or wallet
    if agent_name:
        label = _sanitize_label(agent_name)
    else:
        label = wallet_address[2:10].lower()  # First 8 hex chars

    subname = f"{label}.{domain}"

    # Build ENSIP-25 text record key
    ensip25_key = f"agent-registration[{ERC7930_REGISTRY}][{agent_id}]"

    text_records = {
        ensip25_key: "1",
        "agentscore.score": str(score),
        "agentscore.tier": tier,
        "agentscore.collateral": str(collateral_requirement),
        "description": f"AI Agent — AgentScore {tier}-tier ({score}/1000)",
    }

    try:
        async with http_client(timeout=30) as client:
            resp = await client.post(
                f"{NAMESTONE_BASE_URL}/set-name",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": settings.NAMESTONE_API_KEY,
                },
                json={
                    "domain": domain,
                    "name": label,
                    "address": wallet_address,
                    "text_records": text_records,
                },
            )

            if resp.status_code == 200:
                logger.info(
                    f"[ENS Subnames] Created {subname} → {wallet_address} "
                    f"(score={score}, tier={tier}, ENSIP-25={ensip25_key})"
                )
                return {"subname": subname, "success": True}

            # Handle duplicate — try with wallet suffix
            if resp.status_code == 409 or "already exists" in resp.text.lower():
                label_fallback = f"{label}-{wallet_address[2:8].lower()}"
                subname_fallback = f"{label_fallback}.{domain}"

                resp2 = await client.post(
                    f"{NAMESTONE_BASE_URL}/set-name",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": settings.NAMESTONE_API_KEY,
                    },
                    json={
                        "domain": domain,
                        "name": label_fallback,
                        "address": wallet_address,
                        "text_records": text_records,
                    },
                )

                if resp2.status_code == 200:
                    logger.info(f"[ENS Subnames] Created {subname_fallback} (fallback label)")
                    return {"subname": subname_fallback, "success": True}

                error = f"NameStone fallback also failed: {resp2.status_code} {resp2.text[:200]}"
                logger.warning(f"[ENS Subnames] {error}")
                return {"subname": None, "success": False, "error": error}

            error = f"NameStone API error: {resp.status_code} {resp.text[:200]}"
            logger.warning(f"[ENS Subnames] {error}")
            return {"subname": None, "success": False, "error": error}

    except Exception as e:
        error = f"ENS subname creation failed: {e}"
        logger.warning(f"[ENS Subnames] {error}")
        return {"subname": None, "success": False, "error": error}


async def update_agent_subname(
    subname_label: str,
    wallet_address: str,
    score: int,
    tier: str,
    collateral_requirement: int,
    agent_id: str = "0",
) -> dict:
    """
    Update text records on an existing subname (e.g. after re-scoring).
    NameStone's set-name is idempotent — calling it again updates the records.
    """
    return await create_agent_subname(
        wallet_address=wallet_address,
        score=score,
        tier=tier,
        collateral_requirement=collateral_requirement,
        agent_name=subname_label,
        agent_id=agent_id,
    )


async def get_agent_subname(label: str) -> dict | None:
    """Look up a subname via NameStone API."""
    settings = get_settings()

    if not settings.NAMESTONE_API_KEY or not settings.ENS_DOMAIN:
        return None

    try:
        async with http_client(timeout=15) as client:
            resp = await client.get(
                f"{NAMESTONE_BASE_URL}/get-names",
                headers={"Authorization": settings.NAMESTONE_API_KEY},
                params={"domain": settings.ENS_DOMAIN, "name": label},
            )
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and data:
                    return data[0]
            return None
    except Exception as e:
        logger.debug(f"[ENS Subnames] Lookup failed for {label}: {e}")
        return None
