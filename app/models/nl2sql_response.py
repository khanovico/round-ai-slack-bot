from typing import List, Dict
from pydantic import BaseModel, Field

class NL2SQLResponse(BaseModel):
    """Structured response from NL2SQL Agent for CSV export"""
    interpreted_answer: str = Field(description="Human-readable interpretation of the query results")
    sql_query: str = Field(description="The SQL query that was executed")
    exec_result: List[Dict] = Field(description="sql query execution results in the json format so that can be easily exported as csv file")