"""
Background worker that polls score_requests and runs the scoring pipeline.
Run with: python worker.py
"""
import asyncio
import logging
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-35s │ %(message)s",
    datefmt="%H:%M:%S",
)
# Reduce noise from httpx/httpcore
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
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
        return False

    request = result.data[0]
    request_id = request["id"]
    wallet = request["wallet_address"]
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
        result = await run_scoring_pipeline(wallet, request_id)
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


async def main():
    logger.info("AgentScore Worker started. Polling for score requests...")

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
