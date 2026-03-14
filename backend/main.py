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
    yield
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
