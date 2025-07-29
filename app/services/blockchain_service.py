# services/blockchain_service.py - Unified Web3 Service with HTTP API and Centralized Config
import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Union
from web3 import Web3, AsyncWeb3
from web3.exceptions import Web3Exception, ContractLogicError
from web3.middleware import geth_poa_middleware
import os
import requests
from datetime import datetime, timedelta
import json
from cachetools import TTLCache
import base64

logger = logging.getLogger(__name__)

class BlockchainServiceException(Exception):
    """Custom exception for blockchain service errors"""
    pass

class BlockchainConfig:
    """Centralized configuration management for all blockchain operations"""
    
    def __init__(self):
        # RPC Configuration
        self.rpc_endpoints = [
            "https://polygon-rpc.com",
            "https://rpc-mainnet.matic.network", 
            "https://matic-mainnet.chainstacklabs.com"
        ]
        
        # NFT Contract addresses (Polygon Mainnet)
        self.nft_contracts = {
            'heroes': '0x27331bbfe94d1b8518816462225b16622ac74e2e',
            'weapons': '0x31dd72d810b34c339f2ce9119e2ebfbb9926694a',
            'lands': '0xaae02c81133d865d543df02b1e458de2279c4a5b'
        }
        
        # ERC20 Token addresses for DeFi benefits
        self.erc20_tokens = {
            'moh': '0x1D3dD50B23849247C426AEd040Fb8f93D9123b60',
            'medallc': '0xEDfd96dD07b6eA11393c177686795771579f488a',
            'meda_gas': '0xEDfd96dD07b6eA11393c177686795771579f488a'
        }
        
        # Moralis API Configuration
        self.moralis_api_key = os.getenv("MORALIS_API_KEY")
        self.moralis_base_url = "https://deep-index.moralis.io/api/v2.2"
        
        # Cache Configuration
        self.cache_config = {
            'nft_ttl': 300,      # 5 minutes for NFT data
            'token_ttl': 300,    # 5 minutes for token balances
            'contract_ttl': 3600, # 1 hour for contract calls
            'max_size': 1000     # Maximum cache entries
        }
        
        # Blockchain Configuration
        self.chain = "polygon"
        self.chain_id = 137
        
        logger.info("✅ Blockchain configuration initialized")
    
    def get_contract_address(self, contract_name: str) -> str:
        """Get contract address by name"""
        # Check NFT contracts first
        if contract_name in self.nft_contracts:
            return self.nft_contracts[contract_name]
        
        # Check ERC20 tokens
        if contract_name in self.erc20_tokens:
            return self.erc20_tokens[contract_name]
        
        raise BlockchainServiceException(f"Unknown contract: {contract_name}")
    
    def get_all_contracts(self) -> Dict[str, str]:
        """Get all contract addresses"""
        return {**self.nft_contracts, **self.erc20_tokens}
    
    def get_moralis_headers(self) -> Dict[str, str]:
        """Get Moralis API headers"""
        if not self.moralis_api_key:
            raise BlockchainServiceException("MORALIS_API_KEY environment variable required")
        
        return {
            "X-API-Key": self.moralis_api_key,
            "Accept": "application/json"
        }

class BlockchainService:
    """
    Unified blockchain service combining Web3 RPC calls and Moralis HTTP API
    Provides both direct smart contract interaction and enriched NFT/token data
    """
    
    def __init__(self):
        self.config = BlockchainConfig()
        
        # Unified cache for all blockchain data
        self.cache = TTLCache(
            maxsize=self.config.cache_config['max_size'], 
            ttl=self.config.cache_config['nft_ttl']
        )
        
        # Separate caches for different data types
        self.nft_cache = TTLCache(
            maxsize=500, 
            ttl=self.config.cache_config['nft_ttl']
        )
        self.token_cache = TTLCache(
            maxsize=500, 
            ttl=self.config.cache_config['token_ttl']
        )
        
        # Web3 instances for each RPC endpoint
        self.web3_instances = {}
        self._initialize_web3_instances()
        
        # Contract instances cache
        self.contracts = {}
        
        logger.info("✅ Unified Blockchain Service initialized")
        logger.info(f"📊 Configuration: {len(self.config.nft_contracts)} NFT contracts, {len(self.config.erc20_tokens)} ERC20 tokens")
    
    def _initialize_web3_instances(self):
        """Initialize Web3 instances for all RPC endpoints with failover"""
        for rpc_url in self.config.rpc_endpoints:
            try:
                w3 = Web3(Web3.HTTPProvider(rpc_url))
                # Add PoA middleware for Polygon
                w3.middleware_onion.inject(geth_poa_middleware, layer=0)
                self.web3_instances[rpc_url] = w3
                logger.info(f"✅ Web3 initialized for {rpc_url}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize Web3 for {rpc_url}: {e}")
    
    def _get_working_web3(self) -> Web3:
        """Get the first working Web3 instance with automatic failover"""
        for rpc_url in self.config.rpc_endpoints:
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
        
        raise BlockchainServiceException("All RPC endpoints are unavailable")
    
    def _get_contract(self, contract_name: str, abi: List[Dict]) -> Any:
        """Get contract instance with caching and automatic address resolution"""
        cache_key = f"contract_{contract_name}"
        
        if cache_key in self.contracts:
            return self.contracts[cache_key]
        
        w3 = self._get_working_web3()
        contract_address = self.config.get_contract_address(contract_name)
        
        try:
            contract = w3.eth.contract(
                address=Web3.to_checksum_address(contract_address),
                abi=abi
            )
            self.contracts[cache_key] = contract
            logger.debug(f"✅ Contract {contract_name} loaded at {contract_address}")
            return contract
        except Exception as e:
            raise BlockchainServiceException(f"Failed to load contract {contract_name}: {e}")
    
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
        """Call contract function with retry logic and failover"""
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
                    # Try to get a fresh Web3 instance for next attempt
                    try:
                        self._get_working_web3()
                    except:
                        pass
        
        raise BlockchainServiceException(f"Contract call failed after {max_retries + 1} attempts: {last_exception}")
    
    # ============================================================================
    # WEB3 RPC METHODS (Direct Smart Contract Calls)
    # ============================================================================
    
    async def get_tokens_of_owner(self, contract_name: str, abi: List[Dict], owner_address: str) -> List[int]:
        """Get all token IDs owned by an address via smart contract"""
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
            raise BlockchainServiceException(f"Failed to get tokens: {e}")
    
    async def get_token_attributes(self, contract_name: str, abi: List[Dict], token_id: int) -> Dict[str, int]:
        """Get token attributes via smart contract (sec, ano, inn) or (security, anonymity, innovation)"""
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
                # Return fallback values based on contract type
                if contract_name == 'heroes':
                    attributes = {"sec": 50, "ano": 50, "inn": 50}
                else:
                    attributes = {"security": 60, "anonymity": 60, "innovation": 60}
            else:
                # Parse the result based on contract type
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
            raise BlockchainServiceException(f"Failed to get token attributes: {e}")
    
    async def get_token_info(self, contract_name: str, abi: List[Dict], token_id: int) -> Dict[str, Any]:
        """Get token info via smart contract (varies by contract type)"""
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
            raise BlockchainServiceException(f"Failed to get token info: {e}")
    
    # ============================================================================
    # ERC1155 METHODS (for Land Tickets)
    # ============================================================================
    
    async def get_erc1155_balances(self, contract_name: str, owner_address: str, token_ids: List[int]) -> List[int]:
        """Get ERC1155 token balances for multiple token IDs"""
        # Validate address first
        owner_address = self._validate_address(owner_address)
        
        # Check cache first (shorter TTL for balances since they change frequently)
        cache_key = f"erc1155_balances_{contract_name}_{owner_address.lower()}_{','.join(map(str, token_ids))}"
        if cache_key in self.cache:
            logger.debug(f"🎯 Cache hit for {cache_key}")
            return self.cache[cache_key]
        
        # ERC1155 ABI for balanceOfBatch
        erc1155_abi = [
            {
                "inputs": [
                    {"internalType": "address[]", "name": "accounts", "type": "address[]"},
                    {"internalType": "uint256[]", "name": "ids", "type": "uint256[]"}
                ],
                "name": "balanceOfBatch",
                "outputs": [{"internalType": "uint256[]", "name": "", "type": "uint256[]"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]
        
        try:
            contract = self._get_contract(contract_name, erc1155_abi)
            
            # Prepare arrays for balanceOfBatch call
            addresses = [owner_address] * len(token_ids)
            
            # Call balanceOfBatch function
            contract_function = contract.functions.balanceOfBatch(addresses, token_ids)
            result = await self._call_contract_function_with_retry(contract_function)
            
            # Convert to list of integers
            balances = [int(balance) for balance in result] if result else [0] * len(token_ids)
            
            # Cache the result (shorter TTL for balances)
            self.cache[cache_key] = balances
            
            logger.info(f"✅ ERC1155 balances for {owner_address} in {contract_name}: {dict(zip(token_ids, balances))}")
            return balances
            
        except ValueError as e:
            # Address validation error - this is a client error
            logger.error(f"❌ Address validation failed: {e}")
            raise ValueError(str(e))
        except Exception as e:
            logger.error(f"❌ Failed to get ERC1155 balances for {owner_address}: {e}")
            raise BlockchainServiceException(f"Failed to get ERC1155 balances: {e}")
    
    # ============================================================================
    # ERC20 TOKEN METHODS
    # ============================================================================
    
    async def get_erc20_balance(self, token_name: str, owner_address: str) -> int:
        """Get ERC20 token balance for an address"""
        # Validate address first
        owner_address = self._validate_address(owner_address)
        
        # Check cache first
        cache_key = f"erc20_balance_{token_name}_{owner_address.lower()}"
        if cache_key in self.cache:
            logger.debug(f"🎯 Cache hit for {cache_key}")
            return self.cache[cache_key]
        
        # ERC20 ABI for balanceOf
        erc20_abi = [
            {
                "inputs": [{"internalType": "address", "name": "account", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]
        
        try:
            contract = self._get_contract(token_name, erc20_abi)
            
            # Call balanceOf function
            contract_function = contract.functions.balanceOf(owner_address)
            result = await self._call_contract_function_with_retry(contract_function)
            
            # Convert to integer
            balance = int(result) if result else 0
            
            # Cache the result
            self.cache[cache_key] = balance
            
            logger.info(f"✅ {token_name.upper()} balance for {owner_address}: {balance}")
            return balance
            
        except ValueError as e:
            # Address validation error - this is a client error
            logger.error(f"❌ Address validation failed: {e}")
            raise ValueError(str(e))
        except Exception as e:
            logger.error(f"❌ Failed to get {token_name} balance for {owner_address}: {e}")
            raise BlockchainServiceException(f"Failed to get {token_name} balance: {e}")
    
    async def get_multiple_erc20_balances(self, token_names: List[str], owner_address: str) -> Dict[str, int]:
        """Get multiple ERC20 token balances in parallel"""
        try:
            logger.info(f"🪙 Fetching balances for tokens {token_names} for {owner_address}")
            
            # Create tasks for parallel execution
            tasks = [self.get_erc20_balance(token_name, owner_address) for token_name in token_names]
            
            # Execute all tasks in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Build response dict
            balances = {}
            for i, token_name in enumerate(token_names):
                if isinstance(results[i], Exception):
                    logger.error(f"❌ Failed to get {token_name} balance: {results[i]}")
                    balances[token_name] = 0
                else:
                    balances[token_name] = results[i]
            
            logger.info(f"✅ Retrieved balances: {balances}")
            return balances
            
        except Exception as e:
            logger.error(f"❌ Failed to get multiple token balances: {e}")
            raise BlockchainServiceException(f"Failed to get multiple token balances: {e}")
    
    # ============================================================================
    # MORALIS HTTP API METHODS (Enriched NFT/Token Data)
    # ============================================================================
    
    async def _make_moralis_request(self, endpoint: str, params: Dict = None) -> Dict:
        """Make HTTP request to Moralis API with error handling"""
        url = f"{self.config.moralis_base_url}{endpoint}"
        headers = self.config.get_moralis_headers()
        
        try:
            # Use asyncio to run requests in thread pool for async compatibility
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: requests.get(url, headers=headers, params=params or {})
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                raise BlockchainServiceException("Moralis rate limit exceeded. Please try again later.")
            elif response.status_code == 401:
                raise BlockchainServiceException("Invalid Moralis API key. Please check your configuration.")
            else:
                raise BlockchainServiceException(f"Moralis API error: {response.status_code} - {response.text}")
                
        except requests.exceptions.RequestException as e:
            raise BlockchainServiceException(f"Network error connecting to Moralis: {str(e)}")
    
    async def get_token_portfolio(self, wallet_address: str, chain: str = "polygon") -> Dict:
        """Get token portfolio with USD pricing via Moralis API"""
        # Validate address
        wallet_address = self._validate_address(wallet_address)
        
        # Check cache first
        cache_key = f"portfolio_{wallet_address.lower()}_{chain}"
        if cache_key in self.token_cache:
            cached_data = self.token_cache[cache_key]
            logger.debug(f"🎯 Token portfolio cache hit for {wallet_address}")
            return cached_data
        
        # Fetch from Moralis API
        endpoint = f"/{wallet_address}/erc20"
        params = {
            "chain": chain,
            "exclude_spam": "true",
            "exclude_unverified_contracts": "true"
        }
        
        try:
            raw_data = await self._make_moralis_request(endpoint, params)
            
            # Process and format the data
            processed_tokens = []
            total_usd_value = 0
            
            # Handle both list and dict responses from Moralis
            token_list = raw_data if isinstance(raw_data, list) else raw_data.get("result", [])
            
            for token in token_list:
                # Calculate USD value if price data is available
                balance_wei = int(token.get("balance", "0"))
                decimals = int(token.get("decimals", 18))
                balance_formatted = balance_wei / (10 ** decimals)
                
                # Get USD price (might require separate API call)
                usd_price = await self._get_token_price_via_moralis(token.get("token_address"), chain)
                usd_value = balance_formatted * usd_price if usd_price else 0
                total_usd_value += usd_value
                
                token_data = {
                    "token_address": token.get("token_address"),
                    "name": token.get("name"),
                    "symbol": token.get("symbol"),
                    "logo": token.get("logo"),
                    "decimals": decimals,
                    "balance_wei": balance_wei,
                    "balance_formatted": balance_formatted,
                    "usd_price": usd_price,
                    "usd_value": usd_value,
                    "percentage_relative_to_total_supply": token.get("percentage_relative_to_total_supply")
                }
                processed_tokens.append(token_data)
            
            result = {
                "wallet_address": wallet_address,
                "chain": chain,
                "total_tokens": len(processed_tokens),
                "total_usd_value": total_usd_value,
                "tokens": processed_tokens,
                "last_updated": datetime.now().isoformat()
            }
            
            # Cache the result
            self.token_cache[cache_key] = result
            
            logger.info(f"✅ Token portfolio for {wallet_address}: {len(processed_tokens)} tokens, ${total_usd_value:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch token portfolio: {e}")
            raise BlockchainServiceException(f"Failed to fetch token portfolio: {e}")
    
    async def _get_token_price_via_moralis(self, token_address: str, chain: str) -> Optional[float]:
        """Get current USD price for a token via Moralis"""
        endpoint = f"/erc20/{token_address}/price"
        params = {"chain": chain}
        
        try:
            price_data = await self._make_moralis_request(endpoint, params)
            return float(price_data.get("usdPrice", 0))
        except:
            # If price fetch fails, return None
            return None
    
    async def get_nft_collections_via_moralis(self, wallet_address: str, chain: str = "polygon") -> Dict:
        """Get NFT collections with metadata via Moralis API"""
        # Validate address
        wallet_address = self._validate_address(wallet_address)
        
        # Check cache first
        cache_key = f"nft_collections_{wallet_address.lower()}_{chain}"
        if cache_key in self.nft_cache:
            cached_data = self.nft_cache[cache_key]
            logger.debug(f"🎯 NFT collections cache hit for {wallet_address}")
            return cached_data
        
        # Fetch from Moralis API
        endpoint = f"/{wallet_address}/nft"
        params = {
            "chain": chain,
            "format": "decimal",
            "exclude_spam": "true",
            "media_items": "true"
        }
        
        try:
            raw_data = await self._make_moralis_request(endpoint, params)
            
            # Process and organize by collections
            collections = {}
            total_nfts = 0
            
            # Handle both list and dict responses from Moralis
            nft_list = raw_data if isinstance(raw_data, list) else raw_data.get("result", [])
            
            for nft in nft_list:
                contract_address = nft.get("token_address")
                
                if contract_address not in collections:
                    collections[contract_address] = {
                        "contract_address": contract_address,
                        "name": nft.get("name"),
                        "symbol": nft.get("symbol"),
                        "contract_type": nft.get("contract_type"),
                        "nfts": [],
                        "total_count": 0
                    }
                
                # Parse metadata if available
                metadata = {}
                if nft.get("metadata"):
                    try:
                        metadata = json.loads(nft.get("metadata"))
                    except:
                        metadata = {}
                
                nft_data = {
                    "token_id": nft.get("token_id"),
                    "token_uri": nft.get("token_uri"),
                    "metadata": metadata,
                    "amount": nft.get("amount"),
                    "owner_of": nft.get("owner_of"),
                    "last_metadata_sync": nft.get("last_metadata_sync"),
                    "last_token_uri_sync": nft.get("last_token_uri_sync"),
                    "image": metadata.get("image") if metadata else None,
                    "name": metadata.get("name") if metadata else f"#{nft.get('token_id')}",
                    "description": metadata.get("description") if metadata else None,
                    "attributes": metadata.get("attributes", []) if metadata else []
                }
                
                collections[contract_address]["nfts"].append(nft_data)
                collections[contract_address]["total_count"] += 1
                total_nfts += 1
            
            result = {
                "wallet_address": wallet_address,
                "chain": chain,
                "total_collections": len(collections),
                "total_nfts": total_nfts,
                "collections": list(collections.values()),
                "last_updated": datetime.now().isoformat()
            }
            
            # Cache the result
            self.nft_cache[cache_key] = result
            
            logger.info(f"✅ NFT collections for {wallet_address}: {len(collections)} collections, {total_nfts} NFTs")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch NFT collections: {e}")
            raise BlockchainServiceException(f"Failed to fetch NFT collections: {e}")
    
    async def refresh_wallet_data(self, wallet_address: str, chain: str = "polygon") -> Dict:
        """Force refresh of wallet data (clear cache and fetch fresh data)"""
        # Validate address
        wallet_address = self._validate_address(wallet_address)
        
        # Clear cache for this wallet
        token_cache_key = f"portfolio_{wallet_address.lower()}_{chain}"
        nft_cache_key = f"nft_collections_{wallet_address.lower()}_{chain}"
        
        if token_cache_key in self.token_cache:
            del self.token_cache[token_cache_key]
        if nft_cache_key in self.nft_cache:
            del self.nft_cache[nft_cache_key]
        
        # Also clear related smart contract caches
        contract_cache_keys = [
            f"tokens_heroes_{wallet_address.lower()}",
            f"tokens_weapons_{wallet_address.lower()}",
            f"erc1155_balances_lands_{wallet_address.lower()}_1,2,3"
        ]
        
        for cache_key in contract_cache_keys:
            if cache_key in self.cache:
                del self.cache[cache_key]
        
        # Fetch fresh data
        try:
            tokens_data = await self.get_token_portfolio(wallet_address, chain)
            nfts_data = await self.get_nft_collections_via_moralis(wallet_address, chain)
            
            return {
                "wallet_address": wallet_address,
                "chain": chain,
                "refresh_timestamp": datetime.now().isoformat(),
                "tokens": tokens_data,
                "nfts": nfts_data,
                "status": "success"
            }
            
        except Exception as e:
            return {
                "wallet_address": wallet_address,
                "chain": chain,
                "refresh_timestamp": datetime.now().isoformat(),
                "error": str(e),
                "status": "failed"
            }
    
    # ============================================================================
    # UTILITY AND STATUS METHODS
    # ============================================================================
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get comprehensive service statistics for monitoring"""
        return {
            "service_name": "UnifiedBlockchainService",
            "configuration": {
                "nft_contracts": len(self.config.nft_contracts),
                "erc20_tokens": len(self.config.erc20_tokens),
                "rpc_endpoints": len(self.config.rpc_endpoints),
                "chain": self.config.chain
            },
            "cache_stats": {
                "unified_cache": {
                    "size": len(self.cache),
                    "maxsize": self.cache.maxsize,
                    "ttl": self.cache.ttl
                },
                "nft_cache": {
                    "size": len(self.nft_cache),
                    "maxsize": self.nft_cache.maxsize,
                    "ttl": self.nft_cache.ttl
                },
                "token_cache": {
                    "size": len(self.token_cache),
                    "maxsize": self.token_cache.maxsize,
                    "ttl": self.token_cache.ttl
                }
            },
            "contracts_loaded": list(self.contracts.keys()),
            "rpc_status": self._get_rpc_status()
        }
    
    def _get_rpc_status(self) -> Dict[str, str]:
        """Get status of all RPC endpoints"""
        status = {}
        for rpc_url in self.config.rpc_endpoints:
            if rpc_url in self.web3_instances:
                try:
                    w3 = self.web3_instances[rpc_url]
                    block_number = w3.eth.block_number
                    status[rpc_url] = f"healthy (block: {block_number})"
                except:
                    status[rpc_url] = "unhealthy"
            else:
                status[rpc_url] = "not_initialized"
        return status
    
    def clear_all_caches(self):
        """Clear all caches for debugging or maintenance"""
        self.cache.clear()
        self.nft_cache.clear()
        self.token_cache.clear()
        logger.info("🧹 All caches cleared")
    
    def get_contract_addresses(self) -> Dict[str, str]:
        """Get all configured contract addresses"""
        return self.config.get_all_contracts()
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check for the service"""
        try:
            # Test Web3 connectivity
            w3 = self._get_working_web3()
            current_block = w3.eth.block_number
            
            # Test Moralis API connectivity
            try:
                headers = self.config.get_moralis_headers()
                moralis_status = "available"
            except:
                moralis_status = "unavailable"
            
            return {
                "status": "healthy",
                "web3": {
                    "status": "connected",
                    "current_block": current_block,
                    "active_rpc": self._get_active_rpc_endpoint()
                },
                "moralis": {
                    "status": moralis_status
                },
                "cache": {
                    "unified_entries": len(self.cache),
                    "nft_entries": len(self.nft_cache),
                    "token_entries": len(self.token_cache)
                },
                "configuration": {
                    "contracts": len(self.config.get_all_contracts()),
                    "chain": self.config.chain
                }
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _get_active_rpc_endpoint(self) -> Optional[str]:
        """Get the currently active RPC endpoint"""
        try:
            for rpc_url in self.config.rpc_endpoints:
                if rpc_url in self.web3_instances:
                    w3 = self.web3_instances[rpc_url]
                    try:
                        w3.eth.block_number
                        return rpc_url
                    except:
                        continue
            return None
        except:
            return None
    
    # ============================================================================
    # CONFIGURATION METHODS
    # ============================================================================
    
    def get_config(self) -> Dict[str, Any]:
        """Get current service configuration"""
        return {
            "rpc_endpoints": self.config.rpc_endpoints,
            "nft_contracts": self.config.nft_contracts,
            "erc20_tokens": self.config.erc20_tokens,
            "chain": self.config.chain,
            "chain_id": self.config.chain_id,
            "cache_config": self.config.cache_config,
            "moralis_configured": bool(self.config.moralis_api_key)
        }
    
    def update_contract_address(self, contract_name: str, new_address: str, contract_type: str = "nft"):
        """Update a contract address (useful for testing or network changes)"""
        try:
            # Validate the new address
            new_address = self._validate_address(new_address)
            
            if contract_type == "nft":
                old_address = self.config.nft_contracts.get(contract_name)
                self.config.nft_contracts[contract_name] = new_address
            else:  # erc20
                old_address = self.config.erc20_tokens.get(contract_name)
                self.config.erc20_tokens[contract_name] = new_address
            
            # Clear related caches and contracts
            cache_key = f"contract_{contract_name}"
            if cache_key in self.contracts:
                del self.contracts[cache_key]
            
            # Clear related cache entries
            cache_keys_to_clear = [key for key in self.cache.keys() if contract_name in key]
            for key in cache_keys_to_clear:
                del self.cache[key]
            
            logger.info(f"✅ Updated {contract_name} address: {old_address} → {new_address}")
            
        except Exception as e:
            logger.error(f"❌ Failed to update contract address: {e}")
            raise BlockchainServiceException(f"Failed to update contract address: {e}")

# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

# Create global instance for use throughout the application
blockchain_service = BlockchainService()

# Convenience functions for backward compatibility
async def get_tokens_of_owner(contract_name: str, abi: List[Dict], owner_address: str) -> List[int]:
    """Backward compatibility wrapper"""
    return await blockchain_service.get_tokens_of_owner(contract_name, abi, owner_address)

async def get_token_attributes(contract_name: str, abi: List[Dict], token_id: int) -> Dict[str, int]:
    """Backward compatibility wrapper"""
    return await blockchain_service.get_token_attributes(contract_name, abi, token_id)

async def get_token_info(contract_name: str, abi: List[Dict], token_id: int) -> Dict[str, Any]:
    """Backward compatibility wrapper"""
    return await blockchain_service.get_token_info(contract_name, abi, token_id)

async def get_erc1155_balances(contract_name: str, owner_address: str, token_ids: List[int]) -> List[int]:
    """Backward compatibility wrapper"""
    return await blockchain_service.get_erc1155_balances(contract_name, owner_address, token_ids)

async def get_erc20_balance(token_name: str, owner_address: str) -> int:
    """Backward compatibility wrapper"""
    return await blockchain_service.get_erc20_balance(token_name, owner_address)

def get_contract_addresses() -> Dict[str, str]:
    """Backward compatibility wrapper"""
    return blockchain_service.get_contract_addresses()

def clear_cache():
    """Backward compatibility wrapper"""
    blockchain_service.clear_all_caches()

def get_cache_stats() -> Dict[str, Any]:
    """Backward compatibility wrapper"""
    return blockchain_service.get_service_stats()

# Exception class for backward compatibility
Web3ServiceException = BlockchainServiceException