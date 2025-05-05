"""
Working Capital Optimization Model
Implements the mathematical model for integrated working capital optimization
"""
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class WorkingCapitalOptimizer:
    """
    Working Capital Optimization model that integrates AP and AR management
    to optimize cash flow, financing costs, and business relationships
    """
    
    def __init__(self, neo4j_client):
        """Initialize the Working Capital Optimizer
        
        Args:
            neo4j_client: Neo4j database client for data access
        """
        self.neo4j_client = neo4j_client
        self.horizon_days = 90
        self.objective_weights = {
            'liquidity': 0.4,
            'financing_cost': 0.3,
            'transaction_cost': 0.1,
            'relationship': 0.2
        }
        self.borrowing_rate = 0.0001  # Daily borrowing rate (e.g., 3.65% annual)
        self.investment_rate = 0.00005  # Daily return on excess cash
        self.min_cash_buffer = 100000  # Minimum cash buffer to maintain
        
    def set_objective_weights(self, weights):
        """Set the weights for the multi-objective optimization
        
        Args:
            weights (dict): Dictionary of objective weights
        """
        # Validate weights
        required_keys = ['liquidity', 'financing_cost', 'transaction_cost', 'relationship']
        if not all(key in weights for key in required_keys):
            raise ValueError(f"Weights must include all objectives: {required_keys}")
            
        # Normalize weights to sum to 1
        total = sum(weights.values())
        self.objective_weights = {k: v/total for k, v in weights.items()}
        logger.info(f"Set objective weights to {self.objective_weights}")
        
    def get_cash_flow_forecast(self):
        """Get the cash flow forecast for the optimization horizon
        
        Returns:
            pd.DataFrame: Cash flow forecast with dates, inflows, and outflows
        """
        # Get forecast from Neo4j
        forecast_data = self.neo4j_client.get_cash_flow_forecast(self.horizon_days)
        
        # Convert to DataFrame
        df = pd.DataFrame(forecast_data)
        
        # Ensure all dates in horizon are included
        date_range = pd.date_range(start=datetime.now().date(), periods=self.horizon_days)
        date_df = pd.DataFrame({'date': date_range})
        
        # Merge with forecast data
        result = pd.merge(date_df, df, on='date', how='left')
        result.fillna(0, inplace=True)
        
        return result
        
    def optimize(self, scenario='base'):
        """Run the working capital optimization model
        
        Args:
            scenario (str): Scenario to optimize for (base, conservative, aggressive)
            
        Returns:
            dict: Optimization results including recommendations
        """
        logger.info(f"Running working capital optimization for scenario: {scenario}")
        
        # Get cash flow forecast
        forecast = self.get_cash_flow_forecast()
        
        # Get AR and AP invoices
        ar_invoices = self.neo4j_client.get_invoices_by_type('AR', self.horizon_days)
        ap_invoices = self.neo4j_client.get_invoices_by_type('AP', self.horizon_days)
        
        # Apply scenario adjustments
        if scenario == 'conservative':
            # More conservative: reduce expected AR collections, increase AP
            ar_adjustment = 0.9  # Expect only 90% of AR to be collected on time
            ap_adjustment = 1.0  # Pay all AP on time
            self.min_cash_buffer *= 1.5  # Increase cash buffer
        elif scenario == 'aggressive':
            # More aggressive: increase expected AR collections, delay AP
            ar_adjustment = 1.0  # Expect all AR to be collected
            ap_adjustment = 0.8  # Only pay 80% of AP on time
            self.min_cash_buffer *= 0.7  # Reduce cash buffer
        else:  # base scenario
            ar_adjustment = 0.95
            ap_adjustment = 0.95
        
        # Simulate cash flow with adjustments
        initial_cash = 500000  # Example initial cash position
        cash_balance = [initial_cash]
        borrowing = [0]
        
        for i in range(len(forecast) - 1):
            inflow = forecast.iloc[i]['inflow'] * ar_adjustment
            outflow = forecast.iloc[i]['outflow'] * ap_adjustment
            
            # Calculate new cash balance
            new_balance = cash_balance[-1] + inflow - outflow
            
            # If balance falls below minimum, borrow
            if new_balance < self.min_cash_buffer:
                borrowed_amount = self.min_cash_buffer - new_balance
                new_balance = self.min_cash_buffer
                borrowing.append(borrowed_amount)
            else:
                borrowing.append(0)
                
            cash_balance.append(new_balance)
        
        # Calculate metrics
        avg_cash = np.mean(cash_balance)
        min_cash = np.min(cash_balance)
        total_borrowing = np.sum(borrowing)
        borrowing_cost = total_borrowing * self.borrowing_rate * self.horizon_days
        
        # Generate recommendations
        ap_recommendations = self._generate_ap_recommendations(ap_invoices, cash_balance, forecast)
        ar_recommendations = self._generate_ar_recommendations(ar_invoices, cash_balance, forecast)
        
        return {
            'scenario': scenario,
            'metrics': {
                'average_cash_balance': avg_cash,
                'minimum_cash_balance': min_cash,
                'total_borrowing': total_borrowing,
                'borrowing_cost': borrowing_cost
            },
            'recommendations': {
                'accounts_payable': ap_recommendations,
                'accounts_receivable': ar_recommendations
            },
            'cash_flow_forecast': forecast.to_dict('records'),
            'cash_balance_projection': [{'day': i, 'balance': bal} for i, bal in enumerate(cash_balance)]
        }
    
    def _generate_ap_recommendations(self, ap_invoices, cash_balance, forecast):
        """Generate recommendations for accounts payable
        
        Args:
            ap_invoices (list): List of AP invoices
            cash_balance (list): Projected cash balance
            forecast (pd.DataFrame): Cash flow forecast
            
        Returns:
            list: Recommendations for AP management
        """
        recommendations = []
        
        # Sort invoices by due date
        sorted_invoices = sorted(ap_invoices, key=lambda x: x['i']['dueDate'])
        
        for invoice in sorted_invoices:
            inv = invoice['i']
            due_date = inv['dueDate']
            amount = inv['amount']
            
            # Find index in forecast corresponding to due date
            due_index = forecast.index[forecast['date'] == due_date].tolist()
            if not due_index:
                continue
            due_index = due_index[0]
            
            # Check cash balance around due date
            if due_index < len(cash_balance) and cash_balance[due_index] < self.min_cash_buffer + amount:
                # Cash might be tight, recommend delay if possible
                recommendations.append({
                    'invoice_id': inv['id'],
                    'amount': amount,
                    'due_date': due_date,
                    'action': 'delay',
                    'reason': 'Cash flow constraint',
                    'recommended_payment_date': (datetime.strptime(due_date, '%Y-%m-%d') + timedelta(days=7)).strftime('%Y-%m-%d')
                })
            else:
                # Check if early payment discount is available
                if 'earlyPaymentDate' in inv and 'discountRate' in inv:
                    early_date = inv['earlyPaymentDate']
                    discount_rate = inv['discountRate']
                    discount_amount = amount * discount_rate
                    
                    # If discount benefit exceeds borrowing cost, recommend early payment
                    if discount_amount > (amount * self.borrowing_rate * 30):  # Assuming 30 days
                        recommendations.append({
                            'invoice_id': inv['id'],
                            'amount': amount,
                            'due_date': due_date,
                            'action': 'pay_early',
                            'reason': 'Discount benefit exceeds financing cost',
                            'recommended_payment_date': early_date,
                            'discount_amount': discount_amount
                        })
                    else:
                        recommendations.append({
                            'invoice_id': inv['id'],
                            'amount': amount,
                            'due_date': due_date,
                            'action': 'pay_on_time',
                            'reason': 'Optimal cash management',
                            'recommended_payment_date': due_date
                        })
                else:
                    recommendations.append({
                        'invoice_id': inv['id'],
                        'amount': amount,
                        'due_date': due_date,
                        'action': 'pay_on_time',
                        'reason': 'Maintain supplier relationship',
                        'recommended_payment_date': due_date
                    })
        
        return recommendations
    
    def _generate_ar_recommendations(self, ar_invoices, cash_balance, forecast):
        """Generate recommendations for accounts receivable
        
        Args:
            ar_invoices (list): List of AR invoices
            cash_balance (list): Projected cash balance
            forecast (pd.DataFrame): Cash flow forecast
            
        Returns:
            list: Recommendations for AR management
        """
        recommendations = []
        
        # Sort invoices by due date
        sorted_invoices = sorted(ar_invoices, key=lambda x: x['i']['dueDate'])
        
        for invoice in sorted_invoices:
            inv = invoice['i']
            due_date = inv['dueDate']
            amount = inv['amount']
            
            # Find index in forecast corresponding to due date
            due_index = forecast.index[forecast['date'] == due_date].tolist()
            if not due_index:
                continue
            due_index = due_index[0]
            
            # Check cash balance around due date
            if due_index < len(cash_balance) and cash_balance[due_index] < self.min_cash_buffer:
                # Cash might be tight, recommend aggressive collection
                recommendations.append({
                    'invoice_id': inv['id'],
                    'amount': amount,
                    'due_date': due_date,
                    'action': 'accelerate',
                    'reason': 'Cash flow constraint',
                    'recommended_actions': [
                        {'type': 'reminder', 'timing': 'immediately', 'priority': 'high'},
                        {'type': 'call', 'timing': '3_days_before_due', 'priority': 'high'}
                    ]
                })
            else:
                # Normal collection process
                recommendations.append({
                    'invoice_id': inv['id'],
                    'amount': amount,
                    'due_date': due_date,
                    'action': 'standard',
                    'reason': 'Regular collection process',
                    'recommended_actions': [
                        {'type': 'reminder', 'timing': '7_days_before_due', 'priority': 'normal'},
                        {'type': 'reminder', 'timing': '1_day_after_due', 'priority': 'normal'}
                    ]
                })
                
                # If invoice is large, add additional recommendation
                if amount > 50000:
                    recommendations[-1]['recommended_actions'].append(
                        {'type': 'call', 'timing': '3_days_after_due', 'priority': 'high'}
                    )
        
        return recommendations
