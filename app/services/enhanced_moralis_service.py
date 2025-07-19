# services/enhanced_moralis_service.py - COMPLETE with TokenCacheService integration and Land Tickets
import logging
from typing import Dict, List, Optional, Any
import asyncio

# Import our Web3 service and the new TokenCacheService
from .web3_service import web3_service, Web3ServiceException
from .token_cache_service import TokenCacheService

logger = logging.getLogger(__name__)

# Minimal ABIs - just the functions we need
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

class EnhancedMoralisService:
    """
    Enhanced service with smart contract caching and Land Tickets support
    Now uses TokenCacheService to minimize blockchain calls
    Maintains exact Unity compatibility while dramatically improving performance
    """
    
    def __init__(self):
        self.chain = "polygon"
        
        # Initialize token cache service (will be set up after database import)
        self.token_cache_service = None
        
        logger.info("✅ Enhanced Moralis service initialized with caching support and Land Tickets")
    
    def _get_cache_service(self):
        """Lazy initialization of TokenCacheService to avoid circular imports"""
        if self.token_cache_service is None:
            # Import database module at runtime to avoid circular imports
            from .. import database
            self.token_cache_service = TokenCacheService(web3_service, database)
            logger.info("✅ TokenCacheService initialized")
        
        return self.token_cache_service
    
    async def get_heroes_for_unity(self, address: str) -> Dict:
        """
        Get Heroes NFTs with Unity-compatible format using smart caching
        Returns exact format Unity expects with significant performance improvement
        """
        try:
            logger.info(f"🦸 Fetching Heroes for {address} using smart caching")
            
            # Get cache service
            cache_service = self._get_cache_service()
            
            # Use cached approach - this handles:
            # 1. tokensOfOwner() call (always fresh)
            # 2. Cache lookup for token attributes/info
            # 3. Smart contract calls only for missing tokens
            # 4. Database integration for character data
            heroes = await cache_service.get_heroes_with_cache(address, HEROES_ABI)
            
            # Build Unity-compatible response format
            result = {
                "results": heroes,
                "count": len(heroes),
                "next": None
            }
            
            logger.info(f"✅ Successfully fetched {len(heroes)} Heroes with smart caching (reduced contract calls)")
            return result
            
        except ValueError as e:
            # Address validation error - client error
            logger.error(f"❌ Address validation error: {e}")
            raise ValueError(str(e))
        except Web3ServiceException as e:
            # Web3 service error - server error
            logger.error(f"❌ Web3 service error: {e}")
            raise Web3ServiceException(str(e))
        except Exception as e:
            logger.error(f"❌ Unexpected error fetching heroes: {e}")
            raise Web3ServiceException(f"Unexpected error: {e}")
    
    async def get_weapons_for_unity(self, address: str) -> List[Dict]:
        """
        Get Weapons NFTs with Unity-compatible format using smart caching
        Returns exact format Unity expects with significant performance improvement
        """
        try:
            logger.info(f"⚔️ Fetching Weapons for {address} using smart caching")
            
            # Get cache service
            cache_service = self._get_cache_service()
            
            # Use cached approach - this handles:
            # 1. tokensOfOwner() call (always fresh)  
            # 2. Cache lookup for token attributes/info
            # 3. Smart contract calls only for missing tokens
            # 4. Database integration for weapon name mapping
            weapons = await cache_service.get_weapons_with_cache(address, WEAPONS_ABI)
            
            logger.info(f"✅ Successfully fetched {len(weapons)} Weapons with smart caching (reduced contract calls)")
            return weapons
            
        except ValueError as e:
            # Address validation error - client error
            logger.error(f"❌ Address validation error: {e}")
            raise ValueError(str(e))
        except Web3ServiceException as e:
            # Web3 service error - server error
            logger.error(f"❌ Web3 service error: {e}")
            raise Web3ServiceException(str(e))
        except Exception as e:
            logger.error(f"❌ Unexpected error fetching weapons: {e}")
            raise Web3ServiceException(f"Unexpected error: {e}")
    
    async def get_land_tickets(self, address: str) -> List[Dict]:
        """
        Get Land Tickets with clean, reusable format
        Returns exact format that ProfilePage expects (migrated from nftService.js)
        No caching - always live blockchain data
        """
        try:
            logger.info(f"🏞️ Fetching Land Tickets for {address}")
            
            # Token IDs and metadata (same as old nftService.js)
            token_ids = [1, 2, 3]
            land_metadata = {
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
            
            # Get live balances from blockchain (no caching)
            balances = await web3_service.get_erc1155_balances('lands', address, token_ids)
            
            # Build response in same format as old nftService
            lands = []
            for token_id, balance in zip(token_ids, balances):
                metadata = land_metadata[token_id]
                
                lands.append({
                    "id": token_id,
                    "token_id": token_id,
                    "name": metadata["name"],
                    "rarity": metadata["rarity"],
                    "plots": metadata["plots"],
                    "image": metadata["image"],
                    "balance": balance,
                    "contract_address": "0xaae02c81133d865d543df02b1e458de2279c4a5b",
                    "nft_type": "land"
                })
            
            logger.info(f"✅ Successfully fetched {len(lands)} land types with total {sum(balances)} tickets")
            return lands
            
        except ValueError as e:
            # Address validation error - client error
            logger.error(f"❌ Address validation error: {e}")
            raise ValueError(str(e))
        except Web3ServiceException as e:
            # Web3 service error - server error
            logger.error(f"❌ Web3 service error: {e}")
            raise Web3ServiceException(str(e))
        except Exception as e:
            logger.error(f"❌ Unexpected error fetching land tickets: {e}")
            
            # Return error format (all balances -1 to indicate blockchain failure)
            error_lands = []
            for token_id in [1, 2, 3]:
                metadata = {
                    1: {"name": "Common Land", "rarity": "Common", "plots": 1, "image": "/land1.png"},
                    2: {"name": "Rare Land", "rarity": "Rare", "plots": 3, "image": "/land2.png"},
                    3: {"name": "Legendary Land", "rarity": "Legendary", "plots": 7, "image": "/land3.png"}
                }[token_id]
                
                error_lands.append({
                    "id": token_id,
                    "token_id": token_id,
                    "name": metadata["name"],
                    "rarity": metadata["rarity"],
                    "plots": metadata["plots"],
                    "image": metadata["image"],
                    "balance": -1,  # Error indicator
                    "contract_address": "0xaae02c81133d865d543df02b1e458de2279c4a5b",
                    "nft_type": "land"
                })
            
            logger.warning(f"⚠️ Returning error format for land tickets due to: {e}")
            return error_lands
    
    async def get_enhanced_player_data(self, address: str, chain: str = "polygon") -> Dict:
        """
        Get comprehensive NFT data with enhanced boost calculations
        Now uses smart caching for improved performance and includes Land Tickets
        """
        try:
            logger.info(f"🎮 Fetching enhanced player data for {address} with smart caching")
            
            # Fetch all NFT types in parallel using the cached methods
            heroes_task = self.get_heroes_for_unity(address)
            weapons_task = self.get_weapons_for_unity(address)
            lands_task = self.get_land_tickets(address)
            
            heroes_result, weapons_result, lands_result = await asyncio.gather(
                heroes_task, weapons_task, lands_task, return_exceptions=True
            )
            
            # Handle any exceptions
            if isinstance(heroes_result, Exception):
                logger.error(f"Heroes fetch failed: {heroes_result}")
                heroes_result = {"results": [], "count": 0}
            
            if isinstance(weapons_result, Exception):
                logger.error(f"Weapons fetch failed: {weapons_result}")
                weapons_result = []
            
            if isinstance(lands_result, Exception):
                logger.error(f"Land tickets fetch failed: {lands_result}")
                lands_result = []
            
            # Calculate boosts based on your original system
            hero_count = len(heroes_result.get("results", []))
            weapon_count = len(weapons_result)
            land_count = sum(land.get("balance", 0) for land in lands_result if land.get("balance", 0) > 0)
            
            boosts = {
                "damage_multiplier": min(hero_count * 5, 50),    # +5% per hero (max 50%)
                "fire_rate_bonus": min(weapon_count * 3, 30),   # +3% per weapon (max 30%)
                "score_multiplier": min(land_count * 2, 20),    # +2% per land ticket (max 20%)
                "health_bonus": hero_count * 25 + weapon_count * 15 + land_count * 10
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
                "timestamp": int(asyncio.get_event_loop().time()),
                "cache_enabled": True  # Indicate caching is active
            }
            
        except ValueError as e:
            # Address validation error - client error
            logger.error(f"❌ Address validation error: {e}")
            raise ValueError(str(e))
        except Web3ServiceException as e:
            # Web3 service error - server error  
            logger.error(f"❌ Web3 service error: {e}")
            raise Web3ServiceException(str(e))
        except Exception as e:
            logger.error(f"❌ Unexpected error getting enhanced player data: {e}")
            raise Web3ServiceException(f"Unexpected error: {e}")
    
    # ============================================================================
    # CACHE MANAGEMENT METHODS
    # ============================================================================
    
    async def invalidate_token_cache(self, contract_type: str, token_ids: List[int] = None):
        """
        Invalidate cache entries for specific tokens or entire contract types
        Useful for manual cache management or when token data changes
        """
        try:
            cache_service = self._get_cache_service()
            await cache_service.invalidate_token_cache(contract_type, token_ids)
            
            if token_ids:
                logger.info(f"✅ Invalidated cache for {len(token_ids)} {contract_type} tokens")
            else:
                logger.info(f"✅ Invalidated all {contract_type} cache entries")
                
        except Exception as e:
            logger.error(f"❌ Failed to invalidate cache: {e}")
            raise
    
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """
        Get cache performance statistics for monitoring
        """
        try:
            cache_service = self._get_cache_service()
            stats = await cache_service.get_cache_statistics()
            
            # Add service-level stats
            stats.update({
                "service_name": "EnhancedMoralisService",
                "caching_enabled": True,
                "web3_cache_stats": web3_service.get_cache_stats(),
                "land_tickets_caching": False  # Land tickets are always live
            })
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Failed to get cache statistics: {e}")
            return {"error": str(e)}
    
    async def force_refresh_token(self, contract_type: str, token_id: int) -> Dict[str, Any]:
        """
        Force refresh a specific token from blockchain (bypass cache)
        Useful for debugging or when you need fresh data
        """
        try:
            logger.info(f"🔄 Force refreshing {contract_type} token {token_id}")
            
            # Invalidate cache first
            await self.invalidate_token_cache(contract_type, [token_id])
            
            # The next call will fetch fresh data from blockchain
            if contract_type == 'heroes':
                result = {"message": f"Cache invalidated for heroes token {token_id}"}
            elif contract_type == 'weapons':
                result = {"message": f"Cache invalidated for weapons token {token_id}"}
            elif contract_type == 'lands':
                result = {"message": f"Land tickets don't use caching - always live data"}
            else:
                raise ValueError(f"Unknown contract type: {contract_type}")
            
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
            cache_service = self._get_cache_service()
            cleaned_count = await cache_service.cleanup_old_errors(days_old)
            
            logger.info(f"✅ Cleaned up {cleaned_count} old cache error entries")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup cache errors: {e}")
            return 0

# Create global instance
enhanced_moralis_service = EnhancedMoralisService()