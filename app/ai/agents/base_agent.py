"""
Base agent class for all agent implementations
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, TYPE_CHECKING
from app.core.logging_config import get_logger
import time
from app.ai.history_manager import ChatHistoryManager


class BaseAgent(ABC):
    """Abstract base class for all agents"""
    
    def __init__(self, history_manager: Optional[ChatHistoryManager] = None):
        self.logger = get_logger(f"app.agent.{self.__class__.__name__.lower()}")
        self.history_manager = history_manager
        self.logger.info(f"Initializing {self.__class__.__name__}...")
        
        # Initialize the agent implementation
        self._initialize_agent()
        
        self.logger.info(f"{self.__class__.__name__} initialized successfully")
    
    @abstractmethod
    def _initialize_agent(self):
        """Initialize the specific agent implementation"""
        pass
    
    @abstractmethod
    async def _process_question(self, question: str, context: str = "") -> Dict[str, Any]:
        """Process the question with the specific agent implementation"""
        pass
    
    async def ask(self, question: str, session_id: str = None) -> Dict[str, Any]:
        """
        Process a natural language question with session management
        """
        if session_id is None:
            error_msg = "session_id is required"
            self.logger.error(error_msg)
            return {
                "question": question,
                "answer": error_msg,
                "session_id": None,
                "success": False
            }
            
        self.logger.info(f"Processing question: {question} for session: {session_id}")
        
        try:
            # Build context with chat history if available
            conversation_input = question
            if self.history_manager and session_id:
                # Get conversation context
                from app.core.config import settings
                context = await self.history_manager.get_conversation_context(
                    session_id, 
                    limit=settings.MAX_CHAT_HISTORY_CNT
                )
                if context:
                    conversation_input = f"Previous conversation:\n{context}\n\nCurrent question: {question}"
                
                # Add user message to history
                await self.history_manager.add_message(
                    session_id, 
                    "user", 
                    question,
                    metadata={"timestamp": time.time()}
                )
            
            # Process with the specific agent implementation
            result = await self._process_question(question, conversation_input)
            
            answer = result.get("answer", "No response generated")
            
            # Add assistant response to history
            if self.history_manager and session_id:
                await self.history_manager.add_message(
                    session_id,
                    "assistant", 
                    answer,
                    metadata={
                        "timestamp": time.time(),
                        "agent_type": self.__class__.__name__,
                        **result.get("metadata", {})
                    }
                )
            
            self.logger.info(f"Successfully processed question: {question}")
            
            return {
                "question": question,
                "answer": answer,
                "session_id": session_id,
                "success": True,
                **{k: v for k, v in result.items() if k not in ["answer", "metadata"]}
            }
            
        except Exception as e:
            error_msg = f"Error processing question: {str(e)}"
            
            # Add error to history
            if self.history_manager and session_id:
                await self.history_manager.add_message(
                    session_id,
                    "system",
                    error_msg,
                    metadata={"timestamp": time.time(), "error": True}
                )
            
            self.logger.error(f"Error processing question '{question}': {str(e)}", exc_info=True)
            return {
                "question": question,
                "answer": error_msg,
                "session_id": session_id,
                "success": False
            }
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about the agent"""
        return {
            "agent_type": self.__class__.__name__,
            "has_history_manager": self.history_manager is not None,
            "description": self.__class__.__doc__ or "No description available"
        }