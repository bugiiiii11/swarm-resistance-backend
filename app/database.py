# app/database.py - COMPLETE with token caching system integration
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
    """Initialize database with required tables including TOKEN CACHING SYSTEM"""
    try:
        pool = await get_db_pool()
        
        async with pool.acquire() as connection:
            # ============================================
            # EXISTING CORE TABLES
            # ============================================
            
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
            # CHARACTERS TABLE - Game character data
            # ============================================
            
            # Create characters table for game character data
            await connection.execute('''
                CREATE TABLE IF NOT EXISTS characters (
                    type_szn_id INTEGER PRIMARY KEY,
                    title VARCHAR(50) NOT NULL,
                    class VARCHAR(20) NOT NULL,
                    fraction VARCHAR(20) NOT NULL
                );
            ''')

            # Insert character data if table is empty
            character_count = await connection.fetchval("SELECT COUNT(*) FROM characters")
            if character_count == 0:
                logger.info("🎭 Inserting character data...")
                await connection.execute('''
                    INSERT INTO characters (type_szn_id, title, class, fraction) VALUES
                    (1011, 'Zombie Chad', 'Harvester', 'Renegade'),
                    (1012, 'Farmer', 'Harvester', 'Goliath'),
                    (1013, 'Crypto Queen', 'Warmonger', 'Renegade'),
                    (1014, 'Link', 'Defender', 'Goliath'),
                    (1021, 'Charles', 'Defender', 'Goliath'),
                    (1022, 'Elon', 'Specialist', 'Renegade'),
                    (1023, 'Bridger', 'Defender', 'Goliath'),
                    (1024, 'John', 'Specialist', 'Renegade'),
                    (1031, 'Vitalik', 'Warmonger', 'Goliath'),
                    (1032, 'Warper', 'Defender', 'Renegade'),
                    (1033, 'Michael', 'Specialist', 'Goliath'),
                    (1034, 'Solana', 'Warmonger', 'Renegade'),
                    (1041, 'Harvester', 'Harvester', 'Goliath'),
                    (1042, 'MasterCZ', 'Warmonger', 'Renegade'),
                    (1043, 'Sam', 'Specialist', 'Goliath'),
                    (1044, 'Lunatic', 'Warmonger', 'Renegade'),
                    (1051, 'Shardeus', 'Defender', 'Goliath'),
                    (2010, 'Commander', 'Revolutionist', 'Other'),
                    (2020, 'Floki', 'Revolutionist', 'Other'),
                    (2030, 'Nero', 'Revolutionist', 'Other'),
                    (2040, 'Atom', 'Revolutionist', 'Other'),
                    (3001, 'Ash', 'Specialist', 'Other'),
                    (3002, 'Kroge', 'Specialist', 'Other'),
                    (3003, 'Polytron', 'Specialist', 'Other'),
                    (3004, 'Warpath', 'Specialist', 'Other'),
                    (3005, 'MedaHero', 'Specialist', 'Other'),
                    (3006, 'Coinstore', 'Specialist', 'Other'),
                    (3007, 'Unstoppable Force', 'Specialist', 'Other')
                    ON CONFLICT (type_szn_id) DO NOTHING;
                ''')
                logger.info("✅ Character data inserted successfully")
            else:
                logger.info(f"✅ Characters table already contains {character_count} records")

            # ============================================
            # NEW: SMART CONTRACTS REFERENCE TABLE
            # ============================================
            
            await connection.execute('''
                CREATE TABLE IF NOT EXISTS smart_contracts (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(50) UNIQUE NOT NULL,
                    address VARCHAR(42) UNIQUE NOT NULL,
                    chain VARCHAR(20) DEFAULT 'polygon',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            ''')
            
            # Insert contract data
            contract_count = await connection.fetchval("SELECT COUNT(*) FROM smart_contracts")
            if contract_count == 0:
                logger.info("🔗 Inserting smart contract data...")
                await connection.execute('''
                    INSERT INTO smart_contracts (name, address, chain) VALUES
                        ('heroes', '0x27331bbfe94d1b8518816462225b16622ac74e2e', 'polygon'),
                        ('weapons', '0x31dd72d810b34c339f2ce9119e2ebfbb9926694a', 'polygon'),
                        ('lands', '0xaae02c81133d865d543df02b1e458de2279c4a5b', 'polygon')
                    ON CONFLICT (name) DO NOTHING;
                ''')
                logger.info("✅ Smart contract data inserted successfully")
            else:
                logger.info(f"✅ Smart contracts table already contains {contract_count} records")
            
            # ============================================
            # NEW: WEAPON MAPPING TABLE
            # ============================================
            
            await connection.execute('''
                CREATE TABLE IF NOT EXISTS weapon_mappings (
                    id SERIAL PRIMARY KEY,
                    weapon_tier INTEGER NOT NULL,
                    weapon_type INTEGER NOT NULL,
                    weapon_subtype INTEGER NOT NULL,
                    category INTEGER NOT NULL,
                    weapon_name VARCHAR(100) NOT NULL,
                    UNIQUE(weapon_tier, weapon_type, weapon_subtype, category)
                );
            ''')
            
            # Insert weapon mapping data
            weapon_count = await connection.fetchval("SELECT COUNT(*) FROM weapon_mappings")
            if weapon_count == 0:
                logger.info("⚔️ Inserting weapon mapping data...")
                await connection.execute('''
                    INSERT INTO weapon_mappings (weapon_tier, weapon_type, weapon_subtype, category, weapon_name) VALUES
                        -- WEAPON_TIER_COMMON (1) - WEAPON_TYPE_RANGE (2)
                        (1, 2, 1, 1, 'Viper'),
                        (1, 2, 1, 2, 'Underdog Meda-Gun'),
                        (1, 2, 1, 3, 'Adept''s Repeater'),
                        (1, 2, 1, 4, 'Sandcrawler''s Sniper Rifle'),
                        -- WEAPON_TIER_COMMON (1) - WEAPON_TYPE_MELEE (1)
                        (1, 1, 1, 1, 'Gladiator''s Greatsword'),
                        (1, 1, 1, 2, 'Ryoshi Katana'),
                        (1, 1, 1, 3, 'Tactician''s Claymore'),
                        (1, 1, 1, 4, 'Blessed Blade'),
                        -- WEAPON_TIER_RARE (2) - WEAPON_TYPE_RANGE (2)
                        (2, 2, 1, 1, 'Serpent''s Bite'),
                        (2, 2, 1, 2, 'Victim''s Meda-Gun'),
                        (2, 2, 1, 3, 'Soldier''s Repeater'),
                        (2, 2, 1, 4, 'Tundrastalker''s Sniper Rifle'),
                        -- WEAPON_TIER_RARE (2) - WEAPON_TYPE_MELEE (1)
                        (2, 1, 1, 1, 'Mercilles''s Greatsword'),
                        (2, 1, 1, 2, 'Tadashi Katana'),
                        (2, 1, 1, 3, 'Righteous Claymore'),
                        (2, 1, 1, 4, 'Moon Blade')
                    ON CONFLICT (weapon_tier, weapon_type, weapon_subtype, category) DO NOTHING;
                ''')
                logger.info("✅ Weapon mapping data inserted successfully")
            else:
                logger.info(f"✅ Weapon mappings table already contains {weapon_count} records")
            
            # ============================================
            # NEW: HEROES TOKEN CACHE TABLE
            # ============================================
            
            await connection.execute('''
                CREATE TABLE IF NOT EXISTS heroes_token_cache (
                    id SERIAL PRIMARY KEY,
                    bc_id INTEGER UNIQUE NOT NULL,  -- token_id from blockchain (Unity's id)
                    -- getAttribs data
                    sec INTEGER NOT NULL DEFAULT 0,
                    ano INTEGER NOT NULL DEFAULT 0,
                    inn INTEGER NOT NULL DEFAULT 0,
                    -- getTokenInfo data
                    season_card_id INTEGER NOT NULL DEFAULT 0,
                    serial_number INTEGER NOT NULL DEFAULT 0,
                    -- Additional computed fields
                    card_type INTEGER,
                    season_id INTEGER,
                    card_season_collection_id INTEGER,
                    -- Cache management
                    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    is_valid BOOLEAN DEFAULT TRUE
                );
            ''')
            
            # ============================================
            # NEW: WEAPONS TOKEN CACHE TABLE
            # ============================================
            
            await connection.execute('''
                CREATE TABLE IF NOT EXISTS weapons_token_cache (
                    id SERIAL PRIMARY KEY,
                    bc_id INTEGER UNIQUE NOT NULL,  -- token_id from blockchain (Unity's id)
                    -- getAttribs data
                    security INTEGER NOT NULL DEFAULT 0,
                    anonymity INTEGER NOT NULL DEFAULT 0,
                    innovation INTEGER NOT NULL DEFAULT 0,
                    -- getTokenInfo data
                    weapon_tier INTEGER NOT NULL DEFAULT 1,
                    weapon_type INTEGER NOT NULL DEFAULT 1,
                    weapon_subtype INTEGER NOT NULL DEFAULT 1,
                    category INTEGER NOT NULL DEFAULT 1,
                    serial_number INTEGER NOT NULL DEFAULT 1,
                    -- Cache management
                    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    is_valid BOOLEAN DEFAULT TRUE
                );
            ''')
            
            # ============================================
            # NEW: TOKEN CACHE ERROR LOG TABLE
            # ============================================
            
            await connection.execute('''
                CREATE TABLE IF NOT EXISTS token_cache_errors (
                    id SERIAL PRIMARY KEY,
                    contract_type VARCHAR(20) NOT NULL,  -- 'heroes' or 'weapons'
                    token_id INTEGER NOT NULL,
                    error_type VARCHAR(50) NOT NULL,     -- 'contract_call_failed', 'invalid_response', etc.
                    error_message TEXT,
                    wallet_address VARCHAR(42),
                    retry_count INTEGER DEFAULT 0,
                    resolved BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    resolved_at TIMESTAMP WITH TIME ZONE
                );
            ''')

            # ============================================
            # MEDASHOOTER-SPECIFIC TABLES
            # ============================================
            
            # Raw encrypted data from Unity (Unity compatibility layer)
            await connection.execute('''
                CREATE TABLE IF NOT EXISTS medashooter_unity_scores (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    encrypted_hash TEXT NOT NULL,
                    encrypted_address TEXT NOT NULL,
                    encrypted_delta TEXT NOT NULL,
                    encrypted_parameter1 TEXT NOT NULL,
                    encrypted_parameter2 TEXT NOT NULL,
                    encrypted_parameter3 TEXT NOT NULL,
                    encrypted_parameter4 TEXT NOT NULL,
                    encrypted_parameter5 TEXT NOT NULL,
                    encrypted_parameter6 TEXT NOT NULL,
                    encrypted_parameter7 TEXT NOT NULL,
                    encrypted_parameter8 TEXT NOT NULL,
                    encrypted_parameter9 TEXT NOT NULL,
                    encrypted_parameter10 TEXT NOT NULL,
                    encrypted_parameter11 TEXT NOT NULL,
                    encrypted_parameter12 TEXT NOT NULL,
                    encrypted_parameter13 TEXT NOT NULL,
                    encrypted_parameter14 TEXT NOT NULL,
                    encrypted_parameter15 TEXT NOT NULL,
                    raw_submission JSONB NOT NULL,
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
                    calculated_score INTEGER NOT NULL,
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
                    nft_boosts_used JSONB,
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
                    encrypted_address TEXT NOT NULL,
                    raw_report JSONB NOT NULL,
                    processed BOOLEAN DEFAULT FALSE,
                    submission_time TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            ''')
            
            # ============================================
            # CREATE INDEXES FOR BETTER PERFORMANCE
            # ============================================
            
            # Existing indexes
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
                
                CREATE INDEX IF NOT EXISTS idx_characters_class ON characters(class);
                CREATE INDEX IF NOT EXISTS idx_characters_fraction ON characters(fraction);
                CREATE INDEX IF NOT EXISTS idx_characters_title ON characters(title);
            ''')
            
            # NEW: Token caching indexes
            await connection.execute('''
                -- Smart contracts indexes
                CREATE INDEX IF NOT EXISTS idx_smart_contracts_name ON smart_contracts(name);
                CREATE INDEX IF NOT EXISTS idx_smart_contracts_address ON smart_contracts(address);
                
                -- Weapon mappings indexes
                CREATE INDEX IF NOT EXISTS idx_weapon_mappings_lookup ON weapon_mappings(weapon_tier, weapon_type, weapon_subtype, category);
                
                -- Heroes cache indexes
                CREATE INDEX IF NOT EXISTS idx_heroes_cache_bc_id ON heroes_token_cache(bc_id);
                CREATE INDEX IF NOT EXISTS idx_heroes_cache_season_card_id ON heroes_token_cache(season_card_id);
                CREATE INDEX IF NOT EXISTS idx_heroes_cache_last_updated ON heroes_token_cache(last_updated);
                CREATE INDEX IF NOT EXISTS idx_heroes_cache_is_valid ON heroes_token_cache(is_valid);
                
                -- Weapons cache indexes
                CREATE INDEX IF NOT EXISTS idx_weapons_cache_bc_id ON weapons_token_cache(bc_id);
                CREATE INDEX IF NOT EXISTS idx_weapons_cache_weapon_tier ON weapons_token_cache(weapon_tier);
                CREATE INDEX IF NOT EXISTS idx_weapons_cache_last_updated ON weapons_token_cache(last_updated);
                CREATE INDEX IF NOT EXISTS idx_weapons_cache_is_valid ON weapons_token_cache(is_valid);
                
                -- Error log indexes
                CREATE INDEX IF NOT EXISTS idx_token_cache_errors_contract_type ON token_cache_errors(contract_type);
                CREATE INDEX IF NOT EXISTS idx_token_cache_errors_token_id ON token_cache_errors(token_id);
                CREATE INDEX IF NOT EXISTS idx_token_cache_errors_resolved ON token_cache_errors(resolved);
                CREATE INDEX IF NOT EXISTS idx_token_cache_errors_created_at ON token_cache_errors(created_at);
            ''')
            
            # MedaShooter indexes
            await connection.execute('''
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
            
            # ============================================
            # MEDASHOOTER DUPLICATE PREVENTION OPTIMIZATION
            # ============================================

            # Single strategic index for current leaderboard performance
            await connection.execute('''
                -- Optimize for "get best score per player" queries
                CREATE INDEX IF NOT EXISTS idx_medashooter_best_score_per_player 
                ON medashooter_scores (player_address, final_score DESC, submission_time ASC) 
                WHERE validated = TRUE;
                
                -- Optimize for leaderboard ranking queries
                CREATE INDEX IF NOT EXISTS idx_medashooter_leaderboard_ranking 
                ON medashooter_scores (final_score DESC, submission_time ASC) 
                WHERE validated = TRUE;
            ''')

            # Helper function for efficient current leaderboard
            await connection.execute('''
                -- Function to get current leaderboard (one score per player)
                CREATE OR REPLACE FUNCTION get_current_medashooter_leaderboard(p_limit INTEGER DEFAULT 50)
                RETURNS TABLE(
                    rank BIGINT,
                    player_address VARCHAR(42),
                    final_score INTEGER,
                    submission_time TIMESTAMP WITH TIME ZONE,
                    nft_boosts_used JSONB
                ) AS $$
                BEGIN
                    RETURN QUERY
                    WITH best_scores AS (
                        SELECT DISTINCT ON (s.player_address) 
                            s.player_address,
                            s.final_score,
                            s.submission_time,
                            s.nft_boosts_used
                        FROM medashooter_scores s
                        WHERE s.validated = TRUE
                        ORDER BY s.player_address, s.final_score DESC, s.submission_time ASC
                    )
                    SELECT 
                        ROW_NUMBER() OVER (ORDER BY bs.final_score DESC, bs.submission_time ASC) as rank,
                        bs.player_address,
                        bs.final_score,
                        bs.submission_time,
                        bs.nft_boosts_used
                    FROM best_scores bs
                    ORDER BY bs.final_score DESC, bs.submission_time ASC
                    LIMIT p_limit;
                END;
                $$ LANGUAGE plpgsql;
            ''')
            
            # ============================================
            # HELPER FUNCTIONS AND TRIGGERS
            # ============================================
            
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
            # NEW: TOKEN CACHING HELPER FUNCTIONS
            # ============================================
            
            # Function to get contract address by name
            await connection.execute('''
                CREATE OR REPLACE FUNCTION get_contract_address(contract_name TEXT)
                RETURNS TEXT AS $$
                DECLARE
                    contract_address TEXT;
                BEGIN
                    SELECT address INTO contract_address 
                    FROM smart_contracts 
                    WHERE name = contract_name AND is_active = TRUE;
                    
                    IF contract_address IS NULL THEN
                        RAISE EXCEPTION 'Contract % not found or inactive', contract_name;
                    END IF;
                    
                    RETURN contract_address;
                END;
                $$ LANGUAGE plpgsql;
            ''')
            
            # Function to get weapon name from mapping
            await connection.execute('''
                CREATE OR REPLACE FUNCTION get_weapon_name(
                    p_weapon_tier INTEGER,
                    p_weapon_type INTEGER,
                    p_weapon_subtype INTEGER,
                    p_category INTEGER
                )
                RETURNS TEXT AS $$
                DECLARE
                    weapon_name TEXT;
                BEGIN
                    SELECT wm.weapon_name INTO weapon_name
                    FROM weapon_mappings wm
                    WHERE wm.weapon_tier = p_weapon_tier
                      AND wm.weapon_type = p_weapon_type
                      AND wm.weapon_subtype = p_weapon_subtype
                      AND wm.category = p_category;
                    
                    IF weapon_name IS NULL THEN
                        -- Fallback naming
                        IF p_weapon_type = 2 THEN
                            weapon_name := 'T' || p_weapon_tier || ' Gun #' || p_category;
                        ELSIF p_weapon_type = 1 THEN
                            weapon_name := 'T' || p_weapon_tier || ' Sword #' || p_category;
                        ELSE
                            weapon_name := 'T' || p_weapon_tier || ' Weapon #' || p_category;
                        END IF;
                    END IF;
                    
                    RETURN weapon_name;
                END;
                $$ LANGUAGE plpgsql;
            ''')
            
            # Function to calculate hero card data from season_card_id
            await connection.execute('''
                CREATE OR REPLACE FUNCTION calculate_hero_card_data(season_card_id INTEGER)
                RETURNS TABLE(card_type INTEGER, season_id INTEGER, card_season_collection_id INTEGER) AS $$
                BEGIN
                    RETURN QUERY SELECT 
                        season_card_id / 1000 AS card_type,
                        (season_card_id % 1000) / 10 AS season_id,
                        season_card_id % 10 AS card_season_collection_id;
                END;
                $$ LANGUAGE plpgsql;
            ''')
            
            # Function to get cache statistics
            await connection.execute('''
                CREATE OR REPLACE FUNCTION get_cache_statistics()
                RETURNS TABLE(
                    heroes_cached INTEGER,
                    weapons_cached INTEGER,
                    heroes_invalid INTEGER,
                    weapons_invalid INTEGER,
                    total_errors INTEGER,
                    unresolved_errors INTEGER
                ) AS $$
                BEGIN
                    RETURN QUERY
                    SELECT 
                        (SELECT COUNT(*)::INTEGER FROM heroes_token_cache WHERE is_valid = TRUE),
                        (SELECT COUNT(*)::INTEGER FROM weapons_token_cache WHERE is_valid = TRUE),
                        (SELECT COUNT(*)::INTEGER FROM heroes_token_cache WHERE is_valid = FALSE),
                        (SELECT COUNT(*)::INTEGER FROM weapons_token_cache WHERE is_valid = FALSE),
                        (SELECT COUNT(*)::INTEGER FROM token_cache_errors),
                        (SELECT COUNT(*)::INTEGER FROM token_cache_errors WHERE resolved = FALSE);
                END;
                $$ LANGUAGE plpgsql;
            ''')
            
            # Function to invalidate old cache entries
            await connection.execute('''
                CREATE OR REPLACE FUNCTION invalidate_old_cache_entries(days_old INTEGER DEFAULT 30)
                RETURNS INTEGER AS $$
                DECLARE
                    affected_rows INTEGER;
                BEGIN
                    WITH updated_heroes AS (
                        UPDATE heroes_token_cache 
                        SET is_valid = FALSE 
                        WHERE last_updated < NOW() - INTERVAL '1 day' * days_old AND is_valid = TRUE
                        RETURNING 1
                    ),
                    updated_weapons AS (
                        UPDATE weapons_token_cache 
                        SET is_valid = FALSE 
                        WHERE last_updated < NOW() - INTERVAL '1 day' * days_old AND is_valid = TRUE
                        RETURNING 1
                    )
                    SELECT (SELECT COUNT(*) FROM updated_heroes) + (SELECT COUNT(*) FROM updated_weapons)
                    INTO affected_rows;
                    
                    RETURN affected_rows;
                END;
                $$ LANGUAGE plpgsql;
            ''')
            
            # ============================================
            # NEW: AUTO-UPDATE TRIGGERS FOR TOKEN CACHE
            # ============================================
            
            # Trigger to auto-calculate hero card data
            await connection.execute('''
                CREATE OR REPLACE FUNCTION update_hero_card_data()
                RETURNS TRIGGER AS $$
                BEGIN
                    -- Calculate card data from season_card_id
                    SELECT card_type, season_id, card_season_collection_id
                    INTO NEW.card_type, NEW.season_id, NEW.card_season_collection_id
                    FROM calculate_hero_card_data(NEW.season_card_id);
                    
                    -- Update timestamp
                    NEW.last_updated = NOW();
                    
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            ''')
            
            await connection.execute('''
                DROP TRIGGER IF EXISTS trigger_update_hero_card_data ON heroes_token_cache;
                CREATE TRIGGER trigger_update_hero_card_data
                    BEFORE INSERT OR UPDATE ON heroes_token_cache
                    FOR EACH ROW EXECUTE FUNCTION update_hero_card_data();
            ''')
            
            # Trigger to update weapons timestamp
            await connection.execute('''
                CREATE OR REPLACE FUNCTION update_weapons_timestamp()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.last_updated = NOW();
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            ''')
            
            await connection.execute('''
                DROP TRIGGER IF EXISTS trigger_update_weapons_timestamp ON weapons_token_cache;
                CREATE TRIGGER trigger_update_weapons_timestamp
                    BEFORE UPDATE ON weapons_token_cache
                    FOR EACH ROW EXECUTE FUNCTION update_weapons_timestamp();
            ''')

            # Helper functions for anti-cheat (existing MedaShooter functions)
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

            # Auto-update player stats after score submission (existing MedaShooter function)
            await connection.execute('''
                CREATE OR REPLACE FUNCTION update_player_stats_after_score()
                RETURNS TRIGGER AS $$
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
                $$ LANGUAGE plpgsql;
            ''')

            await connection.execute('''
                DROP TRIGGER IF EXISTS trigger_update_player_stats ON medashooter_scores;
                CREATE TRIGGER trigger_update_player_stats
                    AFTER INSERT ON medashooter_scores
                    FOR EACH ROW EXECUTE FUNCTION update_player_stats_after_score();
            ''')
            
        logger.info("✅ Database initialized successfully with TOKEN CACHING SYSTEM!")
        logger.info("🚀 Smart contract call optimization is now active!")
        logger.info("🎯 Features added: Heroes cache, Weapons cache, Smart contracts table, Weapon mappings")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {str(e)}")
        raise

# Helper functions for database operations - FIXED for asyncpg
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

# Character data helper functions (existing)
async def get_character_by_season_card_id(season_card_id: int) -> dict:
    """Get character data by season_card_id (type_szn_id)"""
    try:
        result = await execute_query(
            "SELECT type_szn_id, title, class, fraction FROM characters WHERE type_szn_id = $1",
            season_card_id
        )
        return result[0] if result else None
    except Exception as e:
        logger.error(f"Failed to get character for season_card_id {season_card_id}: {e}")
        return None

async def get_all_characters() -> list:
    """Get all characters"""
    try:
        result = await execute_query(
            "SELECT type_szn_id, title, class, fraction FROM characters ORDER BY type_szn_id"
        )
        return result
    except Exception as e:
        logger.error(f"Failed to get all characters: {e}")
        return []

# ============================================================================
# NEW: TOKEN CACHE HELPER FUNCTIONS
# ============================================================================

async def get_contract_address_by_name(contract_name: str) -> str:
    """Get contract address by name from database"""
    try:
        result = await execute_query(
            "SELECT address FROM smart_contracts WHERE name = $1 AND is_active = TRUE",
            contract_name
        )
        return result[0]['address'] if result else None
    except Exception as e:
        logger.error(f"Failed to get contract address for {contract_name}: {e}")
        return None

async def get_weapon_name_by_stats(weapon_tier: int, weapon_type: int, weapon_subtype: int, category: int) -> str:
    """Get weapon name from mapping table"""
    try:
        result = await execute_query(
            """SELECT weapon_name FROM weapon_mappings 
               WHERE weapon_tier = $1 AND weapon_type = $2 
               AND weapon_subtype = $3 AND category = $4""",
            weapon_tier, weapon_type, weapon_subtype, category
        )
        return result[0]['weapon_name'] if result else None
    except Exception as e:
        logger.error(f"Failed to get weapon name for {weapon_tier}/{weapon_type}/{weapon_subtype}/{category}: {e}")
        return None

async def get_token_cache_statistics() -> dict:
    """Get token cache statistics"""
    try:
        result = await execute_query("SELECT * FROM get_cache_statistics()")
        if result:
            stats = result[0]
            return {
                "heroes_cached": stats['heroes_cached'],
                "weapons_cached": stats['weapons_cached'],
                "heroes_invalid": stats['heroes_invalid'],
                "weapons_invalid": stats['weapons_invalid'],
                "total_errors": stats['total_errors'],
                "unresolved_errors": stats['unresolved_errors']
            }
        return {}
    except Exception as e:
        logger.error(f"Failed to get cache statistics: {e}")
        return {}

async def invalidate_cache_entries(days_old: int = 30) -> int:
    """Invalidate old cache entries"""
    try:
        result = await execute_query("SELECT invalidate_old_cache_entries($1)", days_old)
        return result[0] if result else 0
    except Exception as e:
        logger.error(f"Failed to invalidate cache entries: {e}")
        return 0

# Cleanup function
async def close_db_pool():
    """Close database connection pool"""
    global _connection_pool
    if _connection_pool:
        await _connection_pool.close()
        _connection_pool = None
        logger.info("Database connection pool closed")