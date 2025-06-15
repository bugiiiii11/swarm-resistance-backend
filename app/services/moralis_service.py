"""
Moralis Web3 Service - HTTP API Implementation
Replaces the problematic Moralis Python package with direct HTTP calls
"""

import requests
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import os
from app.config import settings

class MoralisService:
    def __init__(self):
        self.api_key = os.getenv("MORALIS_API_KEY")
        if not self.api_key:
            raise ValueError("MORALIS_API_KEY environment variable is required")
        
        self.base_url = "https://deep-index.moralis.io/api/v2.2"
        self.headers = {
            "X-API-Key": self.api_key,
            "Accept": "application/json"
        }
        
        # Cache settings
        self.token_cache = {}
        self.nft_cache = {}
        self.cache_duration_tokens = 300  # 5 minutes
        self.cache_duration_nfts = 3600   # 1 hour

    def _is_cache_valid(self, cache_entry: Dict, duration: int) -> bool:
        """Check if cache entry is still valid"""
        if not cache_entry:
            return False
        
        cache_time = cache_entry.get("cached_at")
        if not cache_time:
            return False
            
        return datetime.now() - cache_time < timedelta(seconds=duration)

    async def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """Make HTTP request to Moralis API with error handling"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            # Use asyncio to run requests in thread pool for async compatibility
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: requests.get(url, headers=self.headers, params=params or {})
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                raise Exception("Rate limit exceeded. Please try again later.")
            elif response.status_code == 401:
                raise Exception("Invalid API key. Please check your Moralis API key.")
            else:
                raise Exception(f"Moralis API error: {response.status_code} - {response.text}")
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error connecting to Moralis: {str(e)}")

    async def get_token_balances(self, wallet_address: str, chain: str = "polygon") -> Dict:
        """
        Get token balances for a wallet address with USD pricing
        GET /api/tokens/portfolio endpoint implementation
        """
        # Check cache first
        cache_key = f"{wallet_address}_{chain}_tokens"
        if cache_key in self.token_cache:
            cached_data = self.token_cache[cache_key]
            if self._is_cache_valid(cached_data, self.cache_duration_tokens):
                return cached_data["data"]

        # Fetch from Moralis API
        endpoint = f"/{wallet_address}/erc20"
        params = {
            "chain": chain,
            "exclude_spam": "true",
            "exclude_unverified_contracts": "true"
        }
        
        try:
            raw_data = await self._make_request(endpoint, params)
            
            # Debug: Log the response structure
            logger.info(f"Moralis API response type: {type(raw_data)}")
            logger.info(f"Moralis API response keys: {list(raw_data.keys()) if isinstance(raw_data, dict) else 'List response'}")
            
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
                
                # Get USD price (this might require separate API call)
                usd_price = await self._get_token_price(token.get("token_address"), chain)
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
            self.token_cache[cache_key] = {
                "data": result,
                "cached_at": datetime.now()
            }
            
            return result
            
        except Exception as e:
            raise Exception(f"Failed to fetch token balances: {str(e)}")

    async def _get_token_price(self, token_address: str, chain: str) -> Optional[float]:
        """Get current USD price for a token"""
        endpoint = f"/erc20/{token_address}/price"
        params = {"chain": chain}
        
        try:
            price_data = await self._make_request(endpoint, params)
            return float(price_data.get("usdPrice", 0))
        except:
            # If price fetch fails, return None
            return None

    async def get_nft_collections(self, wallet_address: str, chain: str = "polygon") -> Dict:
        """
        Get NFT collections for a wallet address with metadata
        GET /api/nfts/{address} endpoint implementation
        """
        # Check cache first
        cache_key = f"{wallet_address}_{chain}_nfts"
        if cache_key in self.nft_cache:
            cached_data = self.nft_cache[cache_key]
            if self._is_cache_valid(cached_data, self.cache_duration_nfts):
                return cached_data["data"]

        # Fetch from Moralis API
        endpoint = f"/{wallet_address}/nft"
        params = {
            "chain": chain,
            "format": "decimal",
            "exclude_spam": "true",
            "media_items": "true"
        }
        
        try:
            raw_data = await self._make_request(endpoint, params)
            
            # Debug: Log the response structure  
            logger.info(f"Moralis NFT API response type: {type(raw_data)}")
            logger.info(f"Moralis NFT API response keys: {list(raw_data.keys()) if isinstance(raw_data, dict) else 'List response'}")
            
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
            self.nft_cache[cache_key] = {
                "data": result,
                "cached_at": datetime.now()
            }
            
            return result
            
        except Exception as e:
            raise Exception(f"Failed to fetch NFT collections: {str(e)}")

    async def refresh_wallet_data(self, wallet_address: str, chain: str = "polygon") -> Dict:
        """
        Force refresh of wallet data (clear cache and fetch fresh data)
        POST /api/web3/refresh endpoint implementation
        """
        # Clear cache for this wallet
        token_cache_key = f"{wallet_address}_{chain}_tokens"
        nft_cache_key = f"{wallet_address}_{chain}_nfts"
        
        if token_cache_key in self.token_cache:
            del self.token_cache[token_cache_key]
        if nft_cache_key in self.nft_cache:
            del self.nft_cache[nft_cache_key]
        
        # Fetch fresh data
        try:
            tokens_data = await self.get_token_balances(wallet_address, chain)
            nfts_data = await self.get_nft_collections(wallet_address, chain)
            
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

    def clear_all_cache(self):
        """Clear all cached data"""
        self.token_cache.clear()
        self.nft_cache.clear()

    def get_cache_stats(self) -> Dict:
        """Get cache statistics for monitoring"""
        return {
            "token_cache_entries": len(self.token_cache),
            "nft_cache_entries": len(self.nft_cache),
            "token_cache_duration": self.cache_duration_tokens,
            "nft_cache_duration": self.cache_duration_nfts
        }

# Singleton instance
moralis_service = MoralisService()