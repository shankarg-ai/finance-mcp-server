"""
Accounts Receivable Optimization Model
Implements the mathematical model for AR optimization
"""
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AccountsReceivableOptimizer:
    """
    Accounts Receivable Optimization model that determines optimal collection strategies
    to balance cash flow acceleration, customer relationships, and collection costs
    """
    
    def __init__(self, neo4j_client):
        """Initialize the Accounts Receivable Optimizer
        
        Args:
            neo4j_client: Neo4j database client for data access
        """
        self.neo4j_client = neo4j_client
        self.horizon_days = 90
        self.borrowing_rate = 0.0001  # Daily borrowing rate
        self.customer_importance = {}  # Dictionary of customer importance scores
        self.collection_actions = {
            'reminder_email': {
                'cost': 1,
                'effectiveness': 0.3,  # Probability of accelerating payment
                'relationship_impact': -0.1  # Slight negative impact
            },
            'phone_call': {
                'cost': 10,
                'effectiveness': 0.5,
                'relationship_impact': -0.3
            },
            'personal_visit': {
                'cost': 50,
                'effectiveness': 0.7,
                'relationship_impact': -0.5
            },
            'early_payment_discount': {
                'cost': 0,  # Cost is calculated as percentage of invoice
                'effectiveness': 0.6,
                'relationship_impact': 0.2  # Positive impact
            },
            'late_payment_penalty': {
                'cost': 0,  # Cost is calculated as percentage of invoice
                'effectiveness': 0.4,
                'relationship_impact': -0.6
            },
            'collection_agency': {
                'cost': 0,  # Cost is calculated as percentage of invoice
                'effectiveness': 0.8,
                'relationship_impact': -0.9
            }
        }
        
    def set_customer_importance(self, customer_id, importance_score):
        """Set the importance score for a customer
        
        Args:
            customer_id (str): Customer ID
            importance_score (float): Importance score (0-1)
        """
        if not 0 <= importance_score <= 1:
            raise ValueError("Importance score must be between 0 and 1")
            
        self.customer_importance[customer_id] = importance_score
        logger.info(f"Set importance score for customer {customer_id} to {importance_score}")
        
    def get_receivable_invoices(self):
        """Get all receivable invoices within the optimization horizon
        
        Returns:
            list: List of receivable invoices
        """
        return self.neo4j_client.get_invoices_by_type('AR', self.horizon_days)
        
    def optimize_collection_strategy(self, cash_position, cash_forecast=None, objective='balanced'):
        """Optimize the collection strategy for accounts receivable
        
        Args:
            cash_position (float): Current cash position
            cash_forecast (pd.DataFrame, optional): Cash flow forecast
            objective (str): Optimization objective - 'cash_flow', 'relationship', or 'balanced'
            
        Returns:
            dict: Optimized collection strategy
        """
        logger.info(f"Optimizing accounts receivable collection strategy with objective: {objective}")
        
        # Get receivable invoices
        invoices = self.get_receivable_invoices()
        
        # If no cash forecast provided, get it from the database
        if cash_forecast is None:
            forecast_data = self.neo4j_client.get_cash_flow_forecast(self.horizon_days)
            cash_forecast = pd.DataFrame(forecast_data)
            
        # Create collection strategy
        collection_strategy = []
        
        # Set objective weights based on selected objective
        if objective == 'cash_flow':
            weights = {
                'cash_acceleration': 0.7,
                'relationship': 0.1,
                'cost': 0.2
            }
        elif objective == 'relationship':
            weights = {
                'cash_acceleration': 0.3,
                'relationship': 0.6,
                'cost': 0.1
            }
        else:  # balanced
            weights = {
                'cash_acceleration': 0.5,
                'relationship': 0.3,
                'cost': 0.2
            }
        
        # Prioritize invoices
        prioritized_invoices = self._prioritize_invoices(invoices, cash_position, cash_forecast)
        
        # Process each invoice
        for invoice in prioritized_invoices:
            inv = invoice['invoice']
            priority = invoice['priority']
            customer_id = invoice['customer_id']
            days_overdue = invoice['days_overdue']
            
            # Get invoice details
            amount = inv['amount']
            due_date = datetime.strptime(inv['dueDate'], '%Y-%m-%d').date()
            today = datetime.now().date()
            
            # Determine optimal collection actions based on invoice characteristics
            optimal_actions = self._determine_optimal_actions(
                amount, due_date, days_overdue, customer_id, priority, weights
            )
            
            # Calculate expected benefit
            expected_collection_date = self._calculate_expected_collection_date(
                due_date, optimal_actions
            )
            
            # Calculate financial impact
            financial_impact = self._calculate_financial_impact(
                amount, due_date, expected_collection_date
            )
            
            # Add to collection strategy
            collection_strategy.append({
                'invoice_id': inv['id'],
                'customer_id': customer_id,
                'amount': amount,
                'due_date': due_date.strftime('%Y-%m-%d'),
                'days_overdue': days_overdue,
                'priority': priority,
                'actions': optimal_actions,
                'expected_collection_date': expected_collection_date.strftime('%Y-%m-%d'),
                'financial_impact': financial_impact
            })
        
        # Calculate metrics
        total_receivable = sum(inv['invoice']['amount'] for inv in prioritized_invoices)
        total_actions_cost = sum(
            sum(action['cost'] for action in strategy['actions'])
            for strategy in collection_strategy
        )
        total_financial_impact = sum(strategy['financial_impact'] for strategy in collection_strategy)
        
        return {
            'collection_strategy': collection_strategy,
            'metrics': {
                'total_receivable': total_receivable,
                'total_actions_cost': total_actions_cost,
                'total_financial_impact': total_financial_impact,
                'roi': (total_financial_impact / total_actions_cost) if total_actions_cost > 0 else 0
            }
        }
    
    def _prioritize_invoices(self, invoices, cash_position, cash_forecast):
        """Prioritize invoices based on due date, amount, and customer importance
        
        Args:
            invoices (list): List of invoices
            cash_position (float): Current cash position
            cash_forecast (pd.DataFrame): Cash flow forecast
            
        Returns:
            list: Prioritized list of invoices with priority scores
        """
        prioritized = []
        
        for invoice in invoices:
            inv = invoice['i']
            
            # Get customer ID
            customer_id = None
            customer_query = """
            MATCH (c:Customer)-[:HAS_INVOICE]->(i:Invoice {id: $invoice_id})
            RETURN c.id AS customer_id
            """
            customer_result = self.neo4j_client.run_query(customer_query, {"invoice_id": inv['id']})
            if customer_result:
                customer_id = customer_result[0]['customer_id']
            
            # Calculate days overdue
            due_date = datetime.strptime(inv['dueDate'], '%Y-%m-%d').date()
            today = datetime.now().date()
            days_overdue = (today - due_date).days
            
            # Calculate base priority based on days overdue
            if days_overdue > 90:
                # Severely overdue
                base_priority = 100
            elif days_overdue > 60:
                # Very overdue
                base_priority = 90
            elif days_overdue > 30:
                # Moderately overdue
                base_priority = 80
            elif days_overdue > 0:
                # Slightly overdue
                base_priority = 70
            elif (due_date - today).days < 7:
                # Due within a week
                base_priority = 60
            elif (due_date - today).days < 14:
                # Due within two weeks
                base_priority = 50
            else:
                # Due later
                base_priority = 40
            
            # Adjust for amount (higher amounts get higher priority)
            amount = inv['amount']
            amount_factor = min(20, amount / 5000)  # Max 20 points for amounts >= $100,000
            
            # Adjust for customer importance (inversely - less important customers get higher collection priority)
            importance = self.customer_importance.get(customer_id, 0.5)
            importance_factor = (1 - importance) * 20  # 0-20 points
            
            # Calculate final priority
            final_priority = base_priority + amount_factor + importance_factor
            
            prioritized.append({
                'invoice': inv,
                'customer_id': customer_id,
                'priority': final_priority,
                'days_overdue': days_overdue
            })
        
        # Sort by priority (highest first)
        prioritized.sort(key=lambda x: x['priority'], reverse=True)
        
        return prioritized
    
    def _determine_optimal_actions(self, amount, due_date, days_overdue, customer_id, priority, weights):
        """Determine optimal collection actions for an invoice
        
        Args:
            amount (float): Invoice amount
            due_date (datetime.date): Invoice due date
            days_overdue (int): Days the invoice is overdue
            customer_id (str): Customer ID
            priority (float): Invoice priority
            weights (dict): Objective weights
            
        Returns:
            list: Optimal collection actions
        """
        today = datetime.now().date()
        customer_importance = self.customer_importance.get(customer_id, 0.5)
        actions = []
        
        # Determine actions based on overdue status
        if days_overdue > 90:
            # Severely overdue - consider collection agency for low importance customers
            if customer_importance < 0.4:
                actions.append({
                    'type': 'collection_agency',
                    'timing': 'immediately',
                    'cost': amount * 0.25,  # 25% fee
                    'expected_benefit': amount * 0.8 * self.collection_actions['collection_agency']['effectiveness'],
                    'relationship_impact': self.collection_actions['collection_agency']['relationship_impact']
                })
            else:
                # High importance customer - personal visit
                actions.append({
                    'type': 'personal_visit',
                    'timing': 'immediately',
                    'cost': self.collection_actions['personal_visit']['cost'],
                    'expected_benefit': amount * self.collection_actions['personal_visit']['effectiveness'],
                    'relationship_impact': self.collection_actions['personal_visit']['relationship_impact'] * customer_importance
                })
        elif days_overdue > 60:
            # Very overdue - phone call and late payment penalty
            actions.append({
                'type': 'phone_call',
                'timing': 'immediately',
                'cost': self.collection_actions['phone_call']['cost'],
                'expected_benefit': amount * self.collection_actions['phone_call']['effectiveness'],
                'relationship_impact': self.collection_actions['phone_call']['relationship_impact'] * customer_importance
            })
            
            # Only add late payment penalty for lower importance customers
            if customer_importance < 0.7:
                actions.append({
                    'type': 'late_payment_penalty',
                    'timing': 'immediately',
                    'cost': 0,
                    'expected_benefit': amount * 0.02 * 30,  # 2% per month for 1 month
                    'relationship_impact': self.collection_actions['late_payment_penalty']['relationship_impact'] * customer_importance
                })
        elif days_overdue > 30:
            # Moderately overdue - reminder and phone call
            actions.append({
                'type': 'reminder_email',
                'timing': 'immediately',
                'cost': self.collection_actions['reminder_email']['cost'],
                'expected_benefit': amount * self.collection_actions['reminder_email']['effectiveness'],
                'relationship_impact': self.collection_actions['reminder_email']['relationship_impact'] * customer_importance
            })
            
            actions.append({
                'type': 'phone_call',
                'timing': '3_days_after_reminder',
                'cost': self.collection_actions['phone_call']['cost'],
                'expected_benefit': amount * self.collection_actions['phone_call']['effectiveness'],
                'relationship_impact': self.collection_actions['phone_call']['relationship_impact'] * customer_importance
            })
        elif days_overdue > 0:
            # Slightly overdue - reminder email
            actions.append({
                'type': 'reminder_email',
                'timing': 'immediately',
                'cost': self.collection_actions['reminder_email']['cost'],
                'expected_benefit': amount * self.collection_actions['reminder_email']['effectiveness'],
                'relationship_impact': self.collection_actions['reminder_email']['relationship_impact'] * customer_importance
            })
        elif (due_date - today).days < 7:
            # Due within a week - courtesy reminder
            actions.append({
                'type': 'reminder_email',
                'timing': 'immediately',
                'cost': self.collection_actions['reminder_email']['cost'],
                'expected_benefit': amount * 0.2,  # Lower expectation for pre-due reminders
                'relationship_impact': -0.05  # Very slight negative impact
            })
        elif priority > 70 and amount > 10000:
            # High priority, large amount, not yet due - early payment discount
            actions.append({
                'type': 'early_payment_discount',
                'timing': 'offer_immediately',
                'cost': amount * 0.01,  # 1% discount
                'expected_benefit': amount * 0.99 * self.collection_actions['early_payment_discount']['effectiveness'],
                'relationship_impact': self.collection_actions['early_payment_discount']['relationship_impact']
            })
        
        # Calculate scores for each action based on weights
        for action in actions:
            action['score'] = (
                weights['cash_acceleration'] * action['expected_benefit'] +
                weights['relationship'] * action['relationship_impact'] * 1000 +
                weights['cost'] * -action['cost']
            )
        
        # Sort actions by score (highest first)
        actions.sort(key=lambda x: x['score'], reverse=True)
        
        return actions
    
    def _calculate_expected_collection_date(self, due_date, actions):
        """Calculate the expected collection date based on actions
        
        Args:
            due_date (datetime.date): Invoice due date
            actions (list): Collection actions
            
        Returns:
            datetime.date: Expected collection date
        """
        today = datetime.now().date()
        
        # Base case - if no actions, expect payment on due date
        if not actions:
            return max(today, due_date)
        
        # Calculate days reduction based on actions
        days_reduction = 0
        for action in actions:
            if action['type'] == 'reminder_email':
                days_reduction += 2
            elif action['type'] == 'phone_call':
                days_reduction += 5
            elif action['type'] == 'personal_visit':
                days_reduction += 10
            elif action['type'] == 'early_payment_discount':
                days_reduction += 15
            elif action['type'] == 'late_payment_penalty':
                days_reduction += 3
            elif action['type'] == 'collection_agency':
                days_reduction += 20
        
        # If already overdue, calculate from today
        if due_date < today:
            # Estimate collection in days_reduction days, but at least 1 day
            return today + timedelta(days=max(1, 30 - days_reduction))
        else:
            # Estimate collection days_reduction days before due date, but not before today
            expected_date = due_date - timedelta(days=days_reduction)
            return max(today, expected_date)
    
    def _calculate_financial_impact(self, amount, due_date, expected_collection_date):
        """Calculate the financial impact of accelerated collection
        
        Args:
            amount (float): Invoice amount
            due_date (datetime.date): Invoice due date
            expected_collection_date (datetime.date): Expected collection date
            
        Returns:
            float: Financial impact (positive for benefit)
        """
        # If collection is expected after due date, no acceleration benefit
        if expected_collection_date >= due_date:
            return 0
        
        # Calculate days of acceleration
        days_accelerated = (due_date - expected_collection_date).days
        
        # Calculate financing benefit (avoided borrowing cost)
        financing_benefit = amount * self.borrowing_rate * days_accelerated
        
        return financing_benefit
