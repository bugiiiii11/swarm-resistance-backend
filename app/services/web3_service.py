# services/web3_service.py
import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Union
from web3 import Web3, AsyncWeb3
from web3.exceptions import Web3Exception, ContractLogicError
from web3.middleware import geth_poa_middleware
import os
from cachetools import TTLCache

logger = logging.getLogger(__name__)

class Web3ServiceException(Exception):
    """Custom exception for Web3 service errors"""
    pass

class Web3Service:
    """
    Robust Web3 service for Polygon smart contract interactions
    Supports multiple RPC endpoints with automatic failover
    """
    
    def __init__(self):
        # RPC endpoints in priority order
        self.rpc_endpoints = [
            "https://polygon-rpc.com",
            "https://rpc-mainnet.matic.network", 
            "https://matic-mainnet.chainstacklabs.com"
        ]
        
        # Contract addresses
        self.contract_addresses = {
            'heroes': '0x27331bbfe94d1b8518816462225b16622ac74e2e',
            'weapons': '0x31dd72d810b34c339f2ce9119e2ebfbb9926694a',
            'lands': '0xaae02c81133d865d543df02b1e458de2279c4a5b'
        }
        
        # Simple cache for NFT data (5 minutes TTL)
        self.cache = TTLCache(maxsize=1000, ttl=300)
        
        # Web3 instances for each RPC
        self.web3_instances = {}
        self._initialize_web3_instances()
        
        # Contract instances will be loaded when needed
        self.contracts = {}
        
        logger.info("✅ Web3Service initialized with failover RPC endpoints")
    
    def _initialize_web3_instances(self):
        """Initialize Web3 instances for all RPC endpoints"""
        for rpc_url in self.rpc_endpoints:
            try:
                w3 = Web3(Web3.HTTPProvider(rpc_url))
                # Add PoA middleware for Polygon
                w3.middleware_onion.inject(geth_poa_middleware, layer=0)
                self.web3_instances[rpc_url] = w3
                logger.info(f"✅ Initialized Web3 for {rpc_url}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize Web3 for {rpc_url}: {e}")
    
    def _get_working_web3(self) -> Web3:
        """Get the first working Web3 instance"""
        for rpc_url in self.rpc_endpoints:
            if rpc_url not in self.web3_instances:
                continue
                
            w3 = self.web3_instances[rpc_url]
            try:
                # Quick connectivity test
                block_number = w3.eth.block_number
                logger.debug(f"✅ RPC {rpc_url} working, block: {block_number}")
                return w3
            except Exception as e:
                logger.warning(f"⚠️ RPC {rpc_url} failed: {e}")
                continue
        
        raise Web3ServiceException("All RPC endpoints are unavailable")
    
    def _get_contract(self, contract_name: str, abi: List[Dict]) -> Any:
        """Get contract instance with caching"""
        cache_key = f"contract_{contract_name}"
        
        if cache_key in self.contracts:
            return self.contracts[cache_key]
        
        w3 = self._get_working_web3()
        contract_address = self.contract_addresses.get(contract_name)
        
        if not contract_address:
            raise Web3ServiceException(f"Unknown contract: {contract_name}")
        
        try:
            contract = w3.eth.contract(
                address=Web3.to_checksum_address(contract_address),
                abi=abi
            )
            self.contracts[cache_key] = contract
            logger.debug(f"✅ Contract {contract_name} loaded at {contract_address}")
            return contract
        except Exception as e:
            raise Web3ServiceException(f"Failed to load contract {contract_name}: {e}")
    
    def _validate_address(self, address: str) -> str:
        """Validate and normalize wallet address"""
        if not address:
            raise ValueError("Address cannot be empty")
        
        # Remove any whitespace
        address = address.strip()
        
        # Check basic format
        if not address.startswith('0x') or len(address) != 42:
            raise ValueError(f"Invalid address format: {address}")
        
        try:
            # Validate checksum
            return Web3.to_checksum_address(address)
        except Exception:
            raise ValueError(f"Invalid address checksum: {address}")
    
    async def _call_contract_function_with_retry(self, contract_function, max_retries: int = 2, retry_delay: float = 1.0) -> Any:
        """Call contract function with retry logic"""
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                result = contract_function.call()
                logger.debug(f"✅ Contract call successful on attempt {attempt + 1}")
                return result
            except Exception as e:
                last_exception = e
                logger.warning(f"⚠️ Contract call attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries:
                    logger.info(f"🔄 Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    # Try to get a fresh Web3 instance
                    try:
                        self._get_working_web3()
                    except:
                        pass
        
        raise Web3ServiceException(f"Contract call failed after {max_retries + 1} attempts: {last_exception}")
    
    async def get_tokens_of_owner(self, contract_name: str, abi: List[Dict], owner_address: str) -> List[int]:
        """Get all token IDs owned by an address"""
        # Validate address first
        owner_address = self._validate_address(owner_address)
        
        # Check cache first
        cache_key = f"tokens_{contract_name}_{owner_address.lower()}"
        if cache_key in self.cache:
            logger.debug(f"🎯 Cache hit for {cache_key}")
            return self.cache[cache_key]
        
        try:
            contract = self._get_contract(contract_name, abi)
            
            # Call tokensOfOwner function
            contract_function = contract.functions.tokensOfOwner(owner_address)
            result = await self._call_contract_function_with_retry(contract_function)
            
            # Convert to list of integers
            token_ids = [int(token_id) for token_id in result] if result else []
            
            # Cache the result
            self.cache[cache_key] = token_ids
            
            logger.info(f"✅ Found {len(token_ids)} tokens for {owner_address} in {contract_name}")
            return token_ids
            
        except ValueError as e:
            # Address validation error - this is a client error
            logger.error(f"❌ Address validation failed: {e}")
            raise ValueError(str(e))
        except Exception as e:
            logger.error(f"❌ Failed to get tokens for {owner_address}: {e}")
            raise Web3ServiceException(f"Failed to get tokens: {e}")
    
    async def get_token_attributes(self, contract_name: str, abi: List[Dict], token_id: int) -> Dict[str, int]:
        """Get token attributes (sec, ano, inn) or (security, anonymity, innovation)"""
        cache_key = f"attrs_{contract_name}_{token_id}"
        if cache_key in self.cache:
            logger.debug(f"🎯 Cache hit for {cache_key}")
            return self.cache[cache_key]
        
        try:
            contract = self._get_contract(contract_name, abi)
            
            # Call getAttribs function
            contract_function = contract.functions.getAttribs(token_id)
            result = await self._call_contract_function_with_retry(contract_function)
            
            if not result or len(result) < 3:
                logger.warning(f"⚠️ Invalid getAttribs result for token {token_id}: {result}")
                # Return fallback values
                if contract_name == 'heroes':
                    attributes = {"sec": 50, "ano": 50, "inn": 50}
                else:
                    attributes = {"security": 60, "anonymity": 60, "innovation": 60}
            else:
                # Parse the result
                if contract_name == 'heroes':
                    attributes = {
                        "sec": int(result[0]) if result[0] else 50,
                        "ano": int(result[1]) if result[1] else 50,
                        "inn": int(result[2]) if result[2] else 50
                    }
                else:  # weapons
                    attributes = {
                        "security": int(result[0]) if result[0] else 60,
                        "anonymity": int(result[1]) if result[1] else 60,
                        "innovation": int(result[2]) if result[2] else 60
                    }
            
            # Cache the result
            self.cache[cache_key] = attributes
            
            logger.debug(f"✅ Got attributes for token {token_id}: {attributes}")
            return attributes
            
        except Exception as e:
            logger.error(f"❌ Failed to get attributes for token {token_id}: {e}")
            raise Web3ServiceException(f"Failed to get token attributes: {e}")
    
    async def get_token_info(self, contract_name: str, abi: List[Dict], token_id: int) -> Dict[str, Any]:
        """Get token info (varies by contract type)"""
        cache_key = f"info_{contract_name}_{token_id}"
        if cache_key in self.cache:
            logger.debug(f"🎯 Cache hit for {cache_key}")
            return self.cache[cache_key]
        
        try:
            contract = self._get_contract(contract_name, abi)
            
            # Call getTokenInfo function
            contract_function = contract.functions.getTokenInfo(token_id)
            result = await self._call_contract_function_with_retry(contract_function)
            
            if contract_name == 'heroes':
                # Heroes: (season_card_id, serial_number)
                if result and len(result) >= 2:
                    season_card_id = int(result[0]) if result[0] else 0
                    serial_number = int(result[1]) if result[1] else 0
                    
                    # Decode card data (from your original logic)
                    card_type = season_card_id // 1000
                    season_id = (season_card_id % 1000) // 10
                    card_season_collection_id = season_card_id % 10
                    
                    info = {
                        "season_card_id": season_card_id,
                        "serial_number": serial_number,
                        "card_type": card_type,
                        "season_id": season_id,
                        "card_season_collection_id": card_season_collection_id
                    }
                else:
                    info = {"season_card_id": 0, "serial_number": 0, "card_type": 0, "season_id": 0, "card_season_collection_id": 0}
            
            elif contract_name == 'weapons':
                # Weapons: (weapon_tier, weapon_type, weapon_subtype, category, serial_number)
                if result and len(result) >= 5:
                    info = {
                        "weapon_tier": int(result[0]) if result[0] else 1,
                        "weapon_type": int(result[1]) if result[1] else 1,
                        "weapon_subtype": int(result[2]) if result[2] else 1,
                        "category": int(result[3]) if result[3] else 1,
                        "serial_number": int(result[4]) if result[4] else 1
                    }
                else:
                    info = {"weapon_tier": 1, "weapon_type": 1, "weapon_subtype": 1, "category": 1, "serial_number": 1}
            
            else:
                info = {"raw_result": result}
            
            # Cache the result
            self.cache[cache_key] = info
            
            logger.debug(f"✅ Got info for token {token_id}: {info}")
            return info
            
        except Exception as e:
            logger.error(f"❌ Failed to get info for token {token_id}: {e}")
            raise Web3ServiceException(f"Failed to get token info: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring"""
        return {
            "cache_size": len(self.cache),
            "cache_maxsize": self.cache.maxsize,
            "cache_ttl": self.cache.ttl,
            "rpc_endpoints": self.rpc_endpoints,
            "contracts_loaded": list(self.contracts.keys())
        }
    
    def clear_cache(self):
        """Clear the cache"""
        self.cache.clear()
        logger.info("🧹 Cache cleared")

# Global instance
web3_service = Web3Service()