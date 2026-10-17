from fastapi import APIRouter
from models import CompileIn
from services.compiler import screens
router = APIRouter()

@router.post("/api/screenspec")
async def screenspec(body: CompileIn):
    return screens(body)
