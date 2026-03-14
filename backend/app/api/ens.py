from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from web3 import Web3
from app.services.ens_subnames import create_agent_subname, get_agent_subname
from app.services.supabase import anon_client
from app.config import get_settings

router = APIRouter()


class SubnameRequest(BaseModel):
    wallet_address: str
    agent_name: Optional[str] = None
    agent_id: str = "0"


@router.post("/subname")
async def create_subname(body: SubnameRequest):
    """
    Create an ENS subname for a scored agent.
    Requires the agent to have a valid score in the database.
    """
    settings = get_settings()
    if not settings.NAMESTONE_API_KEY or not settings.ENS_DOMAIN:
        raise HTTPException(
            status_code=503,
            detail="ENS subnames not configured. Set NAMESTONE_API_KEY and ENS_DOMAIN in .env",
        )

    try:
        wallet = Web3.to_checksum_address(body.wallet_address)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid wallet address")

    # Get latest score for this wallet
    result = (
        anon_client.table("scores")
        .select("score, tier, collateral_requirement")
        .eq("wallet_address", wallet)
        .order("scored_at", desc=True)
        .limit(1)
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=404,
            detail="No score found. Score the agent first via POST /score",
        )

    score_data = result.data[0]

    subname_result = await create_agent_subname(
        wallet_address=wallet,
        score=score_data["score"],
        tier=score_data["tier"],
        collateral_requirement=score_data["collateral_requirement"],
        agent_name=body.agent_name,
        agent_id=body.agent_id,
    )

    if subname_result.get("success"):
        return {
            "subname": subname_result["subname"],
            "domain": settings.ENS_DOMAIN,
            "wallet_address": wallet,
            "score": score_data["score"],
            "tier": score_data["tier"],
        }

    raise HTTPException(
        status_code=500,
        detail=subname_result.get("error", "Failed to create ENS subname"),
    )


@router.get("/lookup/{label}")
async def lookup_subname(label: str):
    """Look up an ENS subname created via AgentScore."""
    settings = get_settings()
    if not settings.NAMESTONE_API_KEY or not settings.ENS_DOMAIN:
        raise HTTPException(status_code=503, detail="ENS subnames not configured")

    data = await get_agent_subname(label)
    if not data:
        raise HTTPException(status_code=404, detail=f"Subname '{label}' not found")

    return data
