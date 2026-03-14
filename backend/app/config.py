from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_KEY: str

    # Alchemy RPC
    ALCHEMY_API_KEY: str
    ALCHEMY_BASE_KEY: str = ""
    ALCHEMY_BASE_RPC: str
    ALCHEMY_ETH_RPC: str
    BASE_SEPOLIA_RPC: str = "https://sepolia.base.org"

    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "o3"
    OPENAI_MAX_TOKENS: int = 4096
    OPENAI_TIMEOUT: int = 120

    # HeyElsa x402
    HEYELSA_ENABLED: bool = True
    HEYELSA_BASE_URL: str = "https://x402-api.heyelsa.ai"
    HEYELSA_WALLET_ADDRESS: str = ""
    HEYELSA_WALLET_PRIVATE_KEY: str = ""
    X402_PAYER_PRIVATE_KEY: str = ""

    # Smart Contracts
    ERC8004_REGISTRY: str = "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"
    ERC8004_REPUTATION_REGISTRY: str = "0x8004BAa17C55a88189AE136b182e5fdA19dE9b63"
    VIRTUAL_TOKEN_BASE: str = "0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b"

    # Olas / The Graph
    GRAPH_API_KEY: str = ""

    # Score Anchor Contract (Base Sepolia)
    SCORE_ANCHOR_ADDRESS: str = ""
    SCORE_ANCHOR_PRIVATE_KEY: str = ""

    # ENS Subnames (NameStone — gasless offchain subnames)
    NAMESTONE_API_KEY: str = ""
    ENS_DOMAIN: str = ""  # e.g. "agentscore.eth"

    # Chains
    BASE_CHAIN_ID: int = 8453
    BASE_SEPOLIA_CHAIN_ID: int = 84532

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
