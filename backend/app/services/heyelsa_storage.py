import logging
from app.services.supabase import service_client

logger = logging.getLogger("agentscore.services.heyelsa_storage")


def store_transactions(agent_id: str, wallet_address: str, heyelsa_data: dict) -> None:
    """Persist HeyElsa transaction history to agent_transactions table."""
    transactions = heyelsa_data.get("transaction_history", [])
    if not transactions:
        return

    try:
        rows = []
        for tx in transactions:
            row = {
                "agent_id": agent_id,
                "wallet_address": wallet_address,
                "tx_hash": tx.get("hash") or tx.get("tx_hash") or tx.get("transactionHash", ""),
                "block_number": tx.get("block_number") or tx.get("blockNumber"),
                "chain": tx.get("chain") or tx.get("network") or "base",
                "from_address": tx.get("from") or tx.get("from_address"),
                "to_address": tx.get("to") or tx.get("to_address"),
                "value_raw": str(tx.get("value") or tx.get("value_raw") or "0"),
                "value_usd": float(tx.get("value_usd") or tx.get("valueUSD") or 0),
                "token_symbol": tx.get("token_symbol") or tx.get("symbol") or tx.get("asset"),
                "token_address": tx.get("token_address") or tx.get("contractAddress"),
                "tx_type": tx.get("type") or tx.get("tx_type") or tx.get("category"),
                "protocol_name": tx.get("protocol") or tx.get("protocol_name"),
                "gas_used": float(tx.get("gas_used") or tx.get("gasUsed") or 0),
                "tx_fee_usd": float(tx.get("tx_fee_usd") or tx.get("fee_usd") or 0),
                "is_incoming": tx.get("is_incoming", False),
                "timestamp": tx.get("timestamp") or tx.get("date") or tx.get("block_timestamp"),
                "raw_data": tx,
            }
            if row["tx_hash"] and row["timestamp"]:
                rows.append(row)

        if rows:
            # ON CONFLICT DO NOTHING — skip duplicates
            service_client.table("agent_transactions").upsert(
                rows, on_conflict="wallet_address,tx_hash", ignore_duplicates=True
            ).execute()
            logger.info(f"[HeyElsa Storage] Stored {len(rows)} transactions for {wallet_address}")
    except Exception as e:
        logger.warning(f"[HeyElsa Storage] Failed to store transactions: {e}")


def store_pnl(agent_id: str, wallet_address: str, heyelsa_data: dict) -> None:
    """Persist HeyElsa PnL report snapshot to agent_pnl table."""
    if not heyelsa_data.get("total_trades"):
        return

    try:
        row = {
            "agent_id": agent_id,
            "wallet_address": wallet_address,
            "total_pnl_usd": heyelsa_data.get("total_pnl_usd", 0),
            "realized_pnl_usd": heyelsa_data.get("realized_pnl_usd", 0),
            "unrealized_pnl_usd": heyelsa_data.get("unrealized_pnl_usd", 0),
            "win_rate": heyelsa_data.get("win_rate", 0),
            "total_trades": heyelsa_data.get("total_trades", 0),
            "profitable_trades": heyelsa_data.get("profitable_trades", 0),
            "avg_trade_size_usd": heyelsa_data.get("avg_trade_size_usd", 0),
            "largest_win_usd": heyelsa_data.get("largest_win_usd", 0),
            "largest_loss_usd": heyelsa_data.get("largest_loss_usd", 0),
            "tokens_traded": heyelsa_data.get("tokens_traded", []),
            "period_days": 90,
            "raw_data": heyelsa_data.get("pnl_report"),
        }
        service_client.table("agent_pnl").insert(row).execute()
        logger.info(f"[HeyElsa Storage] Stored PnL snapshot for {wallet_address}")
    except Exception as e:
        logger.warning(f"[HeyElsa Storage] Failed to store PnL: {e}")


def store_positions(agent_id: str, wallet_address: str, heyelsa_data: dict) -> None:
    """Persist HeyElsa token + DeFi positions to agent_positions table."""
    rows = []

    # Token positions from get_portfolio
    for token in heyelsa_data.get("token_positions", []):
        if isinstance(token, dict):
            rows.append({
                "agent_id": agent_id,
                "wallet_address": wallet_address,
                "position_type": "token",
                "token_symbol": token.get("symbol") or token.get("asset") or token.get("token_symbol"),
                "token_address": token.get("address") or token.get("token_address") or token.get("contractAddress"),
                "protocol_name": None,
                "chain": token.get("chain") or token.get("network") or "base",
                "balance_raw": str(token.get("balance") or token.get("amount") or "0"),
                "balance_usd": float(token.get("balance_usd") or token.get("value_usd") or token.get("balanceUSD") or 0),
                "apy": None,
                "raw_data": token,
            })

    # DeFi positions from get_portfolio
    for pos in heyelsa_data.get("defi_positions", []):
        if isinstance(pos, dict):
            rows.append({
                "agent_id": agent_id,
                "wallet_address": wallet_address,
                "position_type": "defi",
                "token_symbol": pos.get("symbol") or pos.get("token"),
                "token_address": pos.get("address") or pos.get("token_address"),
                "protocol_name": pos.get("protocol") or pos.get("protocol_name") or pos.get("platform"),
                "chain": pos.get("chain") or pos.get("network") or "base",
                "balance_raw": str(pos.get("balance") or pos.get("amount") or "0"),
                "balance_usd": float(pos.get("balance_usd") or pos.get("value_usd") or 0),
                "apy": float(pos.get("apy") or 0) if pos.get("apy") else None,
                "raw_data": pos,
            })

    # Staking positions
    for stake in heyelsa_data.get("staking_positions", []):
        if isinstance(stake, dict):
            rows.append({
                "agent_id": agent_id,
                "wallet_address": wallet_address,
                "position_type": "staking",
                "token_symbol": stake.get("symbol") or stake.get("token"),
                "token_address": stake.get("address") or stake.get("token_address"),
                "protocol_name": stake.get("protocol") or stake.get("validator"),
                "chain": stake.get("chain") or stake.get("network") or "base",
                "balance_raw": str(stake.get("balance") or stake.get("amount") or "0"),
                "balance_usd": float(stake.get("balance_usd") or stake.get("value_usd") or 0),
                "apy": float(stake.get("apy") or 0) if stake.get("apy") else None,
                "raw_data": stake,
            })

    if not rows:
        return

    try:
        service_client.table("agent_positions").insert(rows).execute()
        logger.info(f"[HeyElsa Storage] Stored {len(rows)} positions for {wallet_address}")
    except Exception as e:
        logger.warning(f"[HeyElsa Storage] Failed to store positions: {e}")
