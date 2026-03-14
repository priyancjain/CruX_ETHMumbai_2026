from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AgentResponse(BaseModel):
    id: str
    wallet_address: str
    ens_name: Optional[str] = None
    platform: str
    platform_agent_id: str
    agent_name: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    # Joined score data
    score: Optional[int] = None
    tier: Optional[str] = None


class AgentDetailResponse(AgentResponse):
    metadata: Optional[dict] = None
    features: Optional[dict] = None
    latest_score: Optional[dict] = None
