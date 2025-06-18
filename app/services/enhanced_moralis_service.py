# app/services/enhanced_moralis_service.py
"""
Enhanced Moralis Service with MedaShooter Unity Integration
Extends existing moralis_service.py with Unity-compatible NFT endpoints
"""

import requests
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import os
import logging
from app.config import settings
from app.services.moralis_service import MoralisService

logger = logging.getLogger(__name__)

class EnhancedMoralisService(MoralisService):
    """
    Enhanced Moralis service with MedaShooter-specific NFT handling
    Extends the existing MoralisService with Unity game compatibility
    """
    
    def __init__(self):
        super().__init__()
        
        # MedaShooter NFT contract addresses
        self.nft_contracts = {
            "HEROES": "0x27331bbfe94d1b8518816462225b16622ac74e2e",
            "WEAPONS": "0x31dd72d810b34c339f2ce9119e2ebfbb9926694a",
            "LANDS": "0xaae02c81133d865d543df02b1e458de2279c4a5b",
            "MEDA_GAS_TOKEN": "0xEDfd96dD07b6eA11393c177686795771579f488a"
        }
        
        # NFT boost calculation rules
        self.boost_rules = {
            "HEROES": {
                "damage_multiplier": 5,  # +5% per Hero (max 50%)
                "health_bonus": 25       # +25 HP per Hero
            },
            "WEAPONS": {
                "fire_rate_bonus": 3,    # +3% per Weapon (max 30%)
                "health_bonus": 15       # +15 HP per Weapon
            },
            "LANDS": {
                "score_multiplier": 10,  # +10% per Land (max 100%)
                "health_bonus": 35       # +35 HP per Land
            },
            "MEDA_GAS": {
                "multiplier": 2          # +2% per total NFT (max 50%)
            }
        }

    async def get_nfts_by_contract(self, wallet_address: str, contract_address: str, chain: str = "polygon") -> List[Dict]:
        """
        Get NFTs for a specific contract address
        Used by MedaShooter for heroes, weapons, and lands
        """
        endpoint = f"/{wallet_address}/nft"
        params = {
            "chain": chain,
            "format": "decimal",
            "token_addresses": [contract_address],
            "exclude_spam": "true",
            "media_items": "true"
        }
        
        try:
            raw_data = await self._make_request(endpoint, params)
            
            # Handle both list and dict responses from Moralis
            nft_list = raw_data if isinstance(raw_data, list) else raw_data.get("result", [])
            
            processed_nfts = []
            for nft in nft_list:
                # Parse metadata if available
                metadata = {}
                if nft.get("metadata"):
                    try:
                        metadata = json.loads(nft.get("metadata")) if isinstance(nft.get("metadata"), str) else nft.get("metadata")
                    except:
                        metadata = {}
                
                processed_nft = {
                    "token_id": nft.get("token_id"),
                    "token_address": nft.get("token_address"),
                    "token_uri": nft.get("token_uri"),
                    "metadata": metadata,
                    "amount": nft.get("amount"),
                    "owner_of": nft.get("owner_of"),
                    "contract_type": nft.get("contract_type"),
                    "name": nft.get("name"),
                    "symbol": nft.get("symbol")
                }
                
                processed_nfts.append(processed_nft)
            
            return processed_nfts
            
        except Exception as e:
            logger.error(f"Failed to fetch NFTs for contract {contract_address}: {str(e)}")
            return []

    def parse_nft_attributes(self, attributes: List[Dict]) -> Dict:
        """Parse NFT attributes from Moralis format"""
        parsed = {}
        for attr in attributes:
            if isinstance(attr, dict):
                trait_type = attr.get('trait_type', '')
                value = attr.get('value', 0)
                parsed[trait_type] = value
        return parsed

    def map_faction_to_unity_fraction(self, faction: str) -> str:
        """Map NFT faction to Unity's expected fraction format"""
        faction_mapping = {
            'Goliath': 'Goliath',
            'Renegade': 'Renegade', 
            'Neutral': 'Neutral',
            'OTHER': 'Neutral'  # Default fallback
        }
        return faction_mapping.get(faction, 'Neutral')

    async def get_heroes_for_unity(self, wallet_address: str, chain: str = "polygon") -> Dict:
        """
        Get heroes in Unity-compatible format
        
        Unity expects:
        - "sec", "ano", "inn" (not "security", "anonymity", "innovation")
        - Paginated response format with "results", "count", "next"
        """
        try:
            heroes = await self.get_nfts_by_contract(wallet_address, self.nft_contracts["HEROES"], chain)
            
            results = []
            for hero in heroes:
                metadata = hero.get('metadata', {})
                attributes = self.parse_nft_attributes(metadata.get('attributes', []))
                
                # Unity's EXACT expected format
                hero_data = {
                    "id": int(hero.get("token_id", 0)),
                    "bc_id": int(hero.get("token_id", 0)),
                    "title": metadata.get('name', 'Unknown Hero'),
                    "fraction": self.map_faction_to_unity_fraction(attributes.get('Faction', 'Neutral')),
                    "owner": wallet_address.lower(),
                    "card_class": "SPECIALIST",
                    "reward": {
                        "power": attributes.get('Power', 0)
                    },
                    "metadata": {
                        "sec": attributes.get('Security', 0),  # Unity expects "sec"
                        "ano": attributes.get('Anonymity', 0),  # Unity expects "ano"
                        "inn": attributes.get('Innovation', 0),  # Unity expects "inn"
                        "revolution": attributes.get('Revolution', False)
                    }
                }
                results.append(hero_data)
            
            # Unity expects paginated response format
            return {
                "results": results,
                "count": len(results),
                "next": None
            }
            
        except Exception as e:
            logger.error(f"Failed to get heroes for Unity: {str(e)}")
            return {"results": [], "count": 0, "next": None}

    async def get_weapons_for_unity(self, wallet_address: str, chain: str = "polygon") -> List[Dict]:
        """
        Get weapons in Unity-compatible format
        
        Unity expects:
        - "security", "anonymity", "innovation" (full words)
        - "weapon_name" field
        - Direct array response (not paginated)
        """
        try:
            weapons = await self.get_nfts_by_contract(wallet_address, self.nft_contracts["WEAPONS"], chain)
            
            results = []
            for weapon in weapons:
                metadata = weapon.get('metadata', {})
                attributes = self.parse_nft_attributes(metadata.get('attributes', []))
                
                # Unity's EXACT expected format - direct array response
                weapon_data = {
                    "id": int(weapon.get("token_id", 0)),
                    "bc_id": int(weapon.get("token_id", 0)),
                    "owner_address": wallet_address.lower(),
                    "contract_address": self.nft_contracts["WEAPONS"].lower(),
                    "weapon_name": metadata.get('name', 'Unknown Weapon'),  # Critical field
                    "security": attributes.get('Security', 0),  # Unity expects "security"
                    "anonymity": attributes.get('Anonymity', 0),  # Unity expects "anonymity"
                    "innovation": attributes.get('Innovation', 0),  # Unity expects "innovation"
                    "minted": True,
                    "burned": False
                }
                results.append(weapon_data)
            
            return results  # Direct array, not paginated
            
        except Exception as e:
            logger.error(f"Failed to get weapons for Unity: {str(e)}")
            return []

    def calculate_nft_game_boosts(self, heroes: List[Dict], weapons: List[Dict], lands: List[Dict]) -> Dict:
        """Calculate game boosts based on NFT ownership"""
        hero_count = len(heroes)
        weapon_count = len(weapons)
        land_count = len(lands)
        total_nfts = hero_count + weapon_count + land_count
        
        # Calculate boosts according to rules (with caps)
        damage_multiplier = min(hero_count * self.boost_rules["HEROES"]["damage_multiplier"], 50)
        fire_rate_bonus = min(weapon_count * self.boost_rules["WEAPONS"]["fire_rate_bonus"], 30)
        score_multiplier = min(land_count * self.boost_rules["LANDS"]["score_multiplier"], 100)
        
        # Health bonuses
        health_bonus = (
            hero_count * self.boost_rules["HEROES"]["health_bonus"] +
            weapon_count * self.boost_rules["WEAPONS"]["health_bonus"] +
            land_count * self.boost_rules["LANDS"]["health_bonus"]
        )
        
        # MEDA Gas multiplier based on total NFTs
        meda_gas_multiplier = min(total_nfts * self.boost_rules["MEDA_GAS"]["multiplier"], 50)
        
        return {
            "damage_multiplier": damage_multiplier,
            "fire_rate_bonus": fire_rate_bonus,
            "score_multiplier": score_multiplier,
            "health_bonus": health_bonus,
            "meda_gas_multiplier": meda_gas_multiplier
        }

    async def get_enhanced_player_data(self, wallet_address: str, chain: str = "polygon") -> Dict:
        """
        Get comprehensive NFT data with enhanced boost calculations
        Used by Web3 dApp frontend for displaying player advantages
        """
        try:
            # Fetch all NFT contracts
            heroes = await self.get_nfts_by_contract(wallet_address, self.nft_contracts["HEROES"], chain)
            weapons = await self.get_nfts_by_contract(wallet_address, self.nft_contracts["WEAPONS"], chain)
            lands = await self.get_nfts_by_contract(wallet_address, self.nft_contracts["LANDS"], chain)
            
            # Calculate game boosts
            game_boosts = self.calculate_nft_game_boosts(heroes, weapons, lands)
            
            # Prepare detailed NFT data
            nft_details = {
                "heroes": [
                    {
                        "token_id": hero.get("token_id"),
                        "name": hero.get("metadata", {}).get("name", "Unknown Hero"),
                        "image": hero.get("metadata", {}).get("image"),
                        "attributes": self.parse_nft_attributes(hero.get("metadata", {}).get("attributes", []))
                    }
                    for hero in heroes
                ],
                "weapons": [
                    {
                        "token_id": weapon.get("token_id"),
                        "name": weapon.get("metadata", {}).get("name", "Unknown Weapon"),
                        "image": weapon.get("metadata", {}).get("image"),
                        "attributes": self.parse_nft_attributes(weapon.get("metadata", {}).get("attributes", []))
                    }
                    for weapon in weapons
                ],
                "lands": [
                    {
                        "token_id": land.get("token_id"),
                        "name": land.get("metadata", {}).get("name", "Unknown Land"),
                        "image": land.get("metadata", {}).get("image"),
                        "attributes": self.parse_nft_attributes(land.get("metadata", {}).get("attributes", []))
                    }
                    for land in lands
                ]
            }
            
            return {
                "success": True,
                "data": {
                    "wallet_address": wallet_address.lower(),
                    "nft_counts": {
                        "heroes": len(heroes),
                        "weapons": len(weapons),
                        "lands": len(lands),
                        "total": len(heroes) + len(weapons) + len(lands)
                    },
                    "game_boosts": game_boosts,
                    "nft_details": nft_details,
                    "contracts": self.nft_contracts,
                    "unity_compatible": True,
                    "last_updated": datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get enhanced player data: {str(e)}")
            raise Exception(f"Enhanced player data fetch failed: {str(e)}")

# Singleton instance - extends the existing moralis_service
enhanced_moralis_service = EnhancedMoralisService()