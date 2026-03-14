"""
Background worker that polls score_requests and runs the scoring pipeline.
Run with: python worker.py
"""
import asyncio
import logging
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s │ %(name)-35s │ %(message)s",
    datefmt="%H:%M:%S",
)
# Reduce noise from non-worker loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("hpack").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("supabase").setLevel(logging.INFO)
logging.getLogger("postgrest").setLevel(logging.WARNING)
logging.getLogger("gotrue").setLevel(logging.WARNING)
logging.getLogger("realtime").setLevel(logging.WARNING)
logging.getLogger("storage3").setLevel(logging.WARNING)
logger = logging.getLogger("agentscore.worker")

MAX_ATTEMPTS = 3
POLL_INTERVAL = 2  # seconds


async def process_next_request():
    """Poll for next pending request and process it."""
    from app.services.supabase import service_client
    from app.pipeline.graph import run_scoring_pipeline

    # Fetch next pending request (lowest priority number = highest priority)
    result = (
        service_client.table("score_requests")
        .select("*")
        .eq("status", "pending")
        .order("priority", desc=False)
        .order("created_at", desc=False)
        .limit(1)
        .execute()
    )

    if not result.data:
        # Debug: check if there are ANY requests at all
        all_requests = service_client.table("score_requests").select("id, status, wallet_address, created_at").order("created_at", desc=True).limit(5).execute()
        if all_requests.data:
            statuses = [f"{r['status']}({r['wallet_address'][:10]}...)" for r in all_requests.data]
            logger.debug(f"No pending requests. Recent requests: {', '.join(statuses)}")
        return False

    request = result.data[0]
    request_id = request["id"]
    wallet = request["wallet_address"]
    agent_id = request.get("agent_id") or "0"
    attempts = request.get("attempts", 0)

    logger.info(f"Processing request {request_id} for wallet {wallet} (attempt {attempts + 1})")

    # Mark as processing
    service_client.table("score_requests").update({
        "status": "processing",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "attempts": attempts + 1,
    }).eq("id", request_id).execute()

    try:
        # Run scoring pipeline
        result = await run_scoring_pipeline(wallet, request_id, agent_id=agent_id)
        score_id = result.get("score_id")

        if score_id:
            # Success
            service_client.table("score_requests").update({
                "status": "complete",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "result_score_id": score_id,
            }).eq("id", request_id).execute()

            logger.info(f"Request {request_id} completed. Score ID: {score_id}")
        else:
            raise Exception("Pipeline returned no score_id")

    except Exception as e:
        logger.error(f"Request {request_id} failed: {e}")

        new_attempts = attempts + 1
        if new_attempts < MAX_ATTEMPTS:
            # Retry
            service_client.table("score_requests").update({
                "status": "pending",
                "error_message": str(e),
            }).eq("id", request_id).execute()
            logger.info(f"Request {request_id} will be retried (attempt {new_attempts}/{MAX_ATTEMPTS})")
        else:
            # Final failure
            service_client.table("score_requests").update({
                "status": "failed",
                "error_message": str(e),
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", request_id).execute()
            logger.error(f"Request {request_id} permanently failed after {MAX_ATTEMPTS} attempts")

    return True


async def recover_stale_requests():
    """Reset any requests stuck in 'processing' (e.g. from a previous crash) back to 'pending'."""
    from app.services.supabase import service_client
    from datetime import timedelta

    stale_cutoff = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    stale = (
        service_client.table("score_requests")
        .select("id")
        .eq("status", "processing")
        .lt("started_at", stale_cutoff)
        .execute()
    )
    if stale.data:
        for s in stale.data:
            service_client.table("score_requests").update({
                "status": "pending",
                "error_message": "Recovered from stale processing state",
            }).eq("id", s["id"]).execute()
        logger.info(f"Recovered {len(stale.data)} stale processing requests back to pending")


async def main():
    logger.info("AgentScore Worker started. Polling for score requests...")

    # On startup, recover any requests stuck in 'processing' from a previous crash
    try:
        await recover_stale_requests()
    except Exception as e:
        logger.warning(f"Could not recover stale requests: {e}")

    while True:
        try:
            processed = await process_next_request()
            if not processed:
                await asyncio.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            logger.info("Worker stopped.")
            break
        except Exception as e:
            logger.error(f"Worker error: {e}")
            await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
