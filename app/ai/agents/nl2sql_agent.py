from typing import Dict, Any, Optional
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from app.core.config import settings
from app.ai.tools import SQLExecutorTool
from app.ai.history_manager.history_manager import ChatHistoryManager
from app.ai.agents.base_agent import BaseAgent


class NL2SQLAgent(BaseAgent):
    """Natural Language to SQL Agent using OpenAI and LangChain"""
    
    def __init__(self, history_manager: Optional[ChatHistoryManager] = None):
        super().__init__(history_manager)
    
    def _initialize_agent(self):
        """Initialize the NL2SQL agent implementation"""
        self.llm = ChatOpenAI(
            model="gpt-4",
            api_key=settings.OPENAI_API_KEY,
            temperature=0.1
        )
        self.tools = [SQLExecutorTool()]
        self.agent = self._create_agent()
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            max_iterations=3,
            early_stopping_method="generate"
        )
    
    def _create_agent(self):
        """Create the OpenAI tools agent"""
        system_prompt = """
        You are an expert SQL analyst for a mobile app analytics database. Your job is to:
        
        1. Convert natural language questions into SQL queries
        2. Execute those queries using the sql_executor tool
        3. Interpret and explain the results in a clear, business-friendly way
        
        The database contains app metrics with the following schema:
        
        Table: app_metrics
        - id (bigint): Primary key
        - app_name (text): Name of the mobile app
        - platform (text): 'iOS' or 'Android'  
        - date (date): Date of the metrics
        - country (text): Country code (US, GB, DE, FR, CA, AU, etc.)
        - installs (integer): Number of app installs
        - in_app_revenue (numeric): Revenue from in-app purchases in USD
        - ads_revenue (numeric): Revenue from advertisements in USD
        - ua_cost (numeric): User acquisition cost in USD
        
        Guidelines:
        - Always use the sql_executor tool to run queries
        - Write efficient PostgreSQL queries
        - Use appropriate aggregations (SUM, AVG, COUNT) for metrics
        - Include proper date filtering when analyzing trends
        - Group by relevant dimensions (app_name, platform, country, date)
        - Order results meaningfully (usually by metrics DESC)
        - Limit results when showing top/bottom lists
        - Always explain what the results mean in business terms
        
        When users ask questions like:
        - "What are the top performing apps?" -> Query by total installs or revenue
        - "How is iOS vs Android performing?" -> Group by platform and compare metrics
        - "What's the trend over time?" -> Group by date and show time series
        - "Which countries generate most revenue?" -> Group by country and sum revenues
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ])
        
        return create_openai_tools_agent(self.llm, self.tools, prompt)
    
    async def _process_question(self, question: str, context: str = "") -> Dict[str, Any]:
        """Process the question with the NL2SQL agent"""
        # Use context if provided, otherwise use the original question
        input_text = context if context else question
        
        # Process with the agent executor
        result = await self.agent_executor.ainvoke({
            "input": input_text
        })
        
        answer = result.get("output", "No response generated")
        
        return {
            "answer": answer,
            "metadata": {
                "model": "gpt-4",
                "tools_used": ["sql_executor"] if "sql_executor" in str(result) else [],
                "agent_result": result
            }
        }
    
    def ask_sync(self, question: str) -> Dict[str, Any]:
        """
        Synchronous version of ask method
        """
        try:
            result = self.agent_executor.invoke({
                "input": question
            })
            
            return {
                "question": question,
                "answer": result.get("output", "No response generated"),
                "success": True
            }
            
        except Exception as e:
            return {
                "question": question,
                "answer": f"Error processing question: {str(e)}",
                "success": False
            }