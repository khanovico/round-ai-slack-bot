from typing import Dict, Any, List
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.config import settings
from app.agent.tools import SQLExecutorTool
from app.core.logging_config import get_logger


class NL2SQLAgent:
    """Natural Language to SQL Agent using OpenAI and LangChain"""
    
    def __init__(self):
        self.logger = get_logger("app.agent")
        
        self.logger.info("Initializing NL2SQL Agent...")
        
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
        
        self.logger.info("NL2SQL Agent initialized successfully")
    
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
    
    async def ask(self, question: str) -> Dict[str, Any]:
        """
        Process a natural language question and return SQL results with explanation
        """
        self.logger.info(f"Processing question: {question}")
        
        try:
            result = await self.agent_executor.ainvoke({
                "input": question
            })
            
            self.logger.info(f"Successfully processed question: {question}")
            
            return {
                "question": question,
                "answer": result.get("output", "No response generated"),
                "success": True
            }
            
        except Exception as e:
            self.logger.error(f"Error processing question '{question}': {str(e)}", exc_info=True)
            return {
                "question": question,
                "answer": f"Error processing question: {str(e)}",
                "success": False
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