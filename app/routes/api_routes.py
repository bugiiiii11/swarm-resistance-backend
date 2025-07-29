# routes/api_routes.py - Complete Unified API Routes for Unity Game + React dApp
from fastapi import APIRouter, Query, HTTPException, status, Request
from fastapi.responses import PlainTextResponse, JSONResponse
from typing import Optional, Dict, Any
import logging
import time
import json
import asyncio
from datetime import datetime
import numpy as np

# Import our unified services
from app.services.nft_service import nft_service, NFTServiceException
from app.services.blockchain_service import blockchain_service, BlockchainServiceException
from app.database import execute_command, execute_query, execute_transaction

logger = logging.getLogger(__name__)
router = APIRouter()

# Import decryption service for Unity score submission
try:
    from app.services.decryption_service import get_decryption_service
    RSA_DECRYPTION_AVAILABLE = True
    logger.info("✅ RSA decryption service imported successfully")
except ImportError as e:
    RSA_DECRYPTION_AVAILABLE = False
    logger.error(f"❌ Failed to import RSA decryption service: {e}")

# ============================================================================
# UNITY GAME ENDPOINTS (Full Backward Compatibility)
# ============================================================================

@router.get("/api/v1/users/get_items/")
async def get_user_nfts_unity(address: str = Query(..., description="Wallet address")):
    """
    Get Heroes NFTs with Unity-compatible format
    Returns paginated format with "sec"/"ano"/"inn" fields
    
    🎮 Unity Game Endpoint - Zero Breaking Changes
    """
    try:
        logger.info(f"🦸 Unity Heroes endpoint called for address: {address}")
        
        # Call the unified NFT service
        heroes_response = await nft_service.get_heroes_for_unity(address)
        
        logger.info(f"✅ Unity Heroes endpoint successful: {len(heroes_response.get('results', []))} heroes found")
        return heroes_response
        
    except ValueError as e:
        # Address validation error - client error (400)
        logger.warning(f"⚠️ Invalid address provided: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid wallet address: {str(e)}"
        )
    except NFTServiceException as e:
        # NFT service error - server error (503)
        logger.error(f"❌ NFT service unavailable: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"NFT service temporarily unavailable: {str(e)}"
        )
    except Exception as e:
        # Unexpected error - server error (500)
        logger.error(f"❌ Unexpected error in Unity heroes endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred"
        )

@router.get("/api/v1/weapon_item/user_weapons/")
async def get_user_weapons_unity(address: str = Query(..., description="Wallet address")):
    """
    Get Weapons NFTs with Unity-compatible format
    Returns direct array with "security"/"anonymity"/"innovation" fields
    
    🎮 Unity Game Endpoint - Zero Breaking Changes
    """
    try:
        logger.info(f"⚔️ Unity Weapons endpoint called for address: {address}")
        
        # Call the unified NFT service
        weapons_response = await nft_service.get_weapons_for_unity(address)
        
        logger.info(f"✅ Unity Weapons endpoint successful: {len(weapons_response)} weapons found")
        return weapons_response
        
    except ValueError as e:
        # Address validation error - client error (400)
        logger.warning(f"⚠️ Invalid address provided: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid wallet address: {str(e)}"
        )
    except NFTServiceException as e:
        # NFT service error - server error (503)
        logger.error(f"❌ NFT service unavailable: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"NFT service temporarily unavailable: {str(e)}"
        )
    except Exception as e:
        # Unexpected error - server error (500)
        logger.error(f"❌ Unexpected error in Unity weapons endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred"
        )

@router.get("/api/v1/user/active_boost_cards")
async def get_user_active_boost_cards(address: str = Query(..., description="Wallet address")):
    """
    Get user's active NFT boost cards for Unity game
    
    🎮 Unity Game Endpoint - NFT Boosts
    """
    try:
        logger.info(f"🚀 Unity NFT boosts endpoint called for address: {address}")
        
        # Get enhanced player data which includes boost calculations
        player_data = await nft_service.get_enhanced_player_data(address)
        
        # Extract boosts in Unity-compatible format
        boosts = player_data.get("boosts", {})
        counts = player_data.get("counts", {})
        
        # Convert to Unity's expected format
        unity_boosts = {
            "damage_multiplier": boosts.get("damage_multiplier", 0),
            "fire_rate_bonus": boosts.get("fire_rate_bonus", 0),
            "score_multiplier": boosts.get("score_multiplier", 0),
            "health_bonus": boosts.get("health_bonus", 0),
            "nft_counts": {
                "heroes": counts.get("heroes", 0),
                "weapons": counts.get("weapons", 0),
                "lands": counts.get("lands", 0)
            },
            "total_power": boosts.get("total_power", 0)
        }
        
        logger.info(f"✅ Unity NFT boosts: {counts.get('total', 0)} NFTs → {boosts.get('damage_multiplier', 0)}% damage")
        return unity_boosts
        
    except Exception as e:
        logger.error(f"❌ Error in Unity NFT boosts endpoint: {e}")
        # Return empty boosts on error (game should still work)
        return {
            "damage_multiplier": 0,
            "fire_rate_bonus": 0,
            "score_multiplier": 0,
            "health_bonus": 0,
            "nft_counts": {"heroes": 0, "weapons": 0, "lands": 0},
            "total_power": 0
        }

# ============================================================================
# PROFILEPAGE OPTIMIZED ENDPOINTS (72-76% Size Reduction)
# ============================================================================

@router.get("/api/v1/profile/heroes/{address}")
async def get_profile_heroes_optimized(address: str):
    """
    ProfilePage-optimized heroes endpoint
    Returns only essential fields: bc_id, sec, ano, inn, season_card_id
    
    🚀 Performance: 72% size reduction vs /api/v1/users/get_items/
    📱 Usage: ProfilePage heroes tab (default loading)
    """
    try:
        start_time = time.time()
        logger.info(f"🦸‍♂️ ProfilePage Heroes optimized request for: {address[:8]}...")
        
        # Use the optimized method from NFT service
        response = await nft_service.get_heroes_optimized(address)
        
        processing_time = time.time() - start_time
        logger.info(f"✅ ProfilePage Heroes: {len(response['results'])} heroes in {processing_time:.2f}s")
        
        return response
        
    except ValueError as e:
        logger.warning(f"⚠️ Invalid address: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid wallet address: {str(e)}"
        )
    except NFTServiceException as e:
        logger.error(f"❌ NFT service error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NFT service temporarily unavailable"
        )
    except Exception as e:
        logger.error(f"❌ ProfilePage Heroes optimization error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/api/v1/profile/weapons/{address}")
async def get_profile_weapons_optimized(address: str):
    """
    ProfilePage-optimized weapons endpoint
    Returns only essential fields: bc_id, weapon_name, security, anonymity, innovation
    
    🚀 Performance: 76% size reduction vs /api/v1/weapon_item/user_weapons/
    📱 Usage: ProfilePage weapons tab (lazy loading)
    """
    try:
        start_time = time.time()
        logger.info(f"⚔️ ProfilePage Weapons optimized request for: {address[:8]}...")
        
        # Use the optimized method from NFT service
        optimized_weapons = await nft_service.get_weapons_optimized(address)
        
        processing_time = time.time() - start_time
        logger.info(f"✅ ProfilePage Weapons: {len(optimized_weapons)} weapons in {processing_time:.2f}s")
        
        return optimized_weapons
        
    except ValueError as e:
        logger.warning(f"⚠️ Invalid address: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid wallet address: {str(e)}"
        )
    except NFTServiceException as e:
        logger.error(f"❌ NFT service error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NFT service temporarily unavailable"
        )
    except Exception as e:
        logger.error(f"❌ ProfilePage Weapons optimization error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/api/v1/profile/nfts/{address}")
async def get_profile_nfts_combined(
    address: str,
    include_heroes: bool = Query(default=True, description="Include heroes data"),
    include_weapons: bool = Query(default=False, description="Include weapons data")
):
    """
    Combined ProfilePage endpoint with selective loading capability
    Supports lazy loading strategy: heroes by default, weapons on-demand
    
    🚀 Performance: Allows frontend to load only what's needed
    📱 Usage: Alternative to separate endpoints for advanced use cases
    """
    try:
        start_time = time.time()
        logger.info(f"🎮 ProfilePage Combined request for: {address[:8]}...")
        logger.info(f"   Loading: heroes={include_heroes}, weapons={include_weapons}")
        
        result = {}
        
        # Load data based on parameters (supports lazy loading strategy)
        if include_heroes:
            result["heroes"] = await nft_service.get_heroes_optimized(address)
        
        if include_weapons:
            result["weapons"] = await nft_service.get_weapons_optimized(address)
        
        processing_time = time.time() - start_time
        loaded_types = []
        if include_heroes: loaded_types.append("heroes")
        if include_weapons: loaded_types.append("weapons")
        
        logger.info(f"✅ ProfilePage Combined: {'+'.join(loaded_types)} in {processing_time:.2f}s")
        
        return result
        
    except HTTPException:
        # Re-raise HTTP exceptions from child functions
        raise
    except Exception as e:
        logger.error(f"❌ ProfilePage Combined optimization error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

# ============================================================================
# REACT DAPP ENDPOINTS (Web3 Frontend)
# ============================================================================

@router.get("/api/tokens/portfolio")
async def get_token_portfolio(
    address: str = Query(..., description="Wallet address to fetch token portfolio for"),
    chain: str = Query("polygon", description="Blockchain network (polygon, ethereum, bsc, etc.)")
):
    """
    Get token balances for a wallet address with USD pricing
    
    💰 React dApp Endpoint - Token Portfolio
    """
    try:
        logger.info(f"💰 Token portfolio request for address: {address} on chain: {chain}")
        
        # Validate wallet address format (basic validation)
        if not address or len(address) != 42 or not address.startswith("0x"):
            raise HTTPException(
                status_code=400, 
                detail="Invalid wallet address format. Address must be 42 characters starting with 0x"
            )
        
        # Fetch token portfolio using blockchain service
        portfolio_data = await blockchain_service.get_token_portfolio(address, chain)
        
        logger.info(f"✅ Successfully fetched {portfolio_data['total_tokens']} tokens "
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
    
    except BlockchainServiceException as e:
        logger.error(f"Blockchain service error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to fetch token portfolio: {str(e)}"
        )
    
    except Exception as e:
        logger.error(f"Error fetching token portfolio: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to fetch token portfolio: {str(e)}"
        )

@router.get("/api/nfts/{address}")
async def get_nft_collections(
    address: str,
    chain: str = Query("polygon", description="Blockchain network (polygon, ethereum, bsc, etc.)")
):
    """
    Get NFT collections for a wallet address with metadata
    
    🖼️ React dApp Endpoint - NFT Collections
    """
    try:
        logger.info(f"🖼️ NFT collections request for address: {address} on chain: {chain}")
        
        # Validate wallet address format
        if not address or len(address) != 42 or not address.startswith("0x"):
            raise HTTPException(
                status_code=400, 
                detail="Invalid wallet address format. Address must be 42 characters starting with 0x"
            )
        
        # Fetch NFT collections using blockchain service
        nft_data = await blockchain_service.get_nft_collections_via_moralis(address, chain)
        
        logger.info(f"✅ Successfully fetched {nft_data['total_collections']} collections "
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
    
    except BlockchainServiceException as e:
        logger.error(f"Blockchain service error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to fetch NFT collections: {str(e)}"
        )
    
    except Exception as e:
        logger.error(f"Error fetching NFT collections: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to fetch NFT collections: {str(e)}"
        )

@router.post("/api/web3/refresh")
async def refresh_wallet_data(
    address: str = Query(..., description="Wallet address to refresh data for"),
    chain: str = Query("polygon", description="Blockchain network (polygon, ethereum, bsc, etc.)")
):
    """
    Force refresh of wallet data (clears cache and fetches fresh data)
    
    🔄 React dApp Endpoint - Cache Refresh
    """
    try:
        logger.info(f"🔄 Force refreshing wallet data for address: {address} on chain: {chain}")
        
        # Validate wallet address format
        if not address or len(address) != 42 or not address.startswith("0x"):
            raise HTTPException(
                status_code=400, 
                detail="Invalid wallet address format. Address must be 42 characters starting with 0x"
            )
        
        # Force refresh wallet data using blockchain service
        refresh_result = await blockchain_service.refresh_wallet_data(address, chain)
        
        if refresh_result.get("status") == "success":
            logger.info(f"✅ Successfully refreshed wallet data for {address}")
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
    
    except BlockchainServiceException as e:
        logger.error(f"Blockchain service error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to refresh wallet data: {str(e)}"
        )
    
    except Exception as e:
        logger.error(f"Error refreshing wallet data: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to refresh wallet data: {str(e)}"
        )

@router.get("/api/v1/land_tickets/user_land_tickets/")
async def get_user_land_tickets(
    address: str = Query(..., description="Wallet address to fetch land tickets for")
):
    """
    Get Land Tickets for a wallet address
    
    🏞️ React dApp Endpoint - Land Tickets (ERC1155)
    """
    try:
        logger.info(f"🏞️ Land tickets request for address: {address}")
        
        # Validate wallet address format
        if not address or len(address) != 42 or not address.startswith("0x"):
            raise HTTPException(
                status_code=400, 
                detail="Invalid wallet address format. Address must be 42 characters starting with 0x"
            )
        
        # Fetch land tickets using NFT service
        land_tickets = await nft_service.get_land_tickets(address)
        
        # Calculate total tickets for logging
        total_tickets = sum(land.get("balance", 0) for land in land_tickets if land.get("balance", 0) > 0)
        error_count = sum(1 for land in land_tickets if land.get("balance", -1) == -1)
        
        if error_count > 0:
            logger.warning(f"Retrieved land tickets with {error_count} errors for {address}")
        else:
            logger.info(f"✅ Successfully fetched {len(land_tickets)} land types with {total_tickets} total tickets")
        
        return JSONResponse(
            status_code=200,
            content=land_tickets  # Direct array response (like weapons endpoint)
        )
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except NFTServiceException as e:
        logger.error(f"NFT service error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to fetch land tickets: {str(e)}"
        )
    
    except Exception as e:
        logger.error(f"Error fetching land tickets: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to fetch land tickets: {str(e)}"
        )

# ============================================================================
# DEFI INTEGRATION ENDPOINTS (Token Benefits)
# ============================================================================

@router.get("/api/v1/stake/get_data/")
async def get_user_token_benefits(address: str = Query(..., description="Wallet address")):
    """
    Get user's token-based DeFi benefits
    
    Maps ERC20 token holdings to game benefits:
    - MEDALLC tokens → Shield ability (staking simulation)
    - MOH tokens → Basic perk selection (farming simulation)
    
    🪙 DeFi Integration Endpoint
    """
    try:
        logger.info(f"🪙 Token benefits request for address: {address}")
        
        # Get token benefits using NFT service
        benefits_response = await nft_service.get_token_benefits(address)
        
        logger.info(f"✅ Token benefits endpoint successful for {address}")
        return benefits_response
        
    except ValueError as e:
        # Address validation error - client error (400)
        logger.warning(f"⚠️ Invalid address provided: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid wallet address: {str(e)}"
        )
    except NFTServiceException as e:
        # NFT service error - server error (503)
        logger.error(f"❌ NFT service unavailable: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"NFT service temporarily unavailable: {str(e)}"
        )
    except Exception as e:
        # Unexpected error - server error (500)
        logger.error(f"❌ Unexpected error in token benefits endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred"
        )

@router.get("/api/v1/tokens/balances/")
async def get_detailed_token_balances(address: str = Query(..., description="Wallet address")):
    """
    Get detailed token balance information for debugging
    
    🔍 Debug Endpoint - Detailed Token Analysis
    """
    try:
        logger.info(f"🔍 Detailed token balances requested for address: {address}")
        
        # Get detailed token information using NFT service
        detailed_balances = await nft_service.get_detailed_token_balances(address)
        
        return detailed_balances
        
    except ValueError as e:
        logger.warning(f"⚠️ Invalid address provided: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid wallet address: {str(e)}"
        )
    except NFTServiceException as e:
        logger.error(f"❌ NFT service unavailable: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"NFT service temporarily unavailable: {str(e)}"
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error in detailed token balances: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred"
        )

# ============================================================================
# MEDASHOOTER GAME ENDPOINTS (Score Submission & Anti-Cheat)
# ============================================================================

@router.get("/api/v1/minigames/medashooter/timestamp/", response_class=PlainTextResponse)
async def get_medashooter_timestamp():
    """
    Get server timestamp for Unity anti-cheat validation
    Returns plain text timestamp (not JSON) - Unity expects this format
    
    ⏰ Unity Game Endpoint - Anti-Cheat Timestamp
    """
    try:
        # Return current UTC timestamp as integer (Unity expects plain text, not JSON)
        current_timestamp = int(time.time())
        logger.debug(f"🕐 Timestamp endpoint called: {current_timestamp}")
        
        # Return as plain text (Unity expects this exact format)
        return str(current_timestamp)
        
    except Exception as e:
        logger.error(f"❌ Timestamp endpoint error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get timestamp"
        )

@router.post("/api/v1/minigames/medashooter/score/")
async def submit_medashooter_score(request: Request):
    """
    Submit encrypted score data from Unity game
    Handles RSA decryption and score validation with duplicate prevention
    
    🎯 Unity Game Endpoint - Score Submission with Anti-Cheat
    """
    if not RSA_DECRYPTION_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Score submission service not available"
        )
    
    try:
        # Get decryption service
        decryption_service = get_decryption_service()
        if not decryption_service or not decryption_service.is_available():
            logger.error("❌ RSA decryption service not available")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Score decryption service not available"
            )
        
        # Parse request body
        raw_body = await request.body()
        submission_data = json.loads(raw_body.decode('utf-8'))
        
        logger.info(f"🎯 Score submission received with keys: {list(submission_data.keys())}")
        
        # Validate required fields
        required_fields = ["hash", "address", "delta"]
        for field in required_fields:
            if field not in submission_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required field: {field}"
                )
        
        # Decrypt all the data
        try:
            decrypted_data = decryption_service.decrypt_score_submission(submission_data)
            logger.info(f"✅ Score decrypted successfully for address: {decrypted_data['address'][:8]}...")
        except Exception as e:
            logger.error(f"❌ Score decryption failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Score decryption failed: {str(e)}"
            )
        
        # Extract core data
        player_address = decrypted_data['address'].lower()
        raw_score = decrypted_data['score']
        game_duration = decrypted_data['duration']
        enemies_spawned = decrypted_data.get('enemies_spawned', 0)
        
        # Apply Unity's score calculation algorithm
        calculated_score = calculate_unity_score(raw_score)
        
        # Anti-cheat validation
        is_suspicious = False
        blacklist_reason = None
        
        # Check duration vs score ratio
        if game_duration * 100 < calculated_score:
            is_suspicious = True
            blacklist_reason = f"Invalid duration/score ratio: {game_duration}s for {calculated_score} points"
        
        # Check enemies spawned vs score ratio  
        if enemies_spawned * 250 < calculated_score:
            is_suspicious = True
            blacklist_reason = f"Invalid enemies/score ratio: {enemies_spawned} enemies for {calculated_score} points"
        
        # Check if address is already blacklisted
        blacklist_check = await execute_query(
            "SELECT active FROM medashooter_blacklist WHERE player_address = $1 AND active = TRUE",
            player_address
        )
        
        if blacklist_check:
            is_suspicious = True
            blacklist_reason = "Address is blacklisted"
            logger.warning(f"⚠️ Blacklisted address attempted submission: {player_address}")
        
        # Handle suspicious activity
        if is_suspicious:
            logger.warning(f"🚨 Suspicious score submission: {blacklist_reason}")
            
            # Add to blacklist if not already there
            if not blacklist_check:
                await execute_command(
                    """INSERT INTO medashooter_blacklist (player_address, reason, evidence, blacklisted_at, active)
                       VALUES ($1, $2, $3, $4, $5)""",
                    player_address,
                    blacklist_reason,
                    json.dumps({
                        "score": calculated_score,
                        "duration": game_duration,
                        "enemies_spawned": enemies_spawned,
                        "submission_time": datetime.utcnow().isoformat(),
                        "raw_submission": submission_data
                    }),
                    datetime.utcnow(),
                    True
                )
            
            # Still return success to Unity (don't reveal anti-cheat detection)
            return {"status": "Score updated"}
        
        # Score is valid - save to database with duplicate prevention
        try:
            # Store raw encrypted submission first
            unity_score_id = await execute_query(
                """INSERT INTO medashooter_unity_scores 
                   (encrypted_hash, encrypted_address, encrypted_delta, encrypted_parameter1,
                    encrypted_parameter2, encrypted_parameter3, encrypted_parameter4, encrypted_parameter5,
                    encrypted_parameter6, encrypted_parameter7, encrypted_parameter8, encrypted_parameter9,
                    encrypted_parameter10, encrypted_parameter11, encrypted_parameter12, encrypted_parameter13,
                    encrypted_parameter14, encrypted_parameter15, raw_submission, submission_time)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20)
                   RETURNING id""",
                submission_data.get("hash", ""),
                submission_data.get("address", ""),
                submission_data.get("delta", ""),
                submission_data.get("parameter1", ""),
                submission_data.get("parameter2", ""),
                submission_data.get("parameter3", ""),
                submission_data.get("parameter4", ""),
                submission_data.get("parameter5", ""),
                submission_data.get("parameter6", ""),
                submission_data.get("parameter7", ""),
                submission_data.get("parameter8", ""),
                submission_data.get("parameter9", ""),
                submission_data.get("parameter10", ""),
                submission_data.get("parameter11", ""),
                submission_data.get("parameter12", ""),
                submission_data.get("parameter13", ""),
                submission_data.get("parameter14", ""),
                submission_data.get("parameter15", ""),
                json.dumps(submission_data),
                datetime.utcnow()
            )
            
            unity_score_record_id = unity_score_id[0]['id']
            
            # =========================================================================
            # DUPLICATE PREVENTION LOGIC - Check if player already has a score
            # =========================================================================
            
            existing_score = await execute_query(
                """SELECT id, final_score FROM medashooter_scores 
                   WHERE player_address = $1 AND validated = TRUE 
                   ORDER BY final_score DESC LIMIT 1""",
                player_address
            )
            
            if existing_score:
                # Update existing record if new score is better
                if calculated_score > existing_score[0]['final_score']:
                    # Get NFT boost data
                    nft_boosts = await get_nft_boosts_for_player(player_address)
                    
                    await execute_command(
                        """UPDATE medashooter_scores 
                           SET final_score = $1, calculated_score = $2, submission_time = $3,
                               enemies_killed = $4, enemies_spawned = $5, game_duration = $6,
                               waves_completed = $7, travel_distance = $8, perks_collected = $9,
                               coins_collected = $10, shields_collected = $11, 
                               killing_spree_mult = $12, killing_spree_duration = $13,
                               max_killing_spree = $14, attack_speed = $15, 
                               max_score_per_enemy = $16, max_score_per_enemy_scaled = $17,
                               ability_use_count = $18, enemies_killed_while_killing_spree = $19,
                               nft_boosts_used = $20, unity_score_id = $21
                           WHERE id = $22""",
                        min(calculated_score, 60000),  # Keep 60k cap
                        calculated_score,
                        datetime.utcnow(),
                        decrypted_data.get('enemies_killed', 0),
                        decrypted_data.get('enemies_spawned', 0),
                        decrypted_data.get('duration', 0),
                        decrypted_data.get('waves_completed', 0),
                        decrypted_data.get('travel_distance', 0),
                        decrypted_data.get('perks_collected', 0),
                        decrypted_data.get('coins_collected', 0),
                        decrypted_data.get('shields_collected', 0),
                        decrypted_data.get('killing_spree_mult', 0),
                        decrypted_data.get('killing_spree_duration', 0),
                        decrypted_data.get('max_killing_spree', 0),
                        decrypted_data.get('attack_speed', 0.0),
                        decrypted_data.get('max_score_per_enemy', 0),
                        decrypted_data.get('max_score_per_enemy_scaled', 0),
                        decrypted_data.get('ability_use_count', 0),
                        decrypted_data.get('enemies_killed_while_killing_spree', 0),
                        json.dumps(nft_boosts),
                        unity_score_record_id,
                        existing_score[0]['id']
                    )
                    logger.info(f"✅ Updated existing score: {calculated_score} for {player_address[:8]}...")
                else:
                    logger.info(f"⏭️ Score {calculated_score} not better than existing {existing_score[0]['final_score']}")
            else:
                # Create new record for first-time player
                nft_boosts = await get_nft_boosts_for_player(player_address)
                
                await execute_command(
                    """INSERT INTO medashooter_scores 
                       (unity_score_id, player_address, final_score, calculated_score,
                        enemies_killed, enemies_spawned, waves_completed, game_duration,
                        travel_distance, perks_collected, coins_collected, shields_collected,
                        killing_spree_mult, killing_spree_duration, max_killing_spree,
                        attack_speed, max_score_per_enemy, max_score_per_enemy_scaled,
                        ability_use_count, enemies_killed_while_killing_spree, nft_boosts_used,
                        meda_gas_reward, validated, submission_time)
                       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24)""",
                    unity_score_record_id,
                    player_address,
                    min(calculated_score, 60000),  # Cap at 60k like old system
                    calculated_score,
                    decrypted_data.get('enemies_killed', 0),
                    decrypted_data.get('enemies_spawned', 0),
                    decrypted_data.get('waves_completed', 0),
                    decrypted_data.get('duration', 0),
                    decrypted_data.get('travel_distance', 0),
                    decrypted_data.get('perks_collected', 0),
                    decrypted_data.get('coins_collected', 0),
                    decrypted_data.get('shields_collected', 0),
                    decrypted_data.get('killing_spree_mult', 0),
                    decrypted_data.get('killing_spree_duration', 0),
                    decrypted_data.get('max_killing_spree', 0),
                    decrypted_data.get('attack_speed', 0.0),
                    decrypted_data.get('max_score_per_enemy', 0),
                    decrypted_data.get('max_score_per_enemy_scaled', 0),
                    decrypted_data.get('ability_use_count', 0),
                    decrypted_data.get('enemies_killed_while_killing_spree', 0),
                    json.dumps(nft_boosts),
                    0,  # Meda gas reward (implement later)
                    True,  # Validated
                    datetime.utcnow()
                )
                logger.info(f"✅ Created new score record: {calculated_score} for {player_address[:8]}...")
            
            # Log the successful submission
            logger.info(f"🎯 Score submission processed: {calculated_score} points in {game_duration}s")
            
            return {"status": "Score updated"}
            
        except Exception as e:
            logger.error(f"❌ Database error saving score: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save score"
            )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in score submission: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Score submission failed"
        )

@router.get("/api/v1/minigames/medashooter/blacklist/")
async def check_medashooter_blacklist(address: str = Query(..., description="Wallet address to check")):
    """
    Check if an address is blacklisted
    Unity uses this to prevent blacklisted players from playing
    
    🚫 Unity Game Endpoint - Anti-Cheat Blacklist Check
    """
    try:
        # Validate and normalize address
        normalized_address = address.strip().lower()
        
        # Check blacklist
        blacklist_entry = await execute_query(
            "SELECT reason, blacklisted_at FROM medashooter_blacklist WHERE player_address = $1 AND active = TRUE",
            normalized_address
        )
        
        if blacklist_entry:
            logger.warning(f"🚫 Blacklisted address checked: {normalized_address}")
            return {
                "blacklisted": True,
                "reason": blacklist_entry[0]['reason'],
                "since": blacklist_entry[0]['blacklisted_at'].isoformat()
            }
        
        return {"blacklisted": False}
        
    except Exception as e:
        logger.error(f"❌ Blacklist check error: {e}")
        # In case of error, don't block players (fail open)
        return {"blacklisted": False}

@router.post("/api/v1/minigames/medashooter/blacklist/")
async def report_cheating(request: Request):
    """
    Report cheating from Unity (encrypted address)
    Unity calls this when it detects suspicious behavior
    
    🚨 Unity Game Endpoint - Anti-Cheat Reporting
    """
    if not RSA_DECRYPTION_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Anti-cheat service not available"
        )
    
    try:
        # Get decryption service
        decryption_service = get_decryption_service()
        if not decryption_service or not decryption_service.is_available():
            logger.error("❌ RSA decryption service not available")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Anti-cheat service not available"
            )
        
        # Parse request
        raw_body = await request.body()
        report_data = json.loads(raw_body.decode('utf-8'))
        
        if "address" not in report_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing address field"
            )
        
        # Decrypt address
        try:
            decrypted_address = decryption_service.decrypt_info_data(report_data["address"])
            
            # Extract address from Unity's format: <address>0x...</address>
            if decrypted_address.startswith("<address>") and decrypted_address.endswith("</address>"):
                actual_address = decrypted_address[9:-10].lower()
            else:
                actual_address = decrypted_address.lower()
                
        except Exception as e:
            logger.error(f"❌ Failed to decrypt cheat report: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to decrypt report"
            )
        
        # Store raw report first
        await execute_command(
            """INSERT INTO medashooter_unity_cheat_reports 
               (encrypted_address, raw_report, processed, submission_time)
               VALUES ($1, $2, $3, $4)""",
            report_data["address"],
            json.dumps(report_data),
            False,
            datetime.utcnow()
        )
        
        # Check if already blacklisted
        existing_blacklist = await execute_query(
            "SELECT id FROM medashooter_blacklist WHERE player_address = $1 AND active = TRUE",
            actual_address
        )
        
        if not existing_blacklist:
            # Add to blacklist
            await execute_command(
                """INSERT INTO medashooter_blacklist 
                   (player_address, reason, evidence, blacklisted_at, active)
                   VALUES ($1, $2, $3, $4, $5)""",
                actual_address,
                "Reported by Unity anti-cheat system",
                json.dumps({
                    "source": "unity_client",
                    "reported_at": datetime.utcnow().isoformat(),
                    "raw_report": report_data
                }),
                datetime.utcnow(),
                True
            )
            
            logger.warning(f"🚨 Address blacklisted by Unity anti-cheat: {actual_address}")
        
        return {"status": "Report processed"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Cheat report processing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process cheat report"
        )

# ============================================================================
# LEADERBOARD & GAME ANALYTICS ENDPOINTS
# ============================================================================

@router.get("/api/game/medashooter/scoreboard")
async def get_medashooter_scoreboard(
    limit: int = Query(default=50, description="Number of top scores to return"),
    player_address: Optional[str] = Query(default=None, description="Player address for user score")
):
    """
    Get MedaShooter leaderboard with duplicate prevention (one score per wallet)
    Uses optimized database function for fast performance
    
    🏆 Game Analytics Endpoint - Leaderboard
    """
    try:
        # Get top scores (one per wallet) - SUPER FAST with database function
        top_scores = await execute_query(
            "SELECT * FROM get_current_medashooter_leaderboard($1)",
            limit
        )
        
        scoreboard = []
        for score in top_scores:
            scoreboard.append({
                "rank": score["rank"],
                "address": score["player_address"],
                "score": score["final_score"],
                "submission_time": score["submission_time"].isoformat(),
                "nft_boosts": score["nft_boosts_used"] or {}
            })
        
        result = {
            "scoreboard": scoreboard,
            "total_players": len(scoreboard)
        }
        
        # Add user score if requested
        if player_address:
            player_address = player_address.lower()
            user_score = await execute_query(
                """SELECT final_score, submission_time, nft_boosts_used,
                   (SELECT COUNT(*) + 1 FROM medashooter_scores s2 
                    WHERE s2.final_score > s1.final_score AND s2.validated = TRUE
                    AND s2.player_address != s1.player_address) as rank
                   FROM medashooter_scores s1
                   WHERE player_address = $1 AND validated = TRUE
                   ORDER BY final_score DESC LIMIT 1""",
                player_address
            )
            
            if user_score:
                result["user_score"] = {
                    "rank": user_score[0]["rank"],
                    "score": user_score[0]["final_score"],
                    "address": player_address,
                    "submission_time": user_score[0]["submission_time"].isoformat(),
                    "nft_boosts": user_score[0]["nft_boosts_used"] or {}
                }
            else:
                result["user_score"] = None
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Scoreboard error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get scoreboard"
        )

@router.get("/api/game/medashooter/enhanced-player-data")
async def get_enhanced_player_data(
    address: str = Query(..., description="Wallet address"), 
    chain: str = Query(default="polygon", description="Blockchain network")
):
    """
    Get comprehensive NFT data with enhanced boost calculations
    Enhanced endpoint for Web3 dApp usage
    
    🎮 Enhanced Analytics Endpoint - Complete Player Profile
    """
    try:
        logger.info(f"🎮 Enhanced player data request for address: {address}")
        
        # Call the NFT service for comprehensive data
        player_data = await nft_service.get_enhanced_player_data(address, chain)
        
        logger.info(f"✅ Enhanced player data successful: {player_data['counts']['total']} total NFTs")
        return player_data
        
    except ValueError as e:
        # Address validation error - client error (400)
        logger.warning(f"⚠️ Invalid address provided: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid wallet address: {str(e)}"
        )
    except NFTServiceException as e:
        # NFT service error - server error (503)
        logger.error(f"❌ NFT service unavailable: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"NFT service temporarily unavailable: {str(e)}"
        )
    except Exception as e:
        # Unexpected error - server error (500)
        logger.error(f"❌ Unexpected error in enhanced player data endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred"
        )

# ============================================================================
# MONITORING & OPTIMIZATION ENDPOINTS
# ============================================================================

@router.get("/api/v1/profile/optimization-stats")
async def get_profile_optimization_stats():
    """
    Get ProfilePage optimization performance statistics
    Useful for monitoring the effectiveness of the 72-76% size reduction
    
    📊 Monitoring Endpoint - Optimization Statistics
    """
    try:
        # Get cache statistics from services
        nft_cache_stats = await nft_service.get_cache_statistics()
        blockchain_cache_stats = blockchain_service.get_service_stats()
        
        return {
            "optimization_status": "active",
            "version": "unified_v1.0",
            "endpoints": {
                "heroes_optimized": {
                    "path": "/api/v1/profile/heroes/{address}",
                    "size_reduction": "72%",
                    "target_response_time": "< 1.5s",
                    "fields": ["bc_id", "metadata.sec", "metadata.ano", "metadata.inn", "metadata.season_card_id"]
                },
                "weapons_optimized": {
                    "path": "/api/v1/profile/weapons/{address}", 
                    "size_reduction": "76%",
                    "target_response_time": "< 3.0s",
                    "fields": ["bc_id", "weapon_name", "security", "anonymity", "innovation"]
                },
                "combined_optimized": {
                    "path": "/api/v1/profile/nfts/{address}",
                    "features": ["lazy_loading", "selective_data"],
                    "parameters": ["include_heroes", "include_weapons"]
                }
            },
            "comparison": {
                "old_heroes_endpoint": "/api/v1/users/get_items/",
                "old_weapons_endpoint": "/api/v1/weapon_item/user_weapons/",
                "performance_improvement": "3-7x faster loading"
            },
            "cache_info": {
                "nft_service": nft_cache_stats,
                "blockchain_service": blockchain_cache_stats
            },
            "architecture": {
                "unified_services": True,
                "database_caching": True,
                "multi_format_support": True,
                "backward_compatibility": True
            },
            "timestamp": int(time.time())
        }
        
    except Exception as e:
        logger.error(f"❌ Optimization stats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to get optimization statistics"
        )

@router.get("/api/web3/cache/stats")
async def get_cache_stats():
    """
    Get comprehensive cache statistics for monitoring
    
    📈 Monitoring Endpoint - Cache Performance
    """
    try:
        nft_cache_stats = await nft_service.get_cache_statistics()
        blockchain_cache_stats = blockchain_service.get_service_stats()
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "nft_service": nft_cache_stats,
                    "blockchain_service": blockchain_cache_stats,
                    "unified_architecture": True
                },
                "message": "Cache statistics retrieved successfully"
            }
        )
        
    except Exception as e:
        logger.error(f"Error fetching cache stats: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to fetch cache statistics: {str(e)}"
        )

@router.delete("/api/web3/cache/clear")
async def clear_cache():
    """
    Clear all cached data across unified services
    
    🧹 Maintenance Endpoint - Cache Cleanup
    """
    try:
        # Clear both service caches
        blockchain_service.clear_all_caches()
        await nft_service.invalidate_token_cache('heroes')
        await nft_service.invalidate_token_cache('weapons')
        
        logger.info("All unified service caches cleared successfully")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "All unified service caches cleared successfully"
            }
        )
        
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to clear cache: {str(e)}"
        )

@router.get("/api/web3/health")
async def health_check():
    """
    Comprehensive health check endpoint for unified services
    
    ❤️ Health Check Endpoint - Service Status
    """
    try:
        # Get health status from both services
        nft_health = await nft_service.health_check()
        blockchain_health = await blockchain_service.health_check()
        
        overall_status = "healthy" if (
            nft_health.get("status") == "healthy" and 
            blockchain_health.get("status") == "healthy"
        ) else "unhealthy"
        
        return JSONResponse(
            status_code=200 if overall_status == "healthy" else 503,
            content={
                "success": overall_status == "healthy",
                "service": "Unified API Service",
                "status": overall_status,
                "services": {
                    "nft_service": nft_health,
                    "blockchain_service": blockchain_health
                },
                "architecture": {
                    "unified": True,
                    "version": "2_services_1_routes",
                    "endpoints_supported": [
                        "unity_game", "react_dapp", "profilepage_optimized", 
                        "defi_integration", "anti_cheat", "leaderboard"
                    ]
                },
                "message": f"Unified API service is {overall_status}"
            }
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "service": "Unified API Service",
                "status": "unhealthy",
                "error": str(e),
                "message": "Unified API service is experiencing issues"
            }
        )

# ============================================================================
# ADDITIONAL DEBUG & MONITORING ENDPOINTS (from addon file)
# ============================================================================

@router.get("/api/v1/stake/get_data/health")
async def token_benefits_health_check():
    """
    Health check for token benefits service
    Debug endpoint from original medashooter_routes.py
    """
    try:
        # Test blockchain service connectivity
        blockchain_health = await blockchain_service.health_check()
        
        return {
            "status": "healthy" if blockchain_health.get("status") == "healthy" else "unhealthy",
            "service": "token_benefits",
            "blockchain_service": blockchain_health.get("status", "unknown"),
            "current_block": blockchain_health.get("web3", {}).get("current_block"),
            "contracts": blockchain_service.get_contract_addresses(),
            "supported_tokens": ["moh", "medallc"],
            "cache_stats": blockchain_service.get_service_stats().get("cache_stats", {}),
            "timestamp": int(time.time())
        }
        
    except Exception as e:
        logger.error(f"❌ Token benefits health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "token_benefits", 
            "error": str(e),
            "timestamp": int(time.time())
        }

@router.get("/api/web3/service-status")
async def get_web3_service_status():
    """
    Get Web3 service status and cache statistics
    Enhanced monitoring endpoint from original medashooter_routes.py
    """
    try:
        # Get comprehensive service status
        blockchain_health = await blockchain_service.health_check()
        nft_health = await nft_service.health_check()
        
        return {
            "service_status": "healthy" if (
                blockchain_health.get("status") == "healthy" and 
                nft_health.get("status") == "healthy"
            ) else "unhealthy",
            "services": {
                "blockchain_service": blockchain_health,
                "nft_service": nft_health
            },
            "cache_stats": {
                "blockchain": blockchain_service.get_service_stats(),
                "nft": await nft_service.get_cache_statistics()
            },
            "configuration": {
                "contracts": blockchain_service.get_contract_addresses(),
                "architecture": "unified_v2.0"
            },
            "timestamp": int(time.time())
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting service status: {e}")
        return {
            "service_status": "unhealthy",
            "error": str(e),
            "timestamp": int(time.time())
        }

@router.post("/api/web3/clear-cache")
async def clear_web3_cache_post():
    """
    Clear the Web3 service cache (POST version)
    Alternative endpoint from original medashooter_routes.py
    """
    try:
        # Clear all unified service caches
        blockchain_service.clear_all_caches()
        await nft_service.invalidate_token_cache('heroes')
        await nft_service.invalidate_token_cache('weapons')
        
        logger.info("🧹 All unified service caches cleared via POST endpoint")
        
        return {
            "success": True,
            "message": "All unified service caches cleared successfully",
            "cleared": ["blockchain_service", "nft_service_heroes", "nft_service_weapons"],
            "timestamp": int(time.time())
        }
        
    except Exception as e:
        logger.error(f"❌ Error clearing cache via POST: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache: {str(e)}"
        )

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_unity_score(raw_score: int) -> int:
    """
    Apply Unity's score decryption algorithm
    This reverses the encryption Unity applies to scores
    """
    try:
        score = np.uint32(raw_score)
        score = np.uint32(((score >> 16) ^ score) * 0x119DE1F3)
        score = np.uint32(((score >> 16) ^ score) * 0x119DE1F3)
        return int(np.uint32(((score >> 16) ^ score)))
    except Exception as e:
        logger.error(f"❌ Score calculation error: {e}")
        return 0

async def get_nft_boosts_for_player(player_address: str) -> Dict[str, Any]:
    """
    Get current NFT boosts for a player using the unified NFT service
    """
    try:
        player_data = await nft_service.get_enhanced_player_data(player_address)
        return player_data.get("boosts", {})
    except Exception as e:
        logger.warning(f"⚠️ Failed to get NFT boosts for {player_address}: {e}")
        return {}