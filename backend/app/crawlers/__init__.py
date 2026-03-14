import ssl
import httpx

# Python 3.14 + OpenSSL 3.x defaults to SECLEVEL=2 which causes TLS
# connection resets with Cloudflare-fronted APIs. Lower to SECLEVEL=1.
_ssl_ctx = ssl.create_default_context()
_ssl_ctx.set_ciphers("DEFAULT@SECLEVEL=1")
_ssl_ctx.minimum_version = ssl.TLSVersion.TLSv1_2


def http_client(timeout: int = 30) -> httpx.AsyncClient:
    """Return an AsyncClient with compatible TLS settings."""
    return httpx.AsyncClient(verify=_ssl_ctx, timeout=timeout)
