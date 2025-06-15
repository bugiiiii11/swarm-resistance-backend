# app/models/user.py
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, Dict, Any
from datetime import datetime
import uuid
import re

class UserBase(BaseModel):
    """Base user model with common fields"""
    wallet_address: str
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    
    @validator('wallet_address')
    def validate_wallet_address(cls, v):
        """Validate Ethereum wallet address format"""
        if not v:
            raise ValueError('Wallet address is required')
        
        # Remove any whitespace
        v = v.strip()
        
        # Check if it's a valid Ethereum address format
        if not re.match(r'^0x[a-fA-F0-9]{40}$', v):
            raise ValueError('Invalid wallet address format')
        
        # Convert to lowercase for consistency
        return v.lower()
    
    @validator('username')
    def validate_username(cls, v):
        """Validate username format"""
        if v is not None:
            v = v.strip()
            if len(v) < 3:
                raise ValueError('Username must be at least 3 characters long')
            if len(v) > 50:
                raise ValueError('Username must be less than 50 characters')
            if not re.match(r'^[a-zA-Z0-9_-]+$', v):
                raise ValueError('Username can only contain letters, numbers, hyphens, and underscores')
        return v

class UserCreate(UserBase):
    """Model for creating a new user"""
    web3auth_token: str
    
    @validator('web3auth_token')
    def validate_web3auth_token(cls, v):
        """Validate Web3Auth token is present"""
        if not v or not v.strip():
            raise ValueError('Web3Auth token is required')
        return v.strip()

class UserUpdate(BaseModel):
    """Model for updating user profile"""
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    
    @validator('username')
    def validate_username(cls, v):
        """Validate username format"""
        if v is not None:
            v = v.strip()
            if len(v) < 3:
                raise ValueError('Username must be at least 3 characters long')
            if len(v) > 50:
                raise ValueError('Username must be less than 50 characters')
            if not re.match(r'^[a-zA-Z0-9_-]+$', v):
                raise ValueError('Username can only contain letters, numbers, hyphens, and underscores')
        return v

class UserProfile(UserBase):
    """Complete user profile model"""
    id: uuid.UUID
    web3auth_user_id: Optional[str] = None
    is_admin: bool = False
    is_active: bool = True
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            uuid.UUID: lambda v: str(v)
        }

class User(UserProfile):
    """Main user model for internal use"""
    pass

class UserPublic(BaseModel):
    """Public user model (limited fields for public display)"""
    id: str
    username: Optional[str] = None
    wallet_address: str
    created_at: datetime
    
    @validator('id', pre=True)
    def convert_uuid_to_string(cls, v):
        """Convert UUID to string for JSON serialization"""
        if isinstance(v, uuid.UUID):
            return str(v)
        return v
    
    @validator('wallet_address')
    def truncate_wallet_address(cls, v):
        """Truncate wallet address for public display"""
        if len(v) > 10:
            return f"{v[:6]}...{v[-4:]}"
        return v
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class UserStats(BaseModel):
    """User statistics model"""
    user_id: str
    total_tokens: int = 0
    total_nfts: int = 0
    total_usd_value: float = 0.0
    transaction_count: int = 0
    first_transaction_date: Optional[datetime] = None
    last_transaction_date: Optional[datetime] = None
    last_updated: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class UserActivity(BaseModel):
    """User activity model for logging"""
    id: Optional[uuid.UUID] = None
    user_id: uuid.UUID
    action: str
    description: Optional[str] = None
    metadata: Dict[str, Any] = {}
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime
    
    @validator('action')
    def validate_action(cls, v):
        """Validate action string"""
        allowed_actions = [
            'login', 'logout', 'profile_update', 'token_balance_check',
            'nft_view', 'portfolio_view', 'data_refresh', 'admin_action'
        ]
        if v not in allowed_actions:
            # Allow custom actions but log them
            pass
        return v
    
    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            uuid.UUID: lambda v: str(v)
        }

class LoginRequest(BaseModel):
    """Login request model"""
    web3auth_token: str
    wallet_address: Optional[str] = None
    
    @validator('web3auth_token')
    def validate_token(cls, v):
        if not v or not v.strip():
            raise ValueError('Web3Auth token is required')
        return v.strip()

class LoginResponse(BaseModel):
    """Login response model"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserProfile
    message: str = "Login successful"
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            uuid.UUID: lambda v: str(v)
        }

class TokenVerificationResult(BaseModel):
    """Web3Auth token verification result"""
    user_id: str
    wallet_address: str
    email: Optional[str] = None
    name: Optional[str] = None
    provider: Optional[str] = None
    verified: bool = True
    
    @validator('wallet_address')
    def validate_and_normalize_address(cls, v):
        """Validate and normalize wallet address"""
        if not v:
            raise ValueError('Wallet address is required')
        
        v = v.strip().lower()
        if not re.match(r'^0x[a-fA-F0-9]{40}$', v):
            raise ValueError('Invalid wallet address format')
        
        return v

class UserListResponse(BaseModel):
    """Response model for user listing"""
    users: list[UserPublic]
    total: int
    page: int
    size: int
    has_next: bool
    has_previous: bool

class UserSearchRequest(BaseModel):
    """User search request model"""
    query: Optional[str] = None
    wallet_address: Optional[str] = None
    email: Optional[str] = None
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    
    @validator('wallet_address')
    def validate_wallet_search(cls, v):
        if v:
            v = v.strip().lower()
            # Allow partial wallet addresses for search
            if not re.match(r'^0x[a-fA-F0-9]*$', v):
                raise ValueError('Invalid wallet address format for search')
        return v

# Admin-specific models
class AdminUserUpdate(UserUpdate):
    """Admin user update model with additional fields"""
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None

class UserAnalytics(BaseModel):
    """User analytics model"""
    total_users: int
    active_users_24h: int
    active_users_7d: int
    active_users_30d: int
    new_users_24h: int
    new_users_7d: int
    new_users_30d: int
    top_activities: list[Dict[str, Any]]
    user_growth_trend: list[Dict[str, Any]]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
 
