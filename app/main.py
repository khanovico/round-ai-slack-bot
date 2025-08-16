from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time
import logging

# from app.api.dummies import router as dummy_router
from app.api.agent import router as agent_router
from app.core.config import settings
from app.core.logging_config import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"""
--------------------------------------------------------------
🚀 {settings.PROJECT_NAME} v{settings.VERSION} starting up...""")
    yield
    # Shutdown
    logger.info(f"🛑 {settings.PROJECT_NAME} shutting down...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    logger.info(f"Request: {request.method} {request.url}")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(
        f"Response: {response.status_code} - {request.method} {request.url} - {process_time:.4f}s"
    )
    
    return response

# Include routers
# app.include_router(dummy_router, prefix="/dummy", tags=["dummies"])
app.include_router(agent_router)

@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": f"{settings.PROJECT_NAME} project is running!"}

@app.get("/health")
async def health_check():
    logger.info("Health check endpoint accessed")
    return {"status": "healthy"}

