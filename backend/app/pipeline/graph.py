import logging
from langgraph.graph import StateGraph, START, END
from app.pipeline.state import AgentScoreState
from app.pipeline.nodes import (
    fetch_platforms,
    fetch_onchain,
    fetch_erc8004,
    fetch_ens_ensip25,
    node_aggregate_features,
    run_anomaly,
    run_gpt_o3,
    save_score,
    anchor_onchain,
)

logger = logging.getLogger("agentscore.pipeline.graph")


def build_graph() -> StateGraph:
    """Build the 9-node LangGraph scoring pipeline."""
    graph = StateGraph(AgentScoreState)

    # Add all 9 nodes
    graph.add_node("fetch_platforms", fetch_platforms)
    graph.add_node("fetch_onchain", fetch_onchain)
    graph.add_node("fetch_erc8004", fetch_erc8004)
    graph.add_node("fetch_ens_ensip25", fetch_ens_ensip25)
    graph.add_node("aggregate_features", node_aggregate_features)
    graph.add_node("run_anomaly", run_anomaly)
    graph.add_node("run_gpt_o3", run_gpt_o3)
    graph.add_node("save_score", save_score)
    graph.add_node("anchor_onchain", anchor_onchain)

    # Linear edges — ERC-8004 before ENS so agentId is available
    graph.add_edge(START, "fetch_platforms")
    graph.add_edge("fetch_platforms", "fetch_onchain")
    graph.add_edge("fetch_onchain", "fetch_erc8004")
    graph.add_edge("fetch_erc8004", "fetch_ens_ensip25")
    graph.add_edge("fetch_ens_ensip25", "aggregate_features")
    graph.add_edge("aggregate_features", "run_anomaly")
    graph.add_edge("run_anomaly", "run_gpt_o3")
    graph.add_edge("run_gpt_o3", "save_score")
    graph.add_edge("save_score", "anchor_onchain")
    graph.add_edge("anchor_onchain", END)

    return graph


# Compile the graph
scoring_pipeline = build_graph().compile()


async def run_scoring_pipeline(wallet_address: str, request_id: str) -> dict:
    """Run the full scoring pipeline for a wallet address."""
    logger.info(f"\n{'#'*60}")
    logger.info(f"  AGENTSCORE PIPELINE START")
    logger.info(f"  Wallet:  {wallet_address}")
    logger.info(f"  Request: {request_id}")
    logger.info(f"{'#'*60}")

    initial_state: AgentScoreState = {
        "wallet_address": wallet_address,
        "request_id": request_id,
        "virtuals_data": {},
        "elizaos_data": {},
        "olas_data": {},
        "fetch_data": {},
        "erc8004_data": {},
        "onchain_data": {},
        "ens_data": {},
        "heyelsa_data": {},
        "features": {},
        "anomaly_result": {},
        "gpt_response": {},
        "score_id": "",
        "error": "",
    }

    result = await scoring_pipeline.ainvoke(initial_state)

    gpt = result.get("gpt_response", {})
    logger.info(f"\n{'#'*60}")
    logger.info(f"  PIPELINE COMPLETE")
    logger.info(f"  Wallet:     {wallet_address}")
    logger.info(f"  Score:      {gpt.get('score')} / 1000")
    logger.info(f"  Tier:       {gpt.get('tier')}")
    logger.info(f"  Collateral: {gpt.get('collateral_requirement')}%")
    logger.info(f"  Max Loan:   ${gpt.get('max_loan_usdc', 0):,.0f} USDC")
    logger.info(f"  Score ID:   {result.get('score_id')}")
    logger.info(f"{'#'*60}")

    return dict(result)
