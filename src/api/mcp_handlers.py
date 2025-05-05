"""
MCP Handlers for Finance MCP Application
Implements handlers for the FastMCP server
"""
import logging
import json
from fastmcp.router import MCPRouter
from mcp_neo4j_cypher import Neo4jCypherHandler

# Import models
from models.working_capital import WorkingCapitalOptimizer
from models.accounts_payable import AccountsPayableOptimizer
from models.accounts_receivable import AccountsReceivableOptimizer

logger = logging.getLogger(__name__)

def register_mcp_handlers(
    mcp_router: MCPRouter,
    working_capital_optimizer: WorkingCapitalOptimizer,
    accounts_payable_optimizer: AccountsPayableOptimizer,
    accounts_receivable_optimizer: AccountsReceivableOptimizer
):
    """Register MCP handlers with the router
    
    Args:
        mcp_router: The MCP router to register handlers with
        working_capital_optimizer: Working capital optimizer instance
        accounts_payable_optimizer: Accounts payable optimizer instance
        accounts_receivable_optimizer: Accounts receivable optimizer instance
    """
    logger.info("Registering MCP handlers")
    
    # Register Neo4j Cypher handler
    neo4j_handler = Neo4jCypherHandler(
        uri=working_capital_optimizer.neo4j_client.uri,
        user=working_capital_optimizer.neo4j_client.user,
        password=working_capital_optimizer.neo4j_client.password
    )
    mcp_router.register_handler("neo4j.cypher", neo4j_handler.handle)
    
    # Register working capital handlers
    mcp_router.register_handler(
        "finance.working_capital.optimize",
        lambda msg: _handle_working_capital_optimize(msg, working_capital_optimizer)
    )
    
    mcp_router.register_handler(
        "finance.working_capital.set_objective_weights",
        lambda msg: _handle_set_objective_weights(msg, working_capital_optimizer)
    )
    
    # Register accounts payable handlers
    mcp_router.register_handler(
        "finance.accounts_payable.optimize",
        lambda msg: _handle_accounts_payable_optimize(msg, accounts_payable_optimizer)
    )
    
    mcp_router.register_handler(
        "finance.accounts_payable.set_supplier_importance",
        lambda msg: _handle_set_supplier_importance(msg, accounts_payable_optimizer)
    )
    
    # Register accounts receivable handlers
    mcp_router.register_handler(
        "finance.accounts_receivable.optimize",
        lambda msg: _handle_accounts_receivable_optimize(msg, accounts_receivable_optimizer)
    )
    
    mcp_router.register_handler(
        "finance.accounts_receivable.set_customer_importance",
        lambda msg: _handle_set_customer_importance(msg, accounts_receivable_optimizer)
    )
    
    # Register invoice handlers
    mcp_router.register_handler(
        "finance.invoice.create",
        lambda msg: _handle_create_invoice(msg, working_capital_optimizer.neo4j_client)
    )
    
    mcp_router.register_handler(
        "finance.invoice.get_by_type",
        lambda msg: _handle_get_invoices_by_type(msg, working_capital_optimizer.neo4j_client)
    )
    
    # Register cash flow handlers
    mcp_router.register_handler(
        "finance.cash_flow.forecast",
        lambda msg: _handle_get_cash_flow_forecast(msg, working_capital_optimizer.neo4j_client)
    )
    
    logger.info("MCP handlers registered successfully")

def _handle_working_capital_optimize(msg, optimizer):
    """Handle working capital optimization request
    
    Args:
        msg: MCP message
        optimizer: Working capital optimizer instance
        
    Returns:
        dict: Response message
    """
    try:
        payload = json.loads(msg.get("payload", "{}"))
        scenario = payload.get("scenario", "base")
        
        result = optimizer.optimize(scenario=scenario)
        
        return {
            "status": "success",
            "payload": json.dumps(result)
        }
    except Exception as e:
        logger.error(f"Error in working capital optimization: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

def _handle_set_objective_weights(msg, optimizer):
    """Handle setting objective weights
    
    Args:
        msg: MCP message
        optimizer: Working capital optimizer instance
        
    Returns:
        dict: Response message
    """
    try:
        payload = json.loads(msg.get("payload", "{}"))
        weights = payload.get("weights", {})
        
        optimizer.set_objective_weights(weights)
        
        return {
            "status": "success",
            "payload": json.dumps({"weights": weights})
        }
    except Exception as e:
        logger.error(f"Error setting objective weights: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

def _handle_accounts_payable_optimize(msg, optimizer):
    """Handle accounts payable optimization request
    
    Args:
        msg: MCP message
        optimizer: Accounts payable optimizer instance
        
    Returns:
        dict: Response message
    """
    try:
        payload = json.loads(msg.get("payload", "{}"))
        cash_position = payload.get("cash_position", 0)
        
        result = optimizer.optimize_payment_schedule(cash_position=cash_position)
        
        return {
            "status": "success",
            "payload": json.dumps(result)
        }
    except Exception as e:
        logger.error(f"Error in accounts payable optimization: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

def _handle_set_supplier_importance(msg, optimizer):
    """Handle setting supplier importance
    
    Args:
        msg: MCP message
        optimizer: Accounts payable optimizer instance
        
    Returns:
        dict: Response message
    """
    try:
        payload = json.loads(msg.get("payload", "{}"))
        supplier_id = payload.get("supplier_id")
        importance_score = payload.get("importance_score")
        
        if not supplier_id or importance_score is None:
            return {
                "status": "error",
                "error": "Missing supplier_id or importance_score"
            }
        
        optimizer.set_supplier_importance(supplier_id, importance_score)
        
        return {
            "status": "success",
            "payload": json.dumps({
                "supplier_id": supplier_id,
                "importance_score": importance_score
            })
        }
    except Exception as e:
        logger.error(f"Error setting supplier importance: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

def _handle_accounts_receivable_optimize(msg, optimizer):
    """Handle accounts receivable optimization request
    
    Args:
        msg: MCP message
        optimizer: Accounts receivable optimizer instance
        
    Returns:
        dict: Response message
    """
    try:
        payload = json.loads(msg.get("payload", "{}"))
        cash_position = payload.get("cash_position", 0)
        objective = payload.get("objective", "balanced")
        
        result = optimizer.optimize_collection_strategy(
            cash_position=cash_position,
            objective=objective
        )
        
        return {
            "status": "success",
            "payload": json.dumps(result)
        }
    except Exception as e:
        logger.error(f"Error in accounts receivable optimization: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

def _handle_set_customer_importance(msg, optimizer):
    """Handle setting customer importance
    
    Args:
        msg: MCP message
        optimizer: Accounts receivable optimizer instance
        
    Returns:
        dict: Response message
    """
    try:
        payload = json.loads(msg.get("payload", "{}"))
        customer_id = payload.get("customer_id")
        importance_score = payload.get("importance_score")
        
        if not customer_id or importance_score is None:
            return {
                "status": "error",
                "error": "Missing customer_id or importance_score"
            }
        
        optimizer.set_customer_importance(customer_id, importance_score)
        
        return {
            "status": "success",
            "payload": json.dumps({
                "customer_id": customer_id,
                "importance_score": importance_score
            })
        }
    except Exception as e:
        logger.error(f"Error setting customer importance: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

def _handle_create_invoice(msg, neo4j_client):
    """Handle creating a new invoice
    
    Args:
        msg: MCP message
        neo4j_client: Neo4j client instance
        
    Returns:
        dict: Response message
    """
    try:
        payload = json.loads(msg.get("payload", "{}"))
        
        result = neo4j_client.create_invoice(payload)
        
        if not result:
            return {
                "status": "error",
                "error": "Failed to create invoice"
            }
        
        return {
            "status": "success",
            "payload": json.dumps(result)
        }
    except Exception as e:
        logger.error(f"Error creating invoice: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

def _handle_get_invoices_by_type(msg, neo4j_client):
    """Handle getting invoices by type
    
    Args:
        msg: MCP message
        neo4j_client: Neo4j client instance
        
    Returns:
        dict: Response message
    """
    try:
        payload = json.loads(msg.get("payload", "{}"))
        invoice_type = payload.get("type")
        days_horizon = payload.get("days_horizon", 90)
        
        if not invoice_type or invoice_type not in ["AR", "AP"]:
            return {
                "status": "error",
                "error": "Missing or invalid invoice type"
            }
        
        invoices = neo4j_client.get_invoices_by_type(invoice_type, days_horizon)
        
        return {
            "status": "success",
            "payload": json.dumps(invoices)
        }
    except Exception as e:
        logger.error(f"Error getting invoices: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

def _handle_get_cash_flow_forecast(msg, neo4j_client):
    """Handle getting cash flow forecast
    
    Args:
        msg: MCP message
        neo4j_client: Neo4j client instance
        
    Returns:
        dict: Response message
    """
    try:
        payload = json.loads(msg.get("payload", "{}"))
        days_horizon = payload.get("days_horizon", 90)
        
        forecast = neo4j_client.get_cash_flow_forecast(days_horizon)
        
        return {
            "status": "success",
            "payload": json.dumps(forecast)
        }
    except Exception as e:
        logger.error(f"Error getting cash flow forecast: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
