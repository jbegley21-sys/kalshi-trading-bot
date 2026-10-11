"""RSA-PSS / Ed25519 authentication for Kalshi API."""

from __future__ import annotations

import base64
import time

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, padding, rsa


class KalshiAuth:
    """Generates signatures for Kalshi API requests.

    Supports both RSA and Ed25519 private keys (Kalshi issues both).

    Kalshi requires three headers on authenticated requests:
    - KALSHI-ACCESS-KEY: the API key ID
    - KALSHI-ACCESS-TIMESTAMP: current time in milliseconds
    - KALSHI-ACCESS-SIGNATURE: signature of (timestamp + method + path)
    """

    def __init__(self, api_key_id: str, private_key_path: str):
        self.api_key_id = api_key_id
        self._private_key = self._load_private_key(private_key_path)

    @staticmethod
    def _load_private_key(path: str):
        """Load an RSA or Ed25519 private key from a PEM file."""
        with open(path, "rb") as f:
            key = serialization.load_pem_private_key(f.read(), password=None)
        if not isinstance(
            key, (rsa.RSAPrivateKey, ed25519.Ed25519PrivateKey)
        ):
            raise ValueError(
                f"Expected RSA or Ed25519 private key, got {type(key).__name__}"
            )
        return key

    def sign(self, timestamp_ms: int, method: str, path: str) -> str:
        """Generate a signature for a Kalshi API request.

        The message to sign is: str(timestamp_ms) + method_uppercase + path_without_query
        RSA keys use SHA256 with PSS padding (salt_length = DIGEST_LENGTH).
        Ed25519 keys sign the message bytes directly.
        Returns base64-encoded signature string.
        """
        path_without_query = path.split("?")[0]
        message = f"{timestamp_ms}{method.upper()}{path_without_query}".encode("utf-8")

        if isinstance(self._private_key, ed25519.Ed25519PrivateKey):
            signature = self._private_key.sign(message)
        else:
            signature = self._private_key.sign(
                message,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.DIGEST_LENGTH,
                ),
                hashes.SHA256(),
            )
        return base64.b64encode(signature).decode("utf-8")

    def get_headers(self, method: str, path: str) -> dict[str, str]:
        """Generate the three required authentication headers."""
        timestamp_ms = int(time.time() * 1000)
        signature = self.sign(timestamp_ms, method, path)
        return {
            "KALSHI-ACCESS-KEY": self.api_key_id,
            "KALSHI-ACCESS-TIMESTAMP": str(timestamp_ms),
            "KALSHI-ACCESS-SIGNATURE": signature,
        }

