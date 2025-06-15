"""
Swarm Resistance Web3 dApp - FastAPI Backend
Updated with Moralis Web3 functionality via HTTP API calls
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import uvicorn

# Import configuration and database
from app.config import settings
from app.database import init_db

# Import route modules
from app.routes.web3_routes import router as web3_router
# Import other routes as needed
# from app.routes.auth_routes import router as auth_router
# from app.routes.user_routes import router as user_router

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Swarm Resistance Web3 dApp API",
    description="Backend API for Swarm Resistance Web3 dApp with token portfolios and NFT collections",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(web3_router)
# app.include_router(auth_router)
# app.include_router(user_router)

@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup"""
    try:
        logger.info("🚀 Starting Swarm Resistance API...")
        
        # Initialize database
        await init_db()
        logger.info("✅ Database initialized successfully")
        
        # Test Moralis API key if provided
        import os
        if os.getenv("MORALIS_API_KEY"):
            logger.info("✅ Moralis API key found")
        else:
            logger.warning("⚠️  MORALIS_API_KEY not found - Web3 features will not work")
        
        logger.info("✅ Configuration loaded successfully")
        logger.info("🎯 Swarm Resistance API started")
        logger.info("📊 Docs available at: /docs")
        
    except Exception as e:
        logger.error(f"❌ Failed to start application: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on application shutdown"""
    logger.info("🛑 Shutting down Swarm Resistance API...")

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Swarm Resistance Web3 dApp API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "token_portfolio": "/api/tokens/portfolio",
            "nft_collections": "/api/nfts/{address}",
            "refresh_data": "/api/web3/refresh",
            "health_check": "/api/web3/health"
        }
    }

@app.get("/health")
async def health_check():
    """General health check endpoint"""
    try:
        # Test database connection
        from app.database import get_db
        db = next(get_db())
        
        # Test if we can execute a simple query
        result = db.execute("SELECT 1").fetchone()
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "healthy",
                "message": "API is running normally",
                "database": "connected",
                "timestamp": "2025-06-15T12:00:00Z"
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "message": "API is experiencing issues",
                "error": str(e),
                "timestamp": "2025-06-15T12:00:00Z"
            }
        )

@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Custom 404 handler"""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": "The requested endpoint does not exist",
            "docs": "/docs"
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Custom 500 handler"""
    logger.error(f"Internal server error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "docs": "/docs"
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )