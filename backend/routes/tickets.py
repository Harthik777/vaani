from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Literal
from services import store, config
import httpx

router = APIRouter()

class TicketIn(BaseModel):
    kind: Literal["maintenance", "procurement"]
    asset: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1, max_length=10000)

@router.post("/api/tickets")
async def create_ticket(body: TicketIn):
    data = {**body.model_dump(), "status": "queued locally — external dispatch not configured", "created_at": store.now()}
    ident, key = store.create("ticket", data)
    if config.WORK_ORDER_URL:
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(config.WORK_ORDER_URL,
                    headers={"Authorization": "Bearer " + config.WORK_ORDER_API_KEY, "Idempotency-Key": ident},
                    json={"id": ident, **data})
                response.raise_for_status()
            data["status"] = "accepted by configured dispatch service"
        except httpx.HTTPError:
            data["status"] = "queued locally — dispatch service unavailable; retry through your ticket system"
        store.update_ticket(ident, data)
    return {"id": ident, "key": key, **data}
