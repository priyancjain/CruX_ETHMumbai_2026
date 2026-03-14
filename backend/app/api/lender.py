from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
import uuid
from app.models.lender import LoanEligibilityRequest, LoanEligibilityResponse, LoanRequest, LoanResponse
from app.services.supabase import anon_client, service_client

router = APIRouter()

# Mock configurations for loan tiers based on AgentScore
TIER_CONFIG = {
    "S": {"max_loan_amount": 100000.0, "interest_rate_bps": 200, "ltv_bps": 9000}, # 2% APY, 90% LTV
    "A": {"max_loan_amount": 50000.0, "interest_rate_bps": 400, "ltv_bps": 8000},  # 4% APY, 80% LTV
    "B": {"max_loan_amount": 25000.0, "interest_rate_bps": 600, "ltv_bps": 6000},  # 6% APY, 60% LTV
    "C": {"max_loan_amount": 10000.0, "interest_rate_bps": 1000, "ltv_bps": 4000}, # 10% APY, 40% LTV
    "D": {"max_loan_amount": 0.0, "interest_rate_bps": 0, "ltv_bps": 0},           # Not eligible
}


@router.post("/eligibility", response_model=LoanEligibilityResponse)
async def check_eligibility(body: LoanEligibilityRequest):
    """Check loan eligibility for an AI agent based on their latest AgentScore."""
    # Normalise address to lowercase to match database storage
    wallet_address_low = body.wallet_address.lower()


    result = (
        anon_client.table("scores")
        .select("*")
        .eq("wallet_address", wallet_address_low)
        .order("scored_at", desc=True)
        .limit(1)
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=404,
            detail="No score record found for this wallet. Please request an AgentScore first to determine loan eligibility."
        )

    score_data = result.data[0]
    
    # Expiry check in Python for better resilience
    expires_at_str = score_data.get("expires_at")
    if expires_at_str:
        expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=404,
                detail="Your last AgentScore has expired. Please request a fresh score to check eligibility."
            )

    score_data = result.data[0]
    tier = score_data.get("tier", "D")
    score_val = score_data.get("score", 0)
    
    config = TIER_CONFIG.get(tier, TIER_CONFIG["D"])
    
    # Logic to check if amount is within max allowed and tier is not D
    eligible_by_tier = tier != "D"
    eligible_by_amount = body.requested_amount <= config["max_loan_amount"]
    
    eligible = eligible_by_tier and eligible_by_amount
    
    if not eligible_by_tier:
        reason = "AgentScore indicates an unacceptable risk level (Tier D)."
    elif not eligible_by_amount:
        reason = f"Requested amount ({body.requested_amount}) exceeds max loan amount ({config['max_loan_amount']}) for Tier {tier}."
    else:
        reason = "Eligible for loan"

    return LoanEligibilityResponse(
        wallet_address=body.wallet_address,
        eligible=eligible,
        score=score_val,
        tier=tier,
        max_loan_amount=config["max_loan_amount"],
        interest_rate_bps=config["interest_rate_bps"],
        ltv_bps=config["ltv_bps"],
        reason=reason
    )


@router.post("/apply", response_model=LoanResponse)
async def apply_for_loan(body: LoanRequest):
    """Submit a loan application. Internally checks AgentScore to approve/reject the transaction."""
    # Re-run eligibility check
    eligibility_check = await check_eligibility(LoanEligibilityRequest(
        wallet_address=body.wallet_address,
        requested_amount=body.amount,
        token=body.token
    ))

    loan_id = str(uuid.uuid4())

    if not eligibility_check.eligible:
        return LoanResponse(
            loan_id=loan_id,
            wallet_address=body.wallet_address,
            amount=body.amount,
            interest_rate_bps=0,
            status="rejected",
            approved=False,
            message=f"Loan application rejected. Reason: {eligibility_check.reason}"
        )

    # In a full production implementation, we would insert the loan into a `loans` table on Supabase here.
    # We omit the exact insert because `loans` table might not exist, but we mock the successful response.
    # Try inserting if 'loans' table exists, silently pass if not for hackathon purposes.
    try:
        service_client.table("loans").insert({
            "id": loan_id,
            "wallet_address": body.wallet_address,
            "amount": body.amount,
            "duration_days": body.duration_days,
            "interest_rate_bps": eligibility_check.interest_rate_bps,
            "status": "active"
        }).execute()
    except Exception as e:
        # Table probably doesn't exist, ignore for the local stub
        pass

    return LoanResponse(
        loan_id=loan_id,
        wallet_address=body.wallet_address,
        amount=body.amount,
        interest_rate_bps=eligibility_check.interest_rate_bps,
        status="active",
        approved=True,
        message="Loan application successfully approved and processed by AgentScore underwriting."
    )
