"""
Google Agent Dev Kit Integration for Finance MCP Application
Demonstrates how to integrate the Finance MCP server with Google Agent Dev Kit
"""
import os
import logging
import json
import asyncio
from dotenv import load_dotenv
from fastmcp import MCPClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class GoogleAgentMCPIntegration:
    """
    Integration class for connecting Finance MCP with Google Agent Dev Kit
    """
    
    def __init__(self, mcp_host, mcp_port):
        """Initialize the integration
        
        Args:
            mcp_host (str): MCP server host
            mcp_port (int): MCP server port
        """
        self.mcp_host = mcp_host
        self.mcp_port = mcp_port
        self.mcp_client = MCPClient(host=mcp_host, port=mcp_port)
        
    async def connect(self):
        """Connect to the MCP server"""
        await self.mcp_client.connect()
        logger.info(f"Connected to MCP server at {self.mcp_host}:{self.mcp_port}")
        
    async def disconnect(self):
        """Disconnect from the MCP server"""
        await self.mcp_client.disconnect()
        logger.info("Disconnected from MCP server")
        
    async def optimize_working_capital(self, scenario="base"):
        """Optimize working capital
        
        Args:
            scenario (str): Scenario to optimize for
            
        Returns:
            dict: Optimization result
        """
        logger.info(f"Optimizing working capital with scenario: {scenario}")
        
        message = {
            "type": "finance.working_capital.optimize",
            "payload": json.dumps({"scenario": scenario})
        }
        
        response = await self.mcp_client.send_message(message)
        
        if response.get("status") == "success":
            return json.loads(response.get("payload", "{}"))
        else:
            logger.error(f"Error optimizing working capital: {response.get('error')}")
            return {"error": response.get("error")}
            
    async def optimize_accounts_payable(self, cash_position):
        """Optimize accounts payable
        
        Args:
            cash_position (float): Current cash position
            
        Returns:
            dict: Optimization result
        """
        logger.info(f"Optimizing accounts payable with cash position: {cash_position}")
        
        message = {
            "type": "finance.accounts_payable.optimize",
            "payload": json.dumps({"cash_position": cash_position})
        }
        
        response = await self.mcp_client.send_message(message)
        
        if response.get("status") == "success":
            return json.loads(response.get("payload", "{}"))
        else:
            logger.error(f"Error optimizing accounts payable: {response.get('error')}")
            return {"error": response.get("error")}
            
    async def optimize_accounts_receivable(self, cash_position, objective="balanced"):
        """Optimize accounts receivable
        
        Args:
            cash_position (float): Current cash position
            objective (str): Optimization objective
            
        Returns:
            dict: Optimization result
        """
        logger.info(f"Optimizing accounts receivable with cash position: {cash_position} and objective: {objective}")
        
        message = {
            "type": "finance.accounts_receivable.optimize",
            "payload": json.dumps({
                "cash_position": cash_position,
                "objective": objective
            })
        }
        
        response = await self.mcp_client.send_message(message)
        
        if response.get("status") == "success":
            return json.loads(response.get("payload", "{}"))
        else:
            logger.error(f"Error optimizing accounts receivable: {response.get('error')}")
            return {"error": response.get("error")}
            
    async def get_cash_flow_forecast(self, days_horizon=90):
        """Get cash flow forecast
        
        Args:
            days_horizon (int): Number of days to forecast
            
        Returns:
            list: Cash flow forecast
        """
        logger.info(f"Getting cash flow forecast for {days_horizon} days")
        
        message = {
            "type": "finance.cash_flow.forecast",
            "payload": json.dumps({"days_horizon": days_horizon})
        }
        
        response = await self.mcp_client.send_message(message)
        
        if response.get("status") == "success":
            return json.loads(response.get("payload", "{}"))
        else:
            logger.error(f"Error getting cash flow forecast: {response.get('error')}")
            return {"error": response.get("error")}
            
    async def execute_neo4j_query(self, query, parameters=None):
        """Execute a Neo4j Cypher query
        
        Args:
            query (str): Cypher query
            parameters (dict, optional): Query parameters
            
        Returns:
            list: Query results
        """
        if parameters is None:
            parameters = {}
            
        logger.info(f"Executing Neo4j query: {query}")
        
        message = {
            "type": "neo4j.cypher",
            "payload": json.dumps({
                "query": query,
                "parameters": parameters
            })
        }
        
        response = await self.mcp_client.send_message(message)
        
        if response.get("status") == "success":
            return json.loads(response.get("payload", "{}"))
        else:
            logger.error(f"Error executing Neo4j query: {response.get('error')}")
            return {"error": response.get("error")}

async def demo():
    """Run a demonstration of the Google Agent integration"""
    # Load environment variables
    load_dotenv()
    
    # Get MCP server details
    mcp_host = os.getenv("MCP_HOST", "localhost")
    mcp_port = int(os.getenv("MCP_PORT", "9000"))
    
    # Create integration
    integration = GoogleAgentMCPIntegration(mcp_host, mcp_port)
    
    try:
        # Connect to MCP server
        await integration.connect()
        
        # Get cash flow forecast
        logger.info("Getting cash flow forecast...")
        forecast = await integration.get_cash_flow_forecast()
        logger.info(f"Received forecast with {len(forecast)} days")
        
        # Optimize working capital
        logger.info("Optimizing working capital...")
        wc_result = await integration.optimize_working_capital(scenario="base")
        logger.info(f"Working capital optimization complete. Metrics: {wc_result.get('metrics', {})}")
        
        # Optimize accounts payable
        logger.info("Optimizing accounts payable...")
        ap_result = await integration.optimize_accounts_payable(cash_position=500000)
        logger.info(f"Accounts payable optimization complete. Metrics: {ap_result.get('metrics', {})}")
        
        # Optimize accounts receivable
        logger.info("Optimizing accounts receivable...")
        ar_result = await integration.optimize_accounts_receivable(
            cash_position=500000,
            objective="balanced"
        )
        logger.info(f"Accounts receivable optimization complete. Metrics: {ar_result.get('metrics', {})}")
        
        # Execute a Neo4j query
        logger.info("Executing Neo4j query...")
        query_result = await integration.execute_neo4j_query(
            "MATCH (c:Customer) RETURN c.id AS id, c.name AS name LIMIT 5"
        )
        logger.info(f"Query result: {query_result}")
        
    except Exception as e:
        logger.error(f"Error in demo: {e}")
    finally:
        # Disconnect from MCP server
        await integration.disconnect()

if __name__ == "__main__":
    # Run the demo
    asyncio.run(demo())
