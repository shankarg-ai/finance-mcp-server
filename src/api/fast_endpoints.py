"""
FastAPI Endpoints for Finance MCP Application
Provides HTTP endpoints for interacting with the financial models
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional, Union
from datetime import date, datetime
from enum import Enum

# Import database and models
from database.neo4j_client import Neo4jClient
from models.working_capital import WorkingCapitalOptimizer
from models.accounts_payable import AccountsPayableOptimizer
from models.accounts_receivable import AccountsReceivableOptimizer

logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(tags=["Finance API"])

# Enums for validation
class InvoiceType(str, Enum):
    AR = "AR"
    AP = "AP"

class OptimizationScenario(str, Enum):
    BASE = "base"
    CONSERVATIVE = "conservative"
    AGGRESSIVE = "aggressive"

class OptimizationObjective(str, Enum):
    CASH_FLOW = "cash_flow"
    RELATIONSHIP = "relationship"
    BALANCED = "balanced"

# Pydantic models for request/response
class InvoiceCreate(BaseModel):
    """Model for creating a new invoice"""
    amount: float = Field(..., gt=0, description="Invoice amount (must be positive)")
    dueDate: str = Field(..., description="Due date in YYYY-MM-DD format")
    issueDate: str = Field(..., description="Issue date in YYYY-MM-DD format")
    type: InvoiceType = Field(..., description="Invoice type - 'AR' or 'AP'")
    entityId: str = Field(..., description="ID of customer (AR) or supplier (AP)")
    earlyPaymentDate: Optional[str] = Field(None, description="Early payment date for discount")
    discountRate: Optional[float] = Field(None, ge=0, le=1, description="Discount rate for early payment (0-1)")

    @validator('dueDate', 'issueDate', 'earlyPaymentDate')
    def validate_date_format(cls, v):
        if v is None:
            return v
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('Date must be in YYYY-MM-DD format')

    @validator('earlyPaymentDate')
    def validate_early_payment_date(cls, v, values):
        if v is None:
            return v
        if 'issueDate' in values and 'dueDate' in values:
            issue_date = datetime.strptime(values['issueDate'], '%Y-%m-%d')
            due_date = datetime.strptime(values['dueDate'], '%Y-%m-%d')
            early_date = datetime.strptime(v, '%Y-%m-%d')
            if early_date < issue_date or early_date > due_date:
                raise ValueError('Early payment date must be between issue date and due date')
        return v

class OptimizationRequest(BaseModel):
    """Model for optimization request"""
    cashPosition: float = Field(..., ge=0, description="Current cash position")
    scenario: OptimizationScenario = Field(OptimizationScenario.BASE, description="Optimization scenario")
    objective: OptimizationObjective = Field(OptimizationObjective.BALANCED, description="Optimization objective")

class ObjectiveWeights(BaseModel):
    """Model for objective weights"""
    liquidity: float = Field(..., ge=0, le=1, description="Weight for liquidity objective")
    financing_cost: float = Field(..., ge=0, le=1, description="Weight for financing cost objective")
    transaction_cost: float = Field(..., ge=0, le=1, description="Weight for transaction cost objective")
    relationship: float = Field(..., ge=0, le=1, description="Weight for relationship objective")

    @validator('liquidity', 'financing_cost', 'transaction_cost', 'relationship')
    def validate_weights_sum(cls, v, values):
        # Ensure weights sum to approximately 1
        if len(values) == 3:  # This is the last field being validated
            total = v + sum(values.values())
            if not 0.99 <= total <= 1.01:
                raise ValueError('Weights must sum to approximately 1.0')
        return v

class ApiResponse(BaseModel):
    """Base API response model"""
    status: str
    data: Optional[Any] = None
    message: Optional[str] = None

# Dependency to get Neo4j client
def get_neo4j_client():
    """Get Neo4j client dependency"""
    from main import neo4j_client
    return neo4j_client

# Dependency to get optimizers
def get_working_capital_optimizer():
    """Get working capital optimizer dependency"""
    from main import working_capital_optimizer
    return working_capital_optimizer

def get_accounts_payable_optimizer():
    """Get accounts payable optimizer dependency"""
    from main import accounts_payable_optimizer
    return accounts_payable_optimizer

def get_accounts_receivable_optimizer():
    """Get accounts receivable optimizer dependency"""
    from main import accounts_receivable_optimizer
    return accounts_receivable_optimizer

# API Endpoints

@router.post("/invoices", response_model=ApiResponse, summary="Create a new invoice")
async def create_invoice(
    invoice: InvoiceCreate,
    neo4j_client: Neo4jClient = Depends(get_neo4j_client)
):
    """Create a new invoice in the system

    - **amount**: Invoice amount (must be positive)
    - **dueDate**: Due date in YYYY-MM-DD format
    - **issueDate**: Issue date in YYYY-MM-DD format
    - **type**: Invoice type - 'AR' or 'AP'
    - **entityId**: ID of customer (AR) or supplier (AP)
    - **earlyPaymentDate**: Optional early payment date for discount
    - **discountRate**: Optional discount rate for early payment (0-1)
    """
    try:
        result = neo4j_client.create_invoice(invoice.dict())
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create invoice")
        return ApiResponse(status="success", data=result, message="Invoice created successfully")
    except Exception as e:
        logger.error(f"Error creating invoice: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/invoices/{invoice_type}", response_model=ApiResponse, summary="Get invoices by type")
async def get_invoices(
    invoice_type: InvoiceType = Path(..., description="Invoice type - AR or AP"),
    days_horizon: int = Query(90, ge=1, le=365, description="Number of days to look ahead")
):
    """Get invoices by type (AR or AP) within a time horizon

    - **invoice_type**: Type of invoices to retrieve (AR or AP)
    - **days_horizon**: Number of days to look ahead (1-365)
    """
    neo4j_client = get_neo4j_client()
    try:
        invoices = neo4j_client.get_invoices_by_type(invoice_type, days_horizon)
        return ApiResponse(
            status="success", 
            data=invoices, 
            message=f"Retrieved {len(invoices)} {invoice_type} invoices"
        )
    except Exception as e:
        logger.error(f"Error getting invoices: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cash-flow", response_model=ApiResponse, summary="Get cash flow forecast")
async def get_cash_flow(
    days_horizon: int = Query(90, ge=1, le=365, description="Number of days to forecast")
):
    """Get cash flow forecast for the specified horizon

    - **days_horizon**: Number of days to forecast (1-365)
    """
    neo4j_client = get_neo4j_client()
    try:
        forecast = neo4j_client.get_cash_flow_forecast(days_horizon)
        return ApiResponse(
            status="success", 
            data=forecast, 
            message=f"Cash flow forecast for {days_horizon} days"
        )
    except Exception as e:
        logger.error(f"Error getting cash flow forecast: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/optimize/working-capital", response_model=ApiResponse, summary="Optimize working capital")
async def optimize_working_capital(
    request: OptimizationRequest,
    optimizer: WorkingCapitalOptimizer = Depends(get_working_capital_optimizer)
):
    """Optimize working capital management

    - **cashPosition**: Current cash position
    - **scenario**: Optimization scenario (base, conservative, aggressive)
    - **objective**: Optimization objective (cash_flow, relationship, balanced)
    """
    try:
        result = optimizer.optimize(scenario=request.scenario)
        return ApiResponse(
            status="success", 
            data=result, 
            message=f"Working capital optimized with {request.scenario} scenario"
        )
    except Exception as e:
        logger.error(f"Error optimizing working capital: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/optimize/accounts-payable", response_model=ApiResponse, summary="Optimize accounts payable")
async def optimize_accounts_payable(
    request: OptimizationRequest,
    optimizer: AccountsPayableOptimizer = Depends(get_accounts_payable_optimizer)
):
    """Optimize accounts payable payment schedule

    - **cashPosition**: Current cash position
    - **scenario**: Optimization scenario (base, conservative, aggressive)
    """
    try:
        result = optimizer.optimize_payment_schedule(cash_position=request.cashPosition)
        return ApiResponse(
            status="success", 
            data=result, 
            message="Accounts payable payment schedule optimized"
        )
    except Exception as e:
        logger.error(f"Error optimizing accounts payable: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/optimize/accounts-receivable", response_model=ApiResponse, summary="Optimize accounts receivable")
async def optimize_accounts_receivable(
    request: OptimizationRequest,
    optimizer: AccountsReceivableOptimizer = Depends(get_accounts_receivable_optimizer)
):
    """Optimize accounts receivable collection strategy

    - **cashPosition**: Current cash position
    - **objective**: Optimization objective (cash_flow, relationship, balanced)
    """
    try:
        result = optimizer.optimize_collection_strategy(
            cash_position=request.cashPosition,
            objective=request.objective
        )
        return ApiResponse(
            status="success", 
            data=result, 
            message=f"Accounts receivable collection strategy optimized with {request.objective} objective"
        )
    except Exception as e:
        logger.error(f"Error optimizing accounts receivable: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/suppliers/{supplier_id}/importance", response_model=ApiResponse, summary="Set supplier importance")
async def set_supplier_importance(
    supplier_id: str = Path(..., description="Supplier ID"),
    importance_score: float = Query(..., ge=0, le=1, description="Importance score (0-1)"),
    optimizer: AccountsPayableOptimizer = Depends(get_accounts_payable_optimizer)
):
    """Set the importance score for a supplier

    - **supplier_id**: ID of the supplier
    - **importance_score**: Importance score between 0 and 1
    """
    try:
        optimizer.set_supplier_importance(supplier_id, importance_score)
        return ApiResponse(
            status="success", 
            data={"supplier_id": supplier_id, "importance_score": importance_score}, 
            message=f"Supplier {supplier_id} importance set to {importance_score}"
        )
    except Exception as e:
        logger.error(f"Error setting supplier importance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/customers/{customer_id}/importance", response_model=ApiResponse, summary="Set customer importance")
async def set_customer_importance(
    customer_id: str = Path(..., description="Customer ID"),
    importance_score: float = Query(..., ge=0, le=1, description="Importance score (0-1)"),
    optimizer: AccountsReceivableOptimizer = Depends(get_accounts_receivable_optimizer)
):
    """Set the importance score for a customer

    - **customer_id**: ID of the customer
    - **importance_score**: Importance score between 0 and 1
    """
    try:
        optimizer.set_customer_importance(customer_id, importance_score)
        return ApiResponse(
            status="success", 
            data={"customer_id": customer_id, "importance_score": importance_score}, 
            message=f"Customer {customer_id} importance set to {importance_score}"
        )
    except Exception as e:
        logger.error(f"Error setting customer importance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/working-capital/objective-weights", response_model=ApiResponse, summary="Set objective weights")
async def set_objective_weights(
    weights: ObjectiveWeights,
    optimizer: WorkingCapitalOptimizer = Depends(get_working_capital_optimizer)
):
    """Set the weights for the multi-objective optimization

    - **liquidity**: Weight for liquidity objective (0-1)
    - **financing_cost**: Weight for financing cost objective (0-1)
    - **transaction_cost**: Weight for transaction cost objective (0-1)
    - **relationship**: Weight for relationship objective (0-1)

    Note: Weights should sum to approximately 1.0
    """
    try:
        optimizer.set_objective_weights(weights.dict())
        return ApiResponse(
            status="success", 
            data=weights.dict(), 
            message="Objective weights set successfully"
        )
    except Exception as e:
        logger.error(f"Error setting objective weights: {e}")
        raise HTTPException(status_code=500, detail=str(e))
