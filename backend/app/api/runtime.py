from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.local_runtime import heartbeat


router = APIRouter()


class RuntimeClientPayload(BaseModel):
    client_id: str = Field(..., min_length=1, max_length=200)


@router.post("/heartbeat")
def runtime_heartbeat(payload: RuntimeClientPayload):
    return heartbeat(payload.client_id)
