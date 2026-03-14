from fastapi import APIRouter, HTTPException, Header
from datetime import datetime, timezone
from typing import Optional
from app.models.score import ScoreRequest, ScoreResponse, ScoreQueuedResponse
from app.services.supabase import anon_client, service_client
from app.config import get_settings

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
        return ScoreResponse(**score, cached=True)

    # Check for already pending/processing request for same wallet
    pending = (
        anon_client.table("score_requests")
        .select("id, status")
        .eq("wallet_address", wallet)
        .in_("status", ["pending", "processing"])
        .limit(1)
        .execute()
    )
    if pending.data:
        return ScoreQueuedResponse(
            request_id=pending.data[0]["id"],
            status="queued",
            message="Scoring already in progress for this wallet.",
        )

    # Queue scoring request
    result = service_client.table("score_requests").insert({
        "wallet_address": wallet,
        "requested_by": body.requested_by,
        "priority": body.priority,
        "status": "pending",
    }).execute()

    request_id = result.data[0]["id"] if result.data else "unknown"
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

    return ScoreResponse(**result.data[0])


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
    result = await run_scoring_pipeline(body.wallet_address, request_id)

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
