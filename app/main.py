# app/main.py
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
from typing import Optional
import httpx
import asyncio
from datetime import datetime, timedelta

# Import our modules (we'll create these next)
from app.config import settings
from app.database import get_db
from app.models.user import User, UserCreate, UserUpdate
from app.models.token import TokenBalance, NFTHolding
from app.services.moralis_service import MoralisService
from app.services.auth_service import AuthService

# Initialize FastAPI app
app = FastAPI(
    title="Swarm Resistance API",
    description="Backend API for Swarm Resistance Web3 dApp on Polygon",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc"  # ReDoc
)

# Configure CORS for your frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
        "https://your-frontend-domain.com"  # Your deployed frontend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
moralis_service = MoralisService()
auth_service = AuthService()

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "service": "Swarm Resistance API"
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Swarm Resistance Web3 dApp API",
        "description": "Polygon-based decentralized application backend",
        "docs": "/docs",
        "health": "/health",
        "version": "1.0.0",
        "blockchain": "Polygon"
    }

# Authentication dependency
async def get_current_user(authorization: Optional[str] = Header(None)):
    """Dependency to get current authenticated user"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    try:
        # Extract token from "Bearer <token>"
        token = authorization.split(" ")[1] if authorization.startswith("Bearer ") else authorization
        user = await auth_service.verify_token(token)
        return user
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

# ============================================
# USER MANAGEMENT ENDPOINTS
# ============================================

@app.post("/api/auth/login", response_model=dict)
async def login(user_data: UserCreate, db=Depends(get_db)):
    """Login or register user with Web3Auth token"""
    try:
        # Verify Web3Auth token and extract user info
        verified_user = await auth_service.verify_web3auth_token(user_data.web3auth_token)
        
        # Check if user exists, create if not
        user = await auth_service.get_or_create_user(verified_user, db)
        
        # Generate our internal JWT token
        access_token = auth_service.create_access_token(user.id)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "wallet_address": user.wallet_address,
                "email": user.email,
                "username": user.username
            },
            "message": "Login successful"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/users/profile", response_model=dict)
async def get_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return {
        "id": str(current_user.id),
        "wallet_address": current_user.wallet_address,
        "email": current_user.email,
        "username": current_user.username,
        "created_at": current_user.created_at.isoformat(),
        "updated_at": current_user.updated_at.isoformat()
    }

@app.put("/api/users/profile", response_model=dict)
async def update_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db)
):
    """Update user profile"""
    try:
        updated_user = await auth_service.update_user(current_user.id, user_update, db)
        return {
            "message": "Profile updated successfully",
            "user": {
                "id": str(updated_user.id),
                "wallet_address": updated_user.wallet_address,
                "email": updated_user.email,
                "username": updated_user.username
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============================================
# WEB3 DATA ENDPOINTS (MORALIS INTEGRATION)
# ============================================

@app.get("/api/tokens/{token_address}/balance")
async def get_token_balance(
    token_address: str,
    current_user: User = Depends(get_current_user),
    force_refresh: bool = False
):
    """Get user's token balance for a specific token (Moralis)"""
    try:
        balance = await moralis_service.get_token_balance(
            user_address=current_user.wallet_address,
            token_address=token_address,
            force_refresh=force_refresh
        )
        return {
            "token_address": token_address,
            "balance": str(balance.balance),
            "decimals": balance.decimals,
            "symbol": balance.symbol,
            "name": balance.name,
            "last_updated": balance.last_updated.isoformat(),
            "blockchain": "polygon"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/tokens/portfolio")
async def get_token_portfolio(
    current_user: User = Depends(get_current_user),
    force_refresh: bool = False
):
    """Get user's complete token portfolio with USD values (Moralis enriched data)"""
    try:
        portfolio = await moralis_service.get_user_token_portfolio(
            user_address=current_user.wallet_address,
            force_refresh=force_refresh
        )
        return {
            "user_address": current_user.wallet_address,
            "portfolio": portfolio,
            "total_tokens": len(portfolio),
            "blockchain": "polygon",
            "last_updated": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/nfts/{user_address}")
async def get_user_nfts(
    user_address: str,
    current_user: User = Depends(get_current_user),
    force_refresh: bool = False
):
    """Get user's NFT holdings with metadata (Moralis enriched data)"""
    # Verify user can access this address (either their own or admin)
    if user_address.lower() != current_user.wallet_address.lower():
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        nfts = await moralis_service.get_user_nfts(
            user_address=user_address,
            force_refresh=force_refresh
        )
        return {
            "user_address": user_address,
            "nfts": [
                {
                    "contract_address": nft.contract_address,
                    "token_id": nft.token_id,
                    "name": nft.metadata.get("name", "Unknown"),
                    "image": nft.metadata.get("image", ""),
                    "description": nft.metadata.get("description", ""),
                    "attributes": nft.metadata.get("attributes", []),
                    "last_updated": nft.last_updated.isoformat()
                }
                for nft in nfts
            ],
            "total_nfts": len(nfts),
            "blockchain": "polygon"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/web3/refresh")
async def refresh_web3_data(
    current_user: User = Depends(get_current_user)
):
    """Force refresh all Web3 data for current user"""
    try:
        # Trigger background refresh of user's data
        await moralis_service.refresh_user_data(current_user.wallet_address)
        return {
            "message": "Refresh initiated successfully",
            "user_address": current_user.wallet_address,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/web3/analytics")
async def get_user_analytics(
    current_user: User = Depends(get_current_user)
):
    """Get analytics for current user"""
    try:
        analytics = await moralis_service.get_user_analytics(current_user.wallet_address)
        return analytics
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============================================
# ADMIN ENDPOINTS (TODO: Add admin role check)
# ============================================

@app.get("/api/admin/users")
async def list_users(
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100
):
    """List all users (admin only)"""
    # TODO: Add admin role verification
    try:
        users = await auth_service.list_users(skip=skip, limit=limit)
        return {
            "users": [
                {
                    "id": str(user.id),
                    "wallet_address": user.wallet_address,
                    "email": user.email,
                    "username": user.username,
                    "created_at": user.created_at.isoformat()
                }
                for user in users
            ],
            "total": len(users),
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/admin/analytics")
async def get_system_analytics(
    current_user: User = Depends(get_current_user)
):
    """Get system-wide analytics (admin only)"""
    # TODO: Add admin role verification
    try:
        analytics = await moralis_service.get_system_analytics()
        return analytics
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============================================
# ERROR HANDLERS
# ============================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail, 
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error", 
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# ============================================
# STARTUP EVENT
# ============================================

@app.on_event("startup")
async def startup_event():
    """Initialize database and services on startup"""
    try:
        from app.database import init_db
        await init_db()
        print("✅ Database initialized successfully")
        print("🚀 Swarm Resistance API started")
        print(f"📊 Docs available at: /docs")
    except Exception as e:
        print(f"❌ Startup error: {e}")

# Run the app (for local development)
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )