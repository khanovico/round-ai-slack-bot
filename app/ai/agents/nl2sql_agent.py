import json
from typing import Dict, Any, Optional
from langchain_core.output_parsers import PydanticOutputParser
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from app.core.config import settings
from app.ai.tools import SQLExecutorTool
from app.ai.history_manager.history_manager import ChatHistoryManager
from app.ai.agents.base_agent import BaseAgent
from app.models import NL2SQLResponse

from app.ai.prompts import BASIC_NL2SQL_PROMPT


class NL2SQLAgent(BaseAgent):
    """Natural Language to SQL Agent using OpenAI and LangChain with structured output"""
    
    def __init__(self, history_manager: Optional[ChatHistoryManager] = None):
        super().__init__(history_manager)
    
    def _initialize_agent(self):
        """Initialize the NL2SQL agent implementation"""
        self.llm = ChatOpenAI(
            model="gpt-4",
            api_key=settings.OPENAI_API_KEY,
            temperature=0.1
        )
        parser = PydanticOutputParser(pydantic_object=NL2SQLResponse)
        self.format_instructions = parser.get_format_instructions()
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

        system_prompt = BASIC_NL2SQL_PROMPT
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ])
        
        return create_openai_tools_agent(self.llm, self.tools, prompt)
    
    async def _process_question(self, question: str, context: str = "") -> Dict[str, Any]:
        """Process the question with the NL2SQL agent using structured output"""
        # Use context if provided, otherwise use the original question
        input_text = context if context else question
        
        try:
            # First, use the agent executor to execute SQL and get interpreted results
            agent_result = await self.agent_executor.ainvoke({
                "input": input_text,
                "format_instructions": self.format_instructions
            })
            
            agent_output = agent_result.get("output", "No response generated")
            
            # Try to parse the agent's JSON output
            try:
                # The agent should return JSON in the specified format
                if agent_output.strip().startswith('{') and agent_output.strip().endswith('}'):
                    structured_data = json.loads(agent_output)
                    structured_response = NL2SQLResponse(
                        interpreted_answer=structured_data.get("interpreted_answer", ""),
                        sql_query=structured_data.get("sql_query", ""),
                        exec_result=structured_data.get("exec_result", [])
                    )
                else:
                    # Fallback: extract from agent output text and intermediate steps
                    sql_query = ""
                    exec_result = []
                    
                    intermediate_steps = agent_result.get("intermediate_steps", [])
                    for step in intermediate_steps:
                        if len(step) >= 2:
                            action, observation = step[0], step[1]
                            if hasattr(action, 'tool') and action.tool == 'sql_executor':
                                sql_query = action.tool_input
                                
                                # Parse the observation (SQL result) to extract JSON data
                                try:
                                    if "Query Results:" in observation:
                                        json_start = observation.find('[')
                                        json_end = observation.rfind(']') + 1
                                        if json_start != -1 and json_end > json_start:
                                            exec_result = json.loads(observation[json_start:json_end])
                                except (json.JSONDecodeError, ValueError) as e:
                                    self.logger.error(f"Error parsing SQL result: {e}")
                                    exec_result = []
                                break
                    
                    structured_response = NL2SQLResponse(
                        interpreted_answer=agent_output,
                        sql_query=sql_query,
                        exec_result=exec_result
                    )
                    
            except json.JSONDecodeError as e:
                self.logger.error(f"Error parsing agent JSON output: {e}")
                # Fallback to basic structured response
                structured_response = NL2SQLResponse(
                    interpreted_answer=agent_output,
                    sql_query="",
                    exec_result=[]
                )

            self.logger.info(f"Structured output: {structured_response.model_dump()}")
            
            return {
                "answer": structured_response.interpreted_answer,
                "structured_response": structured_response.model_dump(),
                "metadata": {
                    "model": "gpt-4o", 
                    "sql_query": structured_response.sql_query,
                    "result_count": len(structured_response.exec_result),
                    "exec_result": structured_response.exec_result,
                    "tools_used": ["sql_executor"] if len(structured_response.exec_result) > 0 else []
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error in _process_question: {e}")
            error_response = NL2SQLResponse(
                interpreted_answer=f"Error processing question: {str(e)}",
                sql_query="",
                exec_result=[]
            )
            
            return {
                "answer": error_response.interpreted_answer,
                "structured_response": error_response.model_dump(),
                "metadata": {
                    "model": "gpt-4o",
                    "error": str(e)
                }
            }
    