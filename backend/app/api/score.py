import logging
from fastapi import APIRouter, HTTPException, Header
from datetime import datetime, timezone, timedelta
from typing import Optional
from app.models.score import ScoreRequest, ScoreResponse, ScoreQueuedResponse
from app.services.supabase import anon_client, service_client
from app.config import get_settings

logger = logging.getLogger("agentscore.api.score")
router = APIRouter()


@router.post("", response_model=ScoreQueuedResponse | ScoreResponse)
async def request_score(body: ScoreRequest):
    """Request a credit score for an agent wallet. Returns cached if valid."""
    wallet = body.wallet_address

    # Check for valid unexpired score
    existing = (
        anon_client.table("scores")
        .select("*")
        .eq("wallet_address", wallet)
        .gte("expires_at", datetime.now(timezone.utc).isoformat())
        .order("scored_at", desc=True)
        .limit(1)
        .execute()
    )

    if existing.data:
        score = existing.data[0]
        logger.info(f"[POST /score] CACHED score returned for {wallet} → score={score['score']}, tier={score['tier']} (expires {score.get('expires_at')})")
        return ScoreResponse(**score, cached=True)

    logger.info(f"[POST /score] No cached score for {wallet}, will queue scoring request")

    # Expire stale pending/processing requests (older than 5 minutes)
    stale_cutoff = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    stale = (
        service_client.table("score_requests")
        .select("id")
        .eq("wallet_address", wallet)
        .in_("status", ["pending", "processing"])
        .lt("created_at", stale_cutoff)
        .execute()
    )
    if stale.data:
        for s in stale.data:
            service_client.table("score_requests").update({
                "status": "failed",
                "error_message": "Expired — stale request",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", s["id"]).execute()

    # Check for already pending/processing request for same wallet (fresh only)
    pending = (
        anon_client.table("score_requests")
        .select("id, status")
        .eq("wallet_address", wallet)
        .in_("status", ["pending", "processing"])
        .limit(1)
        .execute()
    )
    if pending.data:
        logger.info(f"[POST /score] Already pending/processing request {pending.data[0]['id']} for {wallet}")
        return ScoreQueuedResponse(
            request_id=pending.data[0]["id"],
            status="queued",
            message="Scoring already in progress for this wallet.",
        )

    # Queue scoring request
    request_row = {
        "wallet_address": wallet,
        "requested_by": body.requested_by,
        "priority": body.priority,
        "status": "pending",
    }
    if body.agent_id:
        request_row["agent_id"] = body.agent_id
    result = service_client.table("score_requests").insert(request_row).execute()

    request_id = result.data[0]["id"] if result.data else "unknown"
    logger.info(f"[POST /score] NEW score_request created: id={request_id}, wallet={wallet}, priority={body.priority}")
    return ScoreQueuedResponse(
        request_id=request_id,
        status="queued",
        message="Scoring in progress. Subscribe to Supabase Realtime for live updates.",
    )


@router.get("/{wallet_address}", response_model=ScoreResponse)
async def get_score(wallet_address: str):
    """Get the latest valid score for a wallet."""
    result = (
        anon_client.table("scores")
        .select("*")
        .eq("wallet_address", wallet_address)
        .gte("expires_at", datetime.now(timezone.utc).isoformat())
        .order("scored_at", desc=True)
        .limit(1)
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=404,
            detail="No score found. POST /score to request scoring.",
        )

    score = result.data[0]
    # Extract ENSIP-25 fields from raw_features if not already top-level
    raw = score.get("raw_features") or {}
    if isinstance(raw, dict):
        ensip25_raw = raw.get("ensip25") or {}
        if isinstance(ensip25_raw, dict):
            score.setdefault("ensip25_verified", ensip25_raw.get("ensip25_verified", False))
            score.setdefault("ens_name", ensip25_raw.get("ens_name"))
        else:
            score.setdefault("ensip25_verified", raw.get("ensip25_verified", False))
            score.setdefault("ens_name", raw.get("ens_name"))

    return ScoreResponse(**score)


@router.get("/{wallet_address}/history")
async def get_score_history(wallet_address: str):
    """Get all scores for a wallet, ordered by most recent."""
    result = (
        anon_client.table("scores")
        .select("*")
        .eq("wallet_address", wallet_address)
        .order("scored_at", desc=True)
        .execute()
    )

    return {"wallet_address": wallet_address, "scores": result.data or []}


@router.post("/sync", response_model=ScoreResponse)
async def score_sync(
    body: ScoreRequest,
    x_service_key: Optional[str] = Header(None),
):
    """Synchronous scoring — admin/demo use only. Requires X-Service-Key."""
    settings = get_settings()
    if x_service_key != settings.SUPABASE_SERVICE_KEY:
        raise HTTPException(status_code=403, detail="Invalid service key")

    from app.pipeline.graph import run_scoring_pipeline

    # Create a score request record
    req_result = service_client.table("score_requests").insert({
        "wallet_address": body.wallet_address,
        "requested_by": "sync-api",
        "priority": 1,
        "status": "processing",
    }).execute()

    request_id = req_result.data[0]["id"] if req_result.data else "sync"

    # Run pipeline synchronously
    result = await run_scoring_pipeline(body.wallet_address, request_id, agent_id=body.agent_id or "0")

    # Fetch the saved score
    score_id = result.get("score_id")
    if score_id:
        score_result = anon_client.table("scores").select("*").eq("id", score_id).execute()
        if score_result.data:
            # Update request status
            service_client.table("score_requests").update({
                "status": "complete",
                "result_score_id": score_id,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", request_id).execute()

            return ScoreResponse(**score_result.data[0])

    raise HTTPException(status_code=500, detail="Scoring pipeline failed")
