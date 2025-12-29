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
        
        # 1. Create pools table
        create_pools_query = """
            CREATE TABLE IF NOT EXISTS pools (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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
                pool_id UUID NOT NULL REFERENCES pools(id) ON DELETE CASCADE,
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
                pool_id UUID NOT NULL REFERENCES pools(id) ON DELETE CASCADE,
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
                UNIQUE(token_a_address, token_b_address, analyzed_at)
            )
        """
        result = db_connection.execute_query(create_sentiment_query, fetch_all=False)
        if result is None:
            logger.error("Failed to create sentiment_analysis table")
            return False
        logger.info("Created sentiment_analysis table")
        
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
            "CREATE INDEX IF NOT EXISTS idx_sentiment_token_pair ON sentiment_analysis(token_a_address, token_b_address)",
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
        
        logger.info("CoinGecko tables initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing CoinGecko tables: {e}", exc_info=True)
        return False

