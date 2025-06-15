"""
Web3 API Routes for Swarm Resistance dApp
Implements the three main endpoints using Moralis HTTP API
TEMPORARY: Authentication disabled for initial deployment
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional
import logging
from app.services.moralis_service import moralis_service
# Temporarily commented out auth until we implement it
# from app.services.auth_service import get_current_user

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["web3"])

@router.get("/tokens/portfolio")
async def get_token_portfolio(
    address: str = Query(..., description="Wallet address to fetch token portfolio for"),
    chain: str = Query("polygon", description="Blockchain network (polygon, ethereum, bsc, etc.)")
    # Temporarily removed: current_user: dict = Depends(get_current_user)
):
    """
    Get token balances for a wallet address with USD pricing
    
    - **address**: Wallet address (required)
    - **chain**: Blockchain network (default: polygon)
    - Returns: Token portfolio with balances and USD values
    """
    try:
        logger.info(f"Fetching token portfolio for address: {address} on chain: {chain}")
        
        # Validate wallet address format (basic validation)
        if not address or len(address) != 42 or not address.startswith("0x"):
            raise HTTPException(
                status_code=400, 
                detail="Invalid wallet address format. Address must be 42 characters starting with 0x"
            )
        
        # Fetch token portfolio
        portfolio_data = await moralis_service.get_token_balances(address, chain)
        
        logger.info(f"Successfully fetched {portfolio_data['total_tokens']} tokens "
                   f"with total value ${portfolio_data['total_usd_value']:.2f}")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": portfolio_data,
                "message": f"Successfully fetched token portfolio for {address}"
            }
        )
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        logger.error(f"Error fetching token portfolio: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to fetch token portfolio: {str(e)}"
        )

@router.get("/nfts/{address}")
async def get_nft_collections(
    address: str,
    chain: str = Query("polygon", description="Blockchain network (polygon, ethereum, bsc, etc.)")
    # Temporarily removed: current_user: dict = Depends(get_current_user)
):
    """
    Get NFT collections for a wallet address with metadata
    
    - **address**: Wallet address (required, in URL path)
    - **chain**: Blockchain network (default: polygon)
    - Returns: NFT collections with metadata and images
    """
    try:
        logger.info(f"Fetching NFT collections for address: {address} on chain: {chain}")
        
        # Validate wallet address format
        if not address or len(address) != 42 or not address.startswith("0x"):
            raise HTTPException(
                status_code=400, 
                detail="Invalid wallet address format. Address must be 42 characters starting with 0x"
            )
        
        # Fetch NFT collections
        nft_data = await moralis_service.get_nft_collections(address, chain)
        
        logger.info(f"Successfully fetched {nft_data['total_collections']} collections "
                   f"with {nft_data['total_nfts']} total NFTs")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": nft_data,
                "message": f"Successfully fetched NFT collections for {address}"
            }
        )
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        logger.error(f"Error fetching NFT collections: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to fetch NFT collections: {str(e)}"
        )

@router.post("/web3/refresh")
async def refresh_wallet_data(
    address: str = Query(..., description="Wallet address to refresh data for"),
    chain: str = Query("polygon", description="Blockchain network (polygon, ethereum, bsc, etc.)")
    # Temporarily removed: current_user: dict = Depends(get_current_user)
):
    """
    Force refresh of wallet data (clears cache and fetches fresh data)
    
    - **address**: Wallet address (required)
    - **chain**: Blockchain network (default: polygon)
    - Returns: Refreshed wallet data including tokens and NFTs
    """
    try:
        logger.info(f"Force refreshing wallet data for address: {address} on chain: {chain}")
        
        # Validate wallet address format
        if not address or len(address) != 42 or not address.startswith("0x"):
            raise HTTPException(
                status_code=400, 
                detail="Invalid wallet address format. Address must be 42 characters starting with 0x"
            )
        
        # Force refresh wallet data
        refresh_result = await moralis_service.refresh_wallet_data(address, chain)
        
        if refresh_result.get("status") == "success":
            logger.info(f"Successfully refreshed wallet data for {address}")
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "data": refresh_result,
                    "message": f"Successfully refreshed wallet data for {address}"
                }
            )
        else:
            logger.error(f"Failed to refresh wallet data: {refresh_result.get('error')}")
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to refresh wallet data: {refresh_result.get('error')}"
            )
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        logger.error(f"Error refreshing wallet data: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to refresh wallet data: {str(e)}"
        )

@router.get("/web3/cache/stats")
async def get_cache_stats():
    """
    Get cache statistics for monitoring
    
    - Returns: Cache statistics including entry counts and duration settings
    """
    try:
        cache_stats = moralis_service.get_cache_stats()
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": cache_stats,
                "message": "Cache statistics retrieved successfully"
            }
        )
        
    except Exception as e:
        logger.error(f"Error fetching cache stats: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to fetch cache statistics: {str(e)}"
        )

@router.delete("/web3/cache/clear")
async def clear_cache():
    """
    Clear all cached data
    
    - Returns: Success message
    """
    try:
        moralis_service.clear_all_cache()
        logger.info("All cache cleared successfully")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "All cache cleared successfully"
            }
        )
        
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to clear cache: {str(e)}"
        )

@router.get("/web3/health")
async def health_check():
    """
    Health check endpoint for Web3 service
    
    - Returns: Service status and basic info
    """
    try:
        cache_stats = moralis_service.get_cache_stats()
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "service": "Web3 Moralis Service",
                "status": "healthy",
                "cache_stats": cache_stats,
                "message": "Web3 service is running normally"
            }
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "service": "Web3 Moralis Service",
                "status": "unhealthy",
                "error": str(e),
                "message": "Web3 service is experiencing issues"
            }
        )