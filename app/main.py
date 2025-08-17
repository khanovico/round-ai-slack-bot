from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time

# from app.api.dummies import router as dummy_router
from app.api.cache import router as cache_router
from app.core.config import settings
from app.core.logging_config import setup_logging, get_logger
from app.cache import close_cache, check_cache_health
from app.observability import setup_langsmith

# Setup logging FIRST
setup_logging()
logger = get_logger("app.main")

# Setup LangSmith observability
setup_langsmith()

# Import agent router AFTER logging is set up
from app.api.agent import router as agent_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"""
--------------------------------------------------------------
🚀 {settings.PROJECT_NAME} v{settings.VERSION} starting up...""")
    
    # Check cache health before starting
    logger.info("🔍 Checking cache health...")
    cache_health = await check_cache_health()
    
    if cache_health["status"] == "healthy":
        logger.info(f"✅ Cache ({cache_health['backend']}) is healthy - Response time: {cache_health.get('response_time_ms', 0)}ms")
    else:
        logger.warning(f"⚠️ Cache ({cache_health['backend']}) is unhealthy: {cache_health.get('error', 'Unknown error')}")
        logger.warning("🚀 Starting anyway - cache operations may fail")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down cache connections...")
    await close_cache()
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
app.include_router(cache_router)

@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": f"{settings.PROJECT_NAME} project is running!"}

@app.get("/health")
async def health_check():
    logger.info("Health check endpoint accessed")
    return {"status": "healthy"}

