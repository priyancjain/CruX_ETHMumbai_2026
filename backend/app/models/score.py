from pydantic import BaseModel, field_validator
from typing import Optional
from web3 import Web3


class ScoreRequest(BaseModel):
    wallet_address: str
    agent_id: Optional[str] = None  # ENSIP-25: agent's registry ID (default "0")
    requested_by: Optional[str] = None
    priority: int = 5

    @field_validator("wallet_address")
    @classmethod
    def validate_wallet(cls, v: str) -> str:
        if not v or len(v) < 30:
            raise ValueError("Invalid address format")
        
        # EVM addresses
        if v.startswith("0x"):
            if len(v) != 42:
                raise ValueError("Invalid EVM address format")
            try:
                return Web3.to_checksum_address(v)
            except Exception:
                raise ValueError("Invalid EVM address checksum")
                
        # Cosmos/Fetch.ai or other non-EVM addresses
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: int) -> int:
        return max(1, min(10, v))


class ScoreResponse(BaseModel):
    id: str
    wallet_address: str
    score: int
    tier: str
    collateral_requirement: int
    max_loan_usdc: float
    rationale: str
    key_factors: list = []
    risk_flags: list = []
    model_used: str = "o3"
    anomaly_score: Optional[float] = None
    is_anomaly: bool = False
    ensip25_verified: bool = False
    ens_name: Optional[str] = None
    onchain_tx_hash: Optional[str] = None
    scored_at: Optional[str] = None
    expires_at: Optional[str] = None
    cached: bool = False


class ScoreQueuedResponse(BaseModel):
    request_id: str
    status: str = "queued"
    message: str = "Scoring in progress"
