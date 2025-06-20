# app/services/enhanced_moralis_service.py - SMART CONTRACT VERSION
import aiohttp
import asyncio
import logging
from typing import Dict, List, Optional, Any
import os
import json

logger = logging.getLogger(__name__)

class EnhancedMoralisService:
    """
    Enhanced Moralis service using SMART CONTRACT CALLS (like your original Django backend)
    Calls tokensOfOwner, getTokenInfo, getAttribs directly via Moralis runContractFunction
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
            logger.info("✅ Enhanced Moralis service initialized - SMART CONTRACT VERSION")
    
    async def _call_contract_function(self, contract_address: str, function_name: str, params: List = None) -> Any:
        """Call smart contract function via Moralis runContractFunction API"""
        
        # Updated endpoint for contract function calls
        endpoint = f"/{contract_address}/function"
        
        headers = {
            'X-API-Key': self.api_key,
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        # Build the function call payload
        payload = {
            "chain": self.chain,
            "function_name": function_name,
            "params": params or []
        }
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            logger.debug(f"🔗 Calling contract function: {function_name}")
            logger.debug(f"🔗 URL: {url}")
            logger.debug(f"🔗 Payload: {payload}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.debug(f"✅ Contract call {function_name} result: {result}")
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Contract call failed {response.status}: {error_text}")
                        return None
        except Exception as e:
            logger.error(f"❌ Contract call failed: {e}")
            return None
    
    async def _get_tokens_of_owner(self, contract_address: str, owner_address: str) -> List[int]:
        """Get all token IDs owned by address using tokensOfOwner (like your original backend)"""
        try:
            result = await self._call_contract_function(
                contract_address,
                'tokensOfOwner',
                [owner_address]
            )
            
            if result and isinstance(result, list):
                return [int(token_id) for token_id in result]
            elif result and isinstance(result, dict):
                # Sometimes Moralis wraps the result
                actual_result = result.get('result', result)
                if isinstance(actual_result, list):
                    return [int(token_id) for token_id in actual_result]
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting tokens of owner: {e}")
            return []
    
    async def _get_hero_attributes(self, token_id: int) -> Dict:
        """Get hero attributes using getAttribs (exactly like your card_distribution.py)"""
        try:
            # Call getAttribs function - returns (sec, ano, inn)
            attribs_result = await self._call_contract_function(
                self.contracts['heroes'],
                'getAttribs',
                [str(token_id)]
            )
            
            if attribs_result and len(attribs_result) >= 3:
                sec = int(attribs_result[0]) if attribs_result[0] else 50
                ano = int(attribs_result[1]) if attribs_result[1] else 50
                inn = int(attribs_result[2]) if attribs_result[2] else 50
                
                return {"sec": sec, "ano": ano, "inn": inn}
            
            logger.warning(f"Invalid getAttribs result for hero {token_id}: {attribs_result}")
            return {"sec": 50, "ano": 50, "inn": 50}  # Fallback
            
        except Exception as e:
            logger.error(f"Error getting hero attributes for {token_id}: {e}")
            return {"sec": 50, "ano": 50, "inn": 50}  # Fallback
    
    async def _get_hero_info(self, token_id: int) -> Dict:
        """Get hero token info using getTokenInfo (like your card_distribution.py)"""
        try:
            # Call getTokenInfo function
            token_info = await self._call_contract_function(
                self.contracts['heroes'],
                'getTokenInfo', 
                [str(token_id)]
            )
            
            if token_info and len(token_info) >= 2:
                season_card_id = int(token_info[0]) if token_info[0] else 0
                serial_number = int(token_info[1]) if token_info[1] else 0
                
                # Decode card data like your original decode_card_data function
                card_type = season_card_id // 1000
                season_id = (season_card_id % 1000) // 10
                card_season_collection_id = season_card_id % 10
                
                return {
                    "season_card_id": season_card_id,
                    "serial_number": serial_number,
                    "card_type": card_type,
                    "season_id": season_id, 
                    "card_season_collection_id": card_season_collection_id
                }
            
            return {"season_card_id": 0, "serial_number": 0, "card_type": 0, "season_id": 0, "card_season_collection_id": 0}
            
        except Exception as e:
            logger.error(f"Error getting hero info for {token_id}: {e}")
            return {"season_card_id": 0, "serial_number": 0, "card_type": 0, "season_id": 0, "card_season_collection_id": 0}
    
    async def _get_weapon_attributes(self, token_id: int) -> Dict:
        """Get weapon attributes using getAttribs (exactly like your weapon.py)"""
        try:
            # Call getAttribs function - returns (security, anonymity, innovation)
            attribs_result = await self._call_contract_function(
                self.contracts['weapons'],
                'getAttribs',
                [str(token_id)]
            )
            
            if attribs_result and len(attribs_result) >= 3:
                security = int(attribs_result[0]) if attribs_result[0] else 60
                anonymity = int(attribs_result[1]) if attribs_result[1] else 60
                innovation = int(attribs_result[2]) if attribs_result[2] else 60
                
                return {"security": security, "anonymity": anonymity, "innovation": innovation}
            
            logger.warning(f"Invalid getAttribs result for weapon {token_id}: {attribs_result}")
            return {"security": 60, "anonymity": 60, "innovation": 60}  # Fallback
            
        except Exception as e:
            logger.error(f"Error getting weapon attributes for {token_id}: {e}")
            return {"security": 60, "anonymity": 60, "innovation": 60}  # Fallback
    
    async def _get_weapon_info(self, token_id: int) -> Dict:
        """Get weapon info using getTokenInfo (exactly like your weapon.py)"""
        try:
            # Call getTokenInfo function - returns (weapon_tier, weapon_type, weapon_subtype, category, serial_number)
            token_info = await self._call_contract_function(
                self.contracts['weapons'],
                'getTokenInfo',
                [str(token_id)]
            )
            
            if token_info and len(token_info) >= 5:
                weapon_tier = int(token_info[0]) if token_info[0] else 1
                weapon_type = int(token_info[1]) if token_info[1] else 1
                weapon_subtype = int(token_info[2]) if token_info[2] else 1
                category = int(token_info[3]) if token_info[3] else 1
                serial_number = int(token_info[4]) if token_info[4] else 1
                
                # Get weapon name using your original mapping
                weapon_name = self._get_weapon_name(weapon_tier, weapon_type, weapon_subtype, category)
                
                return {
                    "weapon_tier": weapon_tier,
                    "weapon_type": weapon_type,
                    "weapon_subtype": weapon_subtype,
                    "category": category,
                    "serial_number": serial_number,
                    "weapon_name": weapon_name
                }
            
            return {"weapon_tier": 1, "weapon_type": 1, "weapon_subtype": 1, "category": 1, "serial_number": 1, "weapon_name": "Unknown Weapon"}
            
        except Exception as e:
            logger.error(f"Error getting weapon info for {token_id}: {e}")
            return {"weapon_tier": 1, "weapon_type": 1, "weapon_subtype": 1, "category": 1, "serial_number": 1, "weapon_name": "Unknown Weapon"}
    
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
        Get Heroes NFTs with Unity-compatible format using SMART CONTRACT CALLS
        Returns exact format Unity expects: paginated with "sec"/"ano"/"inn"
        """
        try:
            logger.info(f"🦸 Fetching Heroes for {address} using SMART CONTRACT CALLS")
            
            # Get all token IDs owned by this address (like your original tokensOfOwner call)
            token_ids = await self._get_tokens_of_owner(self.contracts['heroes'], address)
            
            if not token_ids:
                logger.info(f"No heroes found for {address}")
                return {"results": [], "count": 0, "next": None}
            
            heroes = []
            
            for token_id in token_ids:
                try:
                    # Get attributes using your original getAttribs call
                    attributes = await self._get_hero_attributes(token_id)
                    
                    # Get token info using your original getTokenInfo call
                    hero_info = await self._get_hero_info(token_id)
                    
                    # Determine fraction based on your original logic
                    if token_id >= 1 and token_id <= 3000:
                        fraction = "Goliath"
                    elif token_id >= 3001 and token_id <= 6000:
                        fraction = "Renegade"
                    else:
                        fraction = "Neutral"
                    
                    # Determine card class based on card_type (from your original system)
                    card_class = "SPECIALIST"
                    if hero_info["card_type"] == 1:
                        card_class = "COLLECTIBLE"
                    elif hero_info["card_type"] == 2:
                        card_class = "REVOLUTION"
                    elif hero_info["card_type"] == 3:
                        card_class = "INFLUENCER"
                    
                    # Create Unity-compatible hero object (exact format from your docs)
                    hero = {
                        "id": token_id,
                        "bc_id": token_id,
                        "title": f"Hero #{token_id}",
                        "fraction": fraction,
                        "owner": address.lower(),
                        "card_class": card_class,
                        "reward": {
                            "power": hero_info["serial_number"]  # Use serial number as power
                        },
                        "metadata": {
                            "sec": attributes["sec"],      # Unity expects "sec"
                            "ano": attributes["ano"],      # Unity expects "ano"
                            "inn": attributes["inn"],      # Unity expects "inn"
                            "revolution": hero_info["card_type"] == 2
                        }
                    }
                    
                    heroes.append(hero)
                    logger.debug(f"✅ Hero {token_id}: sec={attributes['sec']}, ano={attributes['ano']}, inn={attributes['inn']}")
                    
                except Exception as e:
                    logger.error(f"Error processing hero {token_id}: {e}")
                    continue
            
            result = {
                "results": heroes,
                "count": len(heroes),
                "next": None
            }
            
            logger.info(f"✅ Successfully fetched {len(heroes)} Heroes with LIVE SMART CONTRACT DATA")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error fetching heroes: {e}")
            return {"results": [], "count": 0, "next": None, "error": str(e)}
    
    async def get_weapons_for_unity(self, address: str) -> List[Dict]:
        """
        Get Weapons NFTs with Unity-compatible format using SMART CONTRACT CALLS
        Returns exact format Unity expects: direct array with "security"/"anonymity"/"innovation"
        """
        try:
            logger.info(f"⚔️ Fetching Weapons for {address} using SMART CONTRACT CALLS")
            
            # Get all token IDs owned by this address (like your original tokensOfOwner call)
            token_ids = await self._get_tokens_of_owner(self.contracts['weapons'], address)
            
            if not token_ids:
                logger.info(f"No weapons found for {address}")
                return []
            
            weapons = []
            
            for token_id in token_ids:
                try:
                    # Get attributes using your original getAttribs call
                    attributes = await self._get_weapon_attributes(token_id)
                    
                    # Get weapon info using your original getTokenInfo call  
                    weapon_info = await self._get_weapon_info(token_id)
                    
                    # Create Unity-compatible weapon object (exact format from your docs)
                    weapon = {
                        "id": token_id,
                        "bc_id": token_id,
                        "owner_address": address.lower(),
                        "contract_address": self.contracts['weapons'].lower(),
                        "weapon_name": weapon_info["weapon_name"],
                        "security": attributes["security"],      # Unity expects "security" (full word)
                        "anonymity": attributes["anonymity"],    # Unity expects "anonymity" (full word)
                        "innovation": attributes["innovation"],  # Unity expects "innovation" (full word)
                        "minted": True,
                        "burned": False
                    }
                    
                    weapons.append(weapon)
                    logger.debug(f"✅ Weapon {token_id} ({weapon_info['weapon_name']}): security={attributes['security']}, anonymity={attributes['anonymity']}, innovation={attributes['innovation']}")
                    
                except Exception as e:
                    logger.error(f"Error processing weapon {token_id}: {e}")
                    continue
            
            logger.info(f"✅ Successfully fetched {len(weapons)} Weapons with LIVE SMART CONTRACT DATA")
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