# app/models/token.py
from pydantic import BaseModel, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
from decimal import Decimal
import re

class TokenBase(BaseModel):
    """Base token model"""
    token_address: str
    symbol: Optional[str] = None
    name: Optional[str] = None
    decimals: int = 18
    
    @validator('token_address')
    def validate_token_address(cls, v):
        """Validate token contract address"""
        if not v:
            raise ValueError('Token address is required')
        
        v = v.strip().lower()
        if not re.match(r'^0x[a-fA-F0-9]{40}$', v):
            raise ValueError('Invalid token address format')
        
        return v
    
    @validator('decimals')
    def validate_decimals(cls, v):
        """Validate token decimals"""
        if v < 0 or v > 77:  # ERC20 standard allows up to 77 decimals
            raise ValueError('Token decimals must be between 0 and 77')
        return v

class TokenBalance(TokenBase):
    """Token balance model with pricing data"""
    id: Optional[uuid.UUID] = None
    user_id: uuid.UUID
    balance: Decimal
    logo_url: Optional[str] = None
    usd_price: Optional[Decimal] = None
    usd_value: Optional[Decimal] = None
    percentage_change_24h: Optional[Decimal] = None
    last_updated: datetime
    
    @validator('balance')
    def validate_balance(cls, v):
        """Validate balance is non-negative"""
        if v < 0:
            raise ValueError('Balance cannot be negative')
        return v
    
    @validator('usd_price')
    def validate_usd_price(cls, v):
        """Validate USD price is non-negative"""
        if v is not None and v < 0:
            raise ValueError('USD price cannot be negative')
        return v
    
    def calculate_usd_value(self) -> Optional[Decimal]:
        """Calculate USD value from balance and price"""
        if self.balance and self.usd_price:
            return self.balance * self.usd_price
        return None
    
    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            uuid.UUID: lambda v: str(v),
            Decimal: lambda v: float(v)
        }

class TokenPortfolio(BaseModel):
    """Complete token portfolio for a user"""
    user_address: str
    tokens: List[TokenBalance]
    total_usd_value: Decimal = Decimal('0')
    total_tokens: int = 0
    last_updated: datetime
    blockchain: str = "polygon"
    
    def calculate_totals(self):
        """Calculate portfolio totals"""
        self.total_tokens = len(self.tokens)
        self.total_usd_value = sum(
            (token.usd_value or Decimal('0')) for token in self.tokens
        )
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }

class NFTAttribute(BaseModel):
    """NFT attribute model"""
    trait_type: str
    value: Any
    display_type: Optional[str] = None
    rarity: Optional[float] = None

class NFTBase(BaseModel):
    """Base NFT model"""
    contract_address: str
    token_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    
    @validator('contract_address')
    def validate_contract_address(cls, v):
        """Validate NFT contract address"""
        if not v:
            raise ValueError('Contract address is required')
        
        v = v.strip().lower()
        if not re.match(r'^0x[a-fA-F0-9]{40}$', v):
            raise ValueError('Invalid contract address format')
        
        return v
    
    @validator('token_id')
    def validate_token_id(cls, v):
        """Validate token ID"""
        if not v:
            raise ValueError('Token ID is required')
        return str(v).strip()

class NFTHolding(NFTBase):
    """NFT holding model with enriched metadata"""
    id: Optional[uuid.UUID] = None
    user_id: uuid.UUID
    collection_name: Optional[str] = None
    attributes: List[NFTAttribute] = []
    floor_price: Optional[Decimal] = None
    last_sale_price: Optional[Decimal] = None
    rarity_rank: Optional[int] = None
    metadata: Dict[str, Any] = {}
    last_updated: datetime
    
    @validator('floor_price', 'last_sale_price')
    def validate_prices(cls, v):
        """Validate prices are non-negative"""
        if v is not None and v < 0:
            raise ValueError('Price cannot be negative')
        return v
    
    @validator('rarity_rank')
    def validate_rarity_rank(cls, v):
        """Validate rarity rank is positive"""
        if v is not None and v <= 0:
            raise ValueError('Rarity rank must be positive')
        return v
    
    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            uuid.UUID: lambda v: str(v),
            Decimal: lambda v: float(v)
        }

class NFTCollection(BaseModel):
    """NFT collection model"""
    user_address: str
    nfts: List[NFTHolding]
    total_nfts: int = 0
    collections: Dict[str, int] = {}  # collection_name -> count
    total_floor_value: Optional[Decimal] = None
    last_updated: datetime
    blockchain: str = "polygon"
    
    def calculate_stats(self):
        """Calculate collection statistics"""
        self.total_nfts = len(self.nfts)
        
        # Group by collection
        collection_counts = {}
        total_floor = Decimal('0')
        
        for nft in self.nfts:
            # Count by collection
            collection = nft.collection_name or "Unknown"
            collection_counts[collection] = collection_counts.get(collection, 0) + 1
            
            # Sum floor prices
            if nft.floor_price:
                total_floor += nft.floor_price
        
        self.collections = collection_counts
        self.total_floor_value = total_floor if total_floor > 0 else None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }

class TokenTransfer(BaseModel):
    """Token transfer model"""
    transaction_hash: str
    from_address: str
    to_address: str
    token_address: str
    value: Decimal
    timestamp: datetime
    block_number: int
    gas_used: Optional[int] = None
    gas_price: Optional[Decimal] = None
    
    @validator('transaction_hash')
    def validate_tx_hash(cls, v):
        """Validate transaction hash format"""
        if not re.match(r'^0x[a-fA-F0-9]{64}$', v):
            raise ValueError('Invalid transaction hash format')
        return v.lower()
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }

class WalletAnalytics(BaseModel):
    """Wallet analytics model"""
    user_id: str
    wallet_address: str
    total_tokens: int = 0
    total_nfts: int = 0
    total_usd_value: Decimal = Decimal('0')
    transaction_count: int = 0
    first_transaction_date: Optional[datetime] = None
    last_transaction_date: Optional[datetime] = None
    top_tokens: List[TokenBalance] = []
    top_collections: List[str] = []
    activity_score: float = 0.0
    updated_at: datetime
    
    def calculate_activity_score(self):
        """Calculate wallet activity score based on various factors"""
        score = 0.0
        
        # Token diversity (max 30 points)
        score += min(self.total_tokens * 2, 30)
        
        # NFT diversity (max 20 points)  
        score += min(self.total_nfts * 1, 20)
        
        # Portfolio value (max 30 points)
        if self.total_usd_value > 0:
            # Logarithmic scale for portfolio value
            import math
            value_score = min(math.log10(float(self.total_usd_value)) * 5, 30)
            score += max(value_score, 0)
        
        # Transaction frequency (max 20 points)
        if self.transaction_count > 0:
            tx_score = min(self.transaction_count / 10, 20)
            score += tx_score
        
        self.activity_score = min(score, 100.0)
        return self.activity_score
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }

# Request/Response models for API endpoints
class TokenBalanceRequest(BaseModel):
    """Request model for token balance lookup"""
    token_address: str
    force_refresh: bool = False
    
    @validator('token_address')
    def validate_address(cls, v):
        v = v.strip().lower()
        if not re.match(r'^0x[a-fA-F0-9]{40}$', v):
            raise ValueError('Invalid token address format')
        return v

class TokenPortfolioResponse(BaseModel):
    """Response model for token portfolio"""
    user_address: str
    portfolio: List[TokenBalance]
    total_tokens: int
    total_usd_value: float
    blockchain: str
    last_updated: str
    cache_age_minutes: int = 0

class NFTCollectionResponse(BaseModel):
    """Response model for NFT collection"""
    user_address: str
    nfts: List[NFTHolding]
    total_nfts: int
    collections: Dict[str, int]
    total_floor_value: Optional[float] = None
    blockchain: str
    last_updated: str
    cache_age_minutes: int = 0

class RefreshRequest(BaseModel):
    """Request model for data refresh"""
    force_refresh: bool = True
    refresh_tokens: bool = True
    refresh_nfts: bool = True
    refresh_analytics: bool = True

class RefreshResponse(BaseModel):
    """Response model for data refresh"""
    message: str
    user_address: str
    refreshed_tokens: int = 0
    refreshed_nfts: int = 0
    timestamp: str
    estimated_completion: str  # How long the refresh might take

# Analytics models
class TokenAnalytics(BaseModel):
    """Token analytics model"""
    total_unique_tokens: int
    most_held_tokens: List[Dict[str, Any]]
    average_portfolio_value: float
    median_portfolio_value: float
    top_value_wallets: List[Dict[str, Any]]
    
class NFTAnalytics(BaseModel):
    """NFT analytics model"""
    total_unique_collections: int
    most_popular_collections: List[Dict[str, Any]]
    average_nft_count: float
    rarest_nfts: List[Dict[str, Any]]
    
class SystemAnalytics(BaseModel):
    """System-wide analytics model"""
    total_users: int
    total_wallets_tracked: int
    total_tokens_tracked: int
    total_nfts_tracked: int
    total_portfolio_value: float
    most_active_users: List[Dict[str, Any]]
    recent_activity: List[Dict[str, Any]]
    cache_hit_rate: float
    avg_response_time_ms: float
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
 
