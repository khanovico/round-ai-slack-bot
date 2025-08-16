"""
Cache management API endpoints
"""
from fastapi import APIRouter, HTTPException
from typing import Optional
from app.cache import get_cache, check_cache_health
from app.core.logging_config import get_logger

router = APIRouter(prefix="/cache", tags=["cache"])
logger = get_logger("app.api.cache")


@router.get("/health")
async def cache_health():
    """Get cache health status"""
    try:
        health = await check_cache_health()
        return health
    except Exception as e:
        logger.error(f"Error checking cache health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/info")
async def cache_info():
    """Get cache backend information"""
    try:
        cache = await get_cache()
        info = await cache.get_info()
        return info
    except Exception as e:
        logger.error(f"Error getting cache info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear")
async def clear_cache(pattern: Optional[str] = None):
    """Clear cache, optionally by pattern"""
    try:
        cache = await get_cache()
        cleared_count = await cache.clear(pattern)
        
        logger.info(f"Cleared {cleared_count} cache entries with pattern: {pattern}")
        
        return {
            "message": "Cache cleared successfully",
            "pattern": pattern,
            "cleared_count": cleared_count
        }
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def cache_stats():
    """Get cache statistics"""
    try:
        cache = await get_cache()
        health = await cache.health_check()
        info = await cache.get_info()
        
        return {
            "health": health,
            "info": info
        }
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))