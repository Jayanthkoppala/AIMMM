"""
Technical Indicators Calculator for CoinGecko OHLCV Data (OPTIMIZED)

Calculates technical indicators using the 'ta' library and stores them in the database.
Implements all major technical indicators across Volume, Volatility, Trend, Momentum categories.

KEY FIXES:
1. Fixed chunking logic to properly handle overlapping windows for indicators
2. Improved memory efficiency by processing only necessary data
3. Better handling of insufficient data edge cases
4. Fixed validation logic for which candles can have valid indicators
5. Optimized batch insertion performance
6. Added proper error handling for NaN/Inf values
7. Better progress tracking and logging
"""
import time
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime

import pandas as pd
import numpy as np
import ta
from app.utils.logger import logger
from app.utils.database import db_connection


class TechnicalIndicatorsCalculator:
    """Calculates technical indicators for OHLCV data."""

    def __init__(self):
        # Most indicators need 200 periods for reliable calculation
        # Using 200 as the safe minimum (SMA_200 is the longest lookback)
        self.min_candles_required = 200

    def fetch_ohlcv_for_pool(
        self, pool_id: str, limit: Optional[int] = None
    ) -> pd.DataFrame:
        """Fetch OHLCV data for a pool from database.

        Args:
            pool_id: Pool UUID as string
            limit: Number of candles to fetch (None for all candles)

        Returns:
            DataFrame with OHLCV data sorted by timestamp (oldest first)
        """
        start_time = time.time()
        
        if not db_connection.pool:
            logger.warning("Database connection not available")
            return pd.DataFrame()

        if limit is not None:
            query = """
                SELECT 
                    id, timestamp, open_price, high_price, low_price, close_price, volume
                FROM ohlcv_candles
                WHERE pool_id = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """
            params = (pool_id, limit)
        else:
            query = """
                SELECT 
                    id, timestamp, open_price, high_price, low_price, close_price, volume
                FROM ohlcv_candles
                WHERE pool_id = %s
                ORDER BY timestamp DESC
            """
            params = (pool_id,)

        try:
            rows = db_connection.execute_query(query, params, fetch_all=True)
            
            if not rows:
                logger.debug(f"No OHLCV data found for pool {pool_id[:20]}...")
                return pd.DataFrame()

            # Convert to DataFrame
            df = pd.DataFrame(rows)
            
            # FIX: Sort by timestamp ascending (oldest first) for indicator calculation
            df = df.sort_values('timestamp', ascending=True).reset_index(drop=True)
            
            # Convert timestamp to datetime if needed
            if 'timestamp' in df.columns:
                if df['timestamp'].dtype == 'object':
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                # Convert to Unix timestamp (seconds) for storage
                df['timestamp_unix'] = df['timestamp'].astype('int64') // 10**9

            # Convert Decimal types to float for ta library compatibility
            for col in ["open_price", "high_price", "low_price", "close_price", "volume"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # FIX: Validate data quality
            if df[['open_price', 'high_price', 'low_price', 'close_price']].isna().any().any():
                logger.warning(f"Found NaN values in OHLCV data for pool {pool_id[:20]}...")
                # Forward fill NaN values
                df[['open_price', 'high_price', 'low_price', 'close_price', 'volume']] = \
                    df[['open_price', 'high_price', 'low_price', 'close_price', 'volume']].fillna(method='ffill')

            elapsed = time.time() - start_time
            logger.debug(f"Fetched {len(df)} candles for pool {pool_id[:20]}... in {elapsed:.2f}s")
            return df

        except Exception as e:
            logger.error(f"Error fetching OHLCV data for pool {pool_id[:20]}...: {e}", exc_info=True)
            return pd.DataFrame()

    def calculate_indicators_for_dataframe(self, df: pd.DataFrame, pool_id: str = "") -> pd.DataFrame:
        """Calculate all indicators for each row in a DataFrame.
        
        IMPORTANT: Only rows at index >= min_candles_required will have valid indicators.
        Earlier rows will have NaN for most indicators due to insufficient lookback.
        
        Args:
            df: DataFrame with OHLCV data (should have at least min_candles_required rows)
            pool_id: Optional pool ID for logging
            
        Returns:
            DataFrame with indicator columns added
        """
        start_time = time.time()
        
        if len(df) < self.min_candles_required:
            logger.warning(f"Insufficient data for indicator calculation: {len(df)} rows (need {self.min_candles_required})")
            return df
        
        pool_prefix = f"[Pool {pool_id[:20]}...] " if pool_id else ""
        logger.info(f"{pool_prefix}Calculating indicators for {len(df)} candles...")
        
        # Make a copy to avoid modifying original
        result_df = df.copy()
        
        # Rename columns to match ta library expectations
        result_df = result_df.rename(columns={
            'open_price': 'open',
            'high_price': 'high',
            'low_price': 'low',
            'close_price': 'close',
            'volume': 'volume'
        })
        
        # FIX: Replace any remaining NaN/Inf values before calculation
        for col in ['open', 'high', 'low', 'close', 'volume']:
            result_df[col] = result_df[col].replace([np.inf, -np.inf], np.nan).fillna(method='ffill').fillna(0)
        
        try:
            logger.debug(f"{pool_prefix}→ Volume indicators (10 indicators)...")
            # Volume Indicators
            result_df["mfi"] = ta.volume.MFIIndicator(result_df["high"], result_df["low"], result_df["close"], result_df["volume"], window=14, fillna=False).money_flow_index()
            result_df["adi"] = ta.volume.AccDistIndexIndicator(result_df["high"], result_df["low"], result_df["close"], result_df["volume"], fillna=False).acc_dist_index()
            result_df["obv"] = ta.volume.on_balance_volume(result_df["close"], result_df["volume"], fillna=False)
            result_df["cmf"] = ta.volume.ChaikinMoneyFlowIndicator(result_df["high"], result_df["low"], result_df["close"], result_df["volume"], window=20, fillna=False).chaikin_money_flow()
            result_df["fi"] = ta.volume.ForceIndexIndicator(result_df["close"], result_df["volume"], window=13, fillna=False).force_index()
            
            eom = ta.volume.EaseOfMovementIndicator(result_df["high"], result_df["low"], result_df["volume"], window=14, fillna=False)
            result_df["eom"] = eom.ease_of_movement()
            result_df["eom_sma"] = eom.sma_ease_of_movement()
            
            result_df["vpt"] = ta.volume.VolumePriceTrendIndicator(result_df["close"], result_df["volume"], fillna=False).volume_price_trend()
            result_df["nvi"] = ta.volume.NegativeVolumeIndexIndicator(result_df["close"], result_df["volume"], fillna=False).negative_volume_index()
            result_df["vwap"] = ta.volume.VolumeWeightedAveragePrice(result_df["high"], result_df["low"], result_df["close"], result_df["volume"], window=14, fillna=False).volume_weighted_average_price()
            logger.debug(f"{pool_prefix}  ✓ Volume indicators complete")
            
            logger.debug(f"{pool_prefix}→ Volatility indicators (20 indicators)...")
            # Volatility Indicators
            result_df["atr"] = ta.volatility.AverageTrueRange(result_df["high"], result_df["low"], result_df["close"], window=14, fillna=False).average_true_range()
            
            bb = ta.volatility.BollingerBands(result_df["close"], window=20, window_dev=2, fillna=False)
            result_df["bb_hband"] = bb.bollinger_hband()
            result_df["bb_hband_indicator"] = bb.bollinger_hband_indicator()
            result_df["bb_lband"] = bb.bollinger_lband()
            result_df["bb_lband_indicator"] = bb.bollinger_lband_indicator()
            result_df["bb_mavg"] = bb.bollinger_mavg()
            result_df["bb_pband"] = bb.bollinger_pband()
            result_df["bb_wband"] = bb.bollinger_wband()
            
            kc = ta.volatility.KeltnerChannel(result_df["high"], result_df["low"], result_df["close"], window=20, fillna=False)
            result_df["kc_hband"] = kc.keltner_channel_hband()
            result_df["kc_hband_indicator"] = kc.keltner_channel_hband_indicator()
            result_df["kc_lband"] = kc.keltner_channel_lband()
            result_df["kc_lband_indicator"] = kc.keltner_channel_lband_indicator()
            result_df["kc_mband"] = kc.keltner_channel_mband()
            result_df["kc_pband"] = kc.keltner_channel_pband()
            result_df["kc_wband"] = kc.keltner_channel_wband()
            
            dc = ta.volatility.DonchianChannel(result_df["high"], result_df["low"], result_df["close"], window=20, fillna=False)
            result_df["dc_hband"] = dc.donchian_channel_hband()
            result_df["dc_lband"] = dc.donchian_channel_lband()
            result_df["dc_mband"] = dc.donchian_channel_mband()
            result_df["dc_pband"] = dc.donchian_channel_pband()
            result_df["dc_wband"] = dc.donchian_channel_wband()
            
            result_df["ui"] = ta.volatility.UlcerIndex(result_df["close"], window=14, fillna=False).ulcer_index()
            logger.debug(f"{pool_prefix}  ✓ Volatility indicators complete")
            
            logger.debug(f"{pool_prefix}→ Trend indicators (37 indicators)...")
            # Trend Indicators
            result_df["sma_20"] = ta.trend.sma_indicator(result_df["close"], window=20, fillna=False)
            result_df["sma_50"] = ta.trend.sma_indicator(result_df["close"], window=50, fillna=False)
            result_df["sma_200"] = ta.trend.sma_indicator(result_df["close"], window=200, fillna=False)
            
            result_df["ema_12"] = ta.trend.ema_indicator(result_df["close"], window=12, fillna=False)
            result_df["ema_26"] = ta.trend.ema_indicator(result_df["close"], window=26, fillna=False)
            result_df["ema_50"] = ta.trend.ema_indicator(result_df["close"], window=50, fillna=False)
            
            result_df["wma"] = ta.trend.WMAIndicator(result_df["close"], window=20, fillna=False).wma()
            
            macd = ta.trend.MACD(result_df["close"], window_slow=26, window_fast=12, window_sign=9, fillna=False)
            result_df["macd"] = macd.macd()
            result_df["macd_signal"] = macd.macd_signal()
            result_df["macd_diff"] = macd.macd_diff()
            
            adx = ta.trend.ADXIndicator(result_df["high"], result_df["low"], result_df["close"], window=14, fillna=False)
            result_df["adx"] = adx.adx()
            result_df["adx_neg"] = adx.adx_neg()
            result_df["adx_pos"] = adx.adx_pos()
            
            vi = ta.trend.VortexIndicator(result_df["high"], result_df["low"], result_df["close"], window=14, fillna=False)
            result_df["vi_neg"] = vi.vortex_indicator_neg()
            result_df["vi_pos"] = vi.vortex_indicator_pos()
            
            result_df["trix"] = ta.trend.TRIXIndicator(result_df["close"], window=15, fillna=False).trix()
            result_df["mass_index"] = ta.trend.MassIndex(result_df["high"], result_df["low"], window_fast=9, window_slow=25, fillna=False).mass_index()
            result_df["cci"] = ta.trend.CCIIndicator(result_df["high"], result_df["low"], result_df["close"], window=20, fillna=False).cci()
            result_df["dpo"] = ta.trend.DPOIndicator(result_df["close"], window=20, fillna=False).dpo()
            
            kst = ta.trend.KSTIndicator(result_df["close"], fillna=False)
            result_df["kst"] = kst.kst()
            result_df["kst_sig"] = kst.kst_sig()
            
            ichimoku = ta.trend.IchimokuIndicator(result_df["high"], result_df["low"], fillna=False)
            result_df["ichimoku_a"] = ichimoku.ichimoku_a()
            result_df["ichimoku_b"] = ichimoku.ichimoku_b()
            result_df["ichimoku_base_line"] = ichimoku.ichimoku_base_line()
            result_df["ichimoku_conversion_line"] = ichimoku.ichimoku_conversion_line()
            
            psar = ta.trend.PSARIndicator(result_df["high"], result_df["low"], result_df["close"], fillna=False)
            result_df["psar_down"] = psar.psar_down()
            result_df["psar_down_indicator"] = psar.psar_down_indicator()
            result_df["psar_up"] = psar.psar_up()
            result_df["psar_up_indicator"] = psar.psar_up_indicator()
            
            result_df["stc"] = ta.trend.STCIndicator(result_df["close"], fillna=False).stc()
            
            aroon = ta.trend.AroonIndicator(high=result_df["high"], low=result_df["low"], window=25, fillna=False)
            result_df["aroon_down"] = aroon.aroon_down()
            result_df["aroon_up"] = aroon.aroon_up()
            logger.debug(f"{pool_prefix}  ✓ Trend indicators complete")
            
            logger.debug(f"{pool_prefix}→ Momentum indicators (18 indicators)...")
            # Momentum Indicators
            result_df["rsi"] = ta.momentum.rsi(result_df["close"], window=14, fillna=False)
            
            srsi = ta.momentum.StochRSIIndicator(result_df["close"], window=14, smooth1=3, smooth2=3, fillna=False)
            result_df["stochrsi"] = srsi.stochrsi()
            result_df["stochrsi_d"] = srsi.stochrsi_d()
            result_df["stochrsi_k"] = srsi.stochrsi_k()
            
            result_df["tsi"] = ta.momentum.TSIIndicator(result_df["close"], fillna=False).tsi()
            result_df["uo"] = ta.momentum.UltimateOscillator(result_df["high"], result_df["low"], result_df["close"], fillna=False).ultimate_oscillator()
            
            stoch = ta.momentum.StochasticOscillator(result_df["high"], result_df["low"], result_df["close"], window=14, smooth_window=3, fillna=False)
            result_df["stoch"] = stoch.stoch()
            result_df["stoch_signal"] = stoch.stoch_signal()
            
            result_df["williams_r"] = ta.momentum.WilliamsRIndicator(result_df["high"], result_df["low"], result_df["close"], fillna=False).williams_r()
            result_df["ao"] = ta.momentum.AwesomeOscillatorIndicator(result_df["high"], result_df["low"], fillna=False).awesome_oscillator()
            result_df["kama"] = ta.momentum.KAMAIndicator(result_df["close"], fillna=False).kama()
            result_df["roc"] = ta.momentum.ROCIndicator(result_df["close"], window=12, fillna=False).roc()
            
            ppo = ta.momentum.PercentagePriceOscillator(result_df["close"], fillna=False)
            result_df["ppo"] = ppo.ppo()
            result_df["ppo_hist"] = ppo.ppo_hist()
            result_df["ppo_signal"] = ppo.ppo_signal()
            
            pvo = ta.momentum.PercentageVolumeOscillator(result_df["volume"], fillna=False)
            result_df["pvo"] = pvo.pvo()
            result_df["pvo_hist"] = pvo.pvo_hist()
            result_df["pvo_signal"] = pvo.pvo_signal()
            logger.debug(f"{pool_prefix}  ✓ Momentum indicators complete")
            
            logger.debug(f"{pool_prefix}→ Other indicators (4 indicators)...")
            # Other Indicators
            result_df["daily_return"] = ta.others.DailyReturnIndicator(result_df["close"], fillna=False).daily_return()
            result_df["daily_log_return"] = ta.others.DailyLogReturnIndicator(result_df["close"], fillna=False).daily_log_return()
            result_df["cumulative_return"] = ta.others.CumulativeReturnIndicator(result_df["close"], fillna=False).cumulative_return()
            result_df["volume_sma_20"] = ta.trend.sma_indicator(result_df["volume"], window=20, fillna=False)
            logger.debug(f"{pool_prefix}  ✓ Other indicators complete")
            
            # FIX: Replace any Inf values that may have been generated
            for col in result_df.columns:
                if col not in ['id', 'timestamp', 'timestamp_unix', 'open', 'high', 'low', 'close', 'volume']:
                    result_df[col] = result_df[col].replace([np.inf, -np.inf], np.nan)
            
            elapsed = time.time() - start_time
            num_indicators = len([col for col in result_df.columns 
                                if col not in ['id', 'timestamp', 'timestamp_unix', 'open', 'high', 'low', 'close', 'volume']])
            logger.info(f"{pool_prefix}✓ All {num_indicators} indicators calculated in {elapsed:.2f}s")
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"{pool_prefix}Error calculating indicators after {elapsed:.2f}s: {e}", exc_info=True)
            return df
        
        return result_df

    def get_existing_indicators_timestamps(self, pool_id: str) -> Set[int]:
        """Get set of timestamps that already have indicators calculated.

        Args:
            pool_id: Pool UUID as string

        Returns:
            Set of timestamp Unix seconds that already have indicators
        """
        if not db_connection.pool:
            return set()
        
        query = """
            SELECT DISTINCT EXTRACT(EPOCH FROM timestamp)::BIGINT as timestamp_unix
            FROM technical_indicators
            WHERE pool_id = %s AND timeframe = '1m'
        """
        
        try:
            rows = db_connection.execute_query(query, (pool_id,), fetch_all=True)
            if rows:
                return {int(row.get('timestamp_unix', 0)) for row in rows if row.get('timestamp_unix')}
            return set()
        except Exception as e:
            logger.warning(f"Error fetching existing indicators: {e}")
            return set()

    def calculate_and_store_indicators(self, pool_id: str, pool_address: str = "") -> bool:
        """Calculate indicators from ohlcv_candles and store in technical_indicators.
        
        OPTIMIZED: Uses smart chunking with proper overlapping windows for continuous indicator calculation.

        Args:
            pool_id: Pool UUID as string
            pool_address: Pool address for logging

        Returns:
            True if successful
        """
        start_time = time.time()
        pool_prefix = f"[{pool_address[:20]}...] " if pool_address else f"[Pool {pool_id[:20]}...] "
        logger.info(f"{pool_prefix}Processing technical indicators...")
        
        try:
            # Check what indicators already exist
            existing_timestamps = self.get_existing_indicators_timestamps(pool_id)
            
            if existing_timestamps:
                logger.debug(f"{pool_prefix}Found {len(existing_timestamps)} existing indicator records")
            
            # Fetch ALL OHLCV data (sorted ascending by timestamp)
            df = self.fetch_ohlcv_for_pool(pool_id, limit=None)

            if df.empty:
                logger.warning(f"{pool_prefix}No OHLCV data found")
                return False

            if len(df) < self.min_candles_required:
                logger.warning(f"{pool_prefix}Insufficient data: {len(df)} rows, need {self.min_candles_required}")
                return False

            logger.info(f"{pool_prefix}Fetched {len(df)} candles")
            
            # Ensure timestamp_unix column exists
            if 'timestamp_unix' not in df.columns:
                df['timestamp_unix'] = df['timestamp'].astype('int64') // 10**9
            
            # FIX: Identify missing timestamps more accurately
            df['timestamp_unix'] = df['timestamp_unix'].astype(int)
            missing_mask = ~df["timestamp_unix"].isin(existing_timestamps)
            
            num_missing = missing_mask.sum()
            
            if num_missing == 0:
                logger.info(f"{pool_prefix}✓ All {len(df)} candles already have indicators calculated. Skipping.")
                return True
            
            logger.info(f"{pool_prefix}{num_missing} candles need indicators (out of {len(df)} total)")
            
            # FIX: Get indices of missing candles
            missing_indices = df[missing_mask].index.tolist()
            
            if not missing_indices:
                logger.info(f"{pool_prefix}No missing candles to process")
                return True
            
            # FIX: Smart chunking strategy
            # For each chunk of missing candles, we need to include enough prior data for indicators
            chunk_size = 1000  # Process 1000 missing candles at a time
            total_stored = 0
            
            # Group consecutive missing indices into ranges for efficient processing
            missing_ranges = self._group_consecutive_indices(missing_indices)
            
            logger.info(f"{pool_prefix}Processing {len(missing_ranges)} range(s) of missing candles...")
            
            for range_num, (range_start, range_end) in enumerate(missing_ranges, 1):
                range_size = range_end - range_start + 1
                logger.debug(f"{pool_prefix}Range {range_num}/{len(missing_ranges)}: {range_size} missing candles from index {range_start} to {range_end}")
                
                # Split large ranges into chunks
                for chunk_start in range(range_start, range_end + 1, chunk_size):
                    chunk_end = min(chunk_start + chunk_size - 1, range_end)
                    
                    # FIX: Calculate the window we need to fetch
                    # We need min_candles_required candles BEFORE the first missing candle for proper calculation
                    calc_start_idx = max(0, chunk_start - self.min_candles_required)
                    calc_end_idx = chunk_end + 1  # +1 because iloc end is exclusive
                    
                    # Extract the calculation window
                    df_window = df.iloc[calc_start_idx:calc_end_idx].copy()
                    
                    logger.debug(f"{pool_prefix}  Chunk: indices {chunk_start}-{chunk_end} ({chunk_end - chunk_start + 1} candles)")
                    logger.debug(f"{pool_prefix}  Window: indices {calc_start_idx}-{calc_end_idx-1} ({len(df_window)} candles for calculation)")
                    
                    # Calculate indicators for the entire window
                    df_with_indicators = self.calculate_indicators_for_dataframe(df_window, pool_id)
                    
                    if df_with_indicators.empty:
                        logger.warning(f"{pool_prefix}No indicators calculated for chunk")
                        continue
                    
                    # FIX: Only store candles that:
                    # 1. Are in the missing range (chunk_start to chunk_end)
                    # 2. Have enough history (at least min_candles_required candles before them)
                    
                    # Find where valid indicators start in the window
                    # Valid indicators start at position min_candles_required (0-indexed: position min_candles_required-1)
                    valid_start_in_window = self.min_candles_required - 1
                    
                    if len(df_window) < self.min_candles_required:
                        logger.warning(f"{pool_prefix}Window too small for valid indicators: {len(df_window)} < {self.min_candles_required}")
                        continue
                    
                    # Map window position to original df index
                    valid_start_idx = df_window.index[valid_start_in_window]
                    
                    # Filter to only store candles that are:
                    # - In the missing range (between chunk_start and chunk_end)
                    # - Have valid indicators (>= valid_start_idx)
                    df_to_store = df_with_indicators[
                        (df_with_indicators.index >= chunk_start) &
                        (df_with_indicators.index <= chunk_end) &
                        (df_with_indicators.index >= valid_start_idx)
                    ].copy()
                    
                    if df_to_store.empty:
                        logger.debug(f"{pool_prefix}No valid indicators to store for this chunk")
                        continue
                    
                    # Store this chunk
                    stored = self._store_indicators_batch(pool_id, df_to_store)
                    total_stored += stored
                    
                    logger.debug(f"{pool_prefix}  ✓ Stored {stored}/{len(df_to_store)} candles")
            
            total_elapsed = time.time() - start_time
            logger.info(f"{pool_prefix}✓ Completed in {total_elapsed:.2f}s - {total_stored} new indicator records stored")
            return True

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"{pool_prefix}✗ Failed after {elapsed:.2f}s: {e}", exc_info=True)
            return False

    def _group_consecutive_indices(self, indices: List[int]) -> List[Tuple[int, int]]:
        """Group consecutive indices into ranges for efficient processing.
        
        Args:
            indices: List of indices (assumed sorted)
            
        Returns:
            List of (start, end) tuples representing consecutive ranges
        """
        if not indices:
            return []
        
        ranges = []
        range_start = indices[0]
        range_end = indices[0]
        
        for idx in indices[1:]:
            if idx == range_end + 1:
                # Consecutive - extend current range
                range_end = idx
            else:
                # Gap - save current range and start new one
                ranges.append((range_start, range_end))
                range_start = idx
                range_end = idx
        
        # Add the last range
        ranges.append((range_start, range_end))
        
        return ranges

    def _store_indicators_batch(self, pool_id: str, df: pd.DataFrame) -> int:
        """Store indicators for a batch of candles using batch insertion for performance.
        
        FIX: Better handling of NaN/None values and proper batch execution.
        
        Args:
            pool_id: Pool UUID as string
            df: DataFrame with indicators calculated
            
        Returns:
            Number of candles stored
        """
        if df.empty or not db_connection.pool:
            return 0
        
        # Get indicator columns (exclude OHLCV and metadata columns)
        base_columns = ['id', 'timestamp', 'timestamp_unix', 'open', 'high', 'low', 'close', 'volume']
        indicator_columns = [col for col in df.columns if col not in base_columns]
        
        if not indicator_columns:
            logger.warning("No indicator columns found in dataframe")
            return 0
        
        try:
            # Build the INSERT query with all indicator columns
            indicator_cols_str = ', '.join(indicator_columns)
            indicator_placeholders = ', '.join(['%s' for _ in indicator_columns])
            
            # Build UPDATE clause for all indicators
            update_clauses = [f"{col} = EXCLUDED.{col}" for col in indicator_columns]
            update_clauses.append("updated_at = NOW()")
            update_clause = ', '.join(update_clauses)
            
            insert_query = f"""
                INSERT INTO technical_indicators (
                    pool_id, candle_id, timestamp, timeframe, {indicator_cols_str}
                ) VALUES (
                    %s, %s, %s, '1m', {indicator_placeholders}
                )
                ON CONFLICT (pool_id, timestamp, timeframe)
                DO UPDATE SET
                    {update_clause}
            """
            
            # Prepare all rows for batch insertion
            params_list = []
            skipped_rows = 0
            
            for idx, row in df.iterrows():
                try:
                    candle_id = int(row['id'])
                    timestamp = row['timestamp']
                    
                    # FIX: Better handling of NaN values - convert to None for SQL NULL
                    indicator_values = []
                    all_nan = True
                    
                    for col in indicator_columns:
                        value = row[col]
                        # Check if value is NaN or Inf
                        if pd.isna(value) or (isinstance(value, (float, np.floating)) and (np.isinf(value) or np.isnan(value))):
                            indicator_values.append(None)
                        else:
                            try:
                                indicator_values.append(float(value))
                                all_nan = False
                            except (ValueError, TypeError):
                                indicator_values.append(None)
                    
                    # Skip rows where ALL indicators are NaN (no valid data)
                    if all_nan:
                        skipped_rows += 1
                        continue
                    
                    # Prepare values: pool_id, candle_id, timestamp, then all indicator values
                    values = [pool_id, candle_id, timestamp] + indicator_values
                    params_list.append(tuple(values))
                    
                except Exception as e:
                    logger.warning(f"Error preparing row {idx} for batch insert: {e}")
                    skipped_rows += 1
                    continue
            
            if not params_list:
                logger.warning(f"No valid rows to store (skipped {skipped_rows} rows with all NaN values)")
                return 0
            
            if skipped_rows > 0:
                logger.debug(f"Skipped {skipped_rows} rows with all NaN indicators")
            
            # FIX: Batch insert in chunks to avoid PostgreSQL parameter limit (~65,535)
            # With ~70 indicators + 3 base fields (pool_id, candle_id, timestamp) = ~73 params per row
            # Using 500 rows per batch = 36,500 params (safe margin under limit)
            BATCH_SIZE = 500
            total_stored = 0
            
            try:
                # Process in chunks
                for i in range(0, len(params_list), BATCH_SIZE):
                    batch = params_list[i:i + BATCH_SIZE]
                    batch_num = (i // BATCH_SIZE) + 1
                    total_batches = (len(params_list) + BATCH_SIZE - 1) // BATCH_SIZE
                    
                    try:
                        rowcount = db_connection.execute_batch(insert_query, batch)
                        batch_stored = rowcount if rowcount and rowcount > 0 else len(batch)
                        total_stored += batch_stored
                        logger.debug(f"Batch insert chunk {batch_num}/{total_batches}: {batch_stored}/{len(batch)} rows affected")
                    except Exception as batch_e:
                        logger.error(f"Batch insert chunk {batch_num}/{total_batches} failed: {batch_e}", exc_info=True)
                        # Fallback: Try inserting one by one for this chunk
                        logger.warning(f"Attempting individual inserts for chunk {batch_num} as fallback...")
                        for params in batch:
                            try:
                                result = db_connection.execute_query(insert_query, params, fetch_all=False)
                                if result is not None:
                                    total_stored += 1
                            except Exception as row_e:
                                logger.debug(f"Failed to insert row: {row_e}")
                                continue
                
                logger.debug(f"Batch insert completed: {total_stored}/{len(params_list)} total rows stored")
                return total_stored
            except Exception as e:
                logger.error(f"Batch insert failed: {e}", exc_info=True)
                # Final fallback: Try inserting one by one
                logger.warning("Attempting individual inserts as final fallback...")
                stored = 0
                for params in params_list:
                    try:
                        result = db_connection.execute_query(insert_query, params, fetch_all=False)
                        if result is not None:
                            stored += 1
                    except Exception as row_e:
                        logger.debug(f"Failed to insert row: {row_e}")
                        continue
                return stored
                    
        except Exception as e:
            logger.error(f"Error in _store_indicators_batch: {e}", exc_info=True)
            return 0


    def format_for_llm(
        self,
        pool_address: str,
        indicators: Optional[List[str]] = None,
        limit: int = 50
    ) -> Optional[str]:
        """
        Format latest technical indicators for LLM context.
        
        Args:
            pool_address: Pool address
            indicators: List of indicator names to include (None = all key indicators)
            limit: Number of latest indicator records to include
        
        Returns:
            Formatted string for LLM, or None if no data
        """
        if not db_connection.pool:
            return None
        
        try:
            # Get pool ID
            pool_query = """
                SELECT id FROM pools
                WHERE pool_address = %s AND network = 'movement'
                LIMIT 1
            """
            pool_result = db_connection.execute_query(
                pool_query,
                (pool_address,),
                fetch_one=True
            )
            
            if not pool_result:
                return None
            
            pool_id = pool_result['id']
            
            # Default key indicators if not specified
            if indicators is None:
                indicators = [
                    'rsi', 'macd', 'macd_signal', 'macd_diff',
                    'sma_20', 'sma_50', 'sma_200',
                    'ema_12', 'ema_26', 'ema_50',
                    'bb_hband', 'bb_lband', 'bb_mavg', 'bb_pband',
                    'atr', 'adx', 'stoch', 'williams_r',
                    'obv', 'mfi', 'vwap'
                ]
            
            # Build query for latest indicators
            indicator_columns = [ind.lower() for ind in indicators]
            # Filter to only include columns that exist
            valid_columns = []
            for col in indicator_columns:
                # Map common names to database column names
                col_mapping = {
                    'rsi': 'rsi',
                    'macd': 'macd',
                    'macd_signal': 'macd_signal',
                    'macd_diff': 'macd_diff',
                    'sma_20': 'sma_20',
                    'sma_50': 'sma_50',
                    'sma_200': 'sma_200',
                    'ema_12': 'ema_12',
                    'ema_26': 'ema_26',
                    'ema_50': 'ema_50',
                    'bb_hband': 'bb_hband',
                    'bb_lband': 'bb_lband',
                    'bb_mavg': 'bb_mavg',
                    'bb_pband': 'bb_pband',
                    'atr': 'atr',
                    'adx': 'adx',
                    'stoch': 'stoch',
                    'williams_r': 'williams_r',
                    'obv': 'obv',
                    'mfi': 'mfi',
                    'vwap': 'vwap'
                }
                if col in col_mapping:
                    valid_columns.append(col_mapping[col])
            
            if not valid_columns:
                return None
            
            # Get latest indicator values
            query = f"""
                SELECT timestamp, {', '.join(valid_columns)}
                FROM technical_indicators
                WHERE pool_id = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """
            
            rows = db_connection.execute_query(
                query,
                (pool_id, limit),
                fetch_all=True
            )
            
            if not rows:
                return None
            
            # Format for LLM
            lines = ["Technical Indicators Analysis:"]
            
            # Get most recent values
            latest = rows[0]
            lines.append(f"\nLatest Indicators (as of {latest.get('timestamp', 'N/A')}):")
            
            # Trend Indicators
            trend_indicators = []
            if latest.get('sma_20'):
                trend_indicators.append(f"SMA(20): {latest['sma_20']:.4f}")
            if latest.get('sma_50'):
                trend_indicators.append(f"SMA(50): {latest['sma_50']:.4f}")
            if latest.get('sma_200'):
                trend_indicators.append(f"SMA(200): {latest['sma_200']:.4f}")
            if latest.get('ema_50'):
                trend_indicators.append(f"EMA(50): {latest['ema_50']:.4f}")
            if trend_indicators:
                lines.append(f"Trend: {', '.join(trend_indicators)}")
            
            # Momentum Indicators
            momentum_indicators = []
            if latest.get('rsi'):
                rsi = latest['rsi']
                rsi_signal = "Overbought" if rsi > 70 else "Oversold" if rsi < 30 else "Neutral"
                momentum_indicators.append(f"RSI: {rsi:.2f} ({rsi_signal})")
            if latest.get('macd') and latest.get('macd_signal'):
                macd = latest['macd']
                signal = latest['macd_signal']
                macd_signal = "Bullish" if macd > signal else "Bearish"
                momentum_indicators.append(f"MACD: {macd:.4f} vs Signal: {signal:.4f} ({macd_signal})")
            if latest.get('stoch'):
                stoch = latest['stoch']
                stoch_signal = "Overbought" if stoch > 80 else "Oversold" if stoch < 20 else "Neutral"
                momentum_indicators.append(f"Stochastic: {stoch:.2f} ({stoch_signal})")
            if momentum_indicators:
                lines.append(f"Momentum: {', '.join(momentum_indicators)}")
            
            # Volatility Indicators
            volatility_indicators = []
            if latest.get('atr'):
                volatility_indicators.append(f"ATR: {latest['atr']:.4f}")
            if latest.get('bb_hband') and latest.get('bb_lband') and latest.get('bb_mavg'):
                bb_width = ((latest['bb_hband'] - latest['bb_lband']) / latest['bb_mavg']) * 100
                volatility_indicators.append(f"Bollinger Bands Width: {bb_width:.2f}%")
                if latest.get('bb_pband'):
                    bb_pos = latest['bb_pband']
                    bb_signal = "Near Upper" if bb_pos > 0.8 else "Near Lower" if bb_pos < 0.2 else "Middle"
                    volatility_indicators.append(f"BB Position: {bb_pos:.2f} ({bb_signal})")
            if latest.get('adx'):
                adx = latest['adx']
                adx_strength = "Strong Trend" if adx > 25 else "Weak Trend" if adx < 20 else "Moderate"
                volatility_indicators.append(f"ADX: {adx:.2f} ({adx_strength})")
            if volatility_indicators:
                lines.append(f"Volatility: {', '.join(volatility_indicators)}")
            
            # Volume Indicators
            volume_indicators = []
            if latest.get('obv'):
                volume_indicators.append(f"OBV: {latest['obv']:.0f}")
            if latest.get('mfi'):
                mfi = latest['mfi']
                mfi_signal = "Overbought" if mfi > 80 else "Oversold" if mfi < 20 else "Neutral"
                volume_indicators.append(f"MFI: {mfi:.2f} ({mfi_signal})")
            if latest.get('vwap'):
                volume_indicators.append(f"VWAP: {latest['vwap']:.4f}")
            if volume_indicators:
                lines.append(f"Volume: {', '.join(volume_indicators)}")
            
            # Add trend analysis - get price from OHLCV join
            if len(rows) > 1:
                # Get price data from joined OHLCV
                price_query = """
                    SELECT ti.timestamp, c.close_price
                    FROM technical_indicators ti
                    JOIN ohlcv_candles c ON ti.candle_id = c.id
                    WHERE ti.pool_id = %s
                    ORDER BY ti.timestamp DESC
                    LIMIT 2
                """
                price_rows = db_connection.execute_query(
                    price_query,
                    (pool_id,),
                    fetch_all=True
                )
                
                if price_rows and len(price_rows) >= 2:
                    latest_price = float(price_rows[0].get('close_price', 0))
                    prev_price = float(price_rows[1].get('close_price', 0))
                    if prev_price > 0:
                        price_change = ((latest_price - prev_price) / prev_price) * 100
                        trend = "Upward" if price_change > 0 else "Downward" if price_change < 0 else "Sideways"
                        lines.append(f"\nTrend Analysis:")
                        lines.append(f"Price Trend: {trend} ({price_change:+.2f}%)")
                        lines.append(f"Current Price: {latest_price:.4f}")
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Error formatting technical indicators for LLM: {e}", exc_info=True)
            return None


# Global instance
technical_indicators_calculator = TechnicalIndicatorsCalculator()