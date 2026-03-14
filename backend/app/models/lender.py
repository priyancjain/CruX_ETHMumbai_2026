from pydantic import BaseModel
from typing import Optional

class LoanEligibilityRequest(BaseModel):
    wallet_address: str
    requested_amount: float
    token: str = "USDC"

class LoanEligibilityResponse(BaseModel):
    wallet_address: str
    eligible: bool
    score: int
    tier: str
    max_loan_amount: float
    interest_rate_bps: int
    ltv_bps: int
    reason: str

class LoanRequest(BaseModel):
    wallet_address: str
    amount: float
    duration_days: int
    token: str = "USDC"

class LoanResponse(BaseModel):
    loan_id: str
    wallet_address: str
    amount: float
    interest_rate_bps: int
    status: str
    approved: bool
    message: str
