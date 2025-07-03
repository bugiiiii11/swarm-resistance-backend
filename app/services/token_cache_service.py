# services/token_cache_service.py - Smart Contract Token Caching Service
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class TokenCacheService:
    """
    Smart caching service for NFT token data
    Reduces smart contract calls by caching token attributes and info
    """
    
    def __init__(self, web3_service, database_module):
        self.web3_service = web3_service
        self.db = database_module
        self.error_counts = {"heroes": 0, "weapons": 0}
        logger.info("✅ TokenCacheService initialized")
    
    async def get_heroes_with_cache(self, address: str, heroes_abi: List[Dict]) -> List[Dict]:
        """
        Get heroes data using cache-first strategy
        Returns list of hero dictionaries with all required fields
        """
        try:
            logger.info(f"🦸 Getting heroes for {address} with caching")
            
            # Step 1: Get token IDs from blockchain (always fresh)
            token_ids = await self.web3_service.get_tokens_of_owner('heroes', heroes_abi, address)
            
            if not token_ids:
                logger.info(f"No heroes found for {address}")
                return []
            
            logger.info(f"Found {len(token_ids)} hero token IDs: {token_ids}")
            
            # Step 2: Check cache for each token
            cached_tokens, missing_tokens = await self._check_heroes_cache(token_ids)
            
            logger.info(f"Cache status: {len(cached_tokens)} cached, {len(missing_tokens)} missing")
            
            # Step 3: Fetch missing tokens from smart contracts
            fresh_tokens = []
            if missing_tokens:
                fresh_tokens = await self._fetch_heroes_from_contracts(missing_tokens, heroes_abi)
                
                # Step 4: Save fresh data to cache
                if fresh_tokens:
                    await self._save_heroes_to_cache(fresh_tokens)
            
            # Step 5: Combine cached and fresh data
            all_tokens = cached_tokens + fresh_tokens
            
            # Step 6: Build Unity-compatible response
            heroes = await self._build_heroes_response(all_tokens, address)
            
            logger.info(f"✅ Successfully processed {len(heroes)} heroes for {address}")
            return heroes
            
        except Exception as e:
            logger.error(f"❌ Error in get_heroes_with_cache: {e}")
            # Log error but don't fail completely
            await self._log_cache_error('heroes', 0, 'get_heroes_with_cache_failed', str(e), address)
            raise
    
    async def get_weapons_with_cache(self, address: str, weapons_abi: List[Dict]) -> List[Dict]:
        """
        Get weapons data using cache-first strategy
        Returns list of weapon dictionaries with all required fields
        """
        try:
            logger.info(f"⚔️ Getting weapons for {address} with caching")
            
            # Step 1: Get token IDs from blockchain (always fresh)
            token_ids = await self.web3_service.get_tokens_of_owner('weapons', weapons_abi, address)
            
            if not token_ids:
                logger.info(f"No weapons found for {address}")
                return []
            
            logger.info(f"Found {len(token_ids)} weapon token IDs: {token_ids}")
            
            # Step 2: Check cache for each token
            cached_tokens, missing_tokens = await self._check_weapons_cache(token_ids)
            
            logger.info(f"Cache status: {len(cached_tokens)} cached, {len(missing_tokens)} missing")
            
            # Step 3: Fetch missing tokens from smart contracts
            fresh_tokens = []
            if missing_tokens:
                fresh_tokens = await self._fetch_weapons_from_contracts(missing_tokens, weapons_abi)
                
                # Step 4: Save fresh data to cache
                if fresh_tokens:
                    await self._save_weapons_to_cache(fresh_tokens)
            
            # Step 5: Combine cached and fresh data
            all_tokens = cached_tokens + fresh_tokens
            
            # Step 6: Build Unity-compatible response
            weapons = await self._build_weapons_response(all_tokens, address)
            
            logger.info(f"✅ Successfully processed {len(weapons)} weapons for {address}")
            return weapons
            
        except Exception as e:
            logger.error(f"❌ Error in get_weapons_with_cache: {e}")
            # Log error but don't fail completely
            await self._log_cache_error('weapons', 0, 'get_weapons_with_cache_failed', str(e), address)
            raise
    
    # ============================================================================
    # HEROES CACHE METHODS
    # ============================================================================
    
    async def _check_heroes_cache(self, token_ids: List[int]) -> Tuple[List[Dict], List[int]]:
        """Check which heroes are in cache and which need to be fetched"""
        try:
            # Query cache for all token IDs
            placeholders = ','.join(['$' + str(i+1) for i in range(len(token_ids))])
            query = f"""
                SELECT bc_id, sec, ano, inn, season_card_id, serial_number,
                       card_type, season_id, card_season_collection_id, last_updated
                FROM heroes_token_cache 
                WHERE bc_id IN ({placeholders}) AND is_valid = TRUE
            """
            
            cached_results = await self.db.execute_query(query, *token_ids)
            
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
            
            logger.debug(f"Cache check: {len(cached_tokens)} found, {len(missing_tokens)} missing")
            return cached_tokens, missing_tokens
            
        except Exception as e:
            logger.error(f"❌ Error checking heroes cache: {e}")
            # If cache check fails, treat all as missing
            return [], token_ids
    
    async def _fetch_heroes_from_contracts(self, token_ids: List[int], heroes_abi: List[Dict]) -> List[Dict]:
        """Fetch hero data from smart contracts in batches"""
        fresh_tokens = []
        
        logger.info(f"🔗 Fetching {len(token_ids)} heroes from smart contracts")
        
        for token_id in token_ids:
            try:
                # Get attributes and info in parallel
                attributes_task = self.web3_service.get_token_attributes('heroes', heroes_abi, token_id)
                info_task = self.web3_service.get_token_info('heroes', heroes_abi, token_id)
                
                attributes, hero_info = await asyncio.gather(attributes_task, info_task)
                
                # Calculate additional fields
                season_card_id = hero_info.get("season_card_id", 0)
                card_type = season_card_id // 1000
                season_id = (season_card_id % 1000) // 10
                card_season_collection_id = season_card_id % 10
                
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
                # Continue with other tokens
                continue
        
        logger.info(f"✅ Successfully fetched {len(fresh_tokens)} heroes from contracts")
        return fresh_tokens
    
    async def _save_heroes_to_cache(self, tokens: List[Dict]):
        """Save hero data to cache"""
        try:
            logger.info(f"💾 Saving {len(tokens)} heroes to cache")
            
            for token in tokens:
                await self.db.execute_command(
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
            
            logger.info(f"✅ Saved {len(tokens)} heroes to cache")
            
        except Exception as e:
            logger.error(f"❌ Failed to save heroes to cache: {e}")
            # Don't raise - caching is optional
    
    # ============================================================================
    # WEAPONS CACHE METHODS
    # ============================================================================
    
    async def _check_weapons_cache(self, token_ids: List[int]) -> Tuple[List[Dict], List[int]]:
        """Check which weapons are in cache and which need to be fetched"""
        try:
            # Query cache for all token IDs
            placeholders = ','.join(['$' + str(i+1) for i in range(len(token_ids))])
            query = f"""
                SELECT bc_id, security, anonymity, innovation, weapon_tier, weapon_type,
                       weapon_subtype, category, serial_number, last_updated
                FROM weapons_token_cache 
                WHERE bc_id IN ({placeholders}) AND is_valid = TRUE
            """
            
            cached_results = await self.db.execute_query(query, *token_ids)
            
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
            
            logger.debug(f"Cache check: {len(cached_tokens)} found, {len(missing_tokens)} missing")
            return cached_tokens, missing_tokens
            
        except Exception as e:
            logger.error(f"❌ Error checking weapons cache: {e}")
            # If cache check fails, treat all as missing
            return [], token_ids
    
    async def _fetch_weapons_from_contracts(self, token_ids: List[int], weapons_abi: List[Dict]) -> List[Dict]:
        """Fetch weapon data from smart contracts in batches"""
        fresh_tokens = []
        
        logger.info(f"🔗 Fetching {len(token_ids)} weapons from smart contracts")
        
        for token_id in token_ids:
            try:
                # Get attributes and info in parallel
                attributes_task = self.web3_service.get_token_attributes('weapons', weapons_abi, token_id)
                info_task = self.web3_service.get_token_info('weapons', weapons_abi, token_id)
                
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
                # Continue with other tokens
                continue
        
        logger.info(f"✅ Successfully fetched {len(fresh_tokens)} weapons from contracts")
        return fresh_tokens
    
    async def _save_weapons_to_cache(self, tokens: List[Dict]):
        """Save weapon data to cache"""
        try:
            logger.info(f"💾 Saving {len(tokens)} weapons to cache")
            
            for token in tokens:
                await self.db.execute_command(
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
            
            logger.info(f"✅ Saved {len(tokens)} weapons to cache")
            
        except Exception as e:
            logger.error(f"❌ Failed to save weapons to cache: {e}")
            # Don't raise - caching is optional
    
    # ============================================================================
    # RESPONSE BUILDING METHODS
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
                        character_data = await self.db.execute_query(
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
                # Continue with other heroes
                continue
        
        return heroes
    
    async def _build_weapons_response(self, tokens: List[Dict], address: str) -> List[Dict]:
        """Build Unity-compatible weapons response with weapon names from database"""
        weapons = []
        
        for token in tokens:
            try:
                bc_id = token['bc_id']
                
                # Get weapon name from database
                weapon_name = await self._get_weapon_name_from_db(
                    token['weapon_tier'],
                    token['weapon_type'],
                    token['weapon_subtype'],
                    token['category']
                )
                
                # Get contract address from database
                contract_address = await self._get_contract_address('weapons')
                
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
                # Continue with other weapons
                continue
        
        return weapons
    
    # ============================================================================
    # HELPER METHODS
    # ============================================================================
    
    async def _get_weapon_name_from_db(self, weapon_tier: int, weapon_type: int, weapon_subtype: int, category: int) -> str:
        """Get weapon name from database mapping table"""
        try:
            result = await self.db.execute_query(
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
    
    async def _get_contract_address(self, contract_name: str) -> str:
        """Get contract address from database"""
        try:
            result = await self.db.execute_query(
                "SELECT address FROM smart_contracts WHERE name = $1 AND is_active = TRUE",
                contract_name
            )
            
            if result:
                return result[0]['address']
            else:
                # Fallback to hardcoded addresses (temporary)
                fallback_addresses = {
                    'heroes': '0x27331bbfe94d1b8518816462225b16622ac74e2e',
                    'weapons': '0x31dd72d810b34c339f2ce9119e2ebfbb9926694a',
                    'lands': '0xaae02c81133d865d543df02b1e458de2279c4a5b'
                }
                address = fallback_addresses.get(contract_name, '0x0000000000000000000000000000000000000000')
                logger.warning(f"⚠️ Contract {contract_name} not found in database, using fallback: {address}")
                return address
                
        except Exception as e:
            logger.error(f"❌ Failed to get contract address for {contract_name}: {e}")
            # Return fallback
            fallback_addresses = {
                'heroes': '0x27331bbfe94d1b8518816462225b16622ac74e2e',
                'weapons': '0x31dd72d810b34c339f2ce9119e2ebfbb9926694a'
            }
            return fallback_addresses.get(contract_name, '0x0000000000000000000000000000000000000000')
    
    async def _log_cache_error(self, contract_type: str, token_id: int, error_type: str, error_message: str, wallet_address: str = None):
        """Log cache errors for debugging and monitoring"""
        try:
            await self.db.execute_command(
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
    # CACHE MANAGEMENT METHODS
    # ============================================================================
    
    async def invalidate_token_cache(self, contract_type: str, token_ids: List[int] = None):
        """Invalidate cache entries for specific tokens or all tokens of a contract type"""
        try:
            if token_ids:
                # Invalidate specific tokens
                placeholders = ','.join(['$' + str(i+2) for i in range(len(token_ids))])
                
                if contract_type == 'heroes':
                    query = f"UPDATE heroes_token_cache SET is_valid = FALSE WHERE bc_id IN ({placeholders})"
                else:
                    query = f"UPDATE weapons_token_cache SET is_valid = FALSE WHERE bc_id IN ({placeholders})"
                
                await self.db.execute_command(query, *token_ids)
                logger.info(f"✅ Invalidated cache for {len(token_ids)} {contract_type} tokens")
            else:
                # Invalidate all tokens of this type
                if contract_type == 'heroes':
                    await self.db.execute_command("UPDATE heroes_token_cache SET is_valid = FALSE")
                else:
                    await self.db.execute_command("UPDATE weapons_token_cache SET is_valid = FALSE")
                
                logger.info(f"✅ Invalidated all {contract_type} cache entries")
                
        except Exception as e:
            logger.error(f"❌ Failed to invalidate {contract_type} cache: {e}")
            raise
    
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring"""
        try:
            stats_result = await self.db.execute_query("SELECT * FROM get_cache_statistics()")
            
            if stats_result:
                stats = stats_result[0]
                return {
                    "heroes_cached": stats['heroes_cached'],
                    "weapons_cached": stats['weapons_cached'],
                    "heroes_invalid": stats['heroes_invalid'],
                    "weapons_invalid": stats['weapons_invalid'],
                    "total_errors": stats['total_errors'],
                    "unresolved_errors": stats['unresolved_errors'],
                    "error_counts": self.error_counts.copy(),
                    "cache_hit_rate": {
                        "heroes": self._calculate_hit_rate("heroes", stats['heroes_cached'], stats['total_errors']),
                        "weapons": self._calculate_hit_rate("weapons", stats['weapons_cached'], stats['total_errors'])
                    }
                }
            else:
                return {"error": "Unable to fetch cache statistics"}
                
        except Exception as e:
            logger.error(f"❌ Failed to get cache statistics: {e}")
            return {"error": str(e)}
    
    def _calculate_hit_rate(self, contract_type: str, cached_count: int, total_errors: int) -> float:
        """Calculate cache hit rate for monitoring"""
        total_requests = cached_count + self.error_counts.get(contract_type, 0)
        if total_requests == 0:
            return 0.0
        return (cached_count / total_requests) * 100.0
    
    async def cleanup_old_errors(self, days_old: int = 7):
        """Clean up old resolved errors from the error log"""
        try:
            result = await self.db.execute_command(
                """DELETE FROM token_cache_errors 
                   WHERE resolved = TRUE AND resolved_at < NOW() - INTERVAL '%s days'
                   RETURNING id""",
                days_old
            )
            
            # Count deleted rows (PostgreSQL specific)
            deleted_count = len(result) if result else 0
            logger.info(f"✅ Cleaned up {deleted_count} old error entries")
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup old errors: {e}")
            return 0