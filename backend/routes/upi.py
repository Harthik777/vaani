from fastapi import APIRouter
from pydantic import BaseModel
from services import paytm

router = APIRouter()

class PaymentIn(BaseModel):
    payee: str
    vpa: str = "merchant@paytm"
    amount: float

@router.post("/api/upi/link")
async def upi_link(p: PaymentIn):
    # Anomaly check belongs here too (large amount / new payee) before returning.
    if paytm.enabled():
        try:
            return await paytm.create_payment_link(p.payee, p.vpa, p.amount)
        except Exception:
            pass
    # Deep-link mode — no keys needed, opens any UPI app on a phone
    return {"uri": paytm.upi_deep_link(p.vpa, p.payee, p.amount)}
