from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.agent import NL2SQLAgent, ChatHistoryManager
from app.core.logging_config import get_logger
from app.core.config import settings

router = APIRouter(prefix="/agent", tags=["agent"])
logger = get_logger("app.agent.api")

# Initialize chat history manager
chat_history_manager = ChatHistoryManager(max_cnt=settings.MAX_CHAT_HISTORY_CNT)

# Initialize the agent
logger.info("Initializing NL2SQL Agent...")
nl2sql_agent = NL2SQLAgent(chat_history_manager)
logger.info("NL2SQL Agent initialized successfully")


class QuestionRequest(BaseModel):
    question: str
    session_id: Optional[str] = None


class QuestionResponse(BaseModel):
    question: str
    answer: str
    session_id: Optional[str] = None
    success: bool


class SessionResponse(BaseModel):
    session_id: str
    message: str


@router.post("/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """
    Ask a natural language question about app metrics.
    The agent will convert it to SQL and execute it.
    
    Examples:
    - "What are the top 10 apps by installs?"
    - "How much revenue did iOS apps generate this month?"
    - "Which countries have the highest user acquisition costs?"
    - "Show me the trend of installs over the last 30 days"
    
    If session_id is provided, the conversation history will be maintained.
    """
    logger.info(f"Received question: {request.question} for session: {request.session_id}")
    
    try:
        # Create session if not provided
        session_id = request.session_id
        if not session_id:
            session_id = await chat_history_manager.create_session()
            logger.info(f"Created new session: {session_id}")
        
        result = await nl2sql_agent.ask(request.question, session_id)
        
        if result["success"]:
            logger.info(f"Successfully processed question: {request.question}")
        else:
            logger.warning(f"Failed to process question: {request.question} - {result['answer']}")
            
        return QuestionResponse(**result)
        
    except Exception as e:
        logger.error(f"Error processing question '{request.question}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session", response_model=SessionResponse)
async def create_session():
    """Create a new chat session"""
    try:
        session_id = await chat_history_manager.create_session()
        logger.info(f"Created new session: {session_id}")
        return SessionResponse(
            session_id=session_id,
            message="Session created successfully"
        )
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}/history")
async def get_session_history(session_id: str, limit: int = 20):
    """Get chat history for a session"""
    try:
        history = await chat_history_manager.get_history(session_id, limit=limit)
        return {
            "session_id": session_id,
            "history": history,
            "count": len(history)
        }
    except Exception as e:
        logger.error(f"Error getting session history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}/stats")
async def get_session_stats(session_id: str):
    """Get session statistics"""
    try:
        stats = await chat_history_manager.get_session_stats(session_id)
        return stats
    except Exception as e:
        logger.error(f"Error getting session stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """Clear chat history for a session"""
    try:
        success = await chat_history_manager.clear_history(session_id)
        if success:
            return {"message": f"Session {session_id} cleared successfully"}
        else:
            raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        logger.error(f"Error clearing session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def list_active_sessions(limit: int = 50):
    """List active session IDs"""
    try:
        sessions = await chat_history_manager.list_active_sessions(limit=limit)
        return {
            "sessions": sessions,
            "count": len(sessions)
        }
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/examples")
async def get_example_questions():
    """Get example questions you can ask the agent"""
    return {
        "examples": [
            "What are the top 10 apps by total installs?",
            "How much total revenue did we generate last month?",
            "Compare iOS vs Android performance in terms of revenue",
            "Which countries generate the most in-app purchase revenue?",
            "Show me the apps with the highest user acquisition costs",
            "What's the daily install trend for the last 30 days?",
            "Which apps have the best revenue per install?",
            "What's the average revenue per user by platform?",
            "Show me the top performing apps in the US market",
            "What's the month-over-month growth in installs?"
        ]
    }