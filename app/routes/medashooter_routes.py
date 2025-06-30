# routes/medashooter_routes.py - COMPLETE with token benefits and score submission
from fastapi import APIRouter, Query, HTTPException, status, Request
from fastapi.responses import PlainTextResponse
from typing import Optional, Dict, Any
import logging
import time
import json
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()

# Import the real services with CORRECT paths
try:
    from app.services.enhanced_moralis_service import enhanced_moralis_service
    from app.services.web3_service import web3_service, Web3ServiceException
    from app.services.decryption_service import get_decryption_service
    from app.database import execute_command, execute_query, execute_transaction
    SERVICES_AVAILABLE = True
    logger.info("✅ Web3 services imported successfully")
except ImportError as e:
    SERVICES_AVAILABLE = False
    logger.error(f"❌ Failed to import Web3 services: {e}")

# ERC20 ABI - minimal balanceOf function for token benefits
ERC20_TOKEN_ABI = [
    {
        "inputs": [{"internalType": "address", "name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Token contract addresses for DeFi benefits
TOKEN_CONTRACTS = {
    "moh": "0x1D3dD50B23849247C426AEd040Fb8f93D9123b60",
    "medallc": "0xEDfd96dD07b6eA11393c177686795771579f488a"
}

class TokenBenefitsService:
    """Service for checking ERC20 token balances and mapping to game benefits"""
    
    def __init__(self):
        self.contracts = {}
        logger.info("✅ TokenBenefitsService initialized")
    
    def _get_token_contract(self, token_name: str):
        """Get ERC20 contract instance with caching"""
        cache_key = f"token_{token_name}"
        
        if cache_key in self.contracts:
            return self.contracts[cache_key]
        
        # Get working Web3 instance
        w3 = web3_service._get_working_web3()
        contract_address = TOKEN_CONTRACTS.get(token_name)
        
        if not contract_address:
            raise Web3ServiceException(f"Unknown token: {token_name}")
        
        try:
            contract = w3.eth.contract(
                address=w3.to_checksum_address(contract_address),
                abi=ERC20_TOKEN_ABI
            )
            self.contracts[cache_key] = contract
            logger.debug(f"✅ Token contract {token_name} loaded at {contract_address}")
            return contract
        except Exception as e:
            raise Web3ServiceException(f"Failed to load token contract {token_name}: {e}")
    
    async def get_token_balance(self, token_name: str, address: str) -> int:
        """Get ERC20 token balance for an address"""
        # Validate and normalize address
        try:
            normalized_address = web3_service._validate_address(address)
        except ValueError as e:
            raise ValueError(f"Invalid address: {e}")
        
        # Check cache first
        cache_key = f"token_balance_{token_name}_{normalized_address.lower()}"
        if cache_key in web3_service.cache:
            logger.debug(f"🎯 Cache hit for {cache_key}")
            return web3_service.cache[cache_key]
        
        try:
            contract = self._get_token_contract(token_name)
            
            # Call balanceOf function with retry logic
            contract_function = contract.functions.balanceOf(normalized_address)
            result = await web3_service._call_contract_function_with_retry(contract_function)
            
            balance = int(result) if result else 0
            
            # Cache the result
            web3_service.cache[cache_key] = balance
            
            logger.debug(f"✅ {token_name.upper()} balance for {normalized_address}: {balance}")
            return balance
            
        except Exception as e:
            logger.error(f"❌ Failed to get {token_name} balance for {address}: {e}")
            raise Web3ServiceException(f"Failed to get {token_name} balance: {e}")
    
    async def get_all_token_benefits(self, address: str) -> dict:
        """Get all token balances and map to Unity benefits format"""
        try:
            logger.info(f"🪙 Fetching token benefits for {address}")
            
            # Get both token balances in parallel
            moh_task = self.get_token_balance("moh", address)
            medallc_task = self.get_token_balance("medallc", address)
            
            moh_balance, medallc_balance = await asyncio.gather(
                moh_task, medallc_task, return_exceptions=True
            )
            
            # Handle any exceptions
            if isinstance(moh_balance, Exception):
                logger.error(f"MOH balance fetch failed: {moh_balance}")
                moh_balance = 0
            
            if isinstance(medallc_balance, Exception):
                logger.error(f"MEDALLC balance fetch failed: {medallc_balance}")
                medallc_balance = 0
            
            # Map to Unity-compatible format
            benefits = {
                "standard": {
                    "currently_staked": 1 if medallc_balance > 0 else 0  # MEDALLC → Shield ability
                },
                "liquidity": {
                    "currently_staked": 1 if moh_balance > 0 else 0      # MOH → Basic perk selection
                }
            }
            
            # Log benefits for debugging
            logger.info(f"✅ Token benefits for {address}:")
            logger.info(f"   MEDALLC: {medallc_balance} → Shield: {'YES' if medallc_balance > 0 else 'NO'}")
            logger.info(f"   MOH: {moh_balance} → Perks: {'YES' if moh_balance > 0 else 'NO'}")
            
            return benefits
            
        except ValueError as e:
            # Address validation error - client error
            logger.error(f"❌ Address validation error: {e}")
            raise ValueError(str(e))
        except Web3ServiceException as e:
            # Web3 service error - server error
            logger.error(f"❌ Web3 service error: {e}")
            raise Web3ServiceException(str(e))
        except Exception as e:
            logger.error(f"❌ Unexpected error getting token benefits: {e}")
            raise Web3ServiceException(f"Unexpected error: {e}")

# Create global service instance
token_benefits_service = TokenBenefitsService()

# =============================================================================
# EXISTING ENDPOINTS - Heroes and Weapons
# =============================================================================

@router.get("/api/v1/users/get_items/")
async def get_user_nfts_unity(address: str = Query(..., description="Wallet address")):
    """
    Get Heroes NFTs with Unity-compatible format
    Returns paginated format with "sec"/"ano"/"inn" fields
    """
    if not SERVICES_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Web3 services not available"
        )
    
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
    if not SERVICES_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Web3 services not available"
        )
    
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

# =============================================================================
# NEW TOKEN BENEFITS ENDPOINTS
# =============================================================================

@router.get("/api/v1/staking/")
async def get_user_token_benefits(address: str = Query(..., description="Wallet address")):
    """
    Get user's token-based DeFi benefits
    
    Maps ERC20 token holdings to game benefits:
    - MEDALLC tokens → Shield ability (staking simulation)
    - MOH tokens → Basic perk selection (farming simulation)
    """
    if not SERVICES_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Web3 services not available"
        )
    
    try:
        logger.info(f"🪙 Token benefits endpoint called for address: {address}")
        
        # Get token benefits using real blockchain data
        benefits_response = await token_benefits_service.get_all_token_benefits(address)
        
        logger.info(f"✅ Token benefits endpoint successful for {address}")
        return benefits_response
        
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
        logger.error(f"❌ Unexpected error in token benefits endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred"
        )

@router.get("/api/v1/users/staking/")
async def get_user_token_benefits_alt(address: str = Query(..., description="Wallet address")):
    """Alternative endpoint path for token benefits"""
    return await get_user_token_benefits(address)

@router.get("/api/v1/tokens/balances/")
async def get_detailed_token_balances(address: str = Query(..., description="Wallet address")):
    """
    Get detailed token balance information for debugging
    """
    if not SERVICES_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Web3 services not available"
        )
    
    try:
        logger.info(f"🔍 Detailed token balances requested for address: {address}")
        
        # Get individual token balances
        moh_balance = await token_benefits_service.get_token_balance("moh", address)
        medallc_balance = await token_benefits_service.get_token_balance("medallc", address)
        
        return {
            "address": address.lower(),
            "tokens": {
                "moh": {
                    "balance": moh_balance,
                    "contract": TOKEN_CONTRACTS["moh"],
                    "benefit": "basic_perk_selection",
                    "enabled": moh_balance > 0
                },
                "medallc": {
                    "balance": medallc_balance, 
                    "contract": TOKEN_CONTRACTS["medallc"],
                    "benefit": "shield_ability",
                    "enabled": medallc_balance > 0
                }
            },
            "benefits_summary": {
                "shield_ability": medallc_balance > 0,
                "basic_perk_selection": moh_balance > 0,
                "total_benefits": sum([medallc_balance > 0, moh_balance > 0])
            }
        }
        
    except ValueError as e:
        logger.warning(f"⚠️ Invalid address provided: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid wallet address: {str(e)}"
        )
    except Web3ServiceException as e:
        logger.error(f"❌ Web3 service unavailable: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Blockchain service temporarily unavailable: {str(e)}"
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error in detailed token balances: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred"
        )

# =============================================================================
# EXISTING GAME ENDPOINTS - Timestamp and Score Submission
# =============================================================================

@router.get("/api/v1/minigames/medashooter/timestamp/", response_class=PlainTextResponse)
async def get_medashooter_timestamp():
    """
    Get server timestamp for Unity anti-cheat validation
    Returns plain text timestamp (not JSON) - Unity expects this format
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
    Handles RSA decryption and score validation
    """
    if not SERVICES_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Web3 services not available"
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
        
        # Anti-cheat validation (from old Django logic)
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
        
        # Score is valid - save to database
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
            
            # Check if player already has a score
            existing_score = await execute_query(
                "SELECT final_score FROM medashooter_scores WHERE player_address = $1 ORDER BY final_score DESC LIMIT 1",
                player_address
            )
            
            should_update = True
            if existing_score and existing_score[0]['final_score'] >= calculated_score:
                should_update = False
                logger.info(f"⏭️ Score {calculated_score} not better than existing {existing_score[0]['final_score']}")
            
            if should_update:
                # Get NFT boost data
                nft_boosts = await get_nft_boosts_for_player(player_address)
                
                # Store processed score
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
                
                logger.info(f"✅ Score saved successfully: {calculated_score} for {player_address[:8]}...")
            
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
    """
    if not SERVICES_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Web3 services not available"
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

# =============================================================================
# HEALTH CHECK AND MONITORING ENDPOINTS
# =============================================================================

@router.get("/api/v1/staking/health")
async def token_benefits_health_check():
    """Health check for token benefits service"""
    try:
        # Test Web3 connectivity
        service_status = "healthy" if SERVICES_AVAILABLE else "unavailable"
        
        if SERVICES_AVAILABLE:
            try:
                w3 = web3_service._get_working_web3()
                current_block = w3.eth.block_number
                web3_status = "connected"
            except Exception as e:
                current_block = None
                web3_status = f"error: {str(e)}"
        else:
            current_block = None
            web3_status = "services_not_available"
        
        return {
            "status": service_status,
            "service": "token_benefits",
            "web3_status": web3_status,
            "current_block": current_block,
            "contracts": TOKEN_CONTRACTS,
            "cache_stats": web3_service.get_cache_stats() if SERVICES_AVAILABLE else None,
            "supported_tokens": ["moh", "medallc"]
        }
        
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )

# Enhanced endpoints (already existing)
@router.get("/api/game/medashooter/enhanced-player-data")
async def get_enhanced_player_data(
    address: str = Query(..., description="Wallet address"), 
    chain: str = Query(default="polygon", description="Blockchain network")
):
    """
    Get comprehensive NFT data with enhanced boost calculations
    Enhanced endpoint for Web3 dApp usage
    """
    if not SERVICES_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Web3 services not available"
        )
    
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

@router.get("/api/game/medashooter/scoreboard")
async def get_medashooter_scoreboard(
    limit: int = Query(default=50, description="Number of top scores to return"),
    player_address: Optional[str] = Query(default=None, description="Player address for user score")
):
    """
    Get MedaShooter leaderboard with optional user score
    """
    try:
        # Get top scores
        top_scores = await execute_query(
            """SELECT player_address, final_score, submission_time, nft_boosts_used
               FROM medashooter_scores 
               WHERE validated = TRUE 
               ORDER BY final_score DESC 
               LIMIT $1""",
            limit
        )
        
        scoreboard = []
        for i, score in enumerate(top_scores, 1):
            scoreboard.append({
                "rank": i,
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
                    WHERE s2.final_score > s1.final_score AND s2.validated = TRUE) as rank
                   FROM medashooter_scores s1
                   WHERE player_address = $1 AND validated = TRUE
                   ORDER BY final_score DESC LIMIT 1""",
                player_address
            )
            
            if user_score:
                result["user_score"] = {
                    "address": player_address,
                    "score": user_score[0]["final_score"],
                    "rank": user_score[0]["rank"],
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

# Debug and monitoring endpoints
@router.get("/api/web3/service-status")
async def get_web3_service_status():
    """
    Get Web3 service status and cache statistics
    Useful for monitoring and debugging
    """
    if not SERVICES_AVAILABLE:
        return {
            "service_status": "unavailable",
            "error": "Web3 services not imported",
            "timestamp": int(time.time())
        }
    
    try:
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
            logger.error(f"Web3 connectivity test failed: {e}")
        
        # Test RSA decryption service
        decryption_service = get_decryption_service()
        rsa_status = "available" if (decryption_service and decryption_service.is_available()) else "unavailable"
        
        return {
            "service_status": service_status,
            "current_block": current_block,
            "cache_stats": cache_stats,
            "rsa_decryption": rsa_status,
            "token_contracts": TOKEN_CONTRACTS,
            "timestamp": int(time.time())
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
    if not SERVICES_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Web3 services not available"
        )
    
    try:
        web3_service.clear_cache()
        
        return {
            "message": "Cache cleared successfully",
            "timestamp": int(time.time())
        }
        
    except Exception as e:
        logger.error(f"❌ Error clearing cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to clear cache"
        )

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def calculate_unity_score(raw_score: int) -> int:
    """
    Apply Unity's score decryption algorithm (from old Django code)
    This reverses the encryption Unity applies to scores
    """
    import numpy as np
    
    score = np.uint32(raw_score)
    score = np.uint32(((score >> 16) ^ score) * 0x119DE1F3)
    score = np.uint32(((score >> 16) ^ score) * 0x119DE1F3)
    return int(np.uint32(((score >> 16) ^ score)))

async def get_nft_boosts_for_player(player_address: str) -> Dict[str, Any]:
    """
    Get current NFT boosts for a player using the enhanced service
    """
    try:
        player_data = await enhanced_moralis_service.get_enhanced_player_data(player_address)
        return player_data.get("boosts", {})
    except Exception as e:
        logger.warning(f"⚠️ Failed to get NFT boosts for {player_address}: {e}")
        return {}