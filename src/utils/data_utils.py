"""
Data Utilities for Finance MCP Application
Helper functions for data manipulation and initialization
"""
import logging
import random
from datetime import datetime, timedelta
from database.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)

def generate_sample_data(neo4j_client: Neo4jClient):
    """Generate sample data for the finance application
    
    Args:
        neo4j_client: Neo4j client instance
    """
    logger.info("Generating sample data")
    
    # Create sample customers
    customers = [
        {"id": "cust001", "name": "Acme Corp", "credit_score": 85},
        {"id": "cust002", "name": "Beta Industries", "credit_score": 72},
        {"id": "cust003", "name": "Gamma Technologies", "credit_score": 90},
        {"id": "cust004", "name": "Delta Services", "credit_score": 65},
        {"id": "cust005", "name": "Epsilon Enterprises", "credit_score": 78}
    ]
    
    # Create sample suppliers
    suppliers = [
        {"id": "supp001", "name": "Alpha Materials", "reliability": 92},
        {"id": "supp002", "name": "Bravo Components", "reliability": 88},
        {"id": "supp003", "name": "Charlie Manufacturing", "reliability": 75},
        {"id": "supp004", "name": "Delta Logistics", "reliability": 82},
        {"id": "supp005", "name": "Echo Electronics", "reliability": 95}
    ]
    
    # Create customers in Neo4j
    for customer in customers:
        query = """
        CREATE (c:Customer {
            id: $id,
            name: $name,
            credit_score: $credit_score
        })
        RETURN c
        """
        neo4j_client.run_query(query, customer)
    
    # Create suppliers in Neo4j
    for supplier in suppliers:
        query = """
        CREATE (s:Supplier {
            id: $id,
            name: $name,
            reliability: $reliability
        })
        RETURN s
        """
        neo4j_client.run_query(query, supplier)
    
    # Generate sample AR invoices
    today = datetime.now().date()
    
    for i in range(20):
        customer = random.choice(customers)
        amount = random.uniform(5000, 50000)
        issue_date = today - timedelta(days=random.randint(0, 60))
        due_date = issue_date + timedelta(days=30)  # 30-day terms
        
        invoice_data = {
            "id": f"AR{i+1:04d}",
            "amount": round(amount, 2),
            "issueDate": issue_date.strftime('%Y-%m-%d'),
            "dueDate": due_date.strftime('%Y-%m-%d'),
            "type": "AR",
            "entityId": customer["id"]
        }
        
        neo4j_client.create_invoice(invoice_data)
    
    # Generate sample AP invoices
    for i in range(15):
        supplier = random.choice(suppliers)
        amount = random.uniform(3000, 40000)
        issue_date = today - timedelta(days=random.randint(0, 45))
        due_date = issue_date + timedelta(days=45)  # 45-day terms
        
        # Add early payment discount to some invoices
        if random.random() < 0.3:
            early_payment_date = issue_date + timedelta(days=10)
            discount_rate = 0.02  # 2% discount
        else:
            early_payment_date = None
            discount_rate = None
        
        invoice_data = {
            "id": f"AP{i+1:04d}",
            "amount": round(amount, 2),
            "issueDate": issue_date.strftime('%Y-%m-%d'),
            "dueDate": due_date.strftime('%Y-%m-%d'),
            "type": "AP",
            "entityId": supplier["id"]
        }
        
        if early_payment_date:
            invoice_data["earlyPaymentDate"] = early_payment_date.strftime('%Y-%m-%d')
            invoice_data["discountRate"] = discount_rate
        
        neo4j_client.create_invoice(invoice_data)
    
    logger.info("Sample data generation complete")

def clear_database(neo4j_client: Neo4jClient):
    """Clear all data from the database
    
    Args:
        neo4j_client: Neo4j client instance
    """
    logger.info("Clearing database")
    
    query = """
    MATCH (n)
    DETACH DELETE n
    """
    
    neo4j_client.run_query(query)
    
    logger.info("Database cleared")

def init_database(neo4j_client: Neo4jClient, reset=False):
    """Initialize the database with sample data
    
    Args:
        neo4j_client: Neo4j client instance
        reset: Whether to reset the database first
    """
    # Connect to Neo4j
    neo4j_client.connect()
    
    # Clear database if requested
    if reset:
        clear_database(neo4j_client)
    
    # Check if database already has data
    query = "MATCH (n) RETURN count(n) as count"
    result = neo4j_client.run_query(query)
    
    if result[0]["count"] == 0:
        # Generate sample data
        generate_sample_data(neo4j_client)
    else:
        logger.info(f"Database already contains {result[0]['count']} nodes. Skipping data generation.")
