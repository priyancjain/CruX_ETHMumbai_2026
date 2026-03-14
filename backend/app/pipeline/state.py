from typing import TypedDict


class AgentScoreState(TypedDict, total=False):
    # Input
    wallet_address: str
    request_id: str
    agent_id: str  # ENSIP-25: agent's registry ID (default "0")

    # Raw platform data
    virtuals_data: dict
    elizaos_data: dict
    olas_data: dict
    fetch_data: dict
    erc8004_data: dict

    # Onchain data
    onchain_data: dict
    ens_data: dict
    heyelsa_data: dict

    # Computed
    features: dict  # The 22-signal feature vector
    anomaly_result: dict  # { score: float, is_anomaly: bool }

    # GPT-o3 output
    gpt_response: dict  # { score, tier, collateral_requirement, max_loan_usdc, rationale, key_factors, risk_flags }

    # Final
    score_id: str
    error: str
