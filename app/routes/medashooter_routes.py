# routes/medashooter_routes.py - Updated with proper error handling
from fastapi import APIRouter, Query, HTTPException, status
from typing import Optional
import logging

from services.enhanced_moralis_service import enhanced_moralis_service
from services.web3_service import Web3ServiceException

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/api/v1/users/get_items/")
async def get_user_nfts_unity(address: str = Query(..., description="Wallet address")):
    """
    Get Heroes NFTs with Unity-compatible format
    Returns paginated format with "sec"/"ano"/"inn" fields
    """
    try:
        logger.info(f"🦸 Heroes endpoint called for address: {address}")
        
        # Call the enhanced service
        heroes_response = await enhanced_moralis_service.get_heroes_for_unity(address)
        
        logger.info(f"✅ Heroes endpoint successful: {len(heroes_response.get('results', []))} heroes found")
        return heroes_response
        
    except ValueError as e:
        # Address validation error - client error (400)
        logger.warning(f"⚠️ Invalid address provided: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid wallet address: {str(e)}"
        )
    except Web3ServiceException as e:
        # Web3 service error - server error (503)
        logger.error(f"❌ Web3 service unavailable: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Blockchain service temporarily unavailable: {str(e)}"
        )
    except Exception as e:
        # Unexpected error - server error (500)
        logger.error(f"❌ Unexpected error in heroes endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred"
        )

@router.get("/api/v1/weapon_item/user_weapons/")
async def get_user_weapons_unity(address: str = Query(..., description="Wallet address")):
    """
    Get Weapons NFTs with Unity-compatible format
    Returns direct array with "security"/"anonymity"/"innovation" fields
    """
    try:
        logger.info(f"⚔️ Weapons endpoint called for address: {address}")
        
        # Call the enhanced service
        weapons_response = await enhanced_moralis_service.get_weapons_for_unity(address)
        
        logger.info(f"✅ Weapons endpoint successful: {len(weapons_response)} weapons found")
        return weapons_response
        
    except ValueError as e:
        # Address validation error - client error (400)
        logger.warning(f"⚠️ Invalid address provided: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid wallet address: {str(e)}"
        )
    except Web3ServiceException as e:
        # Web3 service error - server error (503)
        logger.error(f"❌ Web3 service unavailable: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Blockchain service temporarily unavailable: {str(e)}"
        )
    except Exception as e:
        # Unexpected error - server error (500)
        logger.error(f"❌ Unexpected error in weapons endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred"
        )

@router.get("/api/game/medashooter/enhanced-player-data")
async def get_enhanced_player_data(
    address: str = Query(..., description="Wallet address"), 
    chain: str = Query(default="polygon", description="Blockchain network")
):
    """
    Get comprehensive NFT data with enhanced boost calculations
    Enhanced endpoint for Web3 dApp usage
    """
    try:
        logger.info(f"🎮 Enhanced player data endpoint called for address: {address}")
        
        # Call the enhanced service
        player_data = await enhanced_moralis_service.get_enhanced_player_data(address, chain)
        
        logger.info(f"✅ Enhanced player data successful: {player_data['counts']['total']} total NFTs")
        return player_data
        
    except ValueError as e:
        # Address validation error - client error (400)
        logger.warning(f"⚠️ Invalid address provided: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid wallet address: {str(e)}"
        )
    except Web3ServiceException as e:
        # Web3 service error - server error (503)
        logger.error(f"❌ Web3 service unavailable: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Blockchain service temporarily unavailable: {str(e)}"
        )
    except Exception as e:
        # Unexpected error - server error (500)
        logger.error(f"❌ Unexpected error in enhanced player data endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred"
        )

@router.get("/api/web3/service-status")
async def get_web3_service_status():
    """
    Get Web3 service status and cache statistics
    Useful for monitoring and debugging
    """
    try:
        from services.web3_service import web3_service
        
        cache_stats = web3_service.get_cache_stats()
        
        # Test connectivity
        try:
            w3 = web3_service._get_working_web3()
            block_number = w3.eth.block_number
            service_status = "healthy"
            current_block = block_number
        except Exception as e:
            service_status = "unhealthy"
            current_block = None
        
        return {
            "service_status": service_status,
            "current_block": current_block,
            "cache_stats": cache_stats,
            "timestamp": int(__import__('time').time())
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting service status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to get service status"
        )

@router.post("/api/web3/clear-cache")
async def clear_web3_cache():
    """
    Clear the Web3 service cache
    Useful for debugging or forcing fresh data
    """
    try:
        from services.web3_service import web3_service
        
        web3_service.clear_cache()
        
        return {
            "message": "Cache cleared successfully",
            "timestamp": int(__import__('time').time())
        }
        
    except Exception as e:
        logger.error(f"❌ Error clearing cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to clear cache"
        )