# routes/medashooter_routes.py - Minimal version for debugging
from fastapi import APIRouter, Query, HTTPException, status
from typing import Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/api/v1/users/get_items/")
async def get_user_nfts_unity(address: str = Query(..., description="Wallet address")):
    """
    Temporary endpoint - returns empty heroes data
    """
    try:
        logger.info(f"🦸 Heroes endpoint called for address: {address}")
        
        # Return empty but valid Unity format
        return {
            "results": [],
            "count": 0,
            "next": None
        }
        
    except Exception as e:
        logger.error(f"❌ Error in heroes endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred"
        )

@router.get("/api/v1/weapon_item/user_weapons/")
async def get_user_weapons_unity(address: str = Query(..., description="Wallet address")):
    """
    Temporary endpoint - returns empty weapons data
    """
    try:
        logger.info(f"⚔️ Weapons endpoint called for address: {address}")
        
        # Return empty but valid Unity format
        return []
        
    except Exception as e:
        logger.error(f"❌ Error in weapons endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred"
        )

@router.get("/api/debug/test")
async def debug_test():
    """
    Simple test endpoint to verify routes are working
    """
    return {
        "status": "ok",
        "message": "Routes are working",
        "timestamp": int(__import__('time').time())
    }

# Test if we can import the services
@router.get("/api/debug/import-test")
async def debug_import_test():
    """
    Test imports step by step
    """
    import_results = {}
    
    try:
        import web3
        import_results["web3"] = "✅ Success"
    except Exception as e:
        import_results["web3"] = f"❌ Failed: {str(e)}"
    
    try:
        import cachetools
        import_results["cachetools"] = "✅ Success"
    except Exception as e:
        import_results["cachetools"] = f"❌ Failed: {str(e)}"
    
    try:
        from services.web3_service import web3_service
        import_results["web3_service"] = "✅ Success"
    except Exception as e:
        import_results["web3_service"] = f"❌ Failed: {str(e)}"
    
    try:
        from services.enhanced_moralis_service import enhanced_moralis_service
        import_results["enhanced_moralis_service"] = "✅ Success"
    except Exception as e:
        import_results["enhanced_moralis_service"] = f"❌ Failed: {str(e)}"
    
    return {
        "import_results": import_results,
        "timestamp": int(__import__('time').time())
    }