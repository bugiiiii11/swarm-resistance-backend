# services/enhanced_moralis_service.py - COMPLETE with database integration
import logging
from typing import Dict, List, Optional, Any
import asyncio

# Import our new Web3 service
from .web3_service import web3_service, Web3ServiceException

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
    Enhanced service that replicates your original Django backend logic
    Now uses Web3.py for direct smart contract calls instead of Moralis
    Includes database integration for character data
    """
    
    def __init__(self):
        self.chain = "polygon"
        
        # Weapon mappings from your original weapon.py
        self.WEAPON_NAME_MAPPING = {
            1: {  # WEAPON_TIER_COMMON
                2: {  # WEAPON_TYPE_RANGE (Gun)
                    1: {  # WEAPON_SUBTYPE_ONE
                        1: "Viper",
                        2: "Underdog Meda-Gun", 
                        3: "Adept's Repeater",
                        4: "Sandcrawler's Sniper Rifle",
                    }
                },
                1: {  # WEAPON_TYPE_MELEE (Sword)
                    1: {
                        1: "Gladiator's Greatsword",
                        2: "Ryoshi Katana",
                        3: "Tactician's Claymore", 
                        4: "Blessed Blade",
                    }
                }
            },
            2: {  # WEAPON_TIER_RARE
                2: {  # WEAPON_TYPE_RANGE
                    1: {
                        1: "Serpent's Bite",
                        2: "Victim's Meda-Gun",
                        3: "Soldier's Repeater",
                        4: "Tundrastalker's Sniper Rifle",
                    }
                },
                1: {  # WEAPON_TYPE_MELEE
                    1: {
                        1: "Mercilles's Greatsword",
                        2: "Tadashi Katana", 
                        3: "Righteous Claymore",
                        4: "Moon Blade",
                    }
                }
            }
        }
        
        logger.info("✅ Enhanced Moralis service initialized with Web3.py backend and database integration")
    
    def _get_weapon_name(self, weapon_tier: int, weapon_type: int, weapon_subtype: int, category: int) -> str:
        """Get weapon name using your original mapping logic"""
        try:
            return self.WEAPON_NAME_MAPPING[weapon_tier][weapon_type][weapon_subtype][category]
        except (KeyError, IndexError):
            # Fallback naming
            type_name = "Gun" if weapon_type == 2 else "Sword" if weapon_type == 1 else "Weapon"
            return f"T{weapon_tier} {type_name} #{category}"
    
    async def get_heroes_for_unity(self, address: str) -> Dict:
        """
        Get Heroes NFTs with Unity-compatible format using Web3.py
        Returns exact format Unity expects: paginated with "sec"/"ano"/"inn"
        Enhanced with database character lookup
        """
        try:
            logger.info(f"🦸 Fetching Heroes for {address} using Web3.py with database integration")
            
            # Import database function at method level to avoid circular imports
            from ..database import execute_query
            
            # Get all token IDs owned by this address
            token_ids = await web3_service.get_tokens_of_owner('heroes', HEROES_ABI, address)
            
            if not token_ids:
                logger.info(f"No heroes found for {address}")
                return {"results": [], "count": 0, "next": None}
            
            heroes = []
            
            for token_id in token_ids:
                try:
                    # Get attributes and token info in parallel
                    attributes_task = web3_service.get_token_attributes('heroes', HEROES_ABI, token_id)
                    info_task = web3_service.get_token_info('heroes', HEROES_ABI, token_id)
                    
                    attributes, hero_info = await asyncio.gather(attributes_task, info_task)
                    
                    # Extract season_card_id from smart contract data
                    season_card_id = hero_info.get("season_card_id", 0)
                    
                    # Default values in case database lookup fails
                    title = f"Hero #{token_id}"
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
                                if db_class == "Harvester":
                                    card_class = "HARVESTER"
                                elif db_class == "Warmonger":
                                    card_class = "WARMONGER"
                                elif db_class == "Defender":
                                    card_class = "DEFENDER"
                                elif db_class == "Specialist":
                                    card_class = "SPECIALIST"
                                elif db_class == "Revolutionist":
                                    card_class = "REVOLUTIONIST"
                                else:
                                    card_class = "SPECIALIST"  # fallback
                                
                                logger.debug(f"✅ Found character data for token {token_id} (season_card_id: {season_card_id}): {title} - {fraction} - {card_class}")
                            else:
                                logger.warning(f"⚠️ No character found for season_card_id: {season_card_id} (token {token_id})")
                        except Exception as db_error:
                            logger.error(f"❌ Database lookup failed for season_card_id {season_card_id}: {db_error}")
                            # Continue with default values
                    
                    # Create Unity-compatible hero object with actual character data
                    hero = {
                        "id": token_id,
                        "bc_id": token_id,
                        "title": title,
                        "fraction": fraction,
                        "owner": address.lower(),
                        "card_class": card_class,
                        "reward": {
                            "power": hero_info.get("serial_number", 1)
                        },
                        "metadata": {
                            "sec": attributes["sec"],
                            "ano": attributes["ano"],
                            "inn": attributes["inn"],
                            "revolution": hero_info.get("card_type") == 2,
                            "season_card_id": season_card_id  # Include for debugging
                        }
                    }
                    
                    heroes.append(hero)
                    logger.debug(f"✅ Hero {token_id}: {title} ({card_class}/{fraction}) - sec={attributes['sec']}, ano={attributes['ano']}, inn={attributes['inn']}")
                    
                except Exception as e:
                    logger.error(f"Error processing hero {token_id}: {e}")
                    continue
            
            result = {
                "results": heroes,
                "count": len(heroes),
                "next": None
            }
            
            logger.info(f"✅ Successfully fetched {len(heroes)} Heroes with character data from database")
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
        Get Weapons NFTs with Unity-compatible format using Web3.py
        Returns exact format Unity expects: direct array with "security"/"anonymity"/"innovation"
        """
        try:
            logger.info(f"⚔️ Fetching Weapons for {address} using Web3.py")
            
            # Get all token IDs owned by this address
            token_ids = await web3_service.get_tokens_of_owner('weapons', WEAPONS_ABI, address)
            
            if not token_ids:
                logger.info(f"No weapons found for {address}")
                return []
            
            weapons = []
            
            for token_id in token_ids:
                try:
                    # Get attributes and weapon info in parallel
                    attributes_task = web3_service.get_token_attributes('weapons', WEAPONS_ABI, token_id)
                    info_task = web3_service.get_token_info('weapons', WEAPONS_ABI, token_id)
                    
                    attributes, weapon_info = await asyncio.gather(attributes_task, info_task)
                    
                    # Get weapon name using your original mapping
                    weapon_name = self._get_weapon_name(
                        weapon_info["weapon_tier"],
                        weapon_info["weapon_type"],
                        weapon_info["weapon_subtype"],
                        weapon_info["category"]
                    )
                    
                    # Create Unity-compatible weapon object (exact format from your docs)
                    weapon = {
                        "id": token_id,
                        "bc_id": token_id,
                        "owner_address": address.lower(),
                        "contract_address": web3_service.contract_addresses['weapons'].lower(),
                        "weapon_name": weapon_name,
                        "security": attributes["security"],      # Unity expects "security" (full word)
                        "anonymity": attributes["anonymity"],    # Unity expects "anonymity" (full word)
                        "innovation": attributes["innovation"],  # Unity expects "innovation" (full word)
                        "minted": True,
                        "burned": False
                    }
                    
                    weapons.append(weapon)
                    logger.debug(f"✅ Weapon {token_id} ({weapon_name}): security={attributes['security']}, anonymity={attributes['anonymity']}, innovation={attributes['innovation']}")
                    
                except Exception as e:
                    logger.error(f"Error processing weapon {token_id}: {e}")
                    continue
            
            logger.info(f"✅ Successfully fetched {len(weapons)} Weapons with live blockchain attributes")
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
    
    async def get_enhanced_player_data(self, address: str, chain: str = "polygon") -> Dict:
        """
        Get comprehensive NFT data with enhanced boost calculations
        """
        try:
            logger.info(f"🎮 Fetching enhanced player data for {address}")
            
            # Fetch all NFT types in parallel
            heroes_task = self.get_heroes_for_unity(address)
            weapons_task = self.get_weapons_for_unity(address)
            
            heroes_result, weapons_result = await asyncio.gather(
                heroes_task, weapons_task, return_exceptions=True
            )
            
            # Handle any exceptions
            if isinstance(heroes_result, Exception):
                logger.error(f"Heroes fetch failed: {heroes_result}")
                heroes_result = {"results": [], "count": 0}
            
            if isinstance(weapons_result, Exception):
                logger.error(f"Weapons fetch failed: {weapons_result}")
                weapons_result = []
            
            # Calculate boosts based on your original system
            hero_count = len(heroes_result.get("results", []))
            weapon_count = len(weapons_result)
            
            boosts = {
                "damage_multiplier": min(hero_count * 5, 50),    # +5% per hero (max 50%)
                "fire_rate_bonus": min(weapon_count * 3, 30),   # +3% per weapon (max 30%)
                "score_multiplier": 0,  # Would need lands data
                "health_bonus": hero_count * 25 + weapon_count * 15
            }
            
            return {
                "address": address.lower(),
                "chain": chain,
                "nfts": {
                    "heroes": heroes_result,
                    "weapons": weapons_result,
                    "lands": []  # TODO: Implement lands if needed
                },
                "counts": {
                    "heroes": hero_count,
                    "weapons": weapon_count,
                    "lands": 0,
                    "total": hero_count + weapon_count
                },
                "boosts": boosts,
                "timestamp": int(asyncio.get_event_loop().time())
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

# Create global instance
enhanced_moralis_service = EnhancedMoralisService()