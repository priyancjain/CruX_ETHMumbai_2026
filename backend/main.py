import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, score, agents, leaderboard, platforms, discover, enrichment, lender

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-35s │ %(message)s",
    datefmt="%H:%M:%S",
)
# Reduce noise from httpx/httpcore
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger("agentscore")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AgentScore API ready")

    # Embedded worker — runs the scoring pipeline in the same process
    # (needed for Render free tier which has no background worker support)
    # Uses asyncio.to_thread for blocking calls so API stays responsive
    async def worker_loop():
        from worker import process_next_request, recover_stale_requests

        logger.info("Embedded worker started. Polling for score requests...")
        try:
            await recover_stale_requests()
        except Exception as e:
            logger.warning(f"Could not recover stale requests: {e}")
        while True:
            try:
                processed = await process_next_request()
                if not processed:
                    await asyncio.sleep(2)
            except asyncio.CancelledError:
                logger.info("Worker loop cancelled")
                break
            except Exception as e:
                logger.error(f"Worker error: {e}")
                await asyncio.sleep(2)

    worker_task = asyncio.create_task(worker_loop())
    yield
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass
    logger.info("AgentScore API shutting down")


app = FastAPI(
    title="AgentScore API",
    description="Universal Credit Scoring for AI Agents",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow all origins for hackathon
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router, tags=["Health"])
app.include_router(score.router, prefix="/score", tags=["Score"])
app.include_router(agents.router, prefix="/agents", tags=["Agents"])
app.include_router(leaderboard.router, tags=["Leaderboard"])
app.include_router(platforms.router, prefix="/platforms", tags=["Platforms"])
app.include_router(discover.router, tags=["Discovery"])
app.include_router(enrichment.router, prefix="/enrichment", tags=["Enrichment"])
app.include_router(lender.router, prefix="/lender", tags=["Lender"])
