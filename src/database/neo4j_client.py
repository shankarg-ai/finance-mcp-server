"""
Neo4j Client for Finance MCP Application
Handles connections and queries to the Neo4j graph database
"""
import logging
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError

logger = logging.getLogger(__name__)

class Neo4jClient:
    """Client for interacting with Neo4j graph database"""
    
    def __init__(self, uri, user, password):
        """Initialize Neo4j client with connection parameters
        
        Args:
            uri (str): Neo4j connection URI
            user (str): Neo4j username
            password (str): Neo4j password
        """
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None
        
    def connect(self):
        """Connect to Neo4j database"""
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            # Verify connection
            self.driver.verify_connectivity()
            logger.info(f"Connected to Neo4j database at {self.uri}")
            
            # Initialize database with schema constraints if needed
            self._initialize_schema()
            
        except (ServiceUnavailable, AuthError) as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
            
    def close(self):
        """Close the Neo4j connection"""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")
            
    def _initialize_schema(self):
        """Initialize Neo4j schema with constraints and indexes"""
        # Create constraints for uniqueness
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Customer) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Supplier) REQUIRE s.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (i:Invoice) REQUIRE i.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Payment) REQUIRE p.id IS UNIQUE"
        ]
        
        # Create indexes for performance
        indexes = [
            "CREATE INDEX IF NOT EXISTS FOR (i:Invoice) ON (i.dueDate)",
            "CREATE INDEX IF NOT EXISTS FOR (p:Payment) ON (p.date)"
        ]
        
        with self.driver.session() as session:
            for constraint in constraints:
                session.run(constraint)
                
            for index in indexes:
                session.run(index)
                
        logger.info("Neo4j schema initialized with constraints and indexes")
    
    def run_query(self, query, parameters=None):
        """Run a Cypher query against Neo4j
        
        Args:
            query (str): Cypher query to execute
            parameters (dict, optional): Query parameters
            
        Returns:
            list: Query results
        """
        if not self.driver:
            raise RuntimeError("Not connected to Neo4j. Call connect() first.")
            
        if parameters is None:
            parameters = {}
            
        with self.driver.session() as session:
            result = session.run(query, parameters)
            return [record.data() for record in result]
            
    # Financial data specific methods
    
    def create_invoice(self, invoice_data):
        """Create a new invoice in the database
        
        Args:
            invoice_data (dict): Invoice data including id, amount, dueDate, etc.
            
        Returns:
            dict: Created invoice data
        """
        query = """
        CREATE (i:Invoice {
            id: $id,
            amount: $amount,
            dueDate: $dueDate,
            issueDate: $issueDate,
            type: $type
        })
        WITH i
        MATCH (entity)
        WHERE entity.id = $entityId AND 
              (($type = 'AR' AND entity:Customer) OR ($type = 'AP' AND entity:Supplier))
        CREATE (entity)-[r:HAS_INVOICE]->(i)
        RETURN i
        """
        
        result = self.run_query(query, invoice_data)
        return result[0] if result else None
        
    def get_invoices_by_type(self, invoice_type, days_horizon=90):
        """Get invoices by type (AR or AP) within a time horizon
        
        Args:
            invoice_type (str): Type of invoice - 'AR' or 'AP'
            days_horizon (int): Number of days to look ahead
            
        Returns:
            list: Invoices matching the criteria
        """
        query = """
        MATCH (i:Invoice)
        WHERE i.type = $type AND i.dueDate <= date() + duration({days: $horizon})
        RETURN i
        ORDER BY i.dueDate
        """
        
        return self.run_query(query, {"type": invoice_type, "horizon": days_horizon})
        
    def get_cash_flow_forecast(self, days_horizon=90):
        """Get cash flow forecast for the specified horizon
        
        Args:
            days_horizon (int): Number of days to forecast
            
        Returns:
            dict: Daily cash flow forecast
        """
        query = """
        MATCH (i:Invoice)
        WHERE i.dueDate <= date() + duration({days: $horizon})
        RETURN i.dueDate AS date, 
               sum(CASE WHEN i.type = 'AR' THEN i.amount ELSE 0 END) AS inflow,
               sum(CASE WHEN i.type = 'AP' THEN i.amount ELSE 0 END) AS outflow
        ORDER BY date
        """
        
        return self.run_query(query, {"horizon": days_horizon})
