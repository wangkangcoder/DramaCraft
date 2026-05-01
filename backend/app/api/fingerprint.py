from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.fingerprint import analyze_narrative_fingerprint
from app.core.script_formats import DEFAULT_SCRIPT_FORMAT, normalize_script_format


router = APIRouter()


class FingerprintAnalyzeRequest(BaseModel):
    content: str = Field(min_length=1)
    outline: Optional[str] = ""
    characters: Optional[str] = ""
    idea: Optional[str] = ""
    script_format: str = DEFAULT_SCRIPT_FORMAT
    title: Optional[str] = ""


@router.post("/analyze")
def analyze_fingerprint(req: FingerprintAnalyzeRequest):
    try:
        result = analyze_narrative_fingerprint(
            content=req.content,
            outline=req.outline or "",
            characters=req.characters or "",
            idea=req.idea or "",
            script_format=normalize_script_format(req.script_format),
            title=req.title or "",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"叙事指纹分析失败：{exc}") from exc

    return {
        "status": "success",
        "analysis": result,
    }
