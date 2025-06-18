# app/main.py - Enhanced with MedaShooter integration
"""
Swarm Resistance Web3 dApp - FastAPI Backend
Enhanced with MedaShooter game integration
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
from app.routes.medashooter_routes import router as medashooter_router
# Import other routes as needed
# from app.routes.auth_routes import router as auth_router
# from app.routes.user_routes import router as user_router

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Swarm Resistance Web3 dApp API",
    description="Backend API for Swarm Resistance Web3 dApp with token portfolios, NFT collections, and MedaShooter game integration",
    version="2.0.0",  # Updated version
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enhanced CORS middleware for Unity WebGL game
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",  # In production, replace with specific origins
        "https://game.cryptomeda.tech",        # Unity game domain
        "https://app.cryptomeda.tech",         # Web3 dApp domain
        "http://localhost:3000",               # React dev server
        "http://localhost:5173",               # Vite dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(web3_router, tags=["Web3 Services"])
app.include_router(medashooter_router, tags=["MedaShooter Game Integration"])
# app.include_router(auth_router)
# app.include_router(user_router)

@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup"""
    try:
        logger.info("🚀 Starting Swarm Resistance API v2.0...")
        
        # Initialize database
        await init_db()
        logger.info("✅ Database initialized successfully")
        
        # Test MedaShooter RSA decryption service
        try:
            from app.services.decryption_service import MedaShooterDecryption
            decryption = MedaShooterDecryption()
            logger.info("✅ MedaShooter RSA decryption service initialized")
        except Exception as e:
            logger.warning(f"⚠️ MedaShooter RSA service not available: {e}")
        
        # Test Moralis API key if provided
        import os
        if os.getenv("MORALIS_API_KEY"):
            logger.info("✅ Moralis API key found")
        else:
            logger.warning("⚠️  MORALIS_API_KEY not found - Web3 features will not work")
        
        logger.info("✅ Configuration loaded successfully")
        logger.info("🎯 Swarm Resistance API started with MedaShooter integration")
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
        "message": "Swarm Resistance Web3 dApp API with MedaShooter Integration",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            # Web3 dApp endpoints
            "token_portfolio": "/api/tokens/portfolio",
            "nft_collections": "/api/nfts/{address}",
            "refresh_data": "/api/web3/refresh",
            "web3_health": "/api/web3/health",
            
            # MedaShooter Unity-compatible endpoints
            "unity_heroes": "/api/v1/users/get_items/",
            "unity_weapons": "/api/v1/weapon_item/user_weapons/",
            "unity_score_submission": "/api/v1/minigames/medashooter/score/",
            "unity_timestamp": "/api/v1/minigames/medashooter/timestamp/",
            "unity_blacklist": "/api/v1/minigames/medashooter/blacklist/",
            "unity_boost_cards": "/api/v1/user/active_boost_cards",
            
            # Enhanced Web3 endpoints for MedaShooter
            "enhanced_player_data": "/api/game/medashooter/enhanced-player-data",
            "scoreboard": "/api/game/medashooter/scoreboard",
            "player_analytics": "/api/game/medashooter/player-analytics",
            "global_stats": "/api/game/medashooter/global-stats"
        },
        "features": [
            "Web3 wallet integration",
            "Token portfolio tracking",
            "NFT collection management", 
            "MedaShooter Unity game integration",
            "Real-time NFT boost calculations",
            "Score submission with RSA decryption",
            "Anti-cheat validation system",
            "Comprehensive player analytics"
        ]
    }

@app.get("/health")
async def health_check():
    """Enhanced health check endpoint"""
    try:
        # Test database connection - FIXED for asyncpg
        from app.database import get_db_pool
        pool = await get_db_pool()
        
        async with pool.acquire() as connection:
            result = await connection.fetchval("SELECT 1")
        
        # Test MedaShooter services
        medashooter_status = "available"
        rsa_keys_loaded = False
        try:
            from app.services.decryption_service import MedaShooterDecryption
            decryption = MedaShooterDecryption()
            rsa_keys_loaded = (
                decryption._score_private_key is not None and 
                decryption._info_private_key is not None
            )
            medashooter_status = "available"
        except Exception as e:
            medashooter_status = "rsa_keys_missing"
            rsa_keys_loaded = False
        
        # Test Moralis service
        moralis_status = "available" if settings.moralis_api_key else "api_key_missing"
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "healthy",
                "message": "API is running normally",
                "version": "2.0.0",
                "services": {
                    "database": "connected",
                    "moralis": moralis_status,
                    "medashooter": medashooter_status,
                    "rsa_decryption": rsa_keys_loaded
                },
                "timestamp": "2025-06-18T12:00:00Z"
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
                "timestamp": "2025-06-18T12:00:00Z"
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
            "docs": "/docs",
            "available_endpoints": [
                "/api/tokens/portfolio",
                "/api/nfts/{address}",
                "/api/v1/minigames/medashooter/score/",
                "/api/game/medashooter/enhanced-player-data"
            ]
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