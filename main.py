"""
egap-mcp-hub: MCP Hub Service
Phase 1 - JSON-RPC 2.0 handler for MCP Server
"""

from typing import Any, Optional
from fastapi import FastAPI, Request
from pydantic import BaseModel


app = FastAPI(
    title="egap-mcp-hub",
    description="MCP Hub Service for EGAP - Model Context Protocol Server",
    version="0.1.0"
)


# -----------------------------------------------------------------------------
# JSON-RPC 2.0 Models
# -----------------------------------------------------------------------------

class JsonRpcRequest(BaseModel):
    """JSON-RPC 2.0 Request model."""
    jsonrpc: str = "2.0"
    method: str
    params: Optional[dict] = None
    id: Optional[int | str] = None


class JsonRpcResponse(BaseModel):
    """JSON-RPC 2.0 Response model."""
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[dict] = None
    id: Optional[int | str] = None


class JsonRpcError(BaseModel):
    """JSON-RPC 2.0 Error model."""
    code: int
    message: str
    data: Optional[Any] = None


# -----------------------------------------------------------------------------
# MCP Tool Definitions
# -----------------------------------------------------------------------------

class ToolDefinition(BaseModel):
    """MCP Tool Definition model."""
    name: str
    description: str


def list_tools() -> list[ToolDefinition]:
    """
    Returns a list of available MCP tools.
    
    For Phase 1, this returns a hardcoded list with one dummy tool.
    """
    return [
        ToolDefinition(
            name="test_search",
            description="A test tool for Phase 1"
        )
    ]


# -----------------------------------------------------------------------------
# JSON-RPC 2.0 Method Handlers
# -----------------------------------------------------------------------------

def handle_method(method: str, params: Optional[dict] = None) -> Any:
    """
    Route JSON-RPC method calls to appropriate handlers.
    
    Args:
        method: The JSON-RPC method name
        params: Optional parameters for the method
        
    Returns:
        The result of the method call
        
    Raises:
        ValueError: If the method is not found
    """
    if method == "tools/list":
        tools = list_tools()
        return {"tools": [tool.model_dump() for tool in tools]}
    else:
        raise ValueError(f"Method not found: {method}")


# -----------------------------------------------------------------------------
# API Endpoints
# -----------------------------------------------------------------------------

@app.post("/")
async def jsonrpc_handler(request: JsonRpcRequest) -> JsonRpcResponse:
    """
    JSON-RPC 2.0 handler endpoint.
    
    Accepts JSON-RPC 2.0 requests and routes them to appropriate method handlers.
    """
    try:
        # Validate JSON-RPC version
        if request.jsonrpc != "2.0":
            return JsonRpcResponse(
                jsonrpc="2.0",
                error={
                    "code": -32600,
                    "message": "Invalid Request",
                    "data": "jsonrpc must be '2.0'"
                },
                id=request.id
            )
        
        # Handle the method call
        result = handle_method(request.method, request.params)
        
        return JsonRpcResponse(
            jsonrpc="2.0",
            result=result,
            id=request.id
        )
        
    except ValueError as e:
        return JsonRpcResponse(
            jsonrpc="2.0",
            error={
                "code": -32601,
                "message": "Method not found",
                "data": str(e)
            },
            id=request.id
        )
    except Exception as e:
        return JsonRpcResponse(
            jsonrpc="2.0",
            error={
                "code": -32603,
                "message": "Internal error",
                "data": str(e)
            },
            id=request.id
        )


@app.get("/health")
async def health():
    """Health check endpoint for Cloud Run."""
    return {"status": "healthy"}
