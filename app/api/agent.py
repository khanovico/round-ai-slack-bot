from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.agent import NL2SQLAgent
from app.core.logging_config import get_logger

router = APIRouter(prefix="/agent", tags=["agent"])
logger = get_logger("app.agent.api")

# Initialize the agent (you might want to make this a singleton or dependency)
logger.info("Initializing NL2SQL Agent...")
nl2sql_agent = NL2SQLAgent()
logger.info("NL2SQL Agent initialized successfully")


class QuestionRequest(BaseModel):
    question: str


class QuestionResponse(BaseModel):
    question: str
    answer: str
    success: bool


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
    """
    logger.info(f"Received question: {request.question}")
    
    try:
        result = await nl2sql_agent.ask(request.question)
        
        if result["success"]:
            logger.info(f"Successfully processed question: {request.question}")
        else:
            logger.warning(f"Failed to process question: {request.question} - {result['answer']}")
            
        return QuestionResponse(**result)
        
    except Exception as e:
        logger.error(f"Error processing question '{request.question}': {str(e)}", exc_info=True)
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