"""
OHLCV Data Scheduler with Gap Detection and Backfilling (OPTIMIZED)
Fetches and stores OHLCV data with intelligent gap detection and backfilling.
Uses dynamic intervals based on number of pools to stay within API limits.

KEY FIXES:
1. Fixed backfill logic to properly fetch older data using before_timestamp
2. Fixed gap detection to not skip the most recent period
3. Added proper pagination for large backfills
4. Improved error handling and edge cases
5. Better logging for debugging
"""
import asyncio
import time
from typing import List, Optional, Tuple, Dict
from datetime import datetime, timedelta, timezone
from app.config import settings
from app.utils.logger import logger
from app.services.coingecko import get_pool_ohlcv
from app.utils.database import db_connection
from app.services.api_tracker import api_tracker


class RateLimiter:
    """Simple rate limiter to ensure we stay under API rate limits."""
    
    def __init__(self, requests_per_minute: int = 30):
        self.requests_per_minute = requests_per_minute
        self.min_interval = 60.0 / requests_per_minute
        self.last_request_time = 0.0
    
    async def wait_if_needed(self) -> None:
        """Wait if necessary to maintain rate limit."""
        now = time.time()
        time_since_last = now - self.last_request_time
        if time_since_last < self.min_interval:
            sleep_time = self.min_interval - time_since_last
            await asyncio.sleep(sleep_time)
        self.last_request_time = time.time()


class OHLCVScheduler:
    """
    Background scheduler with gap detection and backfilling.
    Fetches and stores OHLCV data, filling any gaps between latest stored candle and current time.
    """
    
    def __init__(self):
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.pools: List[dict] = []
        self.rate_limiter = RateLimiter(requests_per_minute=settings.COINGECKO_API_LIMIT_PER_MINUTE)
    
    def add_pool(self, pool_address: str, network: str = "movement"):
        """Add a pool to monitor."""
        pool_info = {
            "pool_address": pool_address,
            "network": network
        }
        if pool_info not in self.pools:
            self.pools.append(pool_info)
            logger.info(f"Added pool to monitor: {pool_address[:20]}... on {network}")
    
    def remove_pool(self, pool_address: str, network: str = "movement"):
        """Remove a pool from monitoring."""
        self.pools = [
            p for p in self.pools 
            if not (p["pool_address"] == pool_address and p["network"] == network)
        ]
        logger.info(f"Removed pool from monitoring: {pool_address[:20]}... on {network}")
    
    def get_pools_from_db(self) -> List[dict]:
        """Get list of active pools from database with retry logic."""
        if not db_connection.pool:
            logger.warning("Database connection not available, cannot fetch pools")
            return []
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                query = """
                    SELECT pool_address, network 
                    FROM pools 
                    WHERE is_active = TRUE
                """
                results = db_connection.execute_query(query, fetch_all=True, max_retries=2)
                
                if results is None:
                    if attempt < max_retries - 1:
                        logger.warning(f"Database query returned None (error), retrying ({attempt + 1}/{max_retries})...")
                        time.sleep(1)
                        continue
                    else:
                        logger.error("Failed to fetch pools from database after retries")
                        return []
                
                if isinstance(results, list):
                    if results:
                        pools = [{"pool_address": r["pool_address"], "network": r["network"]} for r in results]
                        logger.debug(f"Found {len(pools)} active pool(s) in database")
                        return pools
                    else:
                        logger.debug("No active pools found in database")
                        return []
                else:
                    logger.error(f"Unexpected result type from database query: {type(results)}")
                    return []
                
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Error fetching pools from database (attempt {attempt + 1}/{max_retries}): {e}")
                    time.sleep(1)
                    continue
                else:
                    logger.error(f"Error fetching pools from database after {max_retries} attempts: {e}", exc_info=True)
                    return []
        
        return []
    
    def calculate_scheduler_interval(self, num_pools: int) -> int:
        """Calculate optimal scheduler interval based on number of pools."""
        if num_pools == 0:
            return 60
        
        reserve = settings.OHLCV_SCHEDULER_RESERVE_FOR_MANUAL
        available_calls = int(settings.COINGECKO_API_LIMIT_MONTHLY * (1 - reserve))
        seconds_in_month = 30 * 24 * 60 * 60
        calls_per_pool_per_month = available_calls / num_pools
        interval = int(seconds_in_month / calls_per_pool_per_month)
        interval = max(60, min(interval, 300))
        
        logger.info(f"Calculated scheduler interval: {interval}s ({interval/60:.1f} min) for {num_pools} pool(s)")
        return interval
    
    def get_latest_candle_timestamp(self, pool_id: int) -> Optional[int]:
        """Get the timestamp of the latest stored candle for a pool."""
        if not db_connection.pool:
            return None
        
        try:
            query = """
                SELECT EXTRACT(EPOCH FROM timestamp)::bigint as timestamp
                FROM ohlcv_candles
                WHERE pool_id = %s
                ORDER BY timestamp DESC
                LIMIT 1
            """
            result = db_connection.execute_query(query, (pool_id,), fetch_one=True)
            
            if result and result.get('timestamp'):
                return int(result['timestamp'])
            return None
        except Exception as e:
            logger.error(f"Error getting latest candle timestamp: {e}", exc_info=True)
            return None
    
    def detect_gap(self, pool_id: int, pool_address: str) -> Optional[Tuple[int, int]]:
        """
        Detect if there's a gap between latest stored candle and current time.
        
        FIXED: Now properly includes the current incomplete period in gap detection.
        """
        latest_ts = self.get_latest_candle_timestamp(pool_id)
        now = int(time.time())
        period_seconds = 60
        
        if latest_ts is None:
            # No data exists - fetch from lookback minutes ago
            lookback_seconds = settings.OHLCV_SCHEDULER_LOOKBACK_MINUTES * 60
            start_ts = now - lookback_seconds
            start_ts = (start_ts // period_seconds) * period_seconds
            # FIX: Include current period by not flooring end_ts
            end_ts = now
            logger.info(f"Gap detected for pool {pool_address[:20]}... (no data exists) - fetching from {start_ts} to {end_ts}")
            return (start_ts, end_ts)
        
        # FIX: Changed logic to detect gaps more accurately
        # Calculate the next expected candle timestamp
        next_expected = ((latest_ts // period_seconds) + 1) * period_seconds
        
        # If we're past the next expected candle time, we have a gap
        if now >= next_expected:
            # Start from next expected period
            start_ts = next_expected
            # End at current time (not floored) to include incomplete current period
            end_ts = now
            
            gap_minutes = (end_ts - start_ts) // 60
            logger.info(f"Gap detected for pool {pool_address[:20]}...: {gap_minutes} minutes missing (from {start_ts} to {end_ts})")
            return (start_ts, end_ts)
        
        # No gap
        return None
    
    async def backfill_historical_candles(
        self,
        pool_address: str,
        network: str = "movement",
        num_candles: int = 200
    ) -> int:
        """
        Backfill historical candles for a pool to enable technical indicators calculation.
        
        FIXED: Properly uses before_timestamp to fetch older data in reverse chronological order.
        """
        logger.info(f"Starting backfill for pool {pool_address[:20]}... ({num_candles} candles)")
        
        pool_id = await self._get_or_create_pool(pool_address, network)
        if not pool_id:
            logger.error(f"Could not get/create pool for {pool_address[:20]}... - backfill aborted")
            return 0
        
        # Check how many candles we already have
        existing_count_query = """
            SELECT COUNT(*) as count FROM ohlcv_candles WHERE pool_id = %s
        """
        existing_result = db_connection.execute_query(existing_count_query, (pool_id,), fetch_one=True)
        existing_count = existing_result.get('count', 0) if existing_result else 0
        
        if existing_count >= num_candles:
            logger.info(f"Pool {pool_address[:20]}... already has {existing_count} candles (need {num_candles})")
            return existing_count
        
        needed = num_candles - existing_count
        logger.info(f"Pool {pool_address[:20]}... has {existing_count} candles, fetching {needed} more...")
        
        total_stored = 0
        batch_size = 1000
        
        # FIX: Get the oldest existing candle to fetch before it
        oldest_ts_query = """
            SELECT EXTRACT(EPOCH FROM timestamp)::bigint as timestamp
            FROM ohlcv_candles
            WHERE pool_id = %s
            ORDER BY timestamp ASC
            LIMIT 1
        """
        oldest_result = db_connection.execute_query(oldest_ts_query, (pool_id,), fetch_one=True)
        
        if oldest_result and oldest_result.get('timestamp'):
            # Fetch before the oldest existing candle
            before_timestamp = int(oldest_result['timestamp'])
            logger.info(f"Fetching candles before oldest existing: {before_timestamp}")
        else:
            # No existing candles, fetch before current time
            before_timestamp = int(time.time())
        
        while total_stored < needed:
            remaining = needed - total_stored
            limit = min(batch_size, remaining)
            
            if not api_tracker.can_make_request():
                logger.warning(f"Cannot continue backfill for pool {pool_address[:20]}... - API limit reached")
                break
            
            try:
                # Only rate limit if we have many pools
                if len(self.pools) > 5:
                    await self.rate_limiter.wait_if_needed()
                
                logger.debug(f"Fetching {limit} candles before timestamp {before_timestamp}...")
                
                # FIX: Properly pass before_timestamp to fetch older data
                candles, meta_info = await get_pool_ohlcv(
                    pool_address=pool_address,
                    network=network,
                    timeframe="minute",
                    aggregate=1,
                    limit=limit,
                    currency="usd",
                    token="quote",
                    before_timestamp=before_timestamp
                )
                
                api_tracker.record_call()
                
                if not candles:
                    logger.warning(f"No more candles available for pool {pool_address[:20]}...")
                    break
                
                # Update pool with token info if available
                if meta_info and meta_info.get('base') and meta_info.get('quote'):
                    await self._update_pool_tokens(
                        pool_id,
                        meta_info['base'].get('symbol', ''),
                        meta_info['quote'].get('symbol', ''),
                        meta_info['base'].get('address', ''),
                        meta_info['quote'].get('address', '')
                    )
                
                # Store candles
                stored = await self._store_candles(pool_id, pool_address, candles)
                total_stored += stored
                
                if stored == 0:
                    logger.debug(f"No new candles stored (may be duplicates)")
                    break
                
                # FIX: Update before_timestamp to the oldest candle we just fetched minus 1 second
                oldest_in_batch = min(candle.get('timestamp', before_timestamp) for candle in candles if candle.get('timestamp'))
                before_timestamp = int(oldest_in_batch) - 1
                
                logger.info(f"Backfilled {stored} candles (total: {total_stored}/{needed}), next before: {before_timestamp}")
                
            except Exception as e:
                logger.error(f"Error during backfill for pool {pool_address[:20]}...: {e}", exc_info=True)
                break
        
        logger.info(f"Backfill complete for pool {pool_address[:20]}...: {total_stored} new candles stored")
        return total_stored
    
    async def fetch_and_store_ohlcv_with_range(
        self,
        pool_address: str,
        network: str,
        pool_id: int,
        start_ts: int,
        end_ts: int
    ) -> int:
        """
        Fetch and store OHLCV data for a specific time range (for gap filling).
        
        FIXED: Better calculation of needed candles and proper limit handling.
        """
        if not api_tracker.can_make_request():
            logger.warning(f"Cannot fetch OHLCV for pool {pool_address[:20]}... - API limit reached")
            return 0
        
        try:
            period_seconds = 60
            # FIX: Calculate periods more accurately
            time_span = end_ts - start_ts
            periods = (time_span + period_seconds - 1) // period_seconds  # Ceiling division
            limit = min(max(periods, 1), 1000)
            
            logger.debug(f"Fetching {limit} candles for pool {pool_address[:20]}... (range: {start_ts} to {end_ts}, span: {time_span}s)")
            
            # Only rate limit if we have many pools (> 5) to avoid API throttling
            if len(self.pools) > 5:
                await self.rate_limiter.wait_if_needed()
            
            # FIX: Don't use before_timestamp for forward gaps - let API return latest data
            candles, meta_info = await get_pool_ohlcv(
                pool_address=pool_address,
                network=network,
                timeframe="minute",
                aggregate=1,
                limit=limit,
                currency="usd",
                token="quote"
            )
            
            api_tracker.record_call()
            
            if not candles:
                logger.warning(f"No candles fetched for pool {pool_address[:20]}...")
                return 0
            
            # Update pool with token symbols if meta info is available
            if meta_info and meta_info.get('base') and meta_info.get('quote'):
                await self._update_pool_tokens(
                    pool_id, 
                    meta_info['base'].get('symbol', ''),
                    meta_info['quote'].get('symbol', ''),
                    meta_info['base'].get('address', ''),
                    meta_info['quote'].get('address', '')
                )
            
            # Store all candles - duplicates handled by ON CONFLICT
            # Don't filter by range since CoinGecko returns latest candles, not range-specific
            logger.debug(f"Storing {len(candles)} candles for pool {pool_address[:20]}...")
            
            return await self._store_candles(pool_id, pool_address, candles)
            
        except Exception as e:
            logger.error(f"Error fetching/storing OHLCV for pool {pool_address[:20]}...: {e}", exc_info=True)
            return 0
    
    async def _store_candles(self, pool_id: int, pool_address: str, candles: List[Dict]) -> int:
        """Store candles to database with proper duplicate handling and gap filling."""
        stored_count = 0
        skipped_count = 0
        error_count = 0
        
        # Fill timestamp gaps before storing
        candles = self._fill_timestamp_gaps(candles)
        
        # Get pool_name from pools table
        pool_name = None
        if db_connection.pool:
            try:
                pool_query = "SELECT pool_name FROM pools WHERE id = %s"
                pool_result = db_connection.execute_query(pool_query, (pool_id,), fetch_one=True)
                if pool_result:
                    pool_name = pool_result.get('pool_name')
            except Exception as e:
                logger.warning(f"Could not fetch pool_name for pool {pool_address[:20]}...: {e}")
        
        for i, candle in enumerate(candles):
            try:
                timestamp = candle.get('timestamp')
                if not timestamp:
                    skipped_count += 1
                    continue
                
                # Convert timestamp to datetime (UTC)
                if isinstance(timestamp, (int, float)):
                    candle_dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                elif isinstance(timestamp, str):
                    candle_dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    if candle_dt.tzinfo is None:
                        candle_dt = candle_dt.replace(tzinfo=timezone.utc)
                else:
                    skipped_count += 1
                    continue
                
                # FIX: Better handling of ON CONFLICT to track what was actually inserted
                query = """
                    INSERT INTO ohlcv_candles (
                        pool_id, pool_name, timestamp,
                        open_price, high_price, low_price, close_price, volume
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (pool_id, timestamp) DO UPDATE 
                    SET pool_name = EXCLUDED.pool_name
                    RETURNING (xmax = 0) AS inserted
                """
                
                params = (
                    pool_id,
                    pool_name,
                    candle_dt,
                    float(candle.get('open', 0)),
                    float(candle.get('high', 0)),
                    float(candle.get('low', 0)),
                    float(candle.get('close', 0)),
                    float(candle.get('volume', 0))
                )
                
                result = db_connection.execute_query(query, params, fetch_one=True)
                if result and result.get('inserted'):
                    stored_count += 1
                    
            except Exception as e:
                logger.error(f"Error storing candle {i} for pool {pool_address[:20]}...: {e}", exc_info=True)
                error_count += 1
        
        if stored_count > 0:
            logger.info(f"✓ Stored {stored_count}/{len(candles)} new candles for pool {pool_address[:20]}... (skipped: {skipped_count}, errors: {error_count})")
        elif error_count > 0:
            logger.warning(f"✗ Failed to store candles for pool {pool_address[:20]}... ({error_count} errors, {skipped_count} skipped)")
        
        return stored_count
    
    async def fetch_and_store_ohlcv(self, pool_address: str, network: str = "movement"):
        """Fetch and store OHLCV data for a single pool (with gap detection and backfilling)."""
        try:
            pool_id = await self._get_or_create_pool(pool_address, network)
            if not pool_id:
                logger.error(f"Could not get/create pool for {pool_address[:20]}... - storage aborted")
                return
            
            logger.debug(f"Processing pool {pool_address[:20]}... (pool_id: {pool_id})")
            
            # Check if pool needs backfill (insufficient data for technical indicators)
            MIN_CANDLES_FOR_INDICATORS = 200
            existing_count = await self._get_candle_count(pool_id)
            
            if existing_count < MIN_CANDLES_FOR_INDICATORS:
                logger.info(f"Pool {pool_address[:20]}... has only {existing_count} candles, needs backfill (min: {MIN_CANDLES_FOR_INDICATORS})")
                backfilled = await self.backfill_historical_candles(
                    pool_address=pool_address,
                    network=network,
                    num_candles=MIN_CANDLES_FOR_INDICATORS
                )
                logger.info(f"Backfilled {backfilled} candles for pool {pool_address[:20]}...")
                return  # Backfill handles storage, skip gap detection this cycle
            
            # Detect gap
            gap = self.detect_gap(pool_id, pool_address)
            
            if gap:
                start_ts, end_ts = gap
                logger.info(f"Filling gap for pool {pool_address[:20]}... from {start_ts} to {end_ts}")
                stored = await self.fetch_and_store_ohlcv_with_range(
                    pool_address, network, pool_id, start_ts, end_ts
                )
                if stored > 0:
                    logger.info(f"Filled gap with {stored} candles for pool {pool_address[:20]}...")
                else:
                    logger.warning(f"No candles stored during gap fill for pool {pool_address[:20]}...")
            else:
                logger.info(f"Pool {pool_address[:20]}... is up to date, no gap detected")
                
        except Exception as e:
            logger.error(f"Error in fetch_and_store_ohlcv for pool {pool_address[:20]}...: {e}", exc_info=True)
    
    async def _get_candle_count(self, pool_id: int) -> int:
        """Get the count of stored candles for a pool."""
        if not db_connection.pool:
            return 0
        
        try:
            query = "SELECT COUNT(*) as count FROM ohlcv_candles WHERE pool_id = %s"
            result = db_connection.execute_query(query, (pool_id,), fetch_one=True)
            return result.get('count', 0) if result else 0
        except Exception as e:
            logger.error(f"Error getting candle count: {e}")
            return 0
    
    def _fill_timestamp_gaps(self, candles: List[Dict]) -> List[Dict]:
        """
        Fill missing 1-minute timestamps between candles.
        
        If there's a gap between consecutive candles (e.g., missing minutes),
        create synthetic candles with the last known close price.
        
        Args:
            candles: List of candle dicts with timestamps
        
        Returns:
            List with gaps filled
        """
        if not candles or len(candles) < 2:
            return candles
        
        # Sort by timestamp
        candles = sorted(candles, key=lambda x: x.get('timestamp', 0))
        
        filled_candles = []
        period_seconds = 60  # 1-minute candles
        max_gap_to_fill = 60  # Don't fill gaps larger than 60 minutes
        
        for i, candle in enumerate(candles):
            filled_candles.append(candle)
            
            if i < len(candles) - 1:
                current_ts = candle.get('timestamp', 0)
                next_ts = candles[i + 1].get('timestamp', 0)
                
                if isinstance(current_ts, (int, float)) and isinstance(next_ts, (int, float)):
                    gap_periods = int((next_ts - current_ts) / period_seconds) - 1
                    
                    if 0 < gap_periods <= max_gap_to_fill:
                        last_close = candle.get('close', 0)
                        if last_close > 0:
                            # Fill missing periods
                            for j in range(1, gap_periods + 1):
                                synthetic_ts = int(current_ts + (j * period_seconds))
                                synthetic_candle = {
                                    'timestamp': synthetic_ts,
                                    'open': last_close,
                                    'high': last_close,
                                    'low': last_close,
                                    'close': last_close,
                                    'volume': 0.0
                                }
                                filled_candles.append(synthetic_candle)
        
        gaps_filled = len(filled_candles) - len(candles)
        if gaps_filled > 0:
            logger.info(f"Filled {gaps_filled} missing timestamp gaps in candle data")
        
        return filled_candles
    
    async def _get_or_create_pool(self, pool_address: str, network: str) -> Optional[int]:
        """Get or create a pool entry in the pools table."""
        if not db_connection.pool:
            logger.error("Database connection not available for pool lookup")
            return None
        
        try:
            query = """
                SELECT id FROM pools
                WHERE pool_address = %s AND network = %s
                LIMIT 1
            """
            result = db_connection.execute_query(query, (pool_address, network), fetch_one=True)
            
            if result and result.get('id'):
                pool_id = int(result['id'])
                logger.debug(f"Found existing pool_id {pool_id} for {pool_address[:20]}...")
                return pool_id
            
            logger.debug(f"Creating new pool entry for {pool_address[:20]}... on {network}")
            insert_query = """
                INSERT INTO pools (
                    pool_address, network, is_active
                ) VALUES (
                    %s, %s, %s
                )
                ON CONFLICT (pool_address) 
                DO UPDATE SET is_active = TRUE, updated_at = NOW()
                RETURNING id
            """
            
            params = (pool_address, network, True)
            result = db_connection.execute_query(insert_query, params, fetch_one=True)
            
            if result and result.get('id'):
                pool_id = int(result['id'])
                logger.info(f"Created pool entry with id {pool_id} for {pool_address[:20]}... on {network}")
                return pool_id
            
            logger.error(f"Failed to create/get pool - query returned: {result}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting/creating pool: {e}", exc_info=True)
            return None
    
    async def _update_pool_tokens(self, pool_id: int, base_symbol: str, quote_symbol: str, base_address: str = None, quote_address: str = None):
        """Update pool record with base and quote token symbols and addresses."""
        if not base_symbol or not quote_symbol:
            return
        
        if not db_connection.pool:
            logger.error("Database connection not available for pool update")
            return
        
        try:
            query = """
                UPDATE pools
                SET 
                    token_a_symbol = %s, 
                    token_a_address = %s,
                    token_b_symbol = %s, 
                    token_b_address = %s,
                    updated_at = NOW()
                WHERE id = %s
            """
            result = db_connection.execute_query(
                query, 
                (base_symbol, base_address, quote_symbol, quote_address, pool_id), 
                fetch_all=False
            )
            if result is not None:
                logger.debug(f"Updated pool {pool_id} with tokens: {base_symbol}/{quote_symbol}")
        except Exception as e:
            logger.warning(f"Failed to update pool tokens: {e}", exc_info=True)
    
    async def run_cycle(self):
        """Run one cycle of fetching and storing OHLCV data for all pools."""
        self.pools = self.get_pools_from_db()
        
        if not self.pools:
            logger.debug("No active pools found in database for OHLCV monitoring.")
            return
        
        num_pools = len(self.pools)
        logger.info(f"Starting OHLCV fetch cycle for {num_pools} pool(s)")
        
        usage_stats = api_tracker.get_usage_stats()
        if usage_stats["percentage_used"] > 90:
            logger.warning(f"API usage high: {usage_stats['percentage_used']:.1f}% of monthly limit used")
        
        tasks = [
            self.fetch_and_store_ohlcv(pool["pool_address"], pool["network"])
            for pool in self.pools
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error processing pool {self.pools[i]['pool_address'][:20]}...: {result}")
        
        logger.info("Completed OHLCV fetch cycle")
        
        # Calculate technical indicators in background
        try:
            logger.info("Starting technical indicators calculation...")
            asyncio.create_task(self._calculate_indicators_for_all_pools())
        except Exception as e:
            logger.warning(f"Error initiating technical indicators calculation: {e}", exc_info=True)
    
    async def _calculate_indicators_for_all_pools(self):
        """Calculate technical indicators for all pools (runs asynchronously)."""
        try:
            from app.services.technical_indicators import technical_indicators_calculator
            
            for pool in self.pools:
                pool_address = pool["pool_address"]
                network = pool["network"]
                
                pool_query = """
                    SELECT id FROM pools
                    WHERE pool_address = %s AND network = %s
                    LIMIT 1
                """
                pool_result = db_connection.execute_query(
                    pool_query, 
                    (pool_address, network), 
                    fetch_one=True
                )
                
                if pool_result and pool_result.get('id'):
                    pool_id = int(pool_result['id'])
                    import concurrent.futures
                    loop = asyncio.get_event_loop()
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        await loop.run_in_executor(
                            executor,
                            technical_indicators_calculator.calculate_and_store_indicators,
                            pool_id,
                            pool_address
                        )
            
            logger.info("Technical indicators calculation completed for all pools")
        except Exception as e:
            logger.error(f"Error calculating technical indicators: {e}", exc_info=True)
    
    async def scheduler_loop(self):
        """Main scheduler loop with dynamic intervals and gap detection."""
        logger.info("OHLCV scheduler started - using dynamic intervals with gap detection and backfilling")
        self.running = True
        
        await asyncio.sleep(3)
        
        try:
            await self.run_cycle()
        except Exception as e:
            logger.error(f"Error in initial OHLCV scheduler cycle: {e}", exc_info=True)
        
        iteration = 0
        while self.running:
            try:
                iteration += 1
                cycle_start = time.time()
                
                self.pools = self.get_pools_from_db()
                num_pools = len(self.pools)
                interval = self.calculate_scheduler_interval(num_pools)
                
                logger.info(f"[Iteration {iteration}] Waiting {interval}s ({interval/60:.1f} min) before next cycle...")
                
                try:
                    await asyncio.sleep(interval)
                except asyncio.CancelledError:
                    break
                
                if not self.running:
                    break
                
                await self.run_cycle()
                
                cycle_duration = time.time() - cycle_start
                logger.info(f"[Iteration {iteration}] Cycle completed in {cycle_duration:.1f}s")
                
            except asyncio.CancelledError:
                logger.info("OHLCV scheduler loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in OHLCV scheduler cycle: {e}", exc_info=True)
    
    def start(self):
        """Start the scheduler background task."""
        if self.running:
            logger.warning("OHLCV scheduler is already running")
            return
        
        if not db_connection.pool:
            logger.warning("Database connection not available, cannot start OHLCV scheduler")
            return
        
        self.task = asyncio.create_task(self.scheduler_loop())
        logger.info("OHLCV scheduler task created")
    
    def stop(self):
        """Stop the scheduler."""
        self.running = False
        if self.task:
            self.task.cancel()
            logger.info("OHLCV scheduler stopped")


# Global scheduler instance
ohlcv_scheduler = OHLCVScheduler()