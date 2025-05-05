# Finance MCP Application

This application integrates FastMCP and Neo4j MCP to create a finance application for working capital optimization, accounts payable, and accounts receivable management.

## Overview

The Finance MCP Application provides a comprehensive solution for:
- Working Capital Optimization
- Accounts Payable (AP) Management
- Accounts Receivable (AR) Management
- Cash Flow Forecasting and Analysis

The application uses the MCP (Message Communication Protocol) architecture to enable efficient data exchange and processing.

## Features

- **FastMCP Server**: Implements a high-performance MCP server for financial data processing
- **Neo4j Graph Database**: Stores financial relationships between entities (customers, suppliers, invoices)
- **Financial Optimization Models**: Implements mathematical models for working capital, AP, and AR optimization
- **API Endpoints**: FastAPI for interacting with the financial models
- **Google Agent Dev Kit Integration**: Embeds the MCP server into Google Agent Dev Kit

## Installation

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up environment variables in `.env` file
4. Start the application:
   ```
   python src/main.py
   ```

## Architecture

The application follows a modular architecture:
- `src/models/`: Financial data models and optimization algorithms
- `src/api/`: API endpoints and FastMCP server implementation
- `src/database/`: Neo4j database connection and graph models
- `src/utils/`: Utility functions and helpers

## Usage

See the API documentation at `/docs` after starting the server for detailed usage instructions.
