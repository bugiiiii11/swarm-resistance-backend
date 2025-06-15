# app/database.py
from supabase import create_client, Client
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings
import asyncpg
import asyncio
from typing import AsyncGenerator
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Supabase client for real-time features and auth
supabase: Client = create_client(settings.supabase_url, settings.supabase_key)

# SQLAlchemy setup for direct database operations
if settings.database_url:
    engine = create_engine(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        echo=settings.debug  # Log SQL queries in debug mode
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
else:
    engine = None
    SessionLocal = None
    Base = None
    logger.warning("No database URL provided")

# Async database connection pool
_connection_pool = None

async def get_db_pool():
    """Get async database connection pool"""
    global _connection_pool
    if _connection_pool is None:
        try:
            _connection_pool = await asyncpg.create_pool(
                settings.database_url,
                min_size=1,
                max_size=settings.db_pool_size,
                command_timeout=settings.db_pool_timeout
            )
            logger.info("✅ Database connection pool created")
        except Exception as e:
            logger.error(f"❌ Failed to create database pool: {e}")
            raise
    return _connection_pool

# Database dependency for FastAPI
async def get_db() -> AsyncGenerator:
    """Dependency to get database session"""
    if SessionLocal:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    else:
        # Use Supabase client as fallback
        yield supabase

# Database initialization
async def init_db():
    """Initialize database with required tables"""
    try:
        pool = await get_db_pool()
        
        async with pool.acquire() as connection:
            # Create users table
            await connection.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    wallet_address TEXT UNIQUE NOT NULL,
                    email TEXT,
                    username TEXT,
                    web3auth_user_id TEXT,
                    is_admin BOOLEAN DEFAULT FALSE,
                    is_active BOOLEAN DEFAULT TRUE,
                    last_login TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            ''')
            
            # Create token holdings cache table
            await connection.execute('''
                CREATE TABLE IF NOT EXISTS token_holdings (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                    token_address TEXT NOT NULL,
                    balance DECIMAL NOT NULL DEFAULT 0,
                    decimals INTEGER DEFAULT 18,
                    symbol TEXT,
                    name TEXT,
                    logo_url TEXT,
                    usd_price DECIMAL DEFAULT 0,
                    usd_value DECIMAL DEFAULT 0,
                    percentage_change_24h DECIMAL DEFAULT 0,
                    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    UNIQUE(user_id, token_address)
                );
            ''')
            
            # Create NFT holdings cache table
            await connection.execute('''
                CREATE TABLE IF NOT EXISTS nft_holdings (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                    contract_address TEXT NOT NULL,
                    token_id TEXT NOT NULL,
                    name TEXT,
                    description TEXT,
                    image_url TEXT,
                    metadata JSONB DEFAULT '{}',
                    collection_name TEXT,
                    floor_price DECIMAL DEFAULT 0,
                    last_sale_price DECIMAL DEFAULT 0,
                    rarity_rank INTEGER,
                    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    UNIQUE(user_id, contract_address, token_id)
                );
            ''')
            
            # Create user activity logs table
            await connection.execute('''
                CREATE TABLE IF NOT EXISTS user_activities (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                    action TEXT NOT NULL,
                    description TEXT,
                    metadata JSONB DEFAULT '{}',
                    ip_address TEXT,
                    user_agent TEXT,
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            ''')
            
            # Create API usage tracking table
            await connection.execute('''
                CREATE TABLE IF NOT EXISTS api_usage (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                    endpoint TEXT NOT NULL,
                    method TEXT NOT NULL,
                    status_code INTEGER,
                    response_time_ms INTEGER,
                    moralis_calls INTEGER DEFAULT 0,
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            ''')
            
            # Create wallet analytics table
            await connection.execute('''
                CREATE TABLE IF NOT EXISTS wallet_analytics (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                    wallet_address TEXT NOT NULL,
                    total_tokens INTEGER DEFAULT 0,
                    total_nfts INTEGER DEFAULT 0,
                    total_usd_value DECIMAL DEFAULT 0,
                    transaction_count INTEGER DEFAULT 0,
                    first_transaction_date TIMESTAMP WITH TIME ZONE,
                    last_transaction_date TIMESTAMP WITH TIME ZONE,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    UNIQUE(user_id, wallet_address)
                );
            ''')
            
            # Create indexes for better performance
            await connection.execute('''
                CREATE INDEX IF NOT EXISTS idx_users_wallet_address ON users(wallet_address);
                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
                CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);
                CREATE INDEX IF NOT EXISTS idx_users_last_login ON users(last_login);
                
                CREATE INDEX IF NOT EXISTS idx_token_holdings_user_id ON token_holdings(user_id);
                CREATE INDEX IF NOT EXISTS idx_token_holdings_token_address ON token_holdings(token_address);
                CREATE INDEX IF NOT EXISTS idx_token_holdings_last_updated ON token_holdings(last_updated);
                CREATE INDEX IF NOT EXISTS idx_token_holdings_usd_value ON token_holdings(usd_value);
                
                CREATE INDEX IF NOT EXISTS idx_nft_holdings_user_id ON nft_holdings(user_id);
                CREATE INDEX IF NOT EXISTS idx_nft_holdings_contract ON nft_holdings(contract_address);
                CREATE INDEX IF NOT EXISTS idx_nft_holdings_last_updated ON nft_holdings(last_updated);
                CREATE INDEX IF NOT EXISTS idx_nft_holdings_collection ON nft_holdings(collection_name);
                
                CREATE INDEX IF NOT EXISTS idx_user_activities_user_id ON user_activities(user_id);
                CREATE INDEX IF NOT EXISTS idx_user_activities_action ON user_activities(action);
                CREATE INDEX IF NOT EXISTS idx_user_activities_timestamp ON user_activities(timestamp);
                
                CREATE INDEX IF NOT EXISTS idx_api_usage_user_id ON api_usage(user_id);
                CREATE INDEX IF NOT EXISTS idx_api_usage_endpoint ON api_usage(endpoint);
                CREATE INDEX IF NOT EXISTS idx_api_usage_timestamp ON api_usage(timestamp);
                
                CREATE INDEX IF NOT EXISTS idx_wallet_analytics_user_id ON wallet_analytics(user_id);
                CREATE INDEX IF NOT EXISTS idx_wallet_analytics_wallet_address ON wallet_analytics(wallet_address);
                CREATE INDEX IF NOT EXISTS idx_wallet_analytics_updated_at ON wallet_analytics(updated_at);
            ''')
            
            # Create updated_at trigger function
            await connection.execute('''
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = NOW();
                    RETURN NEW;
                END;
                $$ language 'plpgsql';
            ''')
            
            # Create triggers for automatic updated_at
            await connection.execute('''
                DROP TRIGGER IF EXISTS update_users_updated_at ON users;
                CREATE TRIGGER update_users_updated_at
                    BEFORE UPDATE ON users
                    FOR EACH ROW
                    EXECUTE FUNCTION update_updated_at_column();
                    
                DROP TRIGGER IF EXISTS update_wallet_analytics_updated_at ON wallet_analytics;
                CREATE TRIGGER update_wallet_analytics_updated_at
                    BEFORE UPDATE ON wallet_analytics
                    FOR EACH ROW
                    EXECUTE FUNCTION update_updated_at_column();
            ''')
            
        logger.info("✅ Database initialized successfully!")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {str(e)}")
        raise

# Helper functions for database operations
async def execute_query(query: str, *args):
    """Execute a single query and return results"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as connection:
            result = await connection.fetch(query, *args)
        return result
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        raise

async def execute_command(command: str, *args):
    """Execute a single command (INSERT, UPDATE, DELETE)"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as connection:
            result = await connection.execute(command, *args)
        return result
    except Exception as e:
        logger.error(f"Command execution failed: {e}")
        raise

async def execute_transaction(commands: list):
    """Execute multiple commands in a transaction"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as connection:
            async with connection.transaction():
                results = []
                for command, args in commands:
                    result = await connection.execute(command, *args)
                    results.append(result)
                return results
    except Exception as e:
        logger.error(f"Transaction execution failed: {e}")
        raise

# Health check for database
async def check_db_health() -> dict:
    """Check database connection health"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as connection:
            result = await connection.fetchval("SELECT 1")
            return {
                "status": "healthy",
                "database": "connected",
                "timestamp": asyncio.get_event_loop().time()
            }
    except Exception as e:
        return {
            "status": "unhealthy", 
            "database": "disconnected",
            "error": str(e),
            "timestamp": asyncio.get_event_loop().time()
        }

# Cleanup function
async def close_db_pool():
    """Close database connection pool"""
    global _connection_pool
    if _connection_pool:
        await _connection_pool.close()
        _connection_pool = None
        logger.info("Database connection pool closed")
