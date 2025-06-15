# app/config.py
from pydantic_settings import BaseSettings
from typing import Optional, List
import os

class Settings(BaseSettings):
    # Database Configuration (Supabase)
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_key: str = os.getenv("SUPABASE_KEY", "")
    database_url: str = os.getenv("DATABASE_URL", "")
    
    # Web3 Services Configuration (Moralis)
    moralis_api_key: str = os.getenv("MORALIS_API_KEY", "")
    blockchain_network: str = os.getenv("BLOCKCHAIN_NETWORK", "polygon")
    
    # Supported chains for Moralis
    supported_chains: dict = {
        "polygon": "0x89",
        "ethereum": "0x1",
        "mumbai": "0x13881",  # Polygon testnet
        "sepolia": "0xaa36a7"  # Ethereum testnet
    }
    
    # JWT Settings
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 1 week
    
    # App Settings
    app_name: str = "Swarm Resistance API"
    app_version: str = "1.0.0"
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"
    environment: str = os.getenv("ENVIRONMENT", "development")
    
    # CORS Settings
    allowed_origins: List[str] = [
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    
    # Production origins (add your deployed frontend URL)
    def get_allowed_origins(self) -> List[str]:
        origins = self.allowed_origins.copy()
        
        # Add production origins from environment
        production_origin = os.getenv("FRONTEND_URL")
        if production_origin:
            origins.append(production_origin)
            
        return origins
    
    # Rate Limiting
    rate_limit_requests: int = 100  # requests per minute
    rate_limit_window: int = 60     # window in seconds
    
    # Cache Settings
    cache_token_balance_minutes: int = 5    # Token balance cache duration
    cache_nft_data_minutes: int = 60        # NFT data cache duration
    cache_user_profile_minutes: int = 30    # User profile cache duration
    
    # Moralis API Configuration
    moralis_base_url: str = "https://deep-index.moralis.io/api/v2.2"
    moralis_timeout: int = 30  # seconds
    
    # Database Configuration
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    
    # Logging Configuration
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Web3Auth Configuration
    web3auth_verifier_map: dict = {
        "google": "google-auth-verifier",
        "discord": "discord-auth-verifier", 
        "github": "github-auth-verifier"
    }
    
    # Pagination Defaults
    default_page_size: int = 20
    max_page_size: int = 100
    
    # Feature Flags
    enable_admin_endpoints: bool = os.getenv("ENABLE_ADMIN", "true").lower() == "true"
    enable_rate_limiting: bool = os.getenv("ENABLE_RATE_LIMITING", "true").lower() == "true"
    enable_caching: bool = os.getenv("ENABLE_CACHING", "true").lower() == "true"
    
    # Monitoring & Analytics
    enable_monitoring: bool = os.getenv("ENABLE_MONITORING", "true").lower() == "true"
    sentry_dsn: Optional[str] = os.getenv("SENTRY_DSN")
    
    # Security Settings
    password_min_length: int = 8
    session_timeout_minutes: int = 60 * 24  # 24 hours
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 30
    
    # Blockchain Settings
    def get_chain_id(self) -> str:
        """Get chain ID for current blockchain network"""
        return self.supported_chains.get(self.blockchain_network, "0x89")
    
    def get_moralis_chain_param(self) -> str:
        """Get chain parameter for Moralis API calls"""
        chain_mapping = {
            "polygon": "polygon",
            "ethereum": "eth", 
            "mumbai": "mumbai",
            "sepolia": "sepolia"
        }
        return chain_mapping.get(self.blockchain_network, "polygon")
    
    # Validation
    def validate_settings(self) -> bool:
        """Validate critical settings are present"""
        required_settings = [
            self.supabase_url,
            self.supabase_key,
            self.database_url,
            self.moralis_api_key,
            self.secret_key
        ]
        
        missing = [setting for setting in required_settings if not setting]
        
        if missing:
            raise ValueError(f"Missing required environment variables: {missing}")
        
        return True
    
    # Environment-specific configurations
    @property
    def is_development(self) -> bool:
        return self.environment.lower() == "development"
    
    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"
    
    @property
    def is_testing(self) -> bool:
        return self.environment.lower() == "testing"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Initialize settings instance
settings = Settings()

# Validate settings on import (will raise error if missing required vars)
try:
    settings.validate_settings()
    print("✅ Configuration loaded successfully")
except ValueError as e:
    print(f"❌ Configuration error: {e}")
    print("Please check your .env file and ensure all required variables are set")

# Export commonly used values
MORALIS_API_KEY = settings.moralis_api_key
BLOCKCHAIN_NETWORK = settings.blockchain_network
SECRET_KEY = settings.secret_key
DATABASE_URL = settings.database_url
SUPABASE_URL = settings.supabase_url
SUPABASE_KEY = settings.supabase_key

# Debug information (only in development)
if settings.is_development and settings.debug:
    print(f"🔧 Environment: {settings.environment}")
    print(f"🌐 Blockchain: {settings.blockchain_network}")
    print(f"🔗 Chain ID: {settings.get_chain_id()}")
    print(f"📡 Moralis Chain: {settings.get_moralis_chain_param()}")
    print(f"🗄️ Database connected: {'Yes' if settings.database_url else 'No'}")
    print(f"🔑 Moralis configured: {'Yes' if settings.moralis_api_key else 'No'}")
