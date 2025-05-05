"""
Accounts Payable Optimization Model
Implements the mathematical model for AP optimization
"""
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AccountsPayableOptimizer:
    """
    Accounts Payable Optimization model that determines optimal payment timing
    to balance cash flow, discount capture, and supplier relationships
    """
    
    def __init__(self, neo4j_client):
        """Initialize the Accounts Payable Optimizer
        
        Args:
            neo4j_client: Neo4j database client for data access
        """
        self.neo4j_client = neo4j_client
        self.horizon_days = 90
        self.borrowing_rate = 0.0001  # Daily borrowing rate
        self.min_cash_buffer = 100000  # Minimum cash buffer to maintain
        self.supplier_importance = {}  # Dictionary of supplier importance scores
        
    def set_supplier_importance(self, supplier_id, importance_score):
        """Set the importance score for a supplier
        
        Args:
            supplier_id (str): Supplier ID
            importance_score (float): Importance score (0-1)
        """
        if not 0 <= importance_score <= 1:
            raise ValueError("Importance score must be between 0 and 1")
            
        self.supplier_importance[supplier_id] = importance_score
        logger.info(f"Set importance score for supplier {supplier_id} to {importance_score}")
        
    def get_payable_invoices(self):
        """Get all payable invoices within the optimization horizon
        
        Returns:
            list: List of payable invoices
        """
        return self.neo4j_client.get_invoices_by_type('AP', self.horizon_days)
        
    def optimize_payment_schedule(self, cash_position, cash_forecast=None):
        """Optimize the payment schedule for accounts payable
        
        Args:
            cash_position (float): Current cash position
            cash_forecast (pd.DataFrame, optional): Cash flow forecast
            
        Returns:
            dict: Optimized payment schedule
        """
        logger.info("Optimizing accounts payable payment schedule")
        
        # Get payable invoices
        invoices = self.get_payable_invoices()
        
        # If no cash forecast provided, get it from the database
        if cash_forecast is None:
            forecast_data = self.neo4j_client.get_cash_flow_forecast(self.horizon_days)
            cash_forecast = pd.DataFrame(forecast_data)
            
        # Create payment schedule
        payment_schedule = []
        
        # Track remaining cash
        remaining_cash = cash_position
        
        # Sort invoices by priority
        prioritized_invoices = self._prioritize_invoices(invoices)
        
        # Process each invoice
        for invoice in prioritized_invoices:
            inv = invoice['invoice']
            priority = invoice['priority']
            supplier_id = invoice['supplier_id']
            
            # Get invoice details
            amount = inv['amount']
            due_date = datetime.strptime(inv['dueDate'], '%Y-%m-%d').date()
            today = datetime.now().date()
            days_until_due = (due_date - today).days
            
            # Check if early payment discount is available
            has_discount = False
            discount_amount = 0
            discount_date = None
            
            if 'earlyPaymentDate' in inv and 'discountRate' in inv:
                has_discount = True
                discount_rate = inv['discountRate']
                discount_amount = amount * discount_rate
                discount_date = datetime.strptime(inv['earlyPaymentDate'], '%Y-%m-%d').date()
                days_until_discount = (discount_date - today).days
            
            # Determine optimal payment date
            if has_discount:
                # Calculate benefit of taking discount
                discount_benefit = discount_amount
                
                # Calculate cost of early payment (opportunity cost)
                days_early = days_until_due - days_until_discount
                opportunity_cost = amount * self.borrowing_rate * days_early
                
                # If discount benefit exceeds opportunity cost, pay by discount date
                if discount_benefit > opportunity_cost and remaining_cash >= amount:
                    payment_date = discount_date
                    payment_amount = amount - discount_amount
                    payment_type = "early_with_discount"
                    remaining_cash -= payment_amount
                else:
                    # Pay on due date
                    payment_date = due_date
                    payment_amount = amount
                    payment_type = "on_due_date"
                    remaining_cash -= payment_amount
            else:
                # No discount available
                
                # Check supplier importance
                importance = self.supplier_importance.get(supplier_id, 0.5)
                
                if importance > 0.8:
                    # High importance supplier - pay on time or early
                    if days_until_due <= 5 and remaining_cash >= amount:
                        payment_date = today
                        payment_type = "early_important_supplier"
                    else:
                        payment_date = due_date
                        payment_type = "on_due_date"
                    payment_amount = amount
                    remaining_cash -= payment_amount
                elif remaining_cash < self.min_cash_buffer + amount:
                    # Cash is tight - delay payment if possible
                    delay_days = min(10, max(1, int(30 * (1 - importance))))
                    payment_date = due_date + timedelta(days=delay_days)
                    payment_amount = amount
                    payment_type = "delayed_cash_constraint"
                else:
                    # Normal payment on due date
                    payment_date = due_date
                    payment_amount = amount
                    payment_type = "on_due_date"
                    remaining_cash -= payment_amount
            
            # Add to payment schedule
            payment_schedule.append({
                'invoice_id': inv['id'],
                'supplier_id': supplier_id,
                'amount': amount,
                'payment_amount': payment_amount,
                'due_date': due_date.strftime('%Y-%m-%d'),
                'payment_date': payment_date.strftime('%Y-%m-%d'),
                'payment_type': payment_type,
                'priority': priority,
                'discount_amount': discount_amount if has_discount else 0
            })
        
        # Calculate metrics
        total_payable = sum(inv['invoice']['amount'] for inv in prioritized_invoices)
        total_discount = sum(payment['discount_amount'] for payment in payment_schedule)
        on_time_payments = sum(1 for payment in payment_schedule 
                              if payment['payment_type'] != 'delayed_cash_constraint')
        on_time_percentage = (on_time_payments / len(payment_schedule)) * 100 if payment_schedule else 0
        
        return {
            'payment_schedule': payment_schedule,
            'metrics': {
                'total_payable': total_payable,
                'total_discount_captured': total_discount,
                'discount_percentage': (total_discount / total_payable) * 100 if total_payable > 0 else 0,
                'on_time_percentage': on_time_percentage,
                'remaining_cash': remaining_cash
            }
        }
    
    def _prioritize_invoices(self, invoices):
        """Prioritize invoices based on due date, discount availability, and supplier importance
        
        Args:
            invoices (list): List of invoices
            
        Returns:
            list: Prioritized list of invoices with priority scores
        """
        prioritized = []
        
        for invoice in invoices:
            inv = invoice['i']
            
            # Get supplier ID
            supplier_id = None
            supplier_query = """
            MATCH (s:Supplier)-[:HAS_INVOICE]->(i:Invoice {id: $invoice_id})
            RETURN s.id AS supplier_id
            """
            supplier_result = self.neo4j_client.run_query(supplier_query, {"invoice_id": inv['id']})
            if supplier_result:
                supplier_id = supplier_result[0]['supplier_id']
            
            # Calculate base priority based on due date
            due_date = datetime.strptime(inv['dueDate'], '%Y-%m-%d').date()
            today = datetime.now().date()
            days_until_due = (due_date - today).days
            
            if days_until_due < 0:
                # Overdue
                base_priority = 100
            elif days_until_due < 7:
                # Due within a week
                base_priority = 90
            elif days_until_due < 14:
                # Due within two weeks
                base_priority = 80
            elif days_until_due < 30:
                # Due within a month
                base_priority = 70
            else:
                # Due later
                base_priority = 60
            
            # Adjust for discount availability
            if 'earlyPaymentDate' in inv and 'discountRate' in inv:
                discount_rate = inv['discountRate']
                discount_date = datetime.strptime(inv['earlyPaymentDate'], '%Y-%m-%d').date()
                days_until_discount = (discount_date - today).days
                
                if days_until_discount < 0:
                    # Discount expired
                    discount_priority = 0
                elif days_until_discount < 7:
                    # Discount expiring soon
                    discount_priority = 20 * discount_rate * 100  # e.g., 2% discount = 40 points
                else:
                    # Discount available but not urgent
                    discount_priority = 10 * discount_rate * 100
                    
                base_priority += discount_priority
            
            # Adjust for supplier importance
            importance = self.supplier_importance.get(supplier_id, 0.5)
            importance_priority = importance * 20  # 0-20 points
            
            # Calculate final priority
            final_priority = base_priority + importance_priority
            
            prioritized.append({
                'invoice': inv,
                'supplier_id': supplier_id,
                'priority': final_priority,
                'days_until_due': days_until_due
            })
        
        # Sort by priority (highest first)
        prioritized.sort(key=lambda x: x['priority'], reverse=True)
        
        return prioritized
