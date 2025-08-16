from typing import Any, Dict, Optional
from langchain.tools import BaseTool
from langchain.callbacks.manager import CallbackManagerForToolRun
from sqlalchemy import text
from app.db import AsyncSessionLocal
import asyncio
import json


class SQLExecutorTool(BaseTool):
    """Tool for executing SQL queries against the app_metrics database"""
    
    name: str = "sql_executor"
    description: str = """
    Execute SQL queries against the app_metrics database.
    
    The database contains an 'app_metrics' table with these columns:
    - id (bigint): Primary key
    - app_name (text): Name of the mobile app
    - platform (text): 'iOS' or 'Android'
    - date (date): Date of the metrics
    - country (text): Country code (US, GB, DE, etc.)
    - installs (integer): Number of app installs
    - in_app_revenue (numeric): Revenue from in-app purchases in USD
    - ads_revenue (numeric): Revenue from advertisements in USD
    - ua_cost (numeric): User acquisition cost in USD
    
    Use this tool to execute SQL SELECT queries to answer questions about app performance,
    revenue, installs, and other metrics. Always use proper SQL syntax for PostgreSQL.
    
    Example queries:
    - "SELECT app_name, SUM(installs) FROM app_metrics GROUP BY app_name ORDER BY SUM(installs) DESC LIMIT 10"
    - "SELECT platform, AVG(in_app_revenue) FROM app_metrics WHERE date >= '2025-01-01' GROUP BY platform"
    """
    
    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute the SQL query synchronously by calling the async version"""
        return asyncio.run(self._arun(query, run_manager))
    
    async def _arun(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute the SQL query against the database"""
        try:
            # Basic security check - only allow SELECT statements
            query_lower = query.lower().strip()
            if not query_lower.startswith('select'):
                return "Error: Only SELECT queries are allowed for security reasons."
            
            # Check for dangerous keywords
            dangerous_keywords = ['drop', 'delete', 'insert', 'update', 'alter', 'create', 'truncate']
            if any(keyword in query_lower for keyword in dangerous_keywords):
                return "Error: Query contains potentially dangerous keywords. Only SELECT queries are allowed."
            
            async with AsyncSessionLocal() as session:
                result = await session.execute(text(query))
                rows = result.fetchall()
                columns = result.keys()
                
                if not rows:
                    return "Query executed successfully but returned no results."
                
                # Convert results to a readable format
                results = []
                for row in rows:
                    row_dict = dict(zip(columns, row))
                    results.append(row_dict)
                
                # Limit output to prevent overwhelming the context
                if len(results) > 100:
                    results = results[:100]
                    truncated_msg = f"\n\n(Results truncated to 100 rows out of {len(rows)} total)"
                else:
                    truncated_msg = ""
                
                # Format the output nicely
                output = json.dumps(results, indent=2, default=str)
                return f"Query Results:\n{output}{truncated_msg}"
                
        except Exception as e:
            return f"Error executing query: {str(e)}"