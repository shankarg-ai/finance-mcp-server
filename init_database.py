#!/usr/bin/env python3
"""
Database Initialization Script for Finance MCP Application
Initializes the Neo4j database with sample data
"""
import os
import logging
import argparse
from dotenv import load_dotenv
from src.database.neo4j_client import Neo4jClient
from src.utils.data_utils import init_database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    """Main function to initialize the database"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Initialize the Neo4j database for Finance MCP Application")
    parser.add_argument("--reset", action="store_true", help="Reset the database before initialization")
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Initialize Neo4j client
    neo4j_client = Neo4jClient(
        uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        user=os.getenv("NEO4J_USER", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "password")
    )
    
    try:
        # Initialize database
        init_database(neo4j_client, reset=args.reset)
        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
    finally:
        # Close Neo4j connection
        neo4j_client.close()

if __name__ == "__main__":
    main()
