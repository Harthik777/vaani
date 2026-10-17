"""Executable requirements and agent mediation (see services/agent.py)."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from models import Rule
from services import agent

router = APIRouter()


class ScenarioIn(BaseModel):
    rules: list[Rule] = Field(min_length=1, max_length=100)
    scenario: str = Field(min_length=3, max_length=2000)


class ResolveIn(BaseModel):
    rules: list[Rule] = Field(min_length=2, max_length=100)
    conflict: dict
    transcript: str = Field(default="", max_length=100000)


@router.post("/api/agent/scenario")
async def scenario(body: ScenarioIn):
    try:
        return await agent.scenario([r.model_dump() for r in body.rules], body.scenario)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, f"The scenario check failed: {exc}") from exc


@router.post("/api/agent/resolve")
async def resolve(body: ResolveIn):
    try:
        return await agent.resolve(body.conflict, [r.model_dump() for r in body.rules], body.transcript)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, f"Reconciling failed: {exc}") from exc
