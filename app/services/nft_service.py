# services/nft_service.py - Unified NFT Service with Smart Database Caching
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import json

# Import our new blockchain service and database
from .blockchain_service import blockchain_service, BlockchainServiceException
from app.database import execute_query, execute_command, get_character_by_season_card_id

logger = logging.getLogger(__name__)

# Minimal ABIs - just the functions we need for smart contract calls
HEROES_ABI = [
    {
        "inputs": [{"internalType": "address", "name": "_owner", "type": "address"}],
        "name": "tokensOfOwner",
        "outputs": [{"internalType": "uint256[]", "name": "", "type": "uint256[]"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "_tokenId", "type": "uint256"}],
        "name": "getAttribs",
        "outputs": [
            {"internalType": "uint256", "name": "_sec", "type": "uint256"},
            {"internalType": "uint256", "name": "_ano", "type": "uint256"},
            {"internalType": "uint256", "name": "_inn", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "_tokenId", "type": "uint256"}],
        "name": "getTokenInfo",
        "outputs": [
            {"internalType": "uint256", "name": "", "type": "uint256"},
            {"internalType": "uint256", "name": "", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

WEAPONS_ABI = [
    {
        "inputs": [{"internalType": "address", "name": "_owner", "type": "address"}],
        "name": "tokensOfOwner",
        "outputs": [{"internalType": "uint256[]", "name": "", "type": "uint256[]"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "_tokenId", "type": "uint256"}],
        "name": "getAttribs",
        "outputs": [
            {"internalType": "uint256", "name": "", "type": "uint256"},
            {"internalType": "uint256", "name": "", "type": "uint256"},
            {"internalType": "uint256", "name": "", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "_tokenId", "type": "uint256"}],
        "name": "getTokenInfo",
        "outputs": [
            {"internalType": "uint256", "name": "", "type": "uint256"},
            {"internalType": "uint256", "name": "", "type": "uint256"},
            {"internalType": "uint256", "name": "", "type": "uint256"},
            {"internalType": "uint256", "name": "", "type": "uint256"},
            {"internalType": "uint256", "name": "", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

class NFTServiceException(Exception):
    """Custom exception for NFT service errors"""
    pass

class NFTService:
    """
    Unified NFT service combining smart contract caching and game data processing
    Handles both Unity game format and React dApp requirements
    Integrates enhanced_moralis_service + token_cache_service functionality
    """
    
    def __init__(self):
        self.chain = "polygon"
        self.error_counts = {"heroes": 0, "weapons": 0, "lands": 0}
        
        # Land Tickets metadata (static data)
        self.land_metadata = {
            1: {
                "name": "Common Land",
                "rarity": "Common",
                "plots": 1,
                "image": "/land1.png"
            },
            2: {
                "name": "Rare Land", 
                "rarity": "Rare",
                "plots": 3,
                "image": "/land2.png"
            },
            3: {
                "name": "Legendary Land",
                "rarity": "Legendary", 
                "plots": 7,
                "image": "/land3.png"
            }
        }
        
        logger.info("✅ Unified NFT service initialized with smart caching and multi-format support")
    
    # ============================================================================
    # UNITY-COMPATIBLE NFT METHODS (Heroes & Weapons)
    # ============================================================================
    
    async def get_heroes_for_unity(self, address: str) -> Dict:
        """
        Get Heroes NFTs with Unity-compatible format using smart database caching
        Returns exact format Unity expects with significant performance improvement
        """
        try:
            logger.info(f"🦸 Fetching Heroes for {address} using smart caching")
            
            # Use database-cached approach for massive performance boost
            heroes = await self._get_heroes_with_database_cache(address, HEROES_ABI)
            
            # Build Unity-compatible response format
            result = {
                "results": heroes,
                "count": len(heroes),
                "next": None
            }
            
            logger.info(f"✅ Successfully fetched {len(heroes)} Heroes with smart caching")
            return result
            
        except ValueError as e:
            # Address validation error - client error
            logger.error(f"❌ Address validation error: {e}")
            raise ValueError(str(e))
        except BlockchainServiceException as e:
            # Blockchain service error - server error
            logger.error(f"❌ Blockchain service error: {e}")
            raise NFTServiceException(str(e))
        except Exception as e:
            logger.error(f"❌ Unexpected error fetching heroes: {e}")
            raise NFTServiceException(f"Unexpected error: {e}")
    
    async def get_weapons_for_unity(self, address: str) -> List[Dict]:
        """
        Get Weapons NFTs with Unity-compatible format using smart database caching
        Returns exact format Unity expects with significant performance improvement
        """
        try:
            logger.info(f"⚔️ Fetching Weapons for {address} using smart caching")
            
            # Use database-cached approach for massive performance boost
            weapons = await self._get_weapons_with_database_cache(address, WEAPONS_ABI)
            
            logger.info(f"✅ Successfully fetched {len(weapons)} Weapons with smart caching")
            return weapons
            
        except ValueError as e:
            # Address validation error - client error
            logger.error(f"❌ Address validation error: {e}")
            raise ValueError(str(e))
        except BlockchainServiceException as e:
            # Blockchain service error - server error
            logger.error(f"❌ Blockchain service error: {e}")
            raise NFTServiceException(str(e))
        except Exception as e:
            logger.error(f"❌ Unexpected error fetching weapons: {e}")
            raise NFTServiceException(f"Unexpected error: {e}")
    
    async def get_land_tickets(self, address: str) -> List[Dict]:
        """
        Get Land Tickets with clean, reusable format
        Returns exact format that ProfilePage expects
        No caching - always live blockchain data for accurate balances
        """
        try:
            logger.info(f"🏞️ Fetching Land Tickets for {address}")
            
            # Token IDs for land tickets (ERC1155)
            token_ids = [1, 2, 3]
            
            # Get live balances from blockchain (no caching for balances)
            balances = await blockchain_service.get_erc1155_balances('lands', address, token_ids)
            
            # Build response in expected format
            lands = []
            for token_id, balance in zip(token_ids, balances):
                metadata = self.land_metadata[token_id]
                
                lands.append({
                    "id": token_id,
                    "token_id": token_id,
                    "name": metadata["name"],
                    "rarity": metadata["rarity"],
                    "plots": metadata["plots"],
                    "image": metadata["image"],
                    "balance": balance,
                    "contract_address": blockchain_service.config.get_contract_address('lands'),
                    "nft_type": "land"
                })
            
            logger.info(f"✅ Successfully fetched {len(lands)} land types with total {sum(balances)} tickets")
            return lands
            
        except ValueError as e:
            # Address validation error - client error
            logger.error(f"❌ Address validation error: {e}")
            raise ValueError(str(e))
        except BlockchainServiceException as e:
            # Blockchain service error - server error
            logger.error(f"❌ Blockchain service error: {e}")
            raise NFTServiceException(str(e))
        except Exception as e:
            logger.error(f"❌ Unexpected error fetching land tickets: {e}")
            
            # Return error format (all balances -1 to indicate blockchain failure)
            error_lands = []
            for token_id in [1, 2, 3]:
                metadata = self.land_metadata[token_id]
                
                error_lands.append({
                    "id": token_id,
                    "token_id": token_id,
                    "name": metadata["name"],
                    "rarity": metadata["rarity"],
                    "plots": metadata["plots"],
                    "image": metadata["image"],
                    "balance": -1,  # Error indicator
                    "contract_address": blockchain_service.config.get_contract_address('lands'),
                    "nft_type": "land"
                })
            
            logger.warning(f"⚠️ Returning error format for land tickets due to: {e}")
            return error_lands
    
    # ============================================================================
    # PROFILEPAGE OPTIMIZED METHODS (72-76% Size Reduction)
    # ============================================================================
    
    async def get_heroes_optimized(self, address: str) -> Dict:
        """
        ProfilePage-optimized heroes endpoint - 72% size reduction
        Returns only essential fields: bc_id, sec, ano, inn, season_card_id
        """
        try:
            logger.info(f"🦸‍♂️ ProfilePage Heroes optimized request for: {address[:8]}...")
            
            # Get full heroes data using existing method
            full_heroes_response = await self.get_heroes_for_unity(address)
            
            # Extract ONLY ProfilePage essential fields (massive size reduction)
            optimized_heroes = []
            for hero in full_heroes_response.get("results", []):
                optimized_hero = {
                    "bc_id": hero["bc_id"],                    # React key + token ID display
                    "metadata": {
                        "sec": hero["metadata"]["sec"],        # Power calculation
                        "ano": hero["metadata"]["ano"],        # Power calculation  
                        "inn": hero["metadata"]["inn"],        # Power calculation
                        "season_card_id": hero["metadata"]["season_card_id"]  # Image path + rarity
                    }
                }
                optimized_heroes.append(optimized_hero)
            
            response = {
                "results": optimized_heroes,
                "count": len(optimized_heroes)
            }
            
            original_size = len(str(full_heroes_response))
            optimized_size = len(str(response))
            reduction_percent = ((original_size - optimized_size) / original_size) * 100
            
            logger.info(f"✅ ProfilePage Heroes: {len(optimized_heroes)} heroes")
            logger.info(f"📊 Size reduction: {original_size} → {optimized_size} bytes ({reduction_percent:.1f}% smaller)")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ ProfilePage Heroes optimization error: {e}")
            raise
    
    async def get_weapons_optimized(self, address: str) -> List[Dict]:
        """
        ProfilePage-optimized weapons endpoint - 76% size reduction
        Returns only essential fields: bc_id, weapon_name, security, anonymity, innovation
        """
        try:
            logger.info(f"⚔️ ProfilePage Weapons optimized request for: {address[:8]}...")
            
            # Get full weapons data using existing method
            full_weapons_response = await self.get_weapons_for_unity(address)
            
            # Extract ONLY ProfilePage essential fields (massive size reduction)
            optimized_weapons = []
            for weapon in full_weapons_response:
                optimized_weapon = {
                    "bc_id": weapon["bc_id"],                  # React key + token ID display
                    "weapon_name": weapon["weapon_name"],      # Video path normalization
                    "security": weapon["security"],            # Power calculation
                    "anonymity": weapon["anonymity"],          # Power calculation
                    "innovation": weapon["innovation"]         # Power calculation
                }
                optimized_weapons.append(optimized_weapon)
            
            original_size = len(str(full_weapons_response))
            optimized_size = len(str(optimized_weapons))
            reduction_percent = ((original_size - optimized_size) / original_size) * 100
            
            logger.info(f"✅ ProfilePage Weapons: {len(optimized_weapons)} weapons")
            logger.info(f"📊 Size reduction: {original_size} → {optimized_size} bytes ({reduction_percent:.1f}% smaller)")
            
            return optimized_weapons
            
        except Exception as e:
            logger.error(f"❌ ProfilePage Weapons optimization error: {e}")
            raise
    
    # ============================================================================
    # ENHANCED PLAYER DATA (Web3 dApp + Game Integration)
    # ============================================================================
    
    async def get_enhanced_player_data(self, address: str, chain: str = "polygon") -> Dict:
        """
        Get comprehensive NFT data with enhanced boost calculations
        Combines Unity game data with Web3 dApp requirements
        """
        try:
            logger.info(f"🎮 Fetching enhanced player data for {address}")
            
            # Fetch all NFT types in parallel
            heroes_task = self.get_heroes_for_unity(address)
            weapons_task = self.get_weapons_for_unity(address)
            lands_task = self.get_land_tickets(address)
            
            heroes_result, weapons_result, lands_result = await asyncio.gather(
                heroes_task, weapons_task, lands_task, return_exceptions=True
            )
            
            # Handle any exceptions gracefully
            if isinstance(heroes_result, Exception):
                logger.error(f"Heroes fetch failed: {heroes_result}")
                heroes_result = {"results": [], "count": 0}
            
            if isinstance(weapons_result, Exception):
                logger.error(f"Weapons fetch failed: {weapons_result}")
                weapons_result = []
            
            if isinstance(lands_result, Exception):
                logger.error(f"Land tickets fetch failed: {lands_result}")
                lands_result = []
            
            # Calculate boost statistics
            hero_count = len(heroes_result.get("results", []))
            weapon_count = len(weapons_result)
            land_count = sum(land.get("balance", 0) for land in lands_result if land.get("balance", 0) > 0)
            
            # Enhanced boost calculation (matching Unity's expectations)
            boosts = {
                "damage_multiplier": min(hero_count * 5, 50),    # +5% per hero (max 50%)
                "fire_rate_bonus": min(weapon_count * 3, 30),   # +3% per weapon (max 30%)
                "score_multiplier": min(land_count * 2, 20),    # +2% per land ticket (max 20%)
                "health_bonus": hero_count * 25 + weapon_count * 15 + land_count * 10,
                "total_power": self._calculate_total_power(heroes_result.get("results", []), weapons_result)
            }
            
            return {
                "address": address.lower(),
                "chain": chain,
                "nfts": {
                    "heroes": heroes_result,
                    "weapons": weapons_result,
                    "lands": lands_result
                },
                "counts": {
                    "heroes": hero_count,
                    "weapons": weapon_count,
                    "lands": land_count,
                    "total": hero_count + weapon_count + land_count
                },
                "boosts": boosts,
                "metadata": {
                    "timestamp": int(asyncio.get_event_loop().time()),
                    "cache_enabled": True,
                    "service_version": "unified_v1.0"
                }
            }
            
        except ValueError as e:
            # Address validation error - client error
            logger.error(f"❌ Address validation error: {e}")
            raise ValueError(str(e))
        except NFTServiceException as e:
            # NFT service error - server error  
            logger.error(f"❌ NFT service error: {e}")
            raise NFTServiceException(str(e))
        except Exception as e:
            logger.error(f"❌ Unexpected error getting enhanced player data: {e}")
            raise NFTServiceException(f"Unexpected error: {e}")
    
    def _calculate_total_power(self, heroes: List[Dict], weapons: List[Dict]) -> int:
        """Calculate total power across all NFTs for game balancing"""
        total_power = 0
        
        # Heroes power (sec + ano + inn)
        for hero in heroes:
            metadata = hero.get("metadata", {})
            hero_power = metadata.get("sec", 0) + metadata.get("ano", 0) + metadata.get("inn", 0)
            total_power += hero_power
        
        # Weapons power (security + anonymity + innovation)
        for weapon in weapons:
            weapon_power = weapon.get("security", 0) + weapon.get("anonymity", 0) + weapon.get("innovation", 0)
            total_power += weapon_power
        
        return total_power
    
    # ============================================================================
    # SMART DATABASE CACHING METHODS (Core Performance Optimization)
    # ============================================================================
    
    async def _get_heroes_with_database_cache(self, address: str, heroes_abi: List[Dict]) -> List[Dict]:
        """
        Get heroes data using cache-first strategy with database optimization
        Massive performance improvement by reducing smart contract calls
        """
        try:
            logger.info(f"🦸 Getting heroes for {address} with database caching")
            
            # Step 1: Get token IDs from blockchain (always fresh for ownership verification)
            token_ids = await blockchain_service.get_tokens_of_owner('heroes', heroes_abi, address)
            
            if not token_ids:
                logger.info(f"No heroes found for {address}")
                return []
            
            logger.info(f"Found {len(token_ids)} hero token IDs: {token_ids}")
            
            # Step 2: Check database cache for each token
            cached_tokens, missing_tokens = await self._check_heroes_database_cache(token_ids)
            
            logger.info(f"Cache status: {len(cached_tokens)} cached, {len(missing_tokens)} missing")
            
            # Step 3: Fetch missing tokens from smart contracts
            fresh_tokens = []
            if missing_tokens:
                fresh_tokens = await self._fetch_heroes_from_contracts(missing_tokens, heroes_abi)
                
                # Step 4: Save fresh data to database cache
                if fresh_tokens:
                    await self._save_heroes_to_database_cache(fresh_tokens)
            
            # Step 5: Combine cached and fresh data
            all_tokens = cached_tokens + fresh_tokens
            
            # Step 6: Build Unity-compatible response with character data
            heroes = await self._build_heroes_response(all_tokens, address)
            
            logger.info(f"✅ Successfully processed {len(heroes)} heroes for {address}")
            return heroes
            
        except Exception as e:
            logger.error(f"❌ Error in get_heroes_with_database_cache: {e}")
            await self._log_cache_error('heroes', 0, 'get_heroes_failed', str(e), address)
            raise
    
    async def _get_weapons_with_database_cache(self, address: str, weapons_abi: List[Dict]) -> List[Dict]:
        """
        Get weapons data using cache-first strategy with database optimization
        Massive performance improvement by reducing smart contract calls
        """
        try:
            logger.info(f"⚔️ Getting weapons for {address} with database caching")
            
            # Step 1: Get token IDs from blockchain (always fresh for ownership verification)
            token_ids = await blockchain_service.get_tokens_of_owner('weapons', weapons_abi, address)
            
            if not token_ids:
                logger.info(f"No weapons found for {address}")
                return []
            
            logger.info(f"Found {len(token_ids)} weapon token IDs: {token_ids}")
            
            # Step 2: Check database cache for each token
            cached_tokens, missing_tokens = await self._check_weapons_database_cache(token_ids)
            
            logger.info(f"Cache status: {len(cached_tokens)} cached, {len(missing_tokens)} missing")
            
            # Step 3: Fetch missing tokens from smart contracts
            fresh_tokens = []
            if missing_tokens:
                fresh_tokens = await self._fetch_weapons_from_contracts(missing_tokens, weapons_abi)
                
                # Step 4: Save fresh data to database cache
                if fresh_tokens:
                    await self._save_weapons_to_database_cache(fresh_tokens)
            
            # Step 5: Combine cached and fresh data
            all_tokens = cached_tokens + fresh_tokens
            
            # Step 6: Build Unity-compatible response with weapon names
            weapons = await self._build_weapons_response(all_tokens, address)
            
            logger.info(f"✅ Successfully processed {len(weapons)} weapons for {address}")
            return weapons
            
        except Exception as e:
            logger.error(f"❌ Error in get_weapons_with_database_cache: {e}")
            await self._log_cache_error('weapons', 0, 'get_weapons_failed', str(e), address)
            raise
    
    # ============================================================================
    # HEROES DATABASE CACHE METHODS
    # ============================================================================
    
    async def _check_heroes_database_cache(self, token_ids: List[int]) -> Tuple[List[Dict], List[int]]:
        """Check which heroes are in database cache and which need to be fetched"""
        try:
            # Query database cache for all token IDs
            placeholders = ','.join(['$' + str(i+1) for i in range(len(token_ids))])
            query = f"""
                SELECT bc_id, sec, ano, inn, season_card_id, serial_number,
                       card_type, season_id, card_season_collection_id, last_updated
                FROM heroes_token_cache 
                WHERE bc_id IN ({placeholders}) AND is_valid = TRUE
            """
            
            cached_results = await execute_query(query, *token_ids)
            
            # Convert to list of dicts
            cached_tokens = []
            cached_token_ids = set()
            
            for row in cached_results:
                token_data = {
                    'bc_id': row['bc_id'],
                    'sec': row['sec'],
                    'ano': row['ano'], 
                    'inn': row['inn'],
                    'season_card_id': row['season_card_id'],
                    'serial_number': row['serial_number'],
                    'card_type': row['card_type'],
                    'season_id': row['season_id'],
                    'card_season_collection_id': row['card_season_collection_id'],
                    'last_updated': row['last_updated'],
                    'from_cache': True
                }
                cached_tokens.append(token_data)
                cached_token_ids.add(row['bc_id'])
            
            # Find missing tokens
            missing_tokens = [token_id for token_id in token_ids if token_id not in cached_token_ids]
            
            logger.debug(f"Heroes cache check: {len(cached_tokens)} found, {len(missing_tokens)} missing")
            return cached_tokens, missing_tokens
            
        except Exception as e:
            logger.error(f"❌ Error checking heroes database cache: {e}")
            # If cache check fails, treat all as missing
            return [], token_ids
    
    async def _fetch_heroes_from_contracts(self, token_ids: List[int], heroes_abi: List[Dict]) -> List[Dict]:
        """Fetch hero data from smart contracts in parallel"""
        fresh_tokens = []
        
        logger.info(f"🔗 Fetching {len(token_ids)} heroes from smart contracts")
        
        for token_id in token_ids:
            try:
                # Get attributes and info in parallel
                attributes_task = blockchain_service.get_token_attributes('heroes', heroes_abi, token_id)
                info_task = blockchain_service.get_token_info('heroes', heroes_abi, token_id)
                
                attributes, hero_info = await asyncio.gather(attributes_task, info_task)
                
                # Calculate additional fields
                season_card_id = hero_info.get("season_card_id", 0)
                card_type = season_card_id // 1000 if season_card_id else 0
                season_id = (season_card_id % 1000) // 10 if season_card_id else 0
                card_season_collection_id = season_card_id % 10 if season_card_id else 0
                
                token_data = {
                    'bc_id': token_id,
                    'sec': attributes["sec"],
                    'ano': attributes["ano"],
                    'inn': attributes["inn"],
                    'season_card_id': season_card_id,
                    'serial_number': hero_info.get("serial_number", 0),
                    'card_type': card_type,
                    'season_id': season_id,
                    'card_season_collection_id': card_season_collection_id,
                    'last_updated': datetime.utcnow(),
                    'from_cache': False
                }
                
                fresh_tokens.append(token_data)
                logger.debug(f"✅ Fetched hero {token_id}: sec={attributes['sec']}, season_card_id={season_card_id}")
                
            except Exception as e:
                logger.error(f"❌ Failed to fetch hero {token_id}: {e}")
                await self._log_cache_error('heroes', token_id, 'contract_call_failed', str(e))
                continue
        
        logger.info(f"✅ Successfully fetched {len(fresh_tokens)} heroes from contracts")
        return fresh_tokens
    
    async def _save_heroes_to_database_cache(self, tokens: List[Dict]):
        """Save hero data to database cache"""
        try:
            logger.info(f"💾 Saving {len(tokens)} heroes to database cache")
            
            for token in tokens:
                await execute_command(
                    """INSERT INTO heroes_token_cache 
                       (bc_id, sec, ano, inn, season_card_id, serial_number, last_updated, is_valid)
                       VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                       ON CONFLICT (bc_id) DO UPDATE SET
                           sec = EXCLUDED.sec,
                           ano = EXCLUDED.ano,
                           inn = EXCLUDED.inn,
                           season_card_id = EXCLUDED.season_card_id,
                           serial_number = EXCLUDED.serial_number,
                           last_updated = EXCLUDED.last_updated,
                           is_valid = EXCLUDED.is_valid""",
                    token['bc_id'],
                    token['sec'],
                    token['ano'],
                    token['inn'],
                    token['season_card_id'],
                    token['serial_number'],
                    token['last_updated'],
                    True
                )
            
            logger.info(f"✅ Saved {len(tokens)} heroes to database cache")
            
        except Exception as e:
            logger.error(f"❌ Failed to save heroes to database cache: {e}")
            # Don't raise - caching is optional
    
    # ============================================================================
    # WEAPONS DATABASE CACHE METHODS
    # ============================================================================
    
    async def _check_weapons_database_cache(self, token_ids: List[int]) -> Tuple[List[Dict], List[int]]:
        """Check which weapons are in database cache and which need to be fetched"""
        try:
            # Query database cache for all token IDs
            placeholders = ','.join(['$' + str(i+1) for i in range(len(token_ids))])
            query = f"""
                SELECT bc_id, security, anonymity, innovation, weapon_tier, weapon_type,
                       weapon_subtype, category, serial_number, last_updated
                FROM weapons_token_cache 
                WHERE bc_id IN ({placeholders}) AND is_valid = TRUE
            """
            
            cached_results = await execute_query(query, *token_ids)
            
            # Convert to list of dicts
            cached_tokens = []
            cached_token_ids = set()
            
            for row in cached_results:
                token_data = {
                    'bc_id': row['bc_id'],
                    'security': row['security'],
                    'anonymity': row['anonymity'],
                    'innovation': row['innovation'],
                    'weapon_tier': row['weapon_tier'],
                    'weapon_type': row['weapon_type'],
                    'weapon_subtype': row['weapon_subtype'],
                    'category': row['category'],
                    'serial_number': row['serial_number'],
                    'last_updated': row['last_updated'],
                    'from_cache': True
                }
                cached_tokens.append(token_data)
                cached_token_ids.add(row['bc_id'])
            
            # Find missing tokens
            missing_tokens = [token_id for token_id in token_ids if token_id not in cached_token_ids]
            
            logger.debug(f"Weapons cache check: {len(cached_tokens)} found, {len(missing_tokens)} missing")
            return cached_tokens, missing_tokens
            
        except Exception as e:
            logger.error(f"❌ Error checking weapons database cache: {e}")
            # If cache check fails, treat all as missing
            return [], token_ids
    
    async def _fetch_weapons_from_contracts(self, token_ids: List[int], weapons_abi: List[Dict]) -> List[Dict]:
        """Fetch weapon data from smart contracts in parallel"""
        fresh_tokens = []
        
        logger.info(f"🔗 Fetching {len(token_ids)} weapons from smart contracts")
        
        for token_id in token_ids:
            try:
                # Get attributes and info in parallel
                attributes_task = blockchain_service.get_token_attributes('weapons', weapons_abi, token_id)
                info_task = blockchain_service.get_token_info('weapons', weapons_abi, token_id)
                
                attributes, weapon_info = await asyncio.gather(attributes_task, info_task)
                
                token_data = {
                    'bc_id': token_id,
                    'security': attributes["security"],
                    'anonymity': attributes["anonymity"],
                    'innovation': attributes["innovation"],
                    'weapon_tier': weapon_info["weapon_tier"],
                    'weapon_type': weapon_info["weapon_type"],
                    'weapon_subtype': weapon_info["weapon_subtype"],
                    'category': weapon_info["category"],
                    'serial_number': weapon_info["serial_number"],
                    'last_updated': datetime.utcnow(),
                    'from_cache': False
                }
                
                fresh_tokens.append(token_data)
                logger.debug(f"✅ Fetched weapon {token_id}: security={attributes['security']}, tier={weapon_info['weapon_tier']}")
                
            except Exception as e:
                logger.error(f"❌ Failed to fetch weapon {token_id}: {e}")
                await self._log_cache_error('weapons', token_id, 'contract_call_failed', str(e))
                continue
        
        logger.info(f"✅ Successfully fetched {len(fresh_tokens)} weapons from contracts")
        return fresh_tokens
    
    async def _save_weapons_to_database_cache(self, tokens: List[Dict]):
        """Save weapon data to database cache"""
        try:
            logger.info(f"💾 Saving {len(tokens)} weapons to database cache")
            
            for token in tokens:
                await execute_command(
                    """INSERT INTO weapons_token_cache 
                       (bc_id, security, anonymity, innovation, weapon_tier, weapon_type,
                        weapon_subtype, category, serial_number, last_updated, is_valid)
                       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                       ON CONFLICT (bc_id) DO UPDATE SET
                           security = EXCLUDED.security,
                           anonymity = EXCLUDED.anonymity,
                           innovation = EXCLUDED.innovation,
                           weapon_tier = EXCLUDED.weapon_tier,
                           weapon_type = EXCLUDED.weapon_type,
                           weapon_subtype = EXCLUDED.weapon_subtype,
                           category = EXCLUDED.category,
                           serial_number = EXCLUDED.serial_number,
                           last_updated = EXCLUDED.last_updated,
                           is_valid = EXCLUDED.is_valid""",
                    token['bc_id'],
                    token['security'],
                    token['anonymity'],
                    token['innovation'],
                    token['weapon_tier'],
                    token['weapon_type'],
                    token['weapon_subtype'],
                    token['category'],
                    token['serial_number'],
                    token['last_updated'],
                    True
                )
            
            logger.info(f"✅ Saved {len(tokens)} weapons to database cache")
            
        except Exception as e:
            logger.error(f"❌ Failed to save weapons to database cache: {e}")
            # Don't raise - caching is optional
    
    # ============================================================================
    # RESPONSE BUILDING METHODS (Unity & React dApp Compatible)
    # ============================================================================
    
    async def _build_heroes_response(self, tokens: List[Dict], address: str) -> List[Dict]:
        """Build Unity-compatible heroes response with character data from database"""
        heroes = []
        
        for token in tokens:
            try:
                bc_id = token['bc_id']
                season_card_id = token['season_card_id']
                
                # Default values in case database lookup fails
                title = f"Hero #{bc_id}"
                fraction = "Neutral"
                card_class = "SPECIALIST"
                
                # Lookup character data from database using season_card_id
                if season_card_id:
                    try:
                        character_data = await execute_query(
                            "SELECT title, fraction, class FROM characters WHERE type_szn_id = $1",
                            season_card_id
                        )
                        
                        if character_data:
                            # Found character in database - use actual data
                            character = character_data[0]
                            title = character["title"]
                            fraction = character["fraction"]
                            
                            # Map database class to Unity card_class format
                            db_class = character["class"]
                            class_mapping = {
                                "Harvester": "HARVESTER",
                                "Warmonger": "WARMONGER", 
                                "Defender": "DEFENDER",
                                "Specialist": "SPECIALIST",
                                "Revolutionist": "REVOLUTIONIST"
                            }
                            card_class = class_mapping.get(db_class, "SPECIALIST")
                            
                            logger.debug(f"✅ Found character data for token {bc_id} (season_card_id: {season_card_id}): {title} - {fraction} - {card_class}")
                        else:
                            logger.warning(f"⚠️ No character found for season_card_id: {season_card_id} (token {bc_id})")
                    except Exception as db_error:
                        logger.error(f"❌ Database lookup failed for season_card_id {season_card_id}: {db_error}")
                        # Continue with default values
                
                # Create Unity-compatible hero object
                hero = {
                    "id": bc_id,
                    "bc_id": bc_id,
                    "title": title,
                    "fraction": fraction,
                    "owner": address.lower(),
                    "card_class": card_class,
                    "reward": {
                        "power": token['serial_number']
                    },
                    "metadata": {
                        "sec": token['sec'],
                        "ano": token['ano'],
                        "inn": token['inn'],
                        "revolution": token.get('card_type') == 2,
                        "season_card_id": season_card_id,
                        "cached": token.get('from_cache', False)  # Debug info
                    }
                }
                
                heroes.append(hero)
                logger.debug(f"✅ Hero {bc_id}: {title} ({card_class}/{fraction}) - sec={token['sec']}, ano={token['ano']}, inn={token['inn']}")
                
            except Exception as e:
                logger.error(f"❌ Error building hero response for token {token.get('bc_id', 'unknown')}: {e}")
                await self._log_cache_error('heroes', token.get('bc_id', 0), 'response_build_failed', str(e), address)
                continue
        
        return heroes
    
    async def _build_weapons_response(self, tokens: List[Dict], address: str) -> List[Dict]:
        """Build Unity-compatible weapons response with weapon names from database"""
        weapons = []
        
        for token in tokens:
            try:
                bc_id = token['bc_id']
                
                # Get weapon name from database mapping
                weapon_name = await self._get_weapon_name_from_database(
                    token['weapon_tier'],
                    token['weapon_type'],
                    token['weapon_subtype'],
                    token['category']
                )
                
                # Get contract address
                contract_address = blockchain_service.config.get_contract_address('weapons')
                
                # Create Unity-compatible weapon object
                weapon = {
                    "id": bc_id,
                    "bc_id": bc_id,
                    "owner_address": address.lower(),
                    "contract_address": contract_address.lower(),
                    "weapon_name": weapon_name,
                    "security": token['security'],
                    "anonymity": token['anonymity'],
                    "innovation": token['innovation'],
                    "minted": True,
                    "burned": False,
                    "metadata": {
                        "weapon_tier": token['weapon_tier'],
                        "weapon_type": token['weapon_type'],
                        "weapon_subtype": token['weapon_subtype'],
                        "category": token['category'],
                        "serial_number": token['serial_number'],
                        "cached": token.get('from_cache', False)  # Debug info
                    }
                }
                
                weapons.append(weapon)
                logger.debug(f"✅ Weapon {bc_id} ({weapon_name}): security={token['security']}, anonymity={token['anonymity']}, innovation={token['innovation']}")
                
            except Exception as e:
                logger.error(f"❌ Error building weapon response for token {token.get('bc_id', 'unknown')}: {e}")
                await self._log_cache_error('weapons', token.get('bc_id', 0), 'response_build_failed', str(e), address)
                continue
        
        return weapons
    
    # ============================================================================
    # HELPER METHODS
    # ============================================================================
    
    async def _get_weapon_name_from_database(self, weapon_tier: int, weapon_type: int, weapon_subtype: int, category: int) -> str:
        """Get weapon name from database mapping table"""
        try:
            result = await execute_query(
                """SELECT weapon_name FROM weapon_mappings 
                   WHERE weapon_tier = $1 AND weapon_type = $2 
                   AND weapon_subtype = $3 AND category = $4""",
                weapon_tier, weapon_type, weapon_subtype, category
            )
            
            if result:
                return result[0]['weapon_name']
            else:
                # Fallback naming (same as original logic)
                type_name = "Gun" if weapon_type == 2 else "Sword" if weapon_type == 1 else "Weapon"
                fallback_name = f"T{weapon_tier} {type_name} #{category}"
                logger.warning(f"⚠️ No weapon mapping found for {weapon_tier}/{weapon_type}/{weapon_subtype}/{category}, using fallback: {fallback_name}")
                return fallback_name
                
        except Exception as e:
            logger.error(f"❌ Failed to get weapon name from database: {e}")
            # Fallback naming
            type_name = "Gun" if weapon_type == 2 else "Sword" if weapon_type == 1 else "Weapon"
            return f"T{weapon_tier} {type_name} #{category}"
    
    async def _log_cache_error(self, contract_type: str, token_id: int, error_type: str, error_message: str, wallet_address: str = None):
        """Log cache errors for debugging and monitoring"""
        try:
            await execute_command(
                """INSERT INTO token_cache_errors 
                   (contract_type, token_id, error_type, error_message, wallet_address, retry_count, resolved, created_at)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
                contract_type,
                token_id,
                error_type,
                error_message[:1000],  # Truncate long error messages
                wallet_address,
                0,
                False,
                datetime.utcnow()
            )
            
            # Update error count for monitoring
            self.error_counts[contract_type] = self.error_counts.get(contract_type, 0) + 1
            
        except Exception as e:
            logger.error(f"❌ Failed to log cache error: {e}")
            # Don't raise - error logging shouldn't break the main flow
    
    # ============================================================================
    # ERC20 TOKEN BENEFITS (DeFi Integration)
    # ============================================================================
    
    async def get_token_benefits(self, address: str) -> Dict[str, Any]:
        """
        Get user's token-based DeFi benefits using blockchain service
        Maps ERC20 token holdings to game benefits
        """
        try:
            logger.info(f"🪙 Fetching token benefits for {address}")
            
            # Get both token balances in parallel using blockchain service
            moh_balance = await blockchain_service.get_erc20_balance("moh", address)
            medallc_balance = await blockchain_service.get_erc20_balance("medallc", address)
            
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
            
        except Exception as e:
            logger.error(f"❌ Failed to get token benefits: {e}")
            # Return empty benefits on error
            return {
                "standard": {"currently_staked": 0},
                "liquidity": {"currently_staked": 0}
            }
    
    async def get_detailed_token_balances(self, address: str) -> Dict[str, Any]:
        """Get detailed token balance information for debugging/display"""
        try:
            logger.info(f"🔍 Getting detailed token balances for {address}")
            
            # Get balances using blockchain service
            token_balances = await blockchain_service.get_multiple_erc20_balances(
                ["moh", "medallc"], address
            )
            
            return {
                "address": address.lower(),
                "tokens": {
                    "moh": {
                        "balance": token_balances.get("moh", 0),
                        "contract": blockchain_service.config.get_contract_address("moh"),
                        "benefit": "basic_perk_selection",
                        "enabled": token_balances.get("moh", 0) > 0
                    },
                    "medallc": {
                        "balance": token_balances.get("medallc", 0), 
                        "contract": blockchain_service.config.get_contract_address("medallc"),
                        "benefit": "shield_ability",
                        "enabled": token_balances.get("medallc", 0) > 0
                    }
                },
                "benefits_summary": {
                    "shield_ability": token_balances.get("medallc", 0) > 0,
                    "basic_perk_selection": token_balances.get("moh", 0) > 0,
                    "total_benefits": sum([
                        token_balances.get("medallc", 0) > 0, 
                        token_balances.get("moh", 0) > 0
                    ])
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get detailed token balances: {e}")
            raise NFTServiceException(f"Failed to get detailed token balances: {e}")
    
    # ============================================================================
    # CACHE MANAGEMENT METHODS
    # ============================================================================
    
    async def invalidate_token_cache(self, contract_type: str, token_ids: List[int] = None):
        """
        Invalidate cache entries for specific tokens or entire contract types
        Useful for manual cache management or when token data changes
        """
        try:
            if token_ids:
                # Invalidate specific tokens
                placeholders = ','.join([' + str(i+1) for i in range(len(token_ids))])
                
                if contract_type == 'heroes':
                    query = f"UPDATE heroes_token_cache SET is_valid = FALSE WHERE bc_id IN ({placeholders})"
                else:
                    query = f"UPDATE weapons_token_cache SET is_valid = FALSE WHERE bc_id IN ({placeholders})"
                
                await execute_command(query, *token_ids)
                logger.info(f"✅ Invalidated cache for {len(token_ids)} {contract_type} tokens")
            else:
                # Invalidate all tokens of this type
                if contract_type == 'heroes':
                    await execute_command("UPDATE heroes_token_cache SET is_valid = FALSE")
                else:
                    await execute_command("UPDATE weapons_token_cache SET is_valid = FALSE")
                
                logger.info(f"✅ Invalidated all {contract_type} cache entries")
                
        except Exception as e:
            logger.error(f"❌ Failed to invalidate {contract_type} cache: {e}")
            raise
    
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring"""
        try:
            # Get database cache statistics
            stats_result = await execute_query("SELECT * FROM get_cache_statistics()")
            
            if stats_result:
                stats = stats_result[0]
                db_stats = {
                    "heroes_cached": stats['heroes_cached'],
                    "weapons_cached": stats['weapons_cached'],
                    "heroes_invalid": stats['heroes_invalid'],
                    "weapons_invalid": stats['weapons_invalid'],
                    "total_errors": stats['total_errors'],
                    "unresolved_errors": stats['unresolved_errors']
                }
            else:
                db_stats = {}
            
            # Combine with service-level stats
            return {
                "service_name": "UnifiedNFTService",
                "database_cache": db_stats,
                "blockchain_service_cache": blockchain_service.get_service_stats(),
                "error_counts": self.error_counts.copy(),
                "land_tickets_caching": False,  # Land tickets are always live
                "cache_hit_rate": self._calculate_cache_hit_rates(db_stats),
                "performance_metrics": {
                    "contracts_supported": ["heroes", "weapons", "lands"],
                    "formats_supported": ["unity", "react_dapp", "profilepage_optimized"]
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get cache statistics: {e}")
            return {"error": str(e)}
    
    def _calculate_cache_hit_rates(self, db_stats: Dict) -> Dict[str, float]:
        """Calculate cache hit rates for monitoring"""
        try:
            heroes_total = db_stats.get('heroes_cached', 0) + self.error_counts.get('heroes', 0)
            weapons_total = db_stats.get('weapons_cached', 0) + self.error_counts.get('weapons', 0)
            
            return {
                "heroes": (db_stats.get('heroes_cached', 0) / max(1, heroes_total)) * 100.0,
                "weapons": (db_stats.get('weapons_cached', 0) / max(1, weapons_total)) * 100.0
            }
        except Exception:
            return {"heroes": 0.0, "weapons": 0.0}
    
    async def force_refresh_token(self, contract_type: str, token_id: int) -> Dict[str, Any]:
        """
        Force refresh a specific token from blockchain (bypass cache)
        Useful for debugging or when you need fresh data
        """
        try:
            logger.info(f"🔄 Force refreshing {contract_type} token {token_id}")
            
            # Invalidate cache first
            await self.invalidate_token_cache(contract_type, [token_id])
            
            # Clear related blockchain service cache
            if contract_type in ['heroes', 'weapons']:
                cache_keys_to_clear = [
                    f"attrs_{contract_type}_{token_id}",
                    f"info_{contract_type}_{token_id}"
                ]
                for key in cache_keys_to_clear:
                    if key in blockchain_service.cache:
                        del blockchain_service.cache[key]
            
            result = {"message": f"Cache invalidated for {contract_type} token {token_id}"}
            
            if contract_type == 'lands':
                result["note"] = "Land tickets don't use database caching - always live data"
            
            logger.info(f"✅ Force refresh completed for {contract_type} token {token_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to force refresh token: {e}")
            raise
    
    async def cleanup_cache_errors(self, days_old: int = 7) -> int:
        """
        Clean up old cache error entries
        Returns number of cleaned up entries
        """
        try:
            result = await execute_command(
                """DELETE FROM token_cache_errors 
                   WHERE resolved = TRUE AND resolved_at < NOW() - INTERVAL '%s days'
                   RETURNING id""",
                days_old
            )
            
            # Count deleted rows
            deleted_count = len(result) if result else 0
            logger.info(f"✅ Cleaned up {deleted_count} old cache error entries")
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup cache errors: {e}")
            return 0
    
    # ============================================================================
    # HEALTH CHECK AND MONITORING
    # ============================================================================
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check for the NFT service"""
        try:
            # Test blockchain service connectivity
            blockchain_health = await blockchain_service.health_check()
            
            # Test database connectivity
            try:
                cache_stats = await self.get_cache_statistics()
                database_status = "healthy"
            except Exception as e:
                cache_stats = {}
                database_status = f"unhealthy: {e}"
            
            return {
                "status": "healthy" if blockchain_health.get("status") == "healthy" and database_status == "healthy" else "unhealthy",
                "nft_service": {
                    "status": "operational",
                    "contracts_supported": len(blockchain_service.config.nft_contracts),
                    "formats_supported": ["unity", "react_dapp", "profilepage_optimized"],
                    "error_counts": self.error_counts
                },
                "blockchain_service": blockchain_health,
                "database_cache": {
                    "status": database_status,
                    "statistics": cache_stats.get("database_cache", {})
                },
                "features": {
                    "smart_caching": True,
                    "unity_compatibility": True,
                    "profilepage_optimization": True,
                    "defi_integration": True,
                    "land_tickets": True
                }
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

# Create global instance for use throughout the application
nft_service = NFTService()

# Convenience functions for backward compatibility
async def get_heroes_for_unity(address: str) -> Dict:
    """Backward compatibility wrapper"""
    return await nft_service.get_heroes_for_unity(address)

async def get_weapons_for_unity(address: str) -> List[Dict]:
    """Backward compatibility wrapper"""
    return await nft_service.get_weapons_for_unity(address)

async def get_land_tickets(address: str) -> List[Dict]:
    """Backward compatibility wrapper"""
    return await nft_service.get_land_tickets(address)

async def get_enhanced_player_data(address: str, chain: str = "polygon") -> Dict:
    """Backward compatibility wrapper"""
    return await nft_service.get_enhanced_player_data(address, chain)

async def get_heroes_optimized(address: str) -> Dict:
    """Backward compatibility wrapper"""
    return await nft_service.get_heroes_optimized(address)

async def get_weapons_optimized(address: str) -> List[Dict]:
    """Backward compatibility wrapper"""
    return await nft_service.get_weapons_optimized(address)

async def get_token_benefits(address: str) -> Dict[str, Any]:
    """Backward compatibility wrapper"""
    return await nft_service.get_token_benefits(address)

async def get_cache_statistics() -> Dict[str, Any]:
    """Backward compatibility wrapper"""
    return await nft_service.get_cache_statistics()

async def invalidate_token_cache(contract_type: str, token_ids: List[int] = None):
    """Backward compatibility wrapper"""
    return await nft_service.invalidate_token_cache(contract_type, token_ids)

# Exception class for backward compatibility
EnhancedMoralisServiceException = NFTServiceException