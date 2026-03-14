import logging
import httpx
from web3 import Web3
from app.config import get_settings
from app.crawlers import http_client

logger = logging.getLogger("agentscore.services.ensip25")

# ENS Registry (ETH mainnet) — source of truth for all resolver lookups
ENS_REGISTRY = "0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e"

# ERC-7930 encoded address of ERC-8004 Identity Registry
# 0x0001 = chain ID 1 (ETH mainnet), 0x01 = contract type, 14 = 20 bytes addr
ERC7930_REGISTRY = "0x000100000101148004a169fb4a3325136eb29fa0ceb6d2e539a432"


def _namehash(name: str) -> str:
    """
    EIP-137 namehash using keccak256 (NOT Python's sha3_256).
    Uses pycryptodome for correct Ethereum keccak.
    """
    from Crypto.Hash import keccak as _keccak

    def keccak256(data: bytes) -> bytes:
        k = _keccak.new(digest_bits=256)
        k.update(data)
        return k.digest()

    node = b"\x00" * 32
    if name:
        for label in reversed(name.split(".")):
            label_hash = keccak256(label.encode("utf-8"))
            node = keccak256(node + label_hash)
    return "0x" + node.hex()


async def check_ensip25(wallet_address: str, agent_id=None) -> dict:
    """
    ENSIP-25: Verifiable AI Agent Identity with ENS.

    3-step flow (all via eth_call on ETH mainnet — read-only, free, no gas):
      1. Reverse resolve wallet → ENS name (ENS Registry → resolver → name())
      2. Look up ENSIP-25 text record on the resolver
      3. Verify text value == "1"

    Text record key format:
      agent-registration[0x000100000101148004a169fb4a3325136eb29fa0ceb6d2e539a432][{agentId}]
    """
    settings = get_settings()
    rpc_url = settings.ALCHEMY_ETH_RPC

    try:
        checksum_addr = Web3.to_checksum_address(wallet_address)

        # Step 1: Reverse resolve wallet → ENS name
        ens_name = await _reverse_resolve(checksum_addr, rpc_url)

        if not ens_name:
            logger.info(f"[ENSIP-25] No ENS name for {wallet_address} (most agent wallets don't have one)")
            return {"ens_name": None, "ensip25_verified": False}

        logger.info(f"[ENSIP-25] ENS name found: {ens_name} for {wallet_address}")

        # Step 2: Check ENSIP-25 text record
        agent_id_str = str(agent_id) if agent_id is not None else "0"
        text_key = f"agent-registration[{ERC7930_REGISTRY}][{agent_id_str}]"

        text_value = await _get_text_record(ens_name, text_key, rpc_url)

        # Step 3: Verify — per ENSIP-25 spec, ANY non-empty value confirms the association
        ensip25_verified = bool(text_value)

        result = {
            "ens_name": ens_name,
            "ensip25_verified": ensip25_verified,
            "text_key": text_key,
            "text_value": text_value or "",
        }

        if ensip25_verified:
            logger.info(f"[ENSIP-25] VERIFIED! {ens_name} has '{text_key}' = '1' (+30 score bonus)")
        else:
            logger.info(
                f"[ENSIP-25] Not verified: {ens_name} text record '{text_key}' = '{text_value or ''}'. "
                f"This is normal — ENSIP-25 text records are optional."
            )

        return result

    except Exception as e:
        logger.warning(f"[ENSIP-25] Check failed for {wallet_address}: {e}")
        return {"ens_name": None, "ensip25_verified": False}


# ── Low-level RPC helpers ────────────────────────────────────────────────────


async def _rpc_call(client: httpx.AsyncClient, rpc_url: str, method: str, params: list) -> str | None:
    """Execute a JSON-RPC eth_call and return the result hex string."""
    resp = await client.post(
        rpc_url,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
    )
    data = resp.json()
    if "error" in data:
        logger.debug(f"[ENSIP-25] RPC error: {data['error']}")
        return None
    result = data.get("result", "0x")
    if not result or result == "0x":
        return None
    return result


async def _get_resolver(client: httpx.AsyncClient, rpc_url: str, node_hex: str) -> str | None:
    """
    Get the resolver address for a namehash node from ENS Registry.
    Calls: resolver(bytes32 node) selector 0x0178b8bf
    """
    node_padded = node_hex.replace("0x", "").zfill(64)
    call_data = "0x0178b8bf" + node_padded

    result = await _rpc_call(
        client, rpc_url, "eth_call",
        [{"to": ENS_REGISTRY, "data": call_data}, "latest"],
    )

    if not result or len(result) < 42:
        return None

    addr = "0x" + result[-40:]
    if int(addr, 16) == 0:
        return None
    return Web3.to_checksum_address(addr)


def _hex_to_int(hex_str: str) -> int:
    """Convert hex string to int, handling 0x prefix."""
    return int(hex_str.replace("0x", ""), 16)


# ── Step 1: Reverse resolve ─────────────────────────────────────────────────


async def _reverse_resolve(address: str, rpc_url: str) -> str | None:
    """
    Reverse resolve address → ENS name.
    1. Compute namehash of '{addr}.addr.reverse'
    2. Call resolver(bytes32) on ENS Registry → get resolver address
    3. Call name(bytes32) on the resolver → get ENS name string
    """
    try:
        addr_lower = address.lower().replace("0x", "")
        reverse_name = f"{addr_lower}.addr.reverse"
        reverse_node = _namehash(reverse_name)
        reverse_node_padded = reverse_node[2:].zfill(64)

        async with http_client(timeout=15) as client:
            # Get resolver for this reverse node from ENS Registry
            resolver_addr = await _get_resolver(client, rpc_url, reverse_node)

            if not resolver_addr:
                logger.debug(f"[ENSIP-25] No reverse resolver found, trying web3.py fallback")
                return _reverse_resolve_web3_fallback(address, rpc_url)

            # Call name(bytes32 node) on the resolver — selector 0x691f3431
            name_call = "0x691f3431" + reverse_node_padded
            name_hex = await _rpc_call(
                client, rpc_url, "eth_call",
                [{"to": resolver_addr, "data": name_call}, "latest"],
            )

            if not name_hex or len(name_hex) <= 130:
                logger.debug(f"[ENSIP-25] name() returned empty, trying web3.py fallback")
                return _reverse_resolve_web3_fallback(address, rpc_url)

            # Decode ABI-encoded string: offset (32 bytes) + length (32 bytes) + data
            length = _hex_to_int(name_hex[66:130])
            if length == 0:
                return _reverse_resolve_web3_fallback(address, rpc_url)

            name_bytes = bytes.fromhex(name_hex[130: 130 + length * 2])
            ens_name = name_bytes.decode("utf-8", errors="replace").strip("\x00")

            if not ens_name:
                return _reverse_resolve_web3_fallback(address, rpc_url)

            return ens_name

    except Exception as e:
        logger.debug(f"[ENSIP-25] Reverse resolution RPC failed: {e}")
        return _reverse_resolve_web3_fallback(address, rpc_url)


def _reverse_resolve_web3_fallback(address: str, rpc_url: str) -> str | None:
    """Fallback: use web3.py ENS module for reverse resolution."""
    try:
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        return w3.ens.name(address)
    except Exception as e:
        logger.debug(f"[ENSIP-25] web3.py ENS fallback also failed: {e}")
        return None


# ── Step 2: Text record lookup ───────────────────────────────────────────────


async def _get_text_record(ens_name: str, key: str, rpc_url: str) -> str | None:
    """
    Read an ENS text record.
    1. Compute namehash of the ENS name
    2. Call resolver(bytes32) on ENS Registry → get resolver address
    3. Call text(bytes32 node, string key) on the resolver — selector 0x59d1d43c
    """
    try:
        name_node = _namehash(ens_name)
        name_node_padded = name_node[2:].zfill(64)

        async with http_client(timeout=15) as client:
            # Get resolver for this forward name from ENS Registry
            resolver_addr = await _get_resolver(client, rpc_url, name_node)

            if not resolver_addr:
                logger.debug(f"[ENSIP-25] No resolver found for {ens_name}")
                return None

            # ABI encode: text(bytes32 node, string key)
            key_bytes = key.encode("utf-8")
            key_len = len(key_bytes)
            key_hex = key_bytes.hex()
            # Pad key data to 32-byte boundary
            padded_len = ((key_len + 31) // 32) * 64
            key_padded = key_hex.ljust(padded_len, "0")

            # offset to string data = 0x40 (64 decimal = 2 slots of 32 bytes)
            offset_hex = "0000000000000000000000000000000000000000000000000000000000000040"
            key_len_hex = hex(key_len)[2:].zfill(64)

            call_data = (
                "0x59d1d43c"
                + name_node_padded
                + offset_hex
                + key_len_hex
                + key_padded
            )

            text_hex = await _rpc_call(
                client, rpc_url, "eth_call",
                [{"to": resolver_addr, "data": call_data}, "latest"],
            )

            if not text_hex or len(text_hex) <= 130:
                return None

            return _decode_abi_string(text_hex)

    except Exception as e:
        logger.debug(f"[ENSIP-25] Text record read failed for {ens_name}/{key}: {e}")
        return None


def _decode_abi_string(hex_data: str) -> str | None:
    """Decode an ABI-encoded string from hex response data."""
    try:
        data = hex_data.replace("0x", "")

        if len(data) < 128:  # Need at least offset + length
            return None

        # First 32 bytes = offset to string data
        offset = int(data[:64], 16) * 2  # convert byte offset to hex char offset

        # At offset: 32 bytes = string length
        str_len = int(data[offset:offset + 64], 16)

        if str_len == 0:
            return None

        # After length: the actual string bytes
        str_hex = data[offset + 64:offset + 64 + str_len * 2]
        return bytes.fromhex(str_hex).decode("utf-8", errors="replace").strip("\x00")

    except Exception:
        return None
