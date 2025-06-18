# app/routes/medashooter_routes.py - Updated with real data integration
from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import time
import logging
from app.services.decryption_service import MedaShooterDecryption, calculate_shifted_score
from app.services.enhanced_moralis_service import enhanced_moralis_service
from app.database import execute_query, execute_command

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize decryption service
try:
    decryption_service = MedaShooterDecryption()
    logger.info("✅ MedaShooter RSA decryption service initialized")
except Exception as e:
    logger.warning(f"⚠️ RSA decryption service not available: {e}")
    decryption_service = None

# Pydantic models for Unity compatibility
class UnityScoreSubmission(BaseModel):
    """
    Unity's complete encrypted score submission format
    Exactly matching JsonBuilder.cs output
    """
    hash: str  # RSA encrypted score (score key)
    address: str  # RSA encrypted wallet address (score key)
    delta: str  # RSA encrypted game duration (info key)
    parameter1: str  # RSA encrypted enemies_spawned (info key)
    parameter2: str  # RSA encrypted enemies_killed (info key)
    parameter3: str  # RSA encrypted waves_completed (info key)
    parameter4: str  # RSA encrypted travel_distance (info key)
    parameter5: str  # RSA encrypted perks_collected (info key)
    parameter6: str  # RSA encrypted coins_collected (info key)
    parameter7: str  # RSA encrypted shields_collected (info key)
    parameter8: str  # RSA encrypted killing_spree_mult (info key)
    parameter9: str  # RSA encrypted killing_spree_duration (info key)
    parameter10: str  # RSA encrypted max_killing_spree (info key)
    parameter11: str  # RSA encrypted attack_speed (info key)
    parameter12: str  # RSA encrypted max_score_per_enemy (info key)
    parameter13: str  # RSA encrypted max_score_per_enemy_scaled (info key)
    parameter14: str  # RSA encrypted ability_use_count (info key)
    parameter15: str  # RSA encrypted enemies_killed_while_killing_spree (info key)

class UnityCheatReport(BaseModel):
    """Unity's encrypted cheat report format"""
    address: str  # RSA encrypted address (info key)

# Unity-Compatible Endpoints
@router.get("/api/v1/users/get_items/")
async def get_user_nfts_unity(address: str = Query(..., description="Wallet address")):
    """
    Unity Heroes Endpoint - EXACT format compatibility with REAL blockchain data
    
    Critical field mappings:
    - sec → Unity expects "sec" (not "security")
    - ano → Unity expects "ano" (not "anonymity") 
    - inn → Unity expects "inn" (not "innovation")
    - fraction → Maps to "Goliath|Renegade|Neutral"
    - Response format: Paginated object with results array
    """
    try:
        logger.info(f"🎮 Unity Heroes request for address: {address[:8]}...")
        
        # Fetch heroes from blockchain using enhanced Moralis service
        heroes_response = await enhanced_moralis_service.get_heroes_for_unity(address)
        
        logger.info(f"✅ Heroes response: {heroes_response['count']} heroes for {address[:8]}...")
        return heroes_response
        
    except Exception as e:
        logger.error(f"❌ Heroes endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch heroes")

@router.get("/api/v1/weapon_item/user_weapons/")
async def get_user_weapons_unity(address: str = Query(..., description="Wallet address")):
    """
    Unity Weapons Endpoint - EXACT format compatibility with REAL blockchain data
    
    Critical field mappings:
    - security → Unity expects "security" (full word)
    - anonymity → Unity expects "anonymity" (full word)
    - innovation → Unity expects "innovation" (full word)
    - weapon_name → Critical field Unity requires
    - minted → Boolean indicating NFT status
    - Response format: Direct array (not paginated)
    """
    try:
        logger.info(f"🔫 Unity Weapons request for address: {address[:8]}...")
        
        # Fetch weapons from blockchain using enhanced Moralis service
        weapons_response = await enhanced_moralis_service.get_weapons_for_unity(address)
        
        logger.info(f"✅ Weapons response: {len(weapons_response)} weapons for {address[:8]}...")
        return weapons_response  # Direct array, not paginated
        
    except Exception as e:
        logger.error(f"❌ Weapons endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch weapons")

@router.post("/api/v1/minigames/medashooter/score/")
async def submit_score_unity(submission: UnityScoreSubmission):
    """
    Unity Score Submission Endpoint - Complete RSA decryption and processing
    
    Process:
    1. Store raw encrypted data for Unity compatibility
    2. Decrypt all 17 parameters using RSA keys
    3. Calculate actual score using Unity's algorithm
    4. Validate against anti-cheat rules
    5. Process legitimate scores and update leaderboards
    """
    try:
        logger.info("🎯 Unity score submission received")
        
        # Check if RSA decryption service is available
        if not decryption_service:
            logger.error("❌ RSA decryption service not available")
            return {"status": "Server was not able to decode message"}
        
        # 1. Store raw encrypted data (Unity compatibility layer)
        try:
            unity_score_id = await execute_query("""
                INSERT INTO medashooter_unity_scores (
                    encrypted_hash, encrypted_address, encrypted_delta,
                    encrypted_parameter1, encrypted_parameter2, encrypted_parameter3,
                    encrypted_parameter4, encrypted_parameter5, encrypted_parameter6,
                    encrypted_parameter7, encrypted_parameter8, encrypted_parameter9,
                    encrypted_parameter10, encrypted_parameter11, encrypted_parameter12,
                    encrypted_parameter13, encrypted_parameter14, encrypted_parameter15,
                    raw_submission
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)
                RETURNING id
            """, 
                submission.hash, submission.address, submission.delta,
                submission.parameter1, submission.parameter2, submission.parameter3,
                submission.parameter4, submission.parameter5, submission.parameter6,
                submission.parameter7, submission.parameter8, submission.parameter9,
                submission.parameter10, submission.parameter11, submission.parameter12,
                submission.parameter13, submission.parameter14, submission.parameter15,
                submission.dict()
            )
            unity_record_id = unity_score_id[0]["id"] if unity_score_id else None
        except Exception as e:
            logger.warning(f"⚠️ Failed to store raw Unity data: {e}")
            unity_record_id = None

        # 2. Decrypt all data using RSA keys
        decrypted_data = decryption_service.decrypt_score_submission(submission.dict())
        logger.info(f"📊 Decrypted score: {decrypted_data['score']} from {decrypted_data['address'][:8]}...")
        
        # 3. Calculate actual score using Unity's algorithm
        actual_score = calculate_shifted_score(decrypted_data["score"])
        logger.info(f"🔢 Calculated shifted score: {actual_score}")
        
        # 4. Basic anti-cheat validation (exact logic from Django backend)
        validation_errors = []
        
        # Time vs score validation
        if decrypted_data["duration"] * 100 < actual_score:
            validation_errors.append(f"Time cheat: {actual_score} score in {decrypted_data['duration']} seconds")
        
        # Enemies vs score validation
        if decrypted_data["enemies_spawned"] * 250 < actual_score:
            validation_errors.append(f"Enemy cheat: {actual_score} score with {decrypted_data['enemies_spawned']} enemies")
        
        # Check blacklist
        try:
            blacklisted = await execute_query(
                "SELECT is_address_blacklisted($1)",
                decrypted_data["address"].lower()
            )
            if blacklisted and blacklisted[0].get("is_address_blacklisted"):
                validation_errors.append("Address blacklisted")
        except Exception as e:
            logger.warning(f"⚠️ Blacklist check failed: {e}")
        
        if validation_errors:
            logger.warning(f"⚠️ Anti-cheat violations: {validation_errors}")
            # Flag as cheating but return success to Unity (as per original backend)
            try:
                await execute_command("""
                    INSERT INTO medashooter_blacklist (player_address, reason, evidence)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (player_address) DO UPDATE SET
                        reason = EXCLUDED.reason,
                        evidence = EXCLUDED.evidence,
                        blacklisted_at = NOW()
                """, 
                    decrypted_data["address"].lower(),
                    "Anti-cheat validation failed",
                    {"violations": validation_errors, "score": actual_score}
                )
            except Exception as e:
                logger.warning(f"⚠️ Failed to update blacklist: {e}")
            
            return {"status": "Score updated"}
        
        # 5. Process legitimate score
        try:
            # Get current NFT boosts for the player
            nft_boosts = {}
            try:
                player_data = await enhanced_moralis_service.get_enhanced_player_data(decrypted_data["address"])
                if player_data["success"]:
                    nft_boosts = player_data["data"]["game_boosts"]
            except Exception as e:
                logger.warning(f"⚠️ Failed to get NFT boosts: {e}")
            
            # Store processed score
            score_id = await execute_query("""
                INSERT INTO medashooter_scores (
                    unity_score_id, player_address, final_score, calculated_score,
                    enemies_killed, enemies_spawned, waves_completed, game_duration,
                    travel_distance, perks_collected, coins_collected, shields_collected,
                    killing_spree_mult, killing_spree_duration, max_killing_spree,
                    attack_speed, max_score_per_enemy, max_score_per_enemy_scaled,
                    ability_use_count, enemies_killed_while_killing_spree,
                    nft_boosts_used, meda_gas_reward
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15,
                    $16, $17, $18, $19, $20, $21, $22
                ) RETURNING id
            """,
                unity_record_id, decrypted_data["address"].lower(), decrypted_data["score"], actual_score,
                decrypted_data["enemies_killed"], decrypted_data["enemies_spawned"], 
                decrypted_data["waves_completed"], decrypted_data["duration"],
                decrypted_data["travel_distance"], decrypted_data["perks_collected"],
                decrypted_data["coins_collected"], decrypted_data["shields_collected"],
                decrypted_data["killing_spree_mult"], decrypted_data["killing_spree_duration"],
                decrypted_data["max_killing_spree"], decrypted_data["attack_speed"],
                decrypted_data["max_score_per_enemy"], decrypted_data["max_score_per_enemy_scaled"],
                decrypted_data["ability_use_count"], decrypted_data["enemies_killed_while_killing_spree"],
                nft_boosts, min(int(actual_score / 100), 10000)  # MEDA Gas reward calculation
            )
            
            logger.info(f"✅ Valid score processed: {actual_score}")
            
        except Exception as e:
            logger.error(f"❌ Failed to store processed score: {e}")
            # Still return success to Unity to avoid game disruption
        
        # Unity expects exactly this response format
        return {"status": "Score updated"}
        
    except ValueError as e:
        logger.error(f"❌ Decryption failed: {e}")
        # Unity expects this exact error message for decryption failures
        return {"status": "Server was not able to decode message"}
    
    except Exception as e:
        logger.error(f"❌ Score submission error: {e}")
        return {"status": "Server was not able to decode message"}

@router.get("/api/v1/minigames/medashooter/timestamp/", response_class=PlainTextResponse)
async def get_server_timestamp_unity():
    """
    Unity Timestamp Endpoint - Returns plain text string (NOT JSON)
    
    Critical: Unity expects timestamp as string, not JSON object
    Used for anti-cheat timing validation
    """
    timestamp = str(int(time.time()))
    logger.info(f"⏰ Unity timestamp request: {timestamp}")
    return timestamp

@router.post("/api/v1/minigames/medashooter/blacklist/")
async def report_cheating_unity(request: UnityCheatReport):
    """
    Unity Anti-Cheat Reporting Endpoint
    Receives encrypted cheat reports from Unity's CheatDetector
    """
    try:
        logger.info("🚨 Unity cheat report received")
        
        if not decryption_service:
            logger.error("❌ RSA decryption service not available")
            return {"status": "Server was not able to decode message"}
        
        # Decrypt the reported address using info private key
        encrypted_address = request.address
        decrypted_address = decryption_service.decrypt_info_data(encrypted_address)
        
        # Extract address from Unity's format: <address>0x...</address>
        if decrypted_address.startswith("<address>") and decrypted_address.endswith("</address>"):
            real_address = decrypted_address[9:-10]  # Remove XML tags
            logger.warning(f"🚨 Cheat report for address: {real_address[:8]}...")
            
            # Add to blacklist
            try:
                await execute_command("""
                    INSERT INTO medashooter_blacklist (player_address, reason, evidence)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (player_address) DO UPDATE SET
                        reason = EXCLUDED.reason,
                        evidence = EXCLUDED.evidence,
                        blacklisted_at = NOW()
                """, 
                    real_address.lower(),
                    "Blacklisted from Unity anti-cheat",
                    {"source": "unity_cheat_detector", "encrypted_report": encrypted_address}
                )
            except Exception as e:
                logger.warning(f"⚠️ Failed to update blacklist: {e}")
            
            return {"status": "Report submitted"}
        
        logger.error("❌ Invalid address format in cheat report")
        return {"status": "Invalid address format"}
        
    except Exception as e:
        logger.error(f"❌ Blacklist submission error: {e}")
        return {"status": "Server was not able to decode message"}

@router.get("/api/v1/user/active_boost_cards")
async def get_active_boost_cards_unity(address: str = Query(...)):
    """
    Unity Boost Cards Endpoint - Real NFT advantages from blockchain
    Returns current NFT boosts for the player
    """
    try:
        logger.info(f"⚡ Unity boost cards request for {address[:8]}...")
        
        # Get real NFT boost data
        try:
            player_data = await enhanced_moralis_service.get_enhanced_player_data(address)
            if player_data["success"]:
                boosts = player_data["data"]["game_boosts"]
                logger.info(f"✅ Real NFT boost cards: {boosts}")
                return boosts
        except Exception as e:
            logger.warning(f"⚠️ Failed to get real NFT boosts: {e}")
        
        # Fallback to no boosts
        boosts = {
            "damage_multiplier": 0,
            "fire_rate_bonus": 0,
            "score_multiplier": 0,
            "health_bonus": 0,
            "meda_gas_multiplier": 0
        }
        
        logger.info(f"✅ Fallback boost cards: {boosts}")
        return boosts
        
    except Exception as e:
        logger.error(f"❌ Boost cards error: {e}")
        return {
            "damage_multiplier": 0,
            "fire_rate_bonus": 0,
            "score_multiplier": 0,
            "health_bonus": 0,
            "meda_gas_multiplier": 0
        }

# Enhanced Web3 Endpoints for dApp Frontend
@router.get("/api/game/medashooter/enhanced-player-data")
async def get_enhanced_player_data(
    address: str = Query(..., description="Wallet address"),
    chain: str = Query("polygon", description="Blockchain network")
):
    """
    Comprehensive NFT data with enhanced boost calculations
    Used by Web3 dApp frontend for displaying player advantages
    """
    try:
        logger.info(f"🔍 Enhanced player data request for {address[:8]}...")
        
        # Use the enhanced Moralis service for real blockchain data
        player_data = await enhanced_moralis_service.get_enhanced_player_data(address, chain)
        
        logger.info(f"✅ Enhanced data: {player_data['data']['nft_counts']['total']} total NFTs")
        return player_data
        
    except Exception as e:
        logger.error(f"❌ Enhanced player data error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch enhanced player data: {str(e)}")

@router.get("/api/game/medashooter/scoreboard")
async def get_medashooter_scoreboard(
    address: Optional[str] = Query(None, description="Player address for user score"),
    limit: int = Query(50, description="Number of scores to return"),
    period: str = Query("all", description="Time period: daily|weekly|monthly|all")
):
    """
    Enhanced scoreboard with NFT boost tracking and player rankings
    Uses real database data from score submissions
    """
    try:
        logger.info(f"🏆 Scoreboard request: period={period}, limit={limit}")
        
        # Build time filter based on period
        time_filter = ""
        if period == "daily":
            time_filter = "AND submission_time >= NOW() - INTERVAL '1 day'"
        elif period == "weekly":
            time_filter = "AND submission_time >= NOW() - INTERVAL '7 days'"
        elif period == "monthly":
            time_filter = "AND submission_time >= NOW() - INTERVAL '30 days'"
        
        # Get leaderboard data
        scoreboard_data = await execute_query(f"""
            SELECT 
                ROW_NUMBER() OVER (ORDER BY final_score DESC) as rank,
                player_address as address,
                final_score as score,
                meda_gas_reward,
                COALESCE((nft_boosts_used->>'total_nfts')::int, 0) as nfts_used,
                submission_time,
                nft_boosts_used as nft_boosts
            FROM medashooter_scores 
            WHERE validated = true {time_filter}
            ORDER BY final_score DESC
            LIMIT $1
        """, limit)
        
        # Format scoreboard
        scoreboard = []
        for row in scoreboard_data:
            scoreboard.append({
                "rank": row["rank"],
                "address": row["address"],
                "score": row["score"],
                "meda_gas_reward": row["meda_gas_reward"],
                "nfts_used": row["nfts_used"],
                "submission_time": row["submission_time"].isoformat() if row["submission_time"] else None,
                "nft_boosts": row["nft_boosts"]
            })
        
        # Find user score if address provided
        user_score = None
        if address:
            user_data = await execute_query(f"""
                SELECT 
                    final_score as score,
                    ROW_NUMBER() OVER (ORDER BY final_score DESC) as rank,
                    meda_gas_reward,
                    COALESCE((nft_boosts_used->>'total_nfts')::int, 0) as nfts_used,
                    submission_time
                FROM medashooter_scores 
                WHERE player_address = $1 AND validated = true {time_filter}
                ORDER BY final_score DESC
                LIMIT 1
            """, address.lower())
            
            if user_data:
                user_score = {
                    "score": user_data[0]["score"],
                    "rank": user_data[0]["rank"],
                    "address": address.lower(),
                    "meda_gas_reward": user_data[0]["meda_gas_reward"],
                    "nfts_used": user_data[0]["nfts_used"],
                    "submission_time": user_data[0]["submission_time"].isoformat() if user_data[0]["submission_time"] else None
                }
        
        return {
            "success": True,
            "data": {
                "user_score": user_score,
                "scoreboard": scoreboard,
                "period": period,
                "total_players": len(scoreboard),
                "last_updated": time.time(),
                "nft_boost_enabled": True
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Scoreboard error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch scoreboard: {str(e)}")

# Health check endpoint
@router.get("/api/medashooter/health")
async def medashooter_health_check():
    """MedaShooter-specific health check"""
    try:
        # Test RSA decryption service
        rsa_status = "operational" if decryption_service else "not_available"
        
        # Test database connectivity
        db_test = await execute_query("SELECT 1")
        db_status = "connected" if db_test else "disconnected"
        
        # Test Moralis service
        moralis_status = "operational"
        try:
            await enhanced_moralis_service.get_enhanced_player_data("0x0000000000000000000000000000000000000000")
        except Exception:
            moralis_status = "limited"  # Expected to fail with null address
        
        return {
            "status": "operational",
            "timestamp": int(time.time()),
            "services": {
                "rsa_decryption": rsa_status,
                "database": db_status,
                "moralis_nft_service": moralis_status
            },
            "unity_compatibility": {
                "score_decryption": rsa_status == "operational",
                "field_mappings": "configured",
                "response_formats": "unity_compatible"
            },
            "endpoints": {
                "heroes": "/api/v1/users/get_items/",
                "weapons": "/api/v1/weapon_item/user_weapons/",
                "score_submission": "/api/v1/minigames/medashooter/score/",
                "timestamp": "/api/v1/minigames/medashooter/timestamp/",
                "blacklist": "/api/v1/minigames/medashooter/blacklist/",
                "boost_cards": "/api/v1/user/active_boost_cards"
            }
        }
        
    except Exception as e:
        logger.error(f"MedaShooter health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": int(time.time())
        }