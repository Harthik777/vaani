"""
Paytm / UPI helpers.
Mock + deep-link mode need NO keys. Real Payment Links need staging keys.
"""
from urllib.parse import quote
from services import config

def enabled() -> bool:
    return config.USE_REAL_PAYTM and bool(config.PAYTM_MID)

def upi_deep_link(vpa: str, payee: str, amount: float) -> str:
    """Standard UPI intent string — works with any UPI app, no keys needed."""
    return f"upi://pay?pa={vpa}&pn={quote(payee)}&am={amount}&cu=INR"

async def create_payment_link(payee: str, vpa: str, amount: float) -> dict:
    # REAL CALL: Paytm Payment Links API (staging).
    # Docs: https://business.paytm.com/docs
    raise NotImplementedError("Paytm live not wired — using UPI deep link")
