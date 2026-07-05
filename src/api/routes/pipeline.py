"""Pipeline routes: /status, /voice/command, /approve, /cancel."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.memory.audit import get_logger

router = APIRouter(tags=["pipeline"])
_log = get_logger("api.pipeline")

# Wired at startup by main.py via set_pipeline()
_pipeline: dict[str, Any] = {}


def set_pipeline(preprocessor: Any, classifier: Any, agent_router: Any, session_mgr: Any) -> None:
    """Wire the processing pipeline into the API layer."""
    _pipeline["preprocessor"] = preprocessor
    _pipeline["classifier"] = classifier
    _pipeline["router"] = agent_router
    _pipeline["session"] = session_mgr


def _get_pipeline() -> dict[str, Any] | None:
    return _pipeline if _pipeline else None


class VoiceCommandBody(BaseModel):
    text: str = Field(..., min_length=1)
    language: str = Field(default="en")


class ApproveBody(BaseModel):
    request_id: str
    edited_prompt: str | None = None


class CancelBody(BaseModel):
    request_id: str


@router.get("/status")
async def get_status() -> JSONResponse:
    session = _pipeline.get("session")
    state = session.state if session else "idle"
    session_id = session.session_id if session else None
    return JSONResponse({"state": str(state), "active_request_id": session_id})


@router.post("/voice/command")
async def voice_command(body: VoiceCommandBody) -> JSONResponse:
    """Run text through the full processing pipeline and return the response."""
    pipeline = _get_pipeline()
    if not pipeline:
        return JSONResponse({"status": "not_implemented"}, status_code=501)

    preprocessor = pipeline["preprocessor"]
    classifier = pipeline["classifier"]
    agent_router = pipeline["router"]
    session_mgr = pipeline.get("session")

    from src.memory.session import SessionState
    from src.agents.base import AgentRequest, AllProvidersUnavailableError

    if session_mgr:
        await session_mgr.transition(SessionState.CLASSIFYING)

    try:
        # Use process() if available (Stage 2 structured prompt), fall back to clean()
        if hasattr(preprocessor, "process"):
            pp_result = await preprocessor.process(body.text)
            cleaned = pp_result.stage1_output or body.text
            structured_prompt = pp_result.structured_prompt
        else:
            cleaned = await preprocessor.clean(body.text)
            structured_prompt = None

        tier = classifier.classify(cleaned)

        # Surface incomplete structured prompt for UI review before dispatch
        if structured_prompt is not None and structured_prompt.incomplete:
            return JSONResponse({
                "status": "awaiting_clarification",
                "structured_prompt": structured_prompt.to_dict(),
                "tier": tier,
            })

        if session_mgr:
            await session_mgr.transition(SessionState.EXECUTING)

        from src.memory.vault_context import build_context

        request_id = str(uuid.uuid4())
        system_prefix = await build_context(cleaned)
        request = AgentRequest(prompt=cleaned, request_id=request_id, system_prefix=system_prefix)
        response = await agent_router.route(request)

        _log.info("voice_command_completed", tier=tier, provider=response.provider_name)
        payload: dict = {
            "status": "ok",
            "response": response.content,
            "tier": tier,
            "provider": response.provider_name,
            "request_id": request_id,
        }
        if structured_prompt is not None:
            payload["structured_prompt"] = structured_prompt.to_dict()
        return JSONResponse(payload)

    except AllProvidersUnavailableError as exc:
        _log.error("voice_command_all_failed", error=str(exc))
        raise HTTPException(status_code=503, detail="All AI providers unavailable")
    except Exception as exc:
        _log.error("voice_command_error", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if session_mgr:
            await session_mgr.transition(SessionState.IDLE)


@router.post("/approve")
async def approve(body: ApproveBody) -> JSONResponse:
    """Approve a pending complex task, optionally with an edited prompt."""
    pipeline = _get_pipeline()
    if not pipeline or "approval" not in pipeline:
        return JSONResponse({"status": "not_implemented"}, status_code=501)
    try:
        approval_mgr = pipeline["approval"]
        edited = await approval_mgr.approve(body.request_id, edited_prompt=body.edited_prompt)
        _log.info("task_approved", request_id=body.request_id)
        return JSONResponse({"status": "approved", "prompt": edited})
    except KeyError:
        raise HTTPException(status_code=404, detail=f"No pending request: {body.request_id}")


@router.post("/cancel")
async def cancel(body: CancelBody) -> JSONResponse:
    """Cancel any pending or executing task."""
    pipeline = _get_pipeline()
    if not pipeline or "approval" not in pipeline:
        return JSONResponse({"status": "not_implemented"}, status_code=501)
    approval_mgr = pipeline["approval"]
    await approval_mgr.cancel(body.request_id)
    _log.info("task_cancelled", request_id=body.request_id)
    return JSONResponse({"status": "cancelled"})
