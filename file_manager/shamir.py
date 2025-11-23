import logging
import secrets
from typing import List

logger = logging.getLogger("SecureShare")


class ShamirSecretSharing:
    """A simple Shamir's secret sharing scheme implementation."""

    def __init__(self, prime: int = 2**256 - 189):
        self.prime = prime
        logger.debug(f"Initialized Shamir's Secret Sharing with prime: {prime}")

    def _mod_inverse(self, x: int, p: int) -> int:
        return pow(x, p - 2, p)

    def _eval_polynomial(self, coeffs: List[int], x: int) -> int:
        result = 0
        for coeff in reversed(coeffs):
            result = (result * x + coeff) % self.prime
        return result

    def generate_shares(self, secret: bytes, n: int, t: int) -> List[tuple]:
        if t > n:
            raise ValueError("Threshold cannot be greater than number of shares")
        logger.info(f"Generating {n} shares with threshold {t}")
        secret_int = int.from_bytes(secret, byteorder="big")
        coeffs = [secret_int] + [secrets.randbelow(self.prime) for _ in range(t - 1)]
        shares = []
        for i in range(1, n + 1):
            x = i
            y = self._eval_polynomial(coeffs, x)
            # Store y in a fixed 32-byte length representation.
            y_bytes = y.to_bytes(32, byteorder="big")
            shares.append((x, y_bytes))
        logger.debug(f"Generated {len(shares)} shares")
        return shares

    def reconstruct_secret(self, shares: List[tuple], key_length: int = 32) -> bytes:
        if not shares:
            raise ValueError("No shares provided")
        result = 0
        for i, (x_i, y_i_bytes) in enumerate(shares):
            y_i = int.from_bytes(y_i_bytes, byteorder="big")
            numerator, denominator = 1, 1
            for j, (x_j, _) in enumerate(shares):
                if i == j:
                    continue
                numerator = (numerator * (-x_j)) % self.prime
                denominator = (denominator * (x_i - x_j)) % self.prime
            lagrange = y_i * numerator * self._mod_inverse(denominator, self.prime)
            result = (result + lagrange) % self.prime
        return result.to_bytes(key_length, byteorder="big")

