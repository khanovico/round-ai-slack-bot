from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.ai.intent_classifier import IntentClassifierFactory
from app.ai.services.nl2sql_service import NL2SQLService, NL2SQLServiceResponse
from app.core.logging_config import get_logger
from app.core.config import settings

router = APIRouter(prefix="/agent", tags=["agent"])
logger = get_logger("app.agent.api")

# Initialize chat history manager
nl2sql_service = NL2SQLService()

# Initialize intent classifiers using factory
regex_classifier = IntentClassifierFactory.get_regex_classifier(confidence_threshold=0.8)
semantic_classifier = IntentClassifierFactory.get_semantic_classifier(confidence_threshold=0.6)
logger.info("Intent classifiers initialized successfully")


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


class IntentRequest(BaseModel):
    text: str
    method: str = "semantic"  # semantic, regex, or hybrid


class IntentResponse(BaseModel):
    text: str
    intent: str
    confidence: float
    method: str
    metadata: dict


@router.post("/ask", response_model=NL2SQLServiceResponse)
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
        result = await nl2sql_service.run(request.question, request.session_id)
            
        return result
        
    except Exception as e:
        logger.error(f"Error processing question '{request.question}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/check-intent", response_model=IntentResponse)
async def check_intent(request: IntentRequest):
    """
    Check the intent of a given text using the specified method.
    
    Methods:
    - semantic: Use semantic similarity matching
    - regex: Use regex pattern matching
    - hybrid: Try regex first, fallback to semantic if confidence is low
    """
    logger.info(f"Checking intent for text: '{request.text}' using method: {request.method}")
    
    try:
        if request.method.lower() == "regex":
            result = regex_classifier.classify(request.text)
            method_used = "regex"
        elif request.method.lower() == "semantic":
            result = semantic_classifier.classify(request.text)
            method_used = "semantic"
        elif request.method.lower() == "hybrid":
            # Try regex first
            regex_result = regex_classifier.classify(request.text)
            if regex_classifier.is_confident(regex_result):
                result = regex_result
                method_used = "regex"
            else:
                # Fallback to semantic
                result = semantic_classifier.classify(request.text)
                method_used = "semantic"
                # Add hybrid metadata
                result.metadata["hybrid_fallback"] = True
                result.metadata["regex_result"] = {
                    "intent": regex_result.intent.value,
                    "confidence": regex_result.confidence
                }
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid method: {request.method}. Use 'semantic', 'regex', or 'hybrid'"
            )
        
        logger.info(f"Intent classified as '{result.intent.value}' with confidence {result.confidence}")
        
        return IntentResponse(
            text=request.text,
            intent=result.intent.value,
            confidence=result.confidence,
            method=method_used,
            metadata=result.metadata
        )
        
    except Exception as e:
        logger.error(f"Error checking intent for text '{request.text}': {str(e)}", exc_info=True)
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