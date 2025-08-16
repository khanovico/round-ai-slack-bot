from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import asyncpg
from app.db.database import engine, AsyncSessionLocal


async def check_database_connection() -> bool:
    """Check if database connection is working"""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception:
        return False


async def create_database_if_not_exists() -> None:
    """Create database if it doesn't exist using asyncpg"""
    from app.core.config import settings
    
    try:
        # Connect to postgres database to create the target database
        conn = await asyncpg.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database="postgres"  # Connect to default postgres database
        )
        
        # Check if database exists
        result = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", 
            settings.DB_NAME
        )
        
        if not result:
            # Create database
            await conn.execute(f"CREATE DATABASE {settings.DB_NAME}")
            print(f"Database '{settings.DB_NAME}' created successfully!")
        else:
            print(f"Database '{settings.DB_NAME}' already exists.")
            
        await conn.close()
        
    except Exception as e:
        print(f"Error creating database: {e}")
        raise


async def run_health_check() -> dict:
    """Run basic health checks on the database"""
    health_status = {
        "database_connected": False,
        "tables_exist": False,
        "app_metrics_table": False
    }
    
    try:
        # Check connection
        health_status["database_connected"] = await check_database_connection()
        
        if health_status["database_connected"]:
            async with AsyncSessionLocal() as session:
                # Check if any tables exist
                result = await session.execute(
                    text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
                )
                table_count = result.scalar()
                health_status["tables_exist"] = table_count > 0
                
                # Check if app_metrics table exists
                result = await session.execute(
                    text("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'app_metrics'")
                )
                health_status["app_metrics_table"] = result.scalar() > 0
                
    except Exception as e:
        print(f"Health check failed: {e}")
    
    return health_status