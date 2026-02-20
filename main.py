"""
egap-mcp-hub: MCP Hub Service
Phase 1 - JSON-RPC 2.0 handler for MCP Server with Vertex AI Search, Email, and Storage
"""

from typing import Any, Optional
from fastapi import FastAPI, Request
from pydantic import BaseModel
from google.cloud import discoveryengine_v1 as discoveryengine
from google.cloud import storage


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

# Vertex AI Search
DATA_STORE_ID = "egap-vertex-ai-docs_1770454318783"
PROJECT_ID = "gls-training-486405"

# Google Cloud Storage
ARTIFACT_BUCKET = "gls-training-486405-artifacts"


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
    action_type: str  # "read" or "write" — FRS Action Gating


def list_tools() -> list[ToolDefinition]:
    """
    Returns a list of available MCP tools.
    """
    return [
        ToolDefinition(
            name="search_vertex_docs",
            description="Search the official Vertex AI documentation for technical answers.",
            action_type="read"
        ),
        ToolDefinition(
            name="send_email",
            description="Send an email to a recipient. Requires subject and body.",
            action_type="write"
        ),
        ToolDefinition(
            name="save_file",
            description="Save text content to a file in cloud storage. Requires filename and content.",
            action_type="write"
        )
    ]


# -----------------------------------------------------------------------------
# Vertex AI Search Functions
# -----------------------------------------------------------------------------

def search_knowledge_base(query: str) -> list[str]:
    """
    Search the Vertex AI data store for relevant documentation.
    
    Args:
        query: The search query string
        
    Returns:
        A list of snippet summaries from the search results
    """
    client = discoveryengine.SearchServiceClient()
    
    # Build the serving config path
    serving_config = client.serving_config_path(
        project=PROJECT_ID,
        location="global",
        data_store=DATA_STORE_ID,
        serving_config="default_config"
    )
    
    # Create the search request
    request = discoveryengine.SearchRequest(
        serving_config=serving_config,
        query=query,
        page_size=5,
        content_search_spec=discoveryengine.SearchRequest.ContentSearchSpec(
            snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
                return_snippet=True
            ),
            summary_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec(
                summary_result_count=3,
                include_citations=True
            )
        )
    )
    
    # Execute the search
    response = client.search(request)
    
    # Extract snippets from results
    snippets = []
    for result in response.results:
        document = result.document
        # Try to get snippet from derived_struct_data
        if document.derived_struct_data:
            snippets_data = document.derived_struct_data.get("snippets", [])
            for snippet in snippets_data:
                if isinstance(snippet, dict) and "snippet" in snippet:
                    snippets.append(snippet["snippet"])
        # Also try extracting from extractive_answers if available
        if hasattr(document, 'struct_data') and document.struct_data:
            title = document.struct_data.get("title", "")
            if title:
                snippets.append(f"Document: {title}")
    
    # Include summary if available
    if response.summary and response.summary.summary_text:
        snippets.insert(0, f"Summary: {response.summary.summary_text}")
    
    return snippets if snippets else ["No relevant results found."]


# -----------------------------------------------------------------------------
# Email Functions (Mock)
# -----------------------------------------------------------------------------

def send_email_via_smtp(to_email: str, subject: str, body: str) -> str:
    """
    Mock email sender - logs email details to system logs.
    
    Args:
        to_email: Recipient email address
        subject: Email subject line
        body: Email body content
        
    Returns:
        Mock success message string
    """
    print(f"[MOCK EMAIL] To: {to_email}")
    print(f"[MOCK EMAIL] Subject: {subject}")
    print(f"[MOCK EMAIL] Body: {body}")
    
    return f"[MOCK] Email successfully queued for delivery to {to_email}"


# -----------------------------------------------------------------------------
# Cloud Storage Functions
# -----------------------------------------------------------------------------

def save_artifact(filename: str, content: str) -> str:
    """
    Save text content to a file in Google Cloud Storage.
    
    Args:
        filename: Name of the file to create
        content: Text content to save
        
    Returns:
        Public URL or success message
    """
    client = storage.Client()
    bucket = client.bucket(ARTIFACT_BUCKET)
    blob = bucket.blob(filename)
    
    # Upload the content
    blob.upload_from_string(content, content_type="text/plain")
    
    # Return the GCS URI
    gcs_uri = f"gs://{ARTIFACT_BUCKET}/{filename}"
    return f"File saved successfully: {gcs_uri}"


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
    elif method == "tools/call":
        if not params:
            raise ValueError("tools/call requires params")
        
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})

        # ── FRS Action Gating ─────────────────────────────────────────
        # Look up the tool definition to check its action_type
        tools = list_tools()
        tool_def = next((t for t in tools if t.name == tool_name), None)
        if tool_def and tool_def.action_type == "write":
            approval_token = params.get("approval_token")
            if not approval_token:
                return {
                    "error": {
                        "code": -32001,
                        "message": "APPROVAL_REQUIRED",
                        "data": {
                            "tool": tool_name,
                            "action_type": "write",
                            "hint": "Write tools require an 'approval_token' in params. "
                                    "Obtain one from the HITL governance flow."
                        }
                    }
                }
        # ──────────────────────────────────────────────────────────────

        if tool_name == "search_vertex_docs":
            query = tool_args.get("query", "")
            if not query:
                raise ValueError("search_vertex_docs requires a 'query' argument")
            snippets = search_knowledge_base(query)
            return {"content": [{"type": "text", "text": "\n\n".join(snippets)}]}
        elif tool_name == "send_email":
            to_email = tool_args.get("to_email", "")
            subject = tool_args.get("subject", "")
            body = tool_args.get("body", "")
            if not to_email or not subject or not body:
                raise ValueError("send_email requires 'to_email', 'subject', and 'body' arguments")
            result = send_email_via_smtp(to_email, subject, body)
            return {"content": [{"type": "text", "text": result}]}
        elif tool_name == "save_file":
            filename = tool_args.get("filename", "")
            content = tool_args.get("content", "")
            if not filename or not content:
                raise ValueError("save_file requires 'filename' and 'content' arguments")
            result = save_artifact(filename, content)
            return {"content": [{"type": "text", "text": result}]}
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
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
