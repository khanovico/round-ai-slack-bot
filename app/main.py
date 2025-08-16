from fastapi import FastAPI

# from app.api.dummies import router as dummy_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
)

# Include routers
# app.include_router(dummy_router, prefix="/dummy", tags=["dummies"])

@app.get("/")
async def root():
    return {"message": f"{settings.PROJECT_NAME} project is running!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}