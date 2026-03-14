import logging
from web3 import Web3
from ens import ENS
from app.config import get_settings
from app.crawlers import http_client

logger = logging.getLogger("agentscore.services.ensip25")

# ENS Reverse Registrar (ETH mainnet)
REVERSE_REGISTRAR = "0xa58E81fe9b61B5c3fE2AFD33CF304c454AbFc7Cb"

# ENS Public Resolver 2 (ETH mainnet)
PUBLIC_RESOLVER = "0x4976fb03C32e5B8cfe2b6cCB31c09Ba78EBaBa41"

# ERC-7930 encoded address of ERC-8004 Identity Registry on ETH mainnet
# Version(0001) + ChainType(0000=EVM) + ChainRefLen(01) + ChainRef(01=mainnet)
# + AddrLen(14=20bytes) + Address(8004a169fb4a3325136eb29fa0ceb6d2e539a432)
ERC7930_ETH_REGISTRY = "0x000100000101148004a169fb4a3325136eb29fa0ceb6d2e539a432"

# For Base chain (8453 = 0x2105):
ERC7930_BASE_REGISTRY = "0x0001000002210514" + "8004a169fb4a3325136eb29fa0ceb6d2e539a432"


async def check_ensip25(wallet_address: str, agent_id=None) -> dict:
    """
    ENSIP-25: Verifiable AI Agent Identity with ENS.

    1. Reverse resolve wallet → ENS name via Alchemy ETH mainnet RPC
    2. If ENS name found + agent_id available, check ENSIP-25 text record

    Uses direct JSON-RPC calls via httpx for reliability (avoids web3.py
    ENS module issues with certain providers).
    """
    settings = get_settings()

    try:
        checksum_addr = Web3.to_checksum_address(wallet_address)

        # Step 1: Reverse resolve wallet → ENS name
        ens_name = await _reverse_resolve(checksum_addr, settings.ALCHEMY_ETH_RPC)

        if not ens_name:
            logger.info(f"[ENSIP-25] No ENS name for {wallet_address} (most agent wallets don't have one)")
            return {"ens_name": None, "ensip25_verified": False}

        logger.info(f"[ENSIP-25] ENS name found: {ens_name} for {wallet_address}")

        # Step 2: Verify forward resolution matches (ENS name → wallet)
        forward_addr = await _forward_resolve(ens_name, settings.ALCHEMY_ETH_RPC)
        if forward_addr and forward_addr.lower() != checksum_addr.lower():
            logger.warning(
                f"[ENSIP-25] Forward resolution mismatch: {ens_name} → {forward_addr} "
                f"(expected {checksum_addr}). Treating as unverified."
            )
            return {"ens_name": ens_name, "ensip25_verified": False}

        # Step 3: Check ENSIP-25 text record if we have an agent_id
        if agent_id is not None:
            for registry_erc7930 in [ERC7930_ETH_REGISTRY, ERC7930_BASE_REGISTRY]:
                key = f"agent-registration[{registry_erc7930}][{agent_id}]"
                value = await _get_text_record(ens_name, key, settings.ALCHEMY_ETH_RPC)
                if value:
                    logger.info(f"[ENSIP-25] VERIFIED! {ens_name} has text record '{key}' = '{value}'")
                    return {"ens_name": ens_name, "ensip25_verified": True}

            logger.info(
                f"[ENSIP-25] ENS name {ens_name} found but no agent-registration text record "
                f"(agent_id={agent_id}). This is normal — ENSIP-25 text records are optional."
            )
        else:
            logger.info(f"[ENSIP-25] No agent_id available to check text records for {ens_name}")

        return {"ens_name": ens_name, "ensip25_verified": False}

    except Exception as e:
        logger.warning(f"[ENSIP-25] Check failed for {wallet_address}: {e}")
        return {"ens_name": None, "ensip25_verified": False}


async def _reverse_resolve(address: str, rpc_url: str) -> str | None:
    """Reverse resolve an address to ENS name using eth_call to the reverse registrar."""
    try:
        # Build the reverse node: <addr>.addr.reverse
        addr_lower = address.lower().replace("0x", "")
        reverse_name = f"{addr_lower}.addr.reverse"
        node = ENS.namehash(reverse_name)

        # Call the reverse registrar's name(bytes32) function
        # Function selector for name(bytes32): 0x691f3431
        data = "0x691f3431" + node.hex().replace("0x", "").zfill(64)

        async with http_client(timeout=15) as client:
            resp = await client.post(
                rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "eth_call",
                    "params": [{"to": REVERSE_REGISTRAR, "data": data}, "latest"],
                },
            )
            result = resp.json()

        hex_result = result.get("result", "0x")
        if not hex_result or hex_result == "0x" or len(hex_result) <= 66:
            return None

        # Decode ABI-encoded string response
        return _decode_abi_string(hex_result)

    except Exception as e:
        logger.debug(f"[ENSIP-25] Reverse resolution RPC failed: {e}")
        # Fallback: try web3.py ENS module
        return _reverse_resolve_web3(address, rpc_url)


def _reverse_resolve_web3(address: str, rpc_url: str) -> str | None:
    """Fallback: use web3.py ENS module for reverse resolution."""
    try:
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        return w3.ens.name(address)
    except Exception as e:
        logger.debug(f"[ENSIP-25] web3.py ENS fallback also failed: {e}")
        return None


async def _forward_resolve(ens_name: str, rpc_url: str) -> str | None:
    """Forward resolve ENS name → address using eth_call."""
    try:
        node = ENS.namehash(ens_name)

        # addr(bytes32) selector: 0x3b3b57de
        data = "0x3b3b57de" + node.hex().replace("0x", "").zfill(64)

        async with http_client(timeout=15) as client:
            resp = await client.post(
                rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "eth_call",
                    "params": [{"to": PUBLIC_RESOLVER, "data": data}, "latest"],
                },
            )
            result = resp.json()

        hex_result = result.get("result", "0x")
        if not hex_result or hex_result == "0x" or len(hex_result) < 66:
            return None

        # Last 20 bytes of the 32-byte response
        addr_hex = "0x" + hex_result[-40:]
        return Web3.to_checksum_address(addr_hex)

    except Exception as e:
        logger.debug(f"[ENSIP-25] Forward resolution failed for {ens_name}: {e}")
        return None


async def _get_text_record(ens_name: str, key: str, rpc_url: str) -> str | None:
    """Read an ENS text record using eth_call to the public resolver."""
    try:
        node = ENS.namehash(ens_name)

        # text(bytes32,string) selector: 0x59d1d43c
        # ABI encode: node (bytes32) + offset to string + string length + string data
        key_bytes = key.encode("utf-8")
        key_len = len(key_bytes)
        key_hex = key_bytes.hex()
        # Pad key to 32-byte boundary
        key_padded = key_hex + "0" * (64 - len(key_hex) % 64) if len(key_hex) % 64 != 0 else key_hex

        data = (
            "0x59d1d43c"
            + node.hex().replace("0x", "").zfill(64)        # bytes32 node
            + "0000000000000000000000000000000000000000000000000000000000000040"  # offset to string
            + hex(key_len)[2:].zfill(64)                    # string length
            + key_padded                                     # string data
        )

        async with http_client(timeout=15) as client:
            resp = await client.post(
                rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "eth_call",
                    "params": [{"to": PUBLIC_RESOLVER, "data": data}, "latest"],
                },
            )
            result = resp.json()

        hex_result = result.get("result", "0x")
        if not hex_result or hex_result == "0x" or len(hex_result) <= 66:
            return None

        return _decode_abi_string(hex_result)

    except Exception as e:
        logger.debug(f"[ENSIP-25] Text record read failed for {ens_name}/{key}: {e}")
        return None


def _decode_abi_string(hex_data: str) -> str | None:
    """Decode an ABI-encoded string from hex response data."""
    try:
        # Remove 0x prefix
        data = hex_data.replace("0x", "")

        if len(data) < 128:  # Need at least offset + length
            return None

        # First 32 bytes = offset to string data
        offset = int(data[:64], 16) * 2  # offset in hex chars

        # At offset: 32 bytes = string length
        str_len = int(data[offset:offset + 64], 16)

        if str_len == 0:
            return None

        # After length: the actual string bytes
        str_hex = data[offset + 64:offset + 64 + str_len * 2]
        return bytes.fromhex(str_hex).decode("utf-8")

    except Exception:
        return None
