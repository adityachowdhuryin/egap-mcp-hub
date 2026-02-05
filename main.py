"""
egap-mcp-hub: MCP Hub Service
Phase 0 - Hello World endpoint for Cloud Run deployment verification
"""

from fastapi import FastAPI

app = FastAPI(
    title="egap-mcp-hub",
    description="MCP Hub Service for EGAP",
    version="0.1.0"
)


@app.get("/")
async def root():
    """Root endpoint returning Hello World for deployment verification."""
    return {"message": "Hello World"}


@app.get("/health")
async def health():
    """Health check endpoint for Cloud Run."""
    return {"status": "healthy"}
