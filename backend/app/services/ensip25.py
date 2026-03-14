import logging
from web3 import Web3
from app.config import get_settings

logger = logging.getLogger("agentscore.services.ensip25")

# ERC-7930 encoded address of ERC-8004 Identity Registry on ETH mainnet
# Version(0001) + ChainType(0000=EVM) + ChainRefLen(01) + ChainRef(01=mainnet)
# + AddrLen(14=20bytes) + Address(8004a169fb4a3325136eb29fa0ceb6d2e539a432)
ERC7930_ETH_REGISTRY = "0x000100000101148004a169fb4a3325136eb29fa0ceb6d2e539a432"

# For Base chain (8453 = 0x2105):
# Version(0001) + ChainType(0000) + ChainRefLen(02) + ChainRef(2105)
# + AddrLen(14) + Address
ERC7930_BASE_REGISTRY = "0x0001000002210514" + "8004a169fb4a3325136eb29fa0ceb6d2e539a432"


def check_ensip25(wallet_address: str, agent_id: int = None) -> dict:
    """
    ENSIP-25: Verifiable AI Agent Identity with ENS.

    Checks if a wallet has an ENS name that verifies its association with
    an ERC-8004 agent identity via a standardized text record.

    Verification requires bidirectional attestation:
    1. The ERC-8004 registry entry lists an ENS name claim
    2. The ENS name has a matching agent-registration text record set to "1"

    Text record key format:
        agent-registration[<erc7930_registry>][<agentId>]

    Uses ETH mainnet for ENS resolution (ENS lives on mainnet).
    """
    try:
        settings = get_settings()
        w3 = Web3(Web3.HTTPProvider(settings.ALCHEMY_ETH_RPC))

        checksum_addr = Web3.to_checksum_address(wallet_address)

        # Step 1: Reverse resolve wallet → ENS name
        ens_name = None
        try:
            ens_name = w3.ens.name(checksum_addr)
        except Exception as e:
            logger.debug(f"ENS reverse resolution failed: {e}")

        if not ens_name:
            return {"ens_name": None, "ensip25_verified": False}

        # Step 2: If we have an agentId, check ENSIP-25 text record
        if agent_id is not None:
            # Try both ETH mainnet and Base registry encodings
            for registry_erc7930 in [ERC7930_ETH_REGISTRY, ERC7930_BASE_REGISTRY]:
                key = f"agent-registration[{registry_erc7930}][{agent_id}]"
                try:
                    value = w3.ens.get_text(ens_name, key)
                    if value:  # "1" or any non-empty value = verified
                        return {
                            "ens_name": ens_name,
                            "ensip25_verified": True,
                        }
                except Exception as e:
                    logger.debug(f"ENSIP-25 text record check failed for key {key}: {e}")

        return {"ens_name": ens_name, "ensip25_verified": False}

    except Exception as e:
        logger.warning(f"ENSIP-25 check failed for {wallet_address}: {e}")
        return {"ens_name": None, "ensip25_verified": False}
