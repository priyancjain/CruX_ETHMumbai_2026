import logging
from web3 import Web3
from app.config import get_settings

logger = logging.getLogger("agentscore.crawlers.elizaos")

# ERC-8004 Identity Registry (ERC-721 based) — same address on all chains
IDENTITY_REGISTRY = "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"

# ERC-8004 Reputation Registry
REPUTATION_REGISTRY = "0x8004BAa17C55a88189AE136b182e5fdA19dE9b63"

# ERC-721 ABI for agent lookup
ERC721_ABI = [
    {
        "inputs": [{"name": "owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "index", "type": "uint256"},
        ],
        "name": "tokenOfOwnerByIndex",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]

# Reputation Registry ABI
REPUTATION_ABI = [
    {
        "inputs": [
            {"name": "agentId", "type": "uint256"},
            {"name": "trustedClients", "type": "address[]"},
            {"name": "tag1", "type": "string"},
            {"name": "tag2", "type": "string"},
        ],
        "name": "getSummary",
        "outputs": [
            {"name": "count", "type": "uint64"},
            {"name": "value", "type": "int128"},
            {"name": "decimals", "type": "uint8"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
]


async def fetch_agent(wallet_address: str) -> dict:
    """
    Check if wallet owns an ERC-8004 agent identity NFT.
    Queries Identity Registry (ERC-721) and Reputation Registry.
    Checks both ETH mainnet and Base chain.
    """
    try:
        settings = get_settings()
        
        if not wallet_address.lower().startswith("0x"):
            logger.info(f"[ERC-8004] Skipped — {wallet_address} is not an EVM address")
            return {"found": False}
            
        checksum_addr = Web3.to_checksum_address(wallet_address)

        # Try ETH mainnet first, then Base
        for rpc_url, chain_name in [
            (settings.ALCHEMY_ETH_RPC, "ethereum"),
            (settings.ALCHEMY_BASE_RPC, "base"),
        ]:
            result = _check_chain(rpc_url, checksum_addr, chain_name)
            if result["found"]:
                return result

        logger.info(f"[ERC-8004] Agent NOT found for {wallet_address} on any chain")
        return {"found": False}
    except Exception as e:
        logger.error(f"[ERC-8004] Crawler FAILED for {wallet_address}: {e}")
        return {"found": False}


def _check_chain(rpc_url: str, wallet: str, chain_name: str) -> dict:
    """Check a single chain for ERC-8004 agent registration."""
    try:
        w3 = Web3(Web3.HTTPProvider(rpc_url))

        identity = w3.eth.contract(
            address=Web3.to_checksum_address(IDENTITY_REGISTRY),
            abi=ERC721_ABI,
        )

        # Check if wallet owns any agent NFTs
        balance = identity.functions.balanceOf(wallet).call()
        if balance == 0:
            return {"found": False}

        # Get the first agent ID (tokenId)
        agent_id = identity.functions.tokenOfOwnerByIndex(wallet, 0).call()

        # Query reputation
        reputation_score = 0.0
        feedback_count = 0
        try:
            reputation = w3.eth.contract(
                address=Web3.to_checksum_address(REPUTATION_REGISTRY),
                abi=REPUTATION_ABI,
            )
            count, value, decimals = reputation.functions.getSummary(
                agent_id, [], "uptime", "30days"
            ).call()
            feedback_count = count
            if decimals > 0:
                reputation_score = value / (10**decimals)
            else:
                reputation_score = float(value)
        except Exception as e:
            logger.debug(f"Reputation query failed for agent {agent_id}: {e}")

        result = {
            "found": True,
            "agent_id": agent_id,
            "reputation_score": reputation_score,
            "feedback_count": feedback_count,
            "agent_count": balance,
            "chain": chain_name,
            "is_active": True,
        }
        logger.info(
            f"[ERC-8004] FOUND agent on {chain_name}:\n"
            f"           agent_id         = {agent_id}\n"
            f"           reputation_score = {reputation_score}\n"
            f"           feedback_count   = {feedback_count}\n"
            f"           agent_count      = {balance}"
        )
        return result
    except Exception as e:
        logger.debug(f"[ERC-8004] Not found on {chain_name}: {e}")
        return {"found": False}
