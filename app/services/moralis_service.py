# app/services/moralis_service.py
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio
from decimal import Decimal
import logging
import json

from app.config import settings
from app.database import execute_query, execute_command
from app.models.token import TokenBalance, NFTHolding, TokenPortfolio, NFTCollection
from app.models.user import User

# Set up logging
logger = logging.getLogger(__name__)

class MoralisService:
    """Moralis Web3 API service for Polygon blockchain data"""
    
    def __init__(self):
        self.api_key = settings.moralis_api_key
        self.base_url = settings.moralis_base_url
        self.chain = settings.get_moralis_chain_param()
        self.timeout = settings.moralis_timeout
        
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
            "User-Agent": f"{settings.app_name}/{settings.app_version}"
        }
        
        logger.info(f"✅ Moralis service initialized for {self.chain} network")
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make authenticated request to Moralis API"""
        url = f"{self.base_url}{endpoint}"
        
        # Add default chain parameter
        if params is None:
            params = {}
        params["chain"] = self.chain
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.debug(f"Making Moralis API request: {endpoint}")
                
                response = await client.get(
                    url,
                    headers=self.headers,
                    params=params
                )
                
                response.raise_for_status()
                data = response.json()
                
                logger.debug(f"Moralis API response: {response.status_code}")
                return data
                
        except httpx.TimeoutException:
            logger.error(f"Timeout requesting {endpoint}")
            raise Exception("Moralis API timeout")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} for {endpoint}: {e.response.text}")
            raise Exception(f"Moralis API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Unexpected error requesting {endpoint}: {str(e)}")
            raise Exception(f"Moralis API request failed: {str(e)}")

    async def get_token_balance(
        self, 
        user_address: str, 
        token_address: str, 
        force_refresh: bool = False
    ) -> TokenBalance:
        """Get token balance for user with caching"""
        user_address = user_address.lower()
        token_address = token_address.lower()
        
        # Check cache first (unless force refresh)
        if not force_refresh:
            cache_duration = timedelta(minutes=settings.cache_token_balance_minutes)
            cached_balance = await execute_query(
                """SELECT * FROM token_holdings 
                   WHERE user_id = (SELECT id FROM users WHERE wallet_address = $1)
                   AND token_address = $2
                   AND last_updated > $3""",
                user_address,
                token_address,
                datetime.utcnow() - cache_duration
            )
            
            if cached_balance:
                record = cached_balance[0]
                logger.debug(f"Using cached token balance for {token_address}")
                return TokenBalance(
                    id=record["id"],
                    user_id=record["user_id"],
                    token_address=record["token_address"],
                    balance=record["balance"],
                    decimals=record["decimals"],
                    symbol=record["symbol"],
                    name=record["name"],
                    logo_url=record["logo_url"],
                    usd_price=record["usd_price"],
                    usd_value=record["usd_value"],
                    percentage_change_24h=record["percentage_change_24h"],
                    last_updated=record["last_updated"]
                )
        
        # Fetch fresh data from Moralis
        try:
            # Get token balances with metadata and prices
            balance_data = await self._make_request(
                f"/{user_address}/erc20",
                params={"token_addresses": [token_address]}
            )
            
            if not balance_data:
                raise Exception("No token data found")
            
            # Find the specific token in response
            token_data = None
            for token in balance_data:
                if token["token_address"].lower() == token_address:
                    token_data = token
                    break
            
            if not token_data:
                # Token not found in wallet, but get metadata anyway
                token_data = {
                    "token_address": token_address,
                    "balance": "0",
                    "decimals": "18",
                    "symbol": "UNKNOWN",
                    "name": "Unknown Token",
                    "logo": None,
                    "usd_price": None,
                    "usd_value": None,
                    "percentage_change_24h": None
                }
            
            # Extract and process token information
            raw_balance = int(token_data.get("balance", "0"))
            decimals = int(token_data.get("decimals", 18))
            symbol = token_data.get("symbol", "UNKNOWN")
            name = token_data.get("name", "Unknown Token")
            logo_url = token_data.get("logo")
            
            # Moralis provides enriched data with USD pricing
            usd_price = token_data.get("usd_price")
            if usd_price is not None:
                usd_price = Decimal(str(usd_price))
            
            percentage_change_24h = token_data.get("percentage_change_24h")
            if percentage_change_24h is not None:
                percentage_change_24h = Decimal(str(percentage_change_24h))
            
            # Convert balance to decimal representation
            balance = Decimal(raw_balance) / Decimal(10 ** decimals)
            
            # Calculate USD value
            usd_value = None
            if balance and usd_price:
                usd_value = balance * usd_price
            
            # Get user ID and update cache
            user_id_result = await execute_query(
                "SELECT id FROM users WHERE wallet_address = $1",
                user_address
            )
            
            if not user_id_result:
                raise Exception("User not found")
            
            user_id = user_id_result[0]["id"]
            
            # Update cache with enriched data
            await execute_command(
                """INSERT INTO token_holdings 
                   (user_id, token_address, balance, decimals, symbol, name, 
                    logo_url, usd_price, usd_value, percentage_change_24h, last_updated)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                   ON CONFLICT (user_id, token_address)
                   DO UPDATE SET 
                       balance = $3,
                       decimals = $4,
                       symbol = $5,
                       name = $6,
                       logo_url = $7,
                       usd_price = $8,
                       usd_value = $9,
                       percentage_change_24h = $10,
                       last_updated = $11""",
                user_id,
                token_address,
                balance,
                decimals,
                symbol,
                name,
                logo_url,
                usd_price,
                usd_value,
                percentage_change_24h,
                datetime.utcnow()
            )
            
            logger.info(f"✅ Updated token balance for {symbol} ({token_address})")
            
            return TokenBalance(
                user_id=user_id,
                token_address=token_address,
                balance=balance,
                decimals=decimals,
                symbol=symbol,
                name=name,
                logo_url=logo_url,
                usd_price=usd_price,
                usd_value=usd_value,
                percentage_change_24h=percentage_change_24h,
                last_updated=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Failed to fetch token balance for {token_address}: {str(e)}")
            raise Exception(f"Failed to fetch token balance: {str(e)}")

    async def get_user_token_portfolio(
        self, 
        user_address: str, 
        force_refresh: bool = False
    ) -> List[TokenBalance]:
        """Get complete token portfolio with enriched data"""
        user_address = user_address.lower()
        
        # Check cache first
        if not force_refresh:
            cache_duration = timedelta(minutes=settings.cache_token_balance_minutes)
            cached_portfolio = await execute_query(
                """SELECT * FROM token_holdings 
                   WHERE user_id = (SELECT id FROM users WHERE wallet_address = $1)
                   AND last_updated > $2
                   ORDER BY usd_value DESC NULLS LAST""",
                user_address,
                datetime.utcnow() - cache_duration
            )
            
            if cached_portfolio:
                logger.debug(f"Using cached token portfolio for {user_address}")
                return [
                    TokenBalance(
                        id=record["id"],
                        user_id=record["user_id"],
                        token_address=record["token_address"],
                        balance=record["balance"],
                        decimals=record["decimals"],
                        symbol=record["symbol"],
                        name=record["name"],
                        logo_url=record["logo_url"],
                        usd_price=record["usd_price"],
                        usd_value=record["usd_value"],
                        percentage_change_24h=record["percentage_change_24h"],
                        last_updated=record["last_updated"]
                    )
                    for record in cached_portfolio
                ]
        
        # Fetch fresh portfolio from Moralis
        try:
            # Get all ERC20 tokens with enriched data
            portfolio_data = await self._make_request(f"/{user_address}/erc20")
            
            user_id_result = await execute_query(
                "SELECT id FROM users WHERE wallet_address = $1",
                user_address
            )
            
            if not user_id_result:
                raise Exception("User not found")
            
            user_id = user_id_result[0]["id"]
            
            # Clear old cache for this user
            await execute_command(
                "DELETE FROM token_holdings WHERE user_id = $1",
                user_id
            )
            
            portfolio = []
            
            for token_data in portfolio_data:
                try:
                    # Process each token
                    token_address = token_data["token_address"].lower()
                    raw_balance = int(token_data.get("balance", "0"))
                    decimals = int(token_data.get("decimals", 18))
                    symbol = token_data.get("symbol", "UNKNOWN")
                    name = token_data.get("name", "Unknown Token")
                    logo_url = token_data.get("logo")
                    
                    # Skip tokens with zero balance
                    if raw_balance == 0:
                        continue
                    
                    # Convert balance
                    balance = Decimal(raw_balance) / Decimal(10 ** decimals)
                    
                    # Get pricing data (Moralis enriched response)
                    usd_price = token_data.get("usd_price")
                    if usd_price is not None:
                        usd_price = Decimal(str(usd_price))
                    
                    percentage_change_24h = token_data.get("percentage_change_24h")
                    if percentage_change_24h is not None:
                        percentage_change_24h = Decimal(str(percentage_change_24h))
                    
                    # Calculate USD value
                    usd_value = None
                    if balance and usd_price:
                        usd_value = balance * usd_price
                    
                    # Store in cache
                    await execute_command(
                        """INSERT INTO token_holdings 
                           (user_id, token_address, balance, decimals, symbol, name,
                            logo_url, usd_price, usd_value, percentage_change_24h, last_updated)
                           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)""",
                        user_id,
                        token_address,
                        balance,
                        decimals,
                        symbol,
                        name,
                        logo_url,
                        usd_price,
                        usd_value,
                        percentage_change_24h,
                        datetime.utcnow()
                    )
                    
                    portfolio.append(TokenBalance(
                        user_id=user_id,
                        token_address=token_address,
                        balance=balance,
                        decimals=decimals,
                        symbol=symbol,
                        name=name,
                        logo_url=logo_url,
                        usd_price=usd_price,
                        usd_value=usd_value,
                        percentage_change_24h=percentage_change_24h,
                        last_updated=datetime.utcnow()
                    ))
                    
                except Exception as token_error:
                    logger.warning(f"Failed to process token {token_data.get('token_address', 'unknown')}: {token_error}")
                    continue
            
            # Sort by USD value (highest first)
            portfolio.sort(key=lambda x: x.usd_value or Decimal('0'), reverse=True)
            
            logger.info(f"✅ Updated token portfolio for {user_address}: {len(portfolio)} tokens")
            return portfolio
            
        except Exception as e:
            logger.error(f"Failed to fetch token portfolio for {user_address}: {str(e)}")
            raise Exception(f"Failed to fetch token portfolio: {str(e)}")

    async def get_user_nfts(
        self, 
        user_address: str, 
        force_refresh: bool = False
    ) -> List[NFTHolding]:
        """Get NFT holdings with enriched metadata"""
        user_address = user_address.lower()
        
        # Check cache first
        if not force_refresh:
            cache_duration = timedelta(minutes=settings.cache_nft_data_minutes)
            cached_nfts = await execute_query(
                """SELECT * FROM nft_holdings 
                   WHERE user_id = (SELECT id FROM users WHERE wallet_address = $1)
                   AND last_updated > $2
                   ORDER BY last_updated DESC""",
                user_address,
                datetime.utcnow() - cache_duration
            )
            
            if cached_nfts:
                logger.debug(f"Using cached NFT collection for {user_address}")
                return [
                    NFTHolding(
                        id=record["id"],
                        user_id=record["user_id"],
                        contract_address=record["contract_address"],
                        token_id=record["token_id"],
                        name=record["name"],
                        description=record["description"],
                        image_url=record["image_url"],
                        collection_name=record["collection_name"],
                        floor_price=record["floor_price"],
                        last_sale_price=record["last_sale_price"],
                        rarity_rank=record["rarity_rank"],
                        metadata=record["metadata"],
                        last_updated=record["last_updated"]
                    )
                    for record in cached_nfts
                ]
        
        # Fetch fresh NFT data from Moralis
        try:
            # Get NFTs with enriched metadata
            nft_data = await self._make_request(
                f"/{user_address}/nft",
                params={
                    "format": "decimal",
                    "normalizeMetadata": True,
                    "media_items": False  # Reduce response size
                }
            )
            
            user_id_result = await execute_query(
                "SELECT id FROM users WHERE wallet_address = $1",
                user_address
            )
            
            if not user_id_result:
                raise Exception("User not found")
            
            user_id = user_id_result[0]["id"]
            
            # Clear old cache
            await execute_command(
                "DELETE FROM nft_holdings WHERE user_id = $1",
                user_id
            )
            
            nft_holdings = []
            
            for nft in nft_data.get("result", []):
                try:
                    contract_address = nft["token_address"].lower()
                    token_id = nft["token_id"]
                    
                    # Extract normalized metadata (Moralis enriched data)
                    normalized = nft.get("normalized_metadata", {})
                    metadata = nft.get("metadata", {})
                    
                    name = normalized.get("name") or metadata.get("name") or f"NFT #{token_id}"
                    description = normalized.get("description") or metadata.get("description") or ""
                    image_url = normalized.get("image") or metadata.get("image") or ""
                    
                    # Collection information
                    collection_name = nft.get("name")  # Contract name
                    
                    # Additional enriched data (if available from Moralis)
                    floor_price = nft.get("floor_price")
                    if floor_price:
                        floor_price = Decimal(str(floor_price))
                    
                    last_sale_price = nft.get("last_sale", {}).get("price")
                    if last_sale_price:
                        last_sale_price = Decimal(str(last_sale_price))
                    
                    rarity_rank = nft.get("rarity_rank")
                    
                    # Combine all metadata
                    full_metadata = {
                        **metadata,
                        "normalized": normalized,
                        "attributes": normalized.get("attributes", [])
                    }
                    
                    # Store in cache
                    await execute_command(
                        """INSERT INTO nft_holdings 
                           (user_id, contract_address, token_id, name, description, image_url,
                            collection_name, floor_price, last_sale_price, rarity_rank, metadata, last_updated)
                           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)""",
                        user_id,
                        contract_address,
                        token_id,
                        name,
                        description,
                        image_url,
                        collection_name,
                        floor_price,
                        last_sale_price,
                        rarity_rank,
                        full_metadata,
                        datetime.utcnow()
                    )
                    
                    nft_holdings.append(NFTHolding(
                        user_id=user_id,
                        contract_address=contract_address,
                        token_id=token_id,
                        name=name,
                        description=description,
                        image_url=image_url,
                        collection_name=collection_name,
                        floor_price=floor_price,
                        last_sale_price=last_sale_price,
                        rarity_rank=rarity_rank,
                        metadata=full_metadata,
                        last_updated=datetime.utcnow()
                    ))
                    
                except Exception as nft_error:
                    logger.warning(f"Failed to process NFT {nft.get('token_id', 'unknown')}: {nft_error}")
                    continue
            
            logger.info(f"✅ Updated NFT collection for {user_address}: {len(nft_holdings)} NFTs")
            return nft_holdings
            
        except Exception as e:
            logger.error(f"Failed to fetch NFTs for {user_address}: {str(e)}")
            raise Exception(f"Failed to fetch NFTs: {str(e)}")

    async def refresh_user_data(self, user_address: str):
        """Background task to refresh all user's Web3 data"""
        try:
            logger.info(f"🔄 Starting data refresh for {user_address}")
            
            # Refresh token portfolio
            await self.get_user_token_portfolio(user_address, force_refresh=True)
            
            # Refresh NFT collection
            await self.get_user_nfts(user_address, force_refresh=True)
            
            # Update wallet analytics
            await self._update_wallet_analytics(user_address)
            
            # Log activity
            await self._log_user_activity(
                user_address, 
                "data_refresh", 
                {"timestamp": datetime.utcnow().isoformat()}
            )
            
            logger.info(f"✅ Data refresh completed for {user_address}")
            
        except Exception as e:
            logger.error(f"❌ Data refresh failed for {user_address}: {str(e)}")

    async def get_user_analytics(self, user_address: str) -> Dict[str, Any]:
        """Get comprehensive analytics for user"""
        user_address = user_address.lower()
        
        try:
            # Get token statistics
            token_stats = await execute_query(
                """SELECT COUNT(*) as token_count, 
                          COALESCE(SUM(usd_value), 0) as total_usd_value,
                          COALESCE(AVG(usd_value), 0) as avg_token_value
                   FROM token_holdings 
                   WHERE user_id = (SELECT id FROM users WHERE wallet_address = $1)""",
                user_address
            )
            
            # Get NFT statistics
            nft_stats = await execute_query(
                """SELECT COUNT(*) as nft_count,
                          COUNT(DISTINCT collection_name) as unique_collections,
                          COALESCE(SUM(floor_price), 0) as total_floor_value
                   FROM nft_holdings 
                   WHERE user_id = (SELECT id FROM users WHERE wallet_address = $1)""",
                user_address
            )
            
            # Get activity statistics
            activity_stats = await execute_query(
                """SELECT COUNT(*) as activity_count,
                          COUNT(DISTINCT action) as unique_actions
                   FROM user_activities 
                   WHERE user_id = (SELECT id FROM users WHERE wallet_address = $1)
                   AND timestamp > $2""",
                user_address,
                datetime.utcnow() - timedelta(days=30)
            )
            
            # Get top tokens by value
            top_tokens = await execute_query(
                """SELECT symbol, name, usd_value 
                   FROM token_holdings 
                   WHERE user_id = (SELECT id FROM users WHERE wallet_address = $1)
                   AND usd_value > 0
                   ORDER BY usd_value DESC 
                   LIMIT 5""",
                user_address
            )
            
            return {
                "user_address": user_address,
                "tokens": {
                    "count": token_stats[0]["token_count"] if token_stats else 0,
                    "total_usd_value": float(token_stats[0]["total_usd_value"]) if token_stats else 0,
                    "average_value": float(token_stats[0]["avg_token_value"]) if token_stats else 0,
                    "top_holdings": [
                        {
                            "symbol": token["symbol"],
                            "name": token["name"],
                            "usd_value": float(token["usd_value"])
                        }
                        for token in top_tokens
                    ]
                },
                "nfts": {
                    "count": nft_stats[0]["nft_count"] if nft_stats else 0,
                    "unique_collections": nft_stats[0]["unique_collections"] if nft_stats else 0,
                    "total_floor_value": float(nft_stats[0]["total_floor_value"]) if nft_stats else 0
                },
                "activity": {
                    "recent_actions": activity_stats[0]["activity_count"] if activity_stats else 0,
                    "unique_action_types": activity_stats[0]["unique_actions"] if activity_stats else 0
                },
                "blockchain": self.chain,
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get user analytics for {user_address}: {str(e)}")
            raise Exception(f"Failed to get user analytics: {str(e)}")

    async def get_system_analytics(self) -> Dict[str, Any]:
        """Get system-wide analytics"""
        try:
            # Total users and wallets
            user_stats = await execute_query("SELECT COUNT(*) as count FROM users")
            
            # Active users (last 7 days)
            active_users = await execute_query(
                """SELECT COUNT(DISTINCT user_id) as count FROM user_activities 
                   WHERE timestamp > $1""",
                datetime.utcnow() - timedelta(days=7)
            )
            
            # Token statistics
            token_stats = await execute_query(
                """SELECT COUNT(DISTINCT token_address) as unique_tokens,
                          COALESCE(SUM(usd_value), 0) as total_value
                   FROM token_holdings"""
            )
            
            # NFT statistics
            nft_stats = await execute_query(
                """SELECT COUNT(*) as total_nfts,
                          COUNT(DISTINCT collection_name) as unique_collections
                   FROM nft_holdings"""
            )
            
            # Recent activity
            recent_activity = await execute_query(
                """SELECT action, COUNT(*) as count 
                   FROM user_activities 
                   WHERE timestamp > $1 
                   GROUP BY action 
                   ORDER BY count DESC 
                   LIMIT 10""",
                datetime.utcnow() - timedelta(days=1)
            )
            
            return {
                "users": {
                    "total": user_stats[0]["count"] if user_stats else 0,
                    "active_7_days": active_users[0]["count"] if active_users else 0
                },
                "tokens": {
                    "unique_contracts": token_stats[0]["unique_tokens"] if token_stats else 0,
                    "total_portfolio_value": float(token_stats[0]["total_value"]) if token_stats else 0
                },
                "nfts": {
                    "total_holdings": nft_stats[0]["total_nfts"] if nft_stats else 0,
                    "unique_collections": nft_stats[0]["unique_collections"] if nft_stats else 0
                },
                "activity": {
                    "recent_actions": [
                        {"action": activity["action"], "count": activity["count"]}
                        for activity in recent_activity
                    ]
                },
                "blockchain": self.chain,
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get system analytics: {str(e)}")
            raise Exception(f"Failed to get system analytics: {str(e)}")

    async def _update_wallet_analytics(self, user_address: str):
        """Update wallet analytics table"""
        try:
            user_id_result = await execute_query(
                "SELECT id FROM users WHERE wallet_address = $1",
                user_address.lower()
            )
            
            if not user_id_result:
                return
            
            user_id = user_id_result[0]["id"]
            
            # Calculate current statistics
            token_stats = await execute_query(
                """SELECT COUNT(*) as token_count, COALESCE(SUM(usd_value), 0) as total_value
                   FROM token_holdings WHERE user_id = $1""",
                user_id
            )
            
            nft_stats = await execute_query(
                """SELECT COUNT(*) as nft_count FROM nft_holdings WHERE user_id = $1""",
                user_id
            )
            
            # Update or insert analytics
            await execute_command(
                """INSERT INTO wallet_analytics 
                   (user_id, wallet_address, total_tokens, total_nfts, total_usd_value, updated_at)
                   VALUES ($1, $2, $3, $4, $5, $6)
                   ON CONFLICT (user_id, wallet_address)
                   DO UPDATE SET 
                       total_tokens = $3,
                       total_nfts = $4,
                       total_usd_value = $5,
                       updated_at = $6""",
                user_id,
                user_address.lower(),
                token_stats[0]["token_count"] if token_stats else 0,
                nft_stats[0]["nft_count"] if nft_stats else 0,
                token_stats[0]["total_value"] if token_stats else 0,
                datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Failed to update wallet analytics: {str(e)}")

    async def _log_user_activity(
        self, 
        user_address: str, 
        action: str, 
        metadata: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Log user activity"""
        try:
            user_id_result = await execute_query(
                "SELECT id FROM users WHERE wallet_address = $1",
                user_address.lower()
            )
            
            if user_id_result:
                await execute_command(
                    """INSERT INTO user_activities 
                       (user_id, action, metadata, ip_address, user_agent, timestamp)
                       VALUES ($1, $2, $3, $4, $5, $6)""",
                    user_id_result[0]["id"],
                    action,
                    metadata,
                    ip_address,
                    user_agent,
                    datetime.utcnow()
                )
        except Exception as e:
            logger.error(f"Failed to log user activity: {str(e)}")
 
