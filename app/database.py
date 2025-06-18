# app/database.py - Updated with MedaShooter tables
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

            # ============================================
            # MEDASHOOTER-SPECIFIC TABLES
            # ============================================
            
            # Raw encrypted data from Unity (Unity compatibility layer)
            await connection.execute('''
                CREATE TABLE IF NOT EXISTS medashooter_unity_scores (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    encrypted_hash TEXT NOT NULL,           -- RSA encrypted score (score key)
                    encrypted_address TEXT NOT NULL,        -- RSA encrypted wallet (score key)
                    encrypted_delta TEXT NOT NULL,          -- Game duration (info key)
                    encrypted_parameter1 TEXT NOT NULL,     -- enemies_spawned (info key)
                    encrypted_parameter2 TEXT NOT NULL,     -- enemies_killed (info key)
                    encrypted_parameter3 TEXT NOT NULL,     -- waves_completed (info key)
                    encrypted_parameter4 TEXT NOT NULL,     -- travel_distance (info key)
                    encrypted_parameter5 TEXT NOT NULL,     -- perks_collected (info key)
                    encrypted_parameter6 TEXT NOT NULL,     -- coins_collected (info key)
                    encrypted_parameter7 TEXT NOT NULL,     -- shields_collected (info key)
                    encrypted_parameter8 TEXT NOT NULL,     -- killing_spree_mult (info key)
                    encrypted_parameter9 TEXT NOT NULL,     -- killing_spree_duration (info key)
                    encrypted_parameter10 TEXT NOT NULL,    -- max_killing_spree (info key)
                    encrypted_parameter11 TEXT NOT NULL,    -- attack_speed (info key)
                    encrypted_parameter12 TEXT NOT NULL,    -- max_score_per_enemy (info key)
                    encrypted_parameter13 TEXT NOT NULL,    -- max_score_per_enemy_scaled (info key)
                    encrypted_parameter14 TEXT NOT NULL,    -- ability_use_count (info key)
                    encrypted_parameter15 TEXT NOT NULL,    -- enemies_killed_while_killing_spree (info key)
                    raw_submission JSONB NOT NULL,          -- Complete Unity JSON
                    submission_time TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            ''')

            # Processed leaderboard data with decrypted scores
            await connection.execute('''
                CREATE TABLE IF NOT EXISTS medashooter_scores (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    unity_score_id UUID REFERENCES medashooter_unity_scores(id),
                    player_address VARCHAR(42) NOT NULL,
                    final_score INTEGER NOT NULL,
                    calculated_score INTEGER NOT NULL,      -- Unity's shifted score result
                    -- Decrypted game statistics (15 parameters)
                    enemies_killed INTEGER,
                    enemies_spawned INTEGER,
                    waves_completed INTEGER,
                    game_duration INTEGER,
                    travel_distance INTEGER,
                    perks_collected INTEGER,
                    coins_collected INTEGER,
                    shields_collected INTEGER,
                    killing_spree_mult INTEGER,
                    killing_spree_duration INTEGER,
                    max_killing_spree INTEGER,
                    attack_speed DECIMAL,
                    max_score_per_enemy INTEGER,
                    max_score_per_enemy_scaled INTEGER,
                    ability_use_count INTEGER,
                    enemies_killed_while_killing_spree INTEGER,
                    nft_boosts_used JSONB,                  -- NFT boost snapshot
                    meda_gas_reward INTEGER DEFAULT 0,
                    validated BOOLEAN DEFAULT TRUE,
                    submission_time TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            ''')

            # NFT boost tracking and verification
            await connection.execute('''
                CREATE TABLE IF NOT EXISTS medashooter_nft_boost_usage (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    player_address VARCHAR(42) NOT NULL,
                    score_id UUID REFERENCES medashooter_scores(id),
                    hero_nfts INTEGER DEFAULT 0,
                    weapon_nfts INTEGER DEFAULT 0,
                    land_nfts INTEGER DEFAULT 0,
                    total_nfts INTEGER DEFAULT 0,
                    damage_multiplier INTEGER DEFAULT 0,
                    fire_rate_bonus INTEGER DEFAULT 0,
                    score_multiplier INTEGER DEFAULT 0,
                    health_bonus INTEGER DEFAULT 0,
                    blockchain_verified BOOLEAN DEFAULT FALSE,
                    boost_snapshot JSONB
                );
            ''')

            # Comprehensive player analytics
            await connection.execute('''
                CREATE TABLE IF NOT EXISTS medashooter_player_stats (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    player_address VARCHAR(42) UNIQUE NOT NULL,
                    total_games_played INTEGER DEFAULT 0,
                    web3_connected_games INTEGER DEFAULT 0,
                    nft_games_played INTEGER DEFAULT 0,
                    best_score INTEGER DEFAULT 0,
                    total_meda_gas_earned INTEGER DEFAULT 0,
                    first_game_played TIMESTAMP WITH TIME ZONE,
                    last_game_played TIMESTAMP WITH TIME ZONE,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            ''')

            # Daily leaderboards for rankings and rewards
            await connection.execute('''
                CREATE TABLE IF NOT EXISTS medashooter_daily_leaderboards (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    game_date DATE NOT NULL,
                    player_address VARCHAR(42) NOT NULL,
                    best_daily_score INTEGER NOT NULL,
                    daily_rank INTEGER NOT NULL,
                    nft_boosts_active BOOLEAN DEFAULT FALSE,
                    meda_gas_earned INTEGER DEFAULT 0,
                    UNIQUE(game_date, player_address)
                );
            ''')

            # Player blacklist for anti-cheat system
            await connection.execute('''
                CREATE TABLE IF NOT EXISTS medashooter_blacklist (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    player_address VARCHAR(42) UNIQUE NOT NULL,
                    reason TEXT NOT NULL,
                    evidence JSONB,
                    blacklisted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    active BOOLEAN DEFAULT TRUE
                );
            ''')

            # Encrypted anti-cheat reports from Unity
            await connection.execute('''
                CREATE TABLE IF NOT EXISTS medashooter_unity_cheat_reports (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    encrypted_address TEXT NOT NULL,        -- RSA encrypted reported address
                    raw_report JSONB NOT NULL,
                    processed BOOLEAN DEFAULT FALSE,
                    submission_time TIMESTAMP WITH TIME ZONE DEFAULT NOW()
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
                
                -- MedaShooter indexes
                CREATE INDEX IF NOT EXISTS idx_medashooter_unity_scores_submission_time ON medashooter_unity_scores(submission_time);
                
                CREATE INDEX IF NOT EXISTS idx_medashooter_scores_player_address ON medashooter_scores(player_address);
                CREATE INDEX IF NOT EXISTS idx_medashooter_scores_final_score ON medashooter_scores(final_score);
                CREATE INDEX IF NOT EXISTS idx_medashooter_scores_submission_time ON medashooter_scores(submission_time);
                CREATE INDEX IF NOT EXISTS idx_medashooter_scores_validated ON medashooter_scores(validated);
                
                CREATE INDEX IF NOT EXISTS idx_medashooter_nft_boost_player_address ON medashooter_nft_boost_usage(player_address);
                CREATE INDEX IF NOT EXISTS idx_medashooter_nft_boost_score_id ON medashooter_nft_boost_usage(score_id);
                
                CREATE INDEX IF NOT EXISTS idx_medashooter_player_stats_address ON medashooter_player_stats(player_address);
                CREATE INDEX IF NOT EXISTS idx_medashooter_player_stats_best_score ON medashooter_player_stats(best_score);
                
                CREATE INDEX IF NOT EXISTS idx_medashooter_daily_leaderboards_date ON medashooter_daily_leaderboards(game_date);
                CREATE INDEX IF NOT EXISTS idx_medashooter_daily_leaderboards_rank ON medashooter_daily_leaderboards(daily_rank);
                
                CREATE INDEX IF NOT EXISTS idx_medashooter_blacklist_address ON medashooter_blacklist(player_address);
                CREATE INDEX IF NOT EXISTS idx_medashooter_blacklist_active ON medashooter_blacklist(active);
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

            # ============================================
            # MEDASHOOTER HELPER FUNCTIONS
            # ============================================
            
            # Create helper functions for anti-cheat
            await connection.execute('''
                CREATE OR REPLACE FUNCTION is_address_blacklisted(check_address TEXT)
                RETURNS BOOLEAN AS $$
                BEGIN
                    RETURN EXISTS (
                        SELECT 1 FROM medashooter_blacklist 
                        WHERE player_address = LOWER(check_address) AND active = TRUE
                    );
                END;
                $$ LANGUAGE plpgsql;
            ''')

            # Auto-update player stats after score submission
            await connection.execute('''
                CREATE OR REPLACE FUNCTION update_player_stats_after_score()
                RETURNS TRIGGER AS $
                BEGIN
                    INSERT INTO medashooter_player_stats (
                        player_address, total_games_played, best_score,
                        last_game_played
                    ) VALUES (
                        NEW.player_address, 1, NEW.final_score,
                        NEW.submission_time
                    )
                    ON CONFLICT (player_address) DO UPDATE SET
                        total_games_played = medashooter_player_stats.total_games_played + 1,
                        best_score = GREATEST(medashooter_player_stats.best_score, NEW.final_score),
                        last_game_played = NEW.submission_time,
                        updated_at = NOW();
                    RETURN NEW;
                END;
                $ LANGUAGE plpgsql;
            ''')

            await connection.execute('''
                DROP TRIGGER IF EXISTS trigger_update_player_stats ON medashooter_scores;
                CREATE TRIGGER trigger_update_player_stats
                    AFTER INSERT ON medashooter_scores
                    FOR EACH ROW EXECUTE FUNCTION update_player_stats_after_score();
            ''')
            
        logger.info("✅ Database initialized successfully with MedaShooter tables!")
        
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