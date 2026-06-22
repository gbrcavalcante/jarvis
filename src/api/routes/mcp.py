"""MCP routes: /mcp."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.plugins.mcp_manager import connect_mcp, disconnect_mcp, list_mcp_connections

router = APIRouter(tags=["mcp"])


@router.get("/mcp")
async def list_mcp(provider: str = "claude") -> JSONResponse:
    connections = list_mcp_connections(provider)
    return JSONResponse({
        "provider": provider,
        "connections": [
            {"service_name": name, **cfg}
            for name, cfg in connections.items()
        ],
    })


class ConnectMcpBody(BaseModel):
    service_name: str
    server_url: str
    auth_method: str = "none"
    api_key: str | None = None


@router.post("/mcp/connect")
async def connect_mcp_endpoint(body: ConnectMcpBody, provider: str = "claude") -> JSONResponse:
    connect_mcp(
        provider=provider,
        service_name=body.service_name,
        server_url=body.server_url,
        auth_method=body.auth_method,
        credential=body.api_key,
    )
    return JSONResponse({"service_name": body.service_name, "connected": True})


@router.delete("/mcp/{service_name}")
async def disconnect_mcp_endpoint(service_name: str, provider: str = "claude") -> JSONResponse:
    disconnect_mcp(provider, service_name)
    return JSONResponse({"service_name": service_name, "connected": False})
