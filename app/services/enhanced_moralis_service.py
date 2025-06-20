# app/services/enhanced_moralis_service.py - FIXED VERSION
import aiohttp
import asyncio
import logging
from typing import Dict, List, Optional, Any
import os
import json

logger = logging.getLogger(__name__)

class EnhancedMoralisService:
    """
    Fixed Enhanced Moralis service using proper Moralis Web2 API endpoints
    Uses NFT endpoints instead of contract function calls for better reliability
    """
    
    def __init__(self):
        self.api_key = os.getenv('MORALIS_API_KEY')
        self.base_url = "https://deep-index.moralis.io/api/v2.2"
        self.chain = "polygon"
        
        # Contract addresses from your original system
        self.contracts = {
            'heroes': '0x27331bbfe94d1b8518816462225b16622ac74e2e',
            'weapons': '0x31dd72d810b34c339f2ce9119e2ebfbb9926694a', 
            'lands': '0xaae02c81133d865d543df02b1e458de2279c4a5b'
        }
        
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
        
        if not self.api_key:
            logger.error("❌ MORALIS_API_KEY not found in environment variables")
        else:
            logger.info("✅ Enhanced Moralis service initialized - FIXED VERSION")
    
    async def _make_moralis_request(self, endpoint: str, params: dict = None) -> Optional[dict]:
        """Make HTTP request to Moralis API with proper error handling"""
        url = f"{self.base_url}{endpoint}"
        headers = {
            'X-API-Key': self.api_key,
            'Accept': 'application/json'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.debug(f"✅ Moralis API call successful: {endpoint}")
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Moralis API call failed {response.status}: {error_text}")
                        return None
        except Exception as e:
            logger.error(f"❌ Moralis API request failed: {e}")
            return None
    
    async def _get_nfts_by_contract(self, wallet_address: str, contract_address: str) -> List[Dict]:
        """Get NFTs for a specific contract using Moralis NFT API"""
        endpoint = f"/{wallet_address}/nft"
        params = {
            "chain": self.chain,
            "format": "decimal",
            "token_addresses": [contract_address],
            "exclude_spam": "true",
            "media_items": "false"  # Faster response
        }
        
        try:
            result = await self._make_moralis_request(endpoint, params)
            if result:
                return result.get("result", [])
            return []
            
        except Exception as e:
            logger.error(f"Error getting NFTs for contract {contract_address}: {e}")
            return []
    
    def _parse_nft_metadata(self, nft: dict) -> dict:
        """Parse NFT metadata safely"""
        metadata = {}
        if nft.get("metadata"):
            try:
                if isinstance(nft.get("metadata"), str):
                    metadata = json.loads(nft.get("metadata"))
                else:
                    metadata = nft.get("metadata", {})
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse metadata for token {nft.get('token_id')}")
                metadata = {}
        
        return metadata
    
    def _parse_nft_attributes(self, attributes: List[Dict]) -> Dict:
        """Parse NFT attributes from metadata"""
        parsed = {}
        if not attributes:
            return parsed
            
        for attr in attributes:
            if isinstance(attr, dict):
                trait_type = attr.get('trait_type', '')
                value = attr.get('value', 0)
                parsed[trait_type] = value
        return parsed
    
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
        Get Heroes NFTs with Unity-compatible format using Moralis NFT API
        Returns exact format Unity expects: paginated with "sec"/"ano"/"inn"
        """
        try:
            logger.info(f"🦸 Fetching Heroes for {address} using Moralis NFT API")
            
            # Get NFTs using Moralis NFT endpoint
            nfts = await self._get_nfts_by_contract(address, self.contracts['heroes'])
            
            if not nfts:
                logger.info(f"No heroes found for {address}")
                return {"results": [], "count": 0, "next": None}
            
            heroes = []
            
            for nft in nfts:
                try:
                    token_id = int(nft.get("token_id", 0))
                    metadata = self._parse_nft_metadata(nft)
                    attributes = self._parse_nft_attributes(metadata.get('attributes', []))
                    
                    # Determine fraction based on token ID ranges (from your original logic)
                    if token_id >= 1 and token_id <= 3000:
                        fraction = "Goliath"
                    elif token_id >= 3001 and token_id <= 6000:
                        fraction = "Renegade"
                    else:
                        fraction = "Neutral"
                    
                    # Get attributes or use defaults
                    sec = attributes.get('Security', 50)
                    ano = attributes.get('Anonymity', 50)
                    inn = attributes.get('Innovation', 50)
                    
                    # Determine card class (default to SPECIALIST for now)
                    card_class = "SPECIALIST"
                    
                    # Create Unity-compatible hero object
                    hero = {
                        "id": token_id,
                        "bc_id": token_id,
                        "title": metadata.get('name', f"Hero #{token_id}"),
                        "fraction": fraction,
                        "owner": address.lower(),
                        "card_class": card_class,
                        "reward": {
                            "power": attributes.get('Power', 0)
                        },
                        "metadata": {
                            "sec": sec,      # Unity expects "sec"
                            "ano": ano,      # Unity expects "ano"
                            "inn": inn,      # Unity expects "inn"
                            "revolution": False  # Default for now
                        }
                    }
                    
                    heroes.append(hero)
                    logger.debug(f"✅ Hero {token_id}: sec={sec}, ano={ano}, inn={inn}")
                    
                except Exception as e:
                    logger.error(f"Error processing hero {nft.get('token_id', 'unknown')}: {e}")
                    continue
            
            result = {
                "results": heroes,
                "count": len(heroes),
                "next": None
            }
            
            logger.info(f"✅ Successfully fetched {len(heroes)} Heroes using Moralis NFT API")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error fetching heroes: {e}")
            return {"results": [], "count": 0, "next": None, "error": str(e)}
    
    async def get_weapons_for_unity(self, address: str) -> List[Dict]:
        """
        Get Weapons NFTs with Unity-compatible format using Moralis NFT API
        Returns exact format Unity expects: direct array with "security"/"anonymity"/"innovation"
        """
        try:
            logger.info(f"⚔️ Fetching Weapons for {address} using Moralis NFT API")
            
            # Get NFTs using Moralis NFT endpoint
            nfts = await self._get_nfts_by_contract(address, self.contracts['weapons'])
            
            if not nfts:
                logger.info(f"No weapons found for {address}")
                return []
            
            weapons = []
            
            for nft in nfts:
                try:
                    token_id = int(nft.get("token_id", 0))
                    metadata = self._parse_nft_metadata(nft)
                    attributes = self._parse_nft_attributes(metadata.get('attributes', []))
                    
                    # Get attributes or use defaults
                    security = attributes.get('Security', 60)
                    anonymity = attributes.get('Anonymity', 60)
                    innovation = attributes.get('Innovation', 60)
                    
                    # Get weapon name (from metadata or generate default)
                    weapon_name = metadata.get('name', f"Weapon #{token_id}")
                    
                    # Create Unity-compatible weapon object
                    weapon = {
                        "id": token_id,
                        "bc_id": token_id,
                        "owner_address": address.lower(),
                        "contract_address": self.contracts['weapons'].lower(),
                        "weapon_name": weapon_name,
                        "security": security,      # Unity expects "security" (full word)
                        "anonymity": anonymity,    # Unity expects "anonymity" (full word)
                        "innovation": innovation,  # Unity expects "innovation" (full word)
                        "minted": True,
                        "burned": False
                    }
                    
                    weapons.append(weapon)
                    logger.debug(f"✅ Weapon {token_id} ({weapon_name}): security={security}, anonymity={anonymity}, innovation={innovation}")
                    
                except Exception as e:
                    logger.error(f"Error processing weapon {nft.get('token_id', 'unknown')}: {e}")
                    continue
            
            logger.info(f"✅ Successfully fetched {len(weapons)} Weapons using Moralis NFT API")
            return weapons
            
        except Exception as e:
            logger.error(f"❌ Error fetching weapons: {e}")
            return []
    
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
            
        except Exception as e:
            logger.error(f"❌ Error getting enhanced player data: {e}")
            return {
                "address": address.lower(),
                "error": str(e),
                "nfts": {"heroes": {"results": [], "count": 0}, "weapons": [], "lands": []},
                "counts": {"heroes": 0, "weapons": 0, "lands": 0, "total": 0},
                "boosts": {"damage_multiplier": 0, "fire_rate_bonus": 0, "score_multiplier": 0, "health_bonus": 0}
            }

# Create global instance
enhanced_moralis_service = EnhancedMoralisService()