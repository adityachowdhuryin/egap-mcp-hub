"""
egap-mcp-hub: MCP Hub Service (Architecture Spec v1.0 Compliant)
Standard MCP Server using the official `mcp` Python SDK with FastMCP.
Exposes tools via the Model Context Protocol for decoupled agent-tool interaction.
"""

import os
import logging
from mcp.server.fastmcp import FastMCP
from google.cloud import discoveryengine_v1 as discoveryengine
from google.cloud import storage

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

DATA_STORE_ID = os.getenv("DATA_STORE_ID", "egap-vertex-ai-docs_1770454318783")
PROJECT_ID = os.getenv("PROJECT_ID", "gls-training-486405")
ARTIFACT_BUCKET = os.getenv("ARTIFACT_BUCKET", "gls-training-486405-artifacts")

logger = logging.getLogger("egap-mcp-hub")
logging.basicConfig(level=logging.INFO)

# -----------------------------------------------------------------------------
# MCP Server Initialization
# -----------------------------------------------------------------------------

mcp = FastMCP(
    name="egap-mcp-hub",
    instructions=(
        "EGAP MCP Tool Server. Provides tools for searching documentation, "
        "sending emails, and saving files to cloud storage. "
        "WRITE tools (send_email, save_file) require HITL approval before execution."
    ),
)


# -----------------------------------------------------------------------------
# MCP Tool Definitions
# -----------------------------------------------------------------------------
# Tools are registered with the @mcp.tool() decorator.
# The MCP SDK auto-generates JSON schemas from type hints and docstrings.
# Action Gating metadata is included in the tool description for ADK callbacks.
# -----------------------------------------------------------------------------


@mcp.tool()
def search_vertex_docs(query: str) -> str:
    """Search the official Vertex AI documentation for technical answers.

    This is a READ tool — it executes immediately without approval.

    Args:
        query: The search query string to look up in the knowledge base.

    Returns:
        Relevant documentation snippets from Vertex AI Search.
    """
    logger.info(f"[MCP] search_vertex_docs called with query: {query}")

    try:
        client = discoveryengine.SearchServiceClient()

        serving_config = client.serving_config_path(
            project=PROJECT_ID,
            location="global",
            data_store=DATA_STORE_ID,
            serving_config="default_config",
        )

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
                    include_citations=True,
                ),
            ),
        )

        response = client.search(request)

        snippets = []
        for result in response.results:
            document = result.document
            if document.derived_struct_data:
                snippets_data = document.derived_struct_data.get("snippets", [])
                for snippet in snippets_data:
                    if isinstance(snippet, dict) and "snippet" in snippet:
                        snippets.append(snippet["snippet"])
            if hasattr(document, "struct_data") and document.struct_data:
                title = document.struct_data.get("title", "")
                if title:
                    snippets.append(f"Document: {title}")

        if response.summary and response.summary.summary_text:
            snippets.insert(0, f"Summary: {response.summary.summary_text}")

        return "\n\n".join(snippets) if snippets else "No relevant results found."

    except Exception as e:
        logger.error(f"[MCP] search_vertex_docs error: {e}")
        return f"Error searching knowledge base: {str(e)}"


@mcp.tool()
def send_email(to_email: str, subject: str, body: str) -> str:
    """Send an email to a recipient. Requires subject and body.

    ⚠️ ACTION TYPE: WRITE — This tool requires Human-in-the-Loop (HITL) approval.
    The ADK agent's before_tool_call callback should intercept this and suspend execution.

    Args:
        to_email: Recipient email address.
        subject: Email subject line.
        body: Email body content.

    Returns:
        Confirmation message that the email was queued for delivery.
    """
    logger.info(f"[MCP] send_email called: to={to_email}, subject={subject}")

    # In the MCP architecture, the actual email sending is handled by the
    # orchestrator after HITL approval. This tool returns a mock confirmation.
    # The ADK agent's before_tool_call intercepts WRITE tools before they reach here.
    return f"Email successfully queued for delivery to {to_email}. Subject: {subject}"


@mcp.tool()
def save_file(filename: str, content: str) -> str:
    """Save text content to a file in Google Cloud Storage.

    ⚠️ ACTION TYPE: WRITE — This tool requires Human-in-the-Loop (HITL) approval.
    The ADK agent's before_tool_call callback should intercept this and suspend execution.

    Args:
        filename: Name of the file to create in cloud storage.
        content: Text content to save in the file.

    Returns:
        GCS URI of the saved file or error message.
    """
    logger.info(f"[MCP] save_file called: filename={filename}")

    try:
        client = storage.Client()
        bucket = client.bucket(ARTIFACT_BUCKET)
        blob = bucket.blob(filename)
        blob.upload_from_string(content, content_type="text/plain")

        gcs_uri = f"gs://{ARTIFACT_BUCKET}/{filename}"
        return f"File saved successfully: {gcs_uri}"

    except Exception as e:
        logger.error(f"[MCP] save_file error: {e}")
        return f"Error saving file: {str(e)}"


# -----------------------------------------------------------------------------
# MCP Resources (optional metadata exposed to agents)
# -----------------------------------------------------------------------------

@mcp.resource("egap://tools/action-gating")
def get_action_gating_policy() -> str:
    """Returns the action gating policy for all tools.
    Agents can read this to understand which tools need HITL approval."""
    return """
    Action Gating Policy (FRS Compliant):
    - READ tools execute immediately: search_vertex_docs
    - WRITE tools require HITL approval: send_email, save_file
    
    WRITE tools will be intercepted by the ADK agent's before_tool_call callback.
    The agent suspends execution and creates a PENDING_APPROVAL task.
    Execution resumes via A2A POST /resume after admin approval.
    """


# -----------------------------------------------------------------------------
# Entrypoint
# -----------------------------------------------------------------------------
# Mount FastMCP as an ASGI app under Starlette for Cloud Run compatibility.
# This ensures the HTTP server binds immediately on startup with a /health check.
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    from starlette.applications import Starlette
    from starlette.routing import Route, Mount
    from starlette.responses import JSONResponse

    async def health(request):
        """Health check endpoint for Cloud Run."""
        return JSONResponse({"status": "ok", "service": "egap-mcp-hub"})

    # Mount FastMCP's streamable-http ASGI app at /mcp
    mcp_app = mcp.streamable_http_app()

    app = Starlette(
        routes=[
            Route("/health", health),
            Route("/", health),  # Root health check for Cloud Run
            Mount("/mcp", app=mcp_app),
        ],
    )

    port = int(os.getenv("PORT", "8080"))
    logger.info(f"🚀 EGAP MCP Hub starting on port {port} (ASGI + streamable-http)")
    uvicorn.run(app, host="0.0.0.0", port=port)

