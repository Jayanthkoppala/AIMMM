"""
Database initialization - creates CoinGecko tables.
"""
from app.utils.database import db_connection
from app.utils.logger import logger


def reset_sequence():
    """Reset ohlcv_candles_id_seq to continue from max ID (or start at 1 if no data)."""
    if not db_connection.pool:
        return
    
    try:
        # Check if sequence exists
        seq_exists_query = """
            SELECT EXISTS (
                SELECT 1 FROM pg_class WHERE relname = 'ohlcv_candles_id_seq'
            ) as exists
        """
        seq_exists_result = db_connection.execute_query(seq_exists_query, fetch_one=True)
        seq_exists = seq_exists_result.get('exists', False) if seq_exists_result else False
        
        if not seq_exists:
            # Sequence doesn't exist, create it
            # First get the current max ID to set as starting point
            max_id_query = "SELECT COALESCE(MAX(id), 0) as max_id FROM ohlcv_candles"
            max_result = db_connection.execute_query(max_id_query, fetch_one=True)
            max_id = max_result.get('max_id', 0) if max_result else 0
            
            # Create sequence starting from max_id + 1 (or 1 if no data)
            start_value = max_id + 1 if max_id > 0 else 1
            create_seq_query = f"""
                CREATE SEQUENCE IF NOT EXISTS ohlcv_candles_id_seq
                START WITH {start_value}
                INCREMENT BY 1
                NO MINVALUE
                NO MAXVALUE
                CACHE 1
            """
            db_connection.execute_query(create_seq_query, fetch_all=False)
            
            # Set the table's default to use this sequence
            alter_table_query = """
                ALTER TABLE ohlcv_candles 
                ALTER COLUMN id SET DEFAULT nextval('ohlcv_candles_id_seq')
            """
            db_connection.execute_query(alter_table_query, fetch_all=False)
            
            logger.info(f"Created ohlcv_candles_id_seq starting from ID {start_value} (max existing ID: {max_id})")
        else:
            # Sequence exists, just reset it
            max_id_query = "SELECT COALESCE(MAX(id), 0) as max_id FROM ohlcv_candles"
            max_result = db_connection.execute_query(max_id_query, fetch_one=True)
            max_id = max_result.get('max_id', 0) if max_result else 0
            
            # Set sequence to max_id + 1 (or 1 if no data)
            next_id = max_id + 1 if max_id > 0 else 1
            reset_seq_query = f"SELECT setval('ohlcv_candles_id_seq', {next_id}, false)"
            db_connection.execute_query(reset_seq_query, fetch_all=False)
            
            logger.info(f"Reset ohlcv_candles_id_seq to start from ID {next_id} (max existing ID: {max_id})")
    except Exception as e:
        logger.warning(f"Could not reset ohlcv_candles sequence: {e}")


def init_users_table() -> bool:
    """
    Initialize users table for proper user management.
    Returns True if successful, False otherwise.
    """
    if not db_connection.pool:
        logger.warning("Database connection not available, cannot initialize users table")
        return False
    
    try:
        logger.info("Creating users table...")
        
        # Create users table
        create_users_query = """
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_identifier VARCHAR(255) NOT NULL UNIQUE,
                privy_user_id VARCHAR(255),
                email VARCHAR(255),
                wallet_address VARCHAR(255),
                session_id VARCHAR(255),
                auth_method VARCHAR(50) NOT NULL DEFAULT 'wallet',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                last_active TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """
        result = db_connection.execute_query(create_users_query, fetch_all=False)
        if result is None:
            logger.error("Failed to create users table")
            return False
        logger.info("Created users table")
        
        # Add email column if it doesn't exist (migration)
        try:
            alter_email_query = """
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS email VARCHAR(255)
            """
            db_connection.execute_query(alter_email_query, fetch_all=False)
            logger.info("Added email column to users table (if not exists)")
        except Exception as e:
            logger.warning(f"Error adding email column (may already exist): {e}")
        
        # Create indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_identifier ON users(user_identifier)",
            "CREATE INDEX IF NOT EXISTS idx_users_privy_id ON users(privy_user_id) WHERE privy_user_id IS NOT NULL",
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email) WHERE email IS NOT NULL",
            "CREATE INDEX IF NOT EXISTS idx_users_wallet ON users(wallet_address) WHERE wallet_address IS NOT NULL",
            "CREATE INDEX IF NOT EXISTS idx_users_session ON users(session_id) WHERE session_id IS NOT NULL"
        ]
        
        for idx_query in indexes:
            try:
                db_connection.execute_query(idx_query, fetch_all=False)
            except Exception as e:
                logger.warning(f"Error creating index (may already exist): {e}")
        
        logger.info("Users table initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing users table: {e}", exc_info=True)
        return False


def init_strategy_tables() -> bool:
    """
    Initialize strategy builder tables: user_strategies, strategy_executions, paper_trading_balances.
    Returns True if successful, False otherwise.
    """
    if not db_connection.pool:
        logger.warning("Database connection not available, cannot initialize strategy tables")
        return False
    
    try:
        logger.info("Creating strategy builder tables...")
        
        # Ensure users table exists first
        init_users_table()
        
        # 1. Create user_strategies table with foreign key to users
        create_strategies_query = """
            CREATE TABLE IF NOT EXISTS user_strategies (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                wallet_address VARCHAR(255),
                name VARCHAR(200) NOT NULL,
                description TEXT,
                visibility VARCHAR(20) DEFAULT 'private',
                is_active BOOLEAN DEFAULT FALSE,
                pool_id INTEGER REFERENCES pools(id) ON DELETE SET NULL,
                pool_address TEXT,
                strategy_config JSONB NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                last_execution TIMESTAMP WITH TIME ZONE,
                execution_interval INTEGER DEFAULT 5
            )
        """
        result = db_connection.execute_query(create_strategies_query, fetch_all=False)
        if result is None:
            logger.error("Failed to create user_strategies table")
            return False
        logger.info("Created user_strategies table")
        
        # Migration: Handle existing user_id column if it's VARCHAR
        try:
            # Check if user_id column exists and its type
            check_type_query = """
                SELECT data_type, column_name
                FROM information_schema.columns 
                WHERE table_name = 'user_strategies' 
                AND column_name = 'user_id'
            """
            type_check = db_connection.execute_query(check_type_query, fetch_one=True)
            
            if type_check and type_check.get('data_type') == 'character varying':
                logger.info("Migrating user_strategies.user_id from VARCHAR to UUID...")
                # Step 1: Add new UUID column
                alter_add_uuid = """
                    ALTER TABLE user_strategies 
                    ADD COLUMN IF NOT EXISTS user_id_uuid UUID REFERENCES users(id) ON DELETE CASCADE
                """
                db_connection.execute_query(alter_add_uuid, fetch_all=False)
                
                # Step 2: Migrate data - create users for existing user_ids and link them
                migrate_query = """
                    INSERT INTO users (id, user_identifier, auth_method, created_at)
                    SELECT gen_random_uuid(), user_id, 'legacy', NOW()
                    FROM (SELECT DISTINCT user_id FROM user_strategies WHERE user_id_uuid IS NULL) AS distinct_users
                    ON CONFLICT (user_identifier) DO NOTHING
                """
                db_connection.execute_query(migrate_query, fetch_all=False)
                
                # Step 3: Update user_strategies to link to users
                update_link_query = """
                    UPDATE user_strategies us
                    SET user_id_uuid = u.id
                    FROM users u
                    WHERE us.user_id = u.user_identifier
                    AND us.user_id_uuid IS NULL
                """
                db_connection.execute_query(update_link_query, fetch_all=False)
                
                # Step 4: Drop old column and rename new one
                alter_drop_old = "ALTER TABLE user_strategies DROP COLUMN IF EXISTS user_id"
                db_connection.execute_query(alter_drop_old, fetch_all=False)
                
                alter_rename = "ALTER TABLE user_strategies RENAME COLUMN user_id_uuid TO user_id"
                db_connection.execute_query(alter_rename, fetch_all=False)
                
                logger.info("Migration completed: user_strategies.user_id is now UUID")
        except Exception as e:
            logger.warning(f"Error during user_id migration (may already be migrated): {e}")
        
        # Add pool columns if table already exists (migration)
        try:
            alter_query1 = """
                ALTER TABLE user_strategies 
                ADD COLUMN IF NOT EXISTS pool_id INTEGER REFERENCES pools(id) ON DELETE SET NULL
            """
            db_connection.execute_query(alter_query1, fetch_all=False)
            
            alter_query2 = """
                ALTER TABLE user_strategies 
                ADD COLUMN IF NOT EXISTS pool_address TEXT
            """
            db_connection.execute_query(alter_query2, fetch_all=False)
            logger.info("Added pool columns to user_strategies table (if not exists)")
        except Exception as e:
            logger.warning(f"Error adding pool columns (may already exist): {e}")
        
        # 2. Create strategy_executions table with foreign key to users
        create_executions_query = """
            CREATE TABLE IF NOT EXISTS strategy_executions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                strategy_id UUID NOT NULL REFERENCES user_strategies(id) ON DELETE CASCADE,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                execution_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                
                llm_model VARCHAR(100) NOT NULL,
                decision VARCHAR(20) NOT NULL,
                confidence DECIMAL(5, 4) NOT NULL,
                reasoning TEXT,
                
                execution_mode VARCHAR(20) NOT NULL,
                duration_seconds DECIMAL(10, 3),
                llm_cost DECIMAL(10, 6),
                
                trade_executed BOOLEAN DEFAULT FALSE,
                tx_hash VARCHAR(255),
                symbol VARCHAR(50),
                side VARCHAR(10),
                amount_in DECIMAL(20, 8),
                amount_out DECIMAL(20, 8),
                price DECIMAL(20, 8),
                
                market_data JSONB
            )
        """
        result = db_connection.execute_query(create_executions_query, fetch_all=False)
        if result is None:
            logger.error("Failed to create strategy_executions table")
            return False
        logger.info("Created strategy_executions table")
        
        # 3. Create paper_trading_balances table
        create_balances_query = """
            CREATE TABLE IF NOT EXISTS paper_trading_balances (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                strategy_id UUID NOT NULL REFERENCES user_strategies(id) ON DELETE CASCADE,
                token_address VARCHAR(255) NOT NULL,
                token_symbol VARCHAR(20) NOT NULL,
                balance DECIMAL(30, 8) NOT NULL DEFAULT 0,
                usd_value DECIMAL(20, 8),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                UNIQUE(strategy_id, token_address)
            )
        """
        result = db_connection.execute_query(create_balances_query, fetch_all=False)
        if result is None:
            logger.error("Failed to create paper_trading_balances table")
            return False
        logger.info("Created paper_trading_balances table")
        
        # Create indexes
        import time
        time.sleep(0.1)
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_strategies_user_id ON user_strategies(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_strategies_active ON user_strategies(is_active) WHERE is_active = TRUE",
            "CREATE INDEX IF NOT EXISTS idx_strategies_visibility ON user_strategies(visibility)",
            "CREATE INDEX IF NOT EXISTS idx_executions_strategy_id ON strategy_executions(strategy_id, execution_timestamp DESC)",
            "CREATE INDEX IF NOT EXISTS idx_executions_user_id ON strategy_executions(user_id, execution_timestamp DESC)",
            "CREATE INDEX IF NOT EXISTS idx_balances_strategy_id ON paper_trading_balances(strategy_id)"
        ]
        
        # Migration: Update existing user_id columns from VARCHAR to UUID if needed
        # This is a safe migration that won't break existing data
        try:
            # Check if user_strategies.user_id is already UUID type
            check_type_query = """
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name = 'user_strategies' 
                AND column_name = 'user_id'
            """
            type_check = db_connection.execute_query(check_type_query, fetch_one=True)
            if type_check and type_check.get('data_type') == 'character varying':
                logger.info("Migrating user_strategies.user_id from VARCHAR to UUID...")
                # This migration will be handled by get_or_create_user function
                logger.info("Migration will be handled automatically on first use")
        except Exception as e:
            logger.warning(f"Error checking user_id column type: {e}")
        
        for idx_query in indexes:
            try:
                result = db_connection.execute_query(idx_query, fetch_all=False)
                if result is None:
                    logger.warning(f"Failed to create index: {idx_query[:50]}...")
                else:
                    logger.debug(f"Created index: {idx_query[:50]}...")
            except Exception as e:
                logger.warning(f"Error creating index (may already exist): {e}")
        
        logger.info("Strategy builder tables initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing strategy builder tables: {e}", exc_info=True)
        return False


def init_coingecko_tables() -> bool:
    """
    Initialize CoinGecko tables: pools, ohlcv_candles, technical_indicators, sentiment_analysis,
    autonomous_wallets, user_trading_preferences.
    Returns True if successful, False otherwise.
    """
    if not db_connection.pool:
        logger.warning("Database connection not available, cannot initialize tables")
        return False
    
    try:
        logger.info("Creating CoinGecko tables...")
        
        # 1. Create pools table (with simple integer ID for readability)
        create_pools_query = """
            CREATE TABLE IF NOT EXISTS pools (
                id SERIAL PRIMARY KEY,
                pool_address TEXT NOT NULL UNIQUE,
                network TEXT NOT NULL DEFAULT 'movement',
                pool_name TEXT,
                token_a_symbol TEXT,
                token_a_address TEXT,
                token_b_symbol TEXT,
                token_b_address TEXT,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """
        result = db_connection.execute_query(create_pools_query, fetch_all=False)
        if result is None:
            logger.error("Failed to create pools table")
            return False
        logger.info("Created pools table")
        
        # 2. Create ohlcv_candles table
        # First check if table exists and has correct schema
        check_schema_query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'ohlcv_candles' 
            AND column_name = 'pool_id'
        """
        schema_check = db_connection.execute_query(check_schema_query, fetch_one=True)
        
        # If table exists but doesn't have pool_id, drop it
        if schema_check is None:
            # Table might exist with wrong schema, drop it
            drop_query = "DROP TABLE IF EXISTS ohlcv_candles CASCADE"
            db_connection.execute_query(drop_query, fetch_all=False)
            logger.info("Dropped existing ohlcv_candles table (wrong schema)")
        
        create_ohlcv_query = """
            CREATE TABLE IF NOT EXISTS ohlcv_candles (
                id BIGSERIAL PRIMARY KEY,
                pool_id INTEGER NOT NULL REFERENCES pools(id) ON DELETE CASCADE,
                pool_name TEXT,
                timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                open_price NUMERIC NOT NULL,
                high_price NUMERIC NOT NULL,
                low_price NUMERIC NOT NULL,
                close_price NUMERIC NOT NULL,
                volume NUMERIC DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                UNIQUE(pool_id, timestamp)
            )
        """
        result = db_connection.execute_query(create_ohlcv_query, fetch_all=False)
        if result is None:
            logger.error("Failed to create ohlcv_candles table")
            return False
        logger.info("Created ohlcv_candles table")
        
        # Always reset sequence to continue from max ID (or start at 1 if no data)
        reset_sequence()
        
        # Verify pool_id column exists
        verify_query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'ohlcv_candles' 
            AND column_name = 'pool_id'
        """
        verify_result = db_connection.execute_query(verify_query, fetch_one=True)
        if verify_result is None:
            logger.error("ohlcv_candles table created but pool_id column is missing!")
            return False
        
        # 3. Create technical_indicators table
        # Check if table exists and has correct schema
        check_indicators_schema = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'technical_indicators' 
            AND column_name = 'pool_id'
        """
        indicators_schema_check = db_connection.execute_query(check_indicators_schema, fetch_one=True)
        
        # Check if table has the old normalized schema (indicator_name, indicator_value columns)
        check_old_schema = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'technical_indicators' 
            AND column_name IN ('indicator_name', 'indicator_value')
        """
        old_schema_check = db_connection.execute_query(check_old_schema, fetch_all=True)
        
        # If table exists with old schema (has indicator_name/indicator_value), drop it
        if old_schema_check and len(old_schema_check) > 0:
            drop_query = "DROP TABLE IF EXISTS technical_indicators CASCADE"
            db_connection.execute_query(drop_query, fetch_all=False)
            logger.info("Dropped existing technical_indicators table (old normalized schema, recreating with wide schema)")
        # If table exists but doesn't have pool_id, drop it
        elif indicators_schema_check is None:
            drop_query = "DROP TABLE IF EXISTS technical_indicators CASCADE"
            db_connection.execute_query(drop_query, fetch_all=False)
            logger.info("Dropped existing technical_indicators table (wrong schema)")
        
        create_indicators_query = """
            CREATE TABLE IF NOT EXISTS technical_indicators (
                id BIGSERIAL PRIMARY KEY,
                pool_id INTEGER NOT NULL REFERENCES pools(id) ON DELETE CASCADE,
                candle_id BIGINT REFERENCES ohlcv_candles(id) ON DELETE CASCADE,
                timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                timeframe TEXT NOT NULL DEFAULT '1m',
                
                -- Volume Indicators (10)
                mfi DOUBLE PRECISION,
                adi DOUBLE PRECISION,
                obv DOUBLE PRECISION,
                cmf DOUBLE PRECISION,
                fi DOUBLE PRECISION,
                eom DOUBLE PRECISION,
                eom_sma DOUBLE PRECISION,
                vpt DOUBLE PRECISION,
                nvi DOUBLE PRECISION,
                vwap DOUBLE PRECISION,
                
                -- Volatility Indicators (20)
                atr DOUBLE PRECISION,
                bb_hband DOUBLE PRECISION,
                bb_hband_indicator DOUBLE PRECISION,
                bb_lband DOUBLE PRECISION,
                bb_lband_indicator DOUBLE PRECISION,
                bb_mavg DOUBLE PRECISION,
                bb_pband DOUBLE PRECISION,
                bb_wband DOUBLE PRECISION,
                kc_hband DOUBLE PRECISION,
                kc_hband_indicator DOUBLE PRECISION,
                kc_lband DOUBLE PRECISION,
                kc_lband_indicator DOUBLE PRECISION,
                kc_mband DOUBLE PRECISION,
                kc_pband DOUBLE PRECISION,
                kc_wband DOUBLE PRECISION,
                dc_hband DOUBLE PRECISION,
                dc_lband DOUBLE PRECISION,
                dc_mband DOUBLE PRECISION,
                dc_pband DOUBLE PRECISION,
                dc_wband DOUBLE PRECISION,
                ui DOUBLE PRECISION,
                
                -- Trend Indicators (25)
                sma_20 DOUBLE PRECISION,
                sma_50 DOUBLE PRECISION,
                sma_200 DOUBLE PRECISION,
                ema_12 DOUBLE PRECISION,
                ema_26 DOUBLE PRECISION,
                ema_50 DOUBLE PRECISION,
                wma DOUBLE PRECISION,
                macd DOUBLE PRECISION,
                macd_signal DOUBLE PRECISION,
                macd_diff DOUBLE PRECISION,
                adx DOUBLE PRECISION,
                adx_neg DOUBLE PRECISION,
                adx_pos DOUBLE PRECISION,
                vi_neg DOUBLE PRECISION,
                vi_pos DOUBLE PRECISION,
                trix DOUBLE PRECISION,
                mass_index DOUBLE PRECISION,
                cci DOUBLE PRECISION,
                dpo DOUBLE PRECISION,
                kst DOUBLE PRECISION,
                kst_sig DOUBLE PRECISION,
                ichimoku_a DOUBLE PRECISION,
                ichimoku_b DOUBLE PRECISION,
                ichimoku_base_line DOUBLE PRECISION,
                ichimoku_conversion_line DOUBLE PRECISION,
                psar_down DOUBLE PRECISION,
                psar_down_indicator DOUBLE PRECISION,
                psar_up DOUBLE PRECISION,
                psar_up_indicator DOUBLE PRECISION,
                stc DOUBLE PRECISION,
                aroon_down DOUBLE PRECISION,
                aroon_up DOUBLE PRECISION,
                
                -- Momentum Indicators (15)
                rsi DOUBLE PRECISION,
                stochrsi DOUBLE PRECISION,
                stochrsi_d DOUBLE PRECISION,
                stochrsi_k DOUBLE PRECISION,
                tsi DOUBLE PRECISION,
                uo DOUBLE PRECISION,
                stoch DOUBLE PRECISION,
                stoch_signal DOUBLE PRECISION,
                williams_r DOUBLE PRECISION,
                ao DOUBLE PRECISION,
                kama DOUBLE PRECISION,
                roc DOUBLE PRECISION,
                ppo DOUBLE PRECISION,
                ppo_hist DOUBLE PRECISION,
                ppo_signal DOUBLE PRECISION,
                pvo DOUBLE PRECISION,
                pvo_hist DOUBLE PRECISION,
                pvo_signal DOUBLE PRECISION,
                
                -- Other Indicators (4)
                daily_return DOUBLE PRECISION,
                daily_log_return DOUBLE PRECISION,
                cumulative_return DOUBLE PRECISION,
                volume_sma_20 DOUBLE PRECISION,
                
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                UNIQUE(pool_id, timestamp, timeframe)
            )
        """
        result = db_connection.execute_query(create_indicators_query, fetch_all=False)
        if result is None:
            logger.error("Failed to create technical_indicators table")
            return False
        logger.info("Created technical_indicators table")
        
        # Verify pool_id column exists
        verify_indicators = db_connection.execute_query(check_indicators_schema, fetch_one=True)
        if verify_indicators is None:
            logger.error("technical_indicators table created but pool_id column is missing!")
            return False
        
        # 4. Create sentiment_analysis table
        create_sentiment_query = """
            CREATE TABLE IF NOT EXISTS sentiment_analysis (
                id BIGSERIAL PRIMARY KEY,
                pool_id INTEGER REFERENCES pools(id) ON DELETE CASCADE,
                token_a_address TEXT NOT NULL,
                token_b_address TEXT NOT NULL,
                token_a_symbol TEXT,
                token_b_symbol TEXT,
                token_a_sentiment_score DOUBLE PRECISION NOT NULL,
                token_a_sentiment_label TEXT NOT NULL,
                token_a_confidence DOUBLE PRECISION NOT NULL,
                token_a_key_factors JSONB,
                token_a_social_volume INTEGER DEFAULT 0,
                token_a_mentions_24h INTEGER DEFAULT 0,
                token_a_dominant_emotion TEXT,
                token_b_sentiment_score DOUBLE PRECISION NOT NULL,
                token_b_sentiment_label TEXT NOT NULL,
                token_b_confidence DOUBLE PRECISION NOT NULL,
                token_b_key_factors JSONB,
                token_b_social_volume INTEGER DEFAULT 0,
                token_b_mentions_24h INTEGER DEFAULT 0,
                token_b_dominant_emotion TEXT,
                timeframe TEXT NOT NULL DEFAULT '24h',
                analyzed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                UNIQUE(pool_id, analyzed_at)
            )
        """
        result = db_connection.execute_query(create_sentiment_query, fetch_all=False)
        if result is None:
            logger.error("Failed to create sentiment_analysis table")
            return False
        logger.info("Created sentiment_analysis table")
        
        # Migration: Add pool_id column if table already exists without it
        try:
            alter_sentiment_query = """
                ALTER TABLE sentiment_analysis 
                ADD COLUMN IF NOT EXISTS pool_id INTEGER REFERENCES pools(id) ON DELETE CASCADE
            """
            db_connection.execute_query(alter_sentiment_query, fetch_all=False)
            logger.info("Added pool_id column to sentiment_analysis table (if not exists)")
            
            # Update existing sentiment records to link with pools based on token addresses
            update_pool_id_query = """
                UPDATE sentiment_analysis sa
                SET pool_id = p.id
                FROM pools p
                WHERE sa.pool_id IS NULL
                AND sa.token_a_address = p.token_a_address
                AND sa.token_b_address = p.token_b_address
            """
            db_connection.execute_query(update_pool_id_query, fetch_all=False)
            logger.info("Updated existing sentiment records with pool_id")
        except Exception as e:
            logger.warning(f"Error migrating sentiment_analysis table (may already have pool_id): {e}")
        
        # 5. Create autonomous_wallets table
        create_autonomous_wallets_query = """
            CREATE TABLE IF NOT EXISTS autonomous_wallets (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                privy_user_id TEXT NOT NULL UNIQUE,
                wallet_address TEXT NOT NULL,
                encrypted_private_key TEXT NOT NULL,
                autonomous_enabled BOOLEAN DEFAULT FALSE,
                risk_per_trade DECIMAL(5,4) DEFAULT 0.02,
                max_position_size DECIMAL(5,4) DEFAULT 0.10,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """
        result = db_connection.execute_query(create_autonomous_wallets_query, fetch_all=False)
        if result is None:
            logger.error("Failed to create autonomous_wallets table")
            return False
        logger.info("Created autonomous_wallets table")
        
        # 6. Create user_trading_preferences table
        create_user_preferences_query = """
            CREATE TABLE IF NOT EXISTS user_trading_preferences (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                privy_user_id TEXT NOT NULL,
                preferred_pool_address TEXT,
                token_a_address TEXT,
                token_b_address TEXT,
                min_confidence_threshold DECIMAL(3,2) DEFAULT 0.70,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                FOREIGN KEY (privy_user_id) REFERENCES autonomous_wallets(privy_user_id) ON DELETE CASCADE
            )
        """
        result = db_connection.execute_query(create_user_preferences_query, fetch_all=False)
        if result is None:
            logger.error("Failed to create user_trading_preferences table")
            return False
        logger.info("Created user_trading_preferences table")
        
        # Create indexes (with error handling and small delay to ensure tables are committed)
        import time
        time.sleep(0.1)  # Small delay to ensure tables are committed
        
        # Drop old full index on is_active if it exists (replaced by partial index)
        try:
            drop_old_index_query = "DROP INDEX IF EXISTS idx_pools_active"
            db_connection.execute_query(drop_old_index_query, fetch_all=False)
            logger.debug("Dropped old idx_pools_active index (if it existed)")
        except Exception as e:
            logger.debug(f"Could not drop old idx_pools_active index (may not exist): {e}")
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_pools_address ON pools(pool_address)",
            # Partial index for active pools (more efficient than full index)
            "CREATE INDEX IF NOT EXISTS idx_pools_active ON pools(is_active) WHERE is_active = TRUE",
            # Composite index for efficient queries by pool and timestamp
            "CREATE INDEX IF NOT EXISTS idx_ohlcv_pool_timestamp ON ohlcv_candles(pool_id, timestamp DESC)",
            # Composite index for efficient queries by pool and timestamp
            "CREATE INDEX IF NOT EXISTS idx_indicators_pool_timestamp ON technical_indicators(pool_id, timestamp DESC)",
            # Index for foreign key lookups
            "CREATE INDEX IF NOT EXISTS idx_indicators_candle_id ON technical_indicators(candle_id)",
            # Sentiment analysis indexes
            "CREATE INDEX IF NOT EXISTS idx_sentiment_pool_id ON sentiment_analysis(pool_id)",
            "CREATE INDEX IF NOT EXISTS idx_sentiment_analyzed_at ON sentiment_analysis(analyzed_at DESC)",
            # Autonomous wallets indexes
            "CREATE INDEX IF NOT EXISTS idx_autonomous_wallets_privy_user ON autonomous_wallets(privy_user_id)",
            "CREATE INDEX IF NOT EXISTS idx_autonomous_wallets_enabled ON autonomous_wallets(autonomous_enabled) WHERE autonomous_enabled = TRUE"
        ]
        
        for idx_query in indexes:
            try:
                result = db_connection.execute_query(idx_query, fetch_all=False)
                if result is None:
                    logger.warning(f"Failed to create index: {idx_query[:50]}...")
                else:
                    logger.debug(f"Created index: {idx_query[:50]}...")
            except Exception as e:
                # Index might already exist or table structure issue
                logger.warning(f"Error creating index (may already exist): {e}")
        
        # Seed default pools
        seed_default_pools()
        
        logger.info("CoinGecko tables initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing CoinGecko tables: {e}", exc_info=True)
        return False


def seed_default_pools():
    """
    Seed the database with default trading pools.
    Uses INSERT ... ON CONFLICT to avoid duplicates.
    """
    if not db_connection.pool:
        logger.warning("Database connection not available, cannot seed pools")
        return
    
    default_pools = [
        {
            "pool_address": "0x83193fdc4d23fca53b2a36aef082886f4ef1c345a2c721b31c6e90a51173014d",
            "pool_name": "USDC.e / WETH.e",
            "token_a_symbol": "USDC.e",
            "token_a_address": "0x83121c9f9b0527d1f056e21a950d6bf3b9e9e2e8353d0e95ccea726713cbea39",
            "token_b_symbol": "WETH.e",
            "token_b_address": "0x908828f4fb0213d4034c3ded1630bbd904e8a3a6bf3c63270887f0b06653a376"
        },
        {
            "pool_address": "0xbcbf55e1004687d412f05856ef7c17dcaacc1be632ba2d67b71073d25b425c3b",
            "pool_name": "USDC.e / MOVE",
            "token_a_symbol": "USDC.e",
            "token_a_address": "0x83121c9f9b0527d1f056e21a950d6bf3b9e9e2e8353d0e95ccea726713cbea39",
            "token_b_symbol": "MOVE",
            "token_b_address": "0x000000000000000000000000000000000000000a"
        }
    ]
    
    try:
        insert_query = """
            INSERT INTO pools (
                pool_address, network, pool_name, 
                token_a_symbol, token_a_address, 
                token_b_symbol, token_b_address,
                is_active
            ) VALUES (
                %s, 'movement', %s, %s, %s, %s, %s, TRUE
            )
            ON CONFLICT (pool_address) 
            DO UPDATE SET 
                pool_name = EXCLUDED.pool_name,
                token_a_symbol = EXCLUDED.token_a_symbol,
                token_a_address = EXCLUDED.token_a_address,
                token_b_symbol = EXCLUDED.token_b_symbol,
                token_b_address = EXCLUDED.token_b_address,
                is_active = TRUE,
                updated_at = NOW()
            RETURNING id
        """
        
        for pool in default_pools:
            params = (
                pool["pool_address"],
                pool["pool_name"],
                pool["token_a_symbol"],
                pool["token_a_address"],
                pool["token_b_symbol"],
                pool["token_b_address"]
            )
            result = db_connection.execute_query(insert_query, params, fetch_one=True)
            if result:
                logger.info(f"Seeded pool: {pool['pool_name']} (id: {result.get('id')})")
            else:
                logger.warning(f"Failed to seed pool: {pool['pool_name']}")
        
        logger.info(f"Seeded {len(default_pools)} default pools")
        
    except Exception as e:
        logger.error(f"Error seeding default pools: {e}", exc_info=True)

