#!/usr/bin/env python3
"""
Finance MCP Application - Main Entry Point
Implements a FastMCP server with Neo4j integration for financial data processing
"""
import os
import logging
import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv
from fastmcp import MCPServer
from fastmcp.router import MCPRouter

# Import application components
from api.mcp_handlers import register_mcp_handlers
from api.rest_endpoints import router as api_router
from database.neo4j_client import Neo4jClient
from models.working_capital import WorkingCapitalOptimizer
from models.accounts_payable import AccountsPayableOptimizer
from models.accounts_receivable import AccountsReceivableOptimizer

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Finance MCP Application",
    description="Finance application using FastMCP and Neo4j MCP for working capital optimization",
    version="1.0.0"
)

# Add API routes
app.include_router(api_router, prefix="/api")

# Initialize Neo4j client
neo4j_client = Neo4jClient(
    uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    user=os.getenv("NEO4J_USER", "neo4j"),
    password=os.getenv("NEO4J_PASSWORD", "password")
)

# Initialize financial models
working_capital_optimizer = WorkingCapitalOptimizer(neo4j_client)
accounts_payable_optimizer = AccountsPayableOptimizer(neo4j_client)
accounts_receivable_optimizer = AccountsReceivableOptimizer(neo4j_client)

# Create MCP Router
mcp_router = MCPRouter()

# Create MCP Server
mcp_server = MCPServer(
    host=os.getenv("MCP_HOST", "0.0.0.0"),
    port=int(os.getenv("MCP_PORT", "9000")),
    router=mcp_router
)

# Register MCP handlers
register_mcp_handlers(
    mcp_router, 
    working_capital_optimizer, 
    accounts_payable_optimizer, 
    accounts_receivable_optimizer
)

# Start MCP server when application starts
@app.on_event("startup")
async def startup_event():
    logger.info("Starting Finance MCP Application")
    # Connect to Neo4j
    neo4j_client.connect()
    # Start MCP server
    mcp_server.start()
    logger.info(f"MCP Server started on {mcp_server.host}:{mcp_server.port}")

# Shutdown MCP server when application stops
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Finance MCP Application")
    # Stop MCP server
    mcp_server.stop()
    # Close Neo4j connection
    neo4j_client.close()

if __name__ == "__main__":
    # Run FastAPI application with Uvicorn
    uvicorn.run(
        "main:app", 
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8000")),
        reload=True
    )
