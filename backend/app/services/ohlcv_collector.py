"""
OHLCV Data Collector Service
Polls Switchboard for price data and aggregates into OHLCV candles.
"""
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from app.config import settings
from app.utils.logger import logger
from app.utils.database import db_connection
from app.services.oracle import fetch_switchboard_price_from_blockchain, get_token_prices


class OHLCVCollector:
    """
    Collects price data from Switchboard and aggregate into OHLCV candles.
    
    Strategy:
    1. Poll Switchboard every N seconds (configurable, e.g., every 10-60 seconds)
    2. Store raw price ticks in price_ticks table
    3. Aggregate ticks into OHLCV candles (1m, 5m, 15m, 1h, etc.)
    4. Store candles in ohlcv_candles table
    """
    
    def __init__(self, poll_interval_seconds: int = 10):
        """
        Initialize OHLCV collector.
        
        Args:
            poll_interval_seconds: How often to poll Switchboard (default: 10 seconds)
        """
        self.poll_interval = poll_interval_seconds
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
    
    async def get_active_token_pairs(self) -> List[Dict]:
        """Get all active token pairs to monitor."""
        query = """
            SELECT id, token_a_address, token_b_address, switchboard_feed_id
            FROM token_pairs
            WHERE is_active = TRUE
            ORDER BY created_at
        """
        pairs = db_connection.execute_query(query, fetch_all=True)
        return pairs or []
    
    async def register_token_pair(
        self,
        token_a_address: str,
        token_b_address: str,
        switchboard_feed_id: str,
        token_a_symbol: Optional[str] = None,
        token_b_symbol: Optional[str] = None
    ) -> Optional[str]:
        """
        Register a new token pair for monitoring.
        
        Returns:
            token_pair_id if successful, None otherwise
        """
        query = """
            INSERT INTO token_pairs (
                token_a_address, token_b_address, switchboard_feed_id,
                token_a_symbol, token_b_symbol, is_active
            )
            VALUES (%s, %s, %s, %s, %s, TRUE)
            ON CONFLICT (token_a_address, token_b_address, switchboard_feed_id)
            DO UPDATE SET is_active = TRUE, updated_at = NOW()
            RETURNING id
        """
        result = db_connection.execute_query(
            query,
            params=(token_a_address, token_b_address, switchboard_feed_id, token_a_symbol, token_b_symbol),
            fetch_one=True
        )
        if result:
            logger.info(f"Registered token pair: {token_a_address[:10]}.../{token_b_address[:10]}...")
            return str(result['id'])
        return None
    
    async def collect_price_tick(
        self,
        token_pair_id: str,
        price: float,
        feed_id: str,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Store a raw price tick from Switchboard.
        
        Args:
            token_pair_id: UUID of the token pair
            price: Current price
            feed_id: Switchboard feed/aggregator address
            timestamp: Price timestamp (defaults to now)
        
        Returns:
            True if successful
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        query = """
            INSERT INTO price_ticks (
                token_pair_id, timestamp, price, feed_id, source
            )
            VALUES (%s, %s, %s, %s, 'switchboard')
        """
        
        try:
            db_connection.execute_query(
                query,
                params=(token_pair_id, timestamp, price, feed_id),
                fetch_all=False
            )
            return True
        except Exception as e:
            logger.error(f"Failed to store price tick: {e}", exc_info=True)
            return False
    
    async def aggregate_candles(
        self,
        token_pair_id: str,
        timeframe: str = '1m',
        force_recalculate: bool = False
    ) -> int:
        """
        Aggregate price ticks into OHLCV candles for a given timeframe.
        
        Args:
            token_pair_id: UUID of the token pair
            timeframe: '1m', '5m', '15m', '1h', '4h', '1d'
            force_recalculate: Recalculate even if candle exists
        
        Returns:
            Number of candles created/updated
        """
        # Map timeframe to interval
        timeframe_intervals = {
            '1m': timedelta(minutes=1),
            '5m': timedelta(minutes=5),
            '15m': timedelta(minutes=15),
            '1h': timedelta(hours=1),
            '4h': timedelta(hours=4),
            '1d': timedelta(days=1)
        }
        
        if timeframe not in timeframe_intervals:
            logger.error(f"Invalid timeframe: {timeframe}")
            return 0
        
        interval = timeframe_intervals[timeframe]
        
        # Get the latest candle timestamp for this pair and timeframe
        latest_candle_query = """
            SELECT MAX(timestamp) as latest_timestamp
            FROM ohlcv_candles
            WHERE token_pair_id = %s AND timeframe = %s
        """
        latest_result = db_connection.execute_query(
            latest_candle_query,
            params=(token_pair_id, timeframe),
            fetch_one=True
        )
        
        start_time = None
        if latest_result and latest_result.get('latest_timestamp') and not force_recalculate:
            start_time = latest_result['latest_timestamp']
        else:
            # Get earliest price tick
            earliest_query = """
                SELECT MIN(timestamp) as earliest_timestamp
                FROM price_ticks
                WHERE token_pair_id = %s
            """
            earliest_result = db_connection.execute_query(
                earliest_query,
                params=(token_pair_id,),
                fetch_one=True
            )
            if earliest_result and earliest_result.get('earliest_timestamp'):
                start_time = earliest_result['earliest_timestamp']
        
        if not start_time:
            logger.debug(f"No price ticks found for token_pair_id: {token_pair_id}")
            return 0
        
        # Get all price ticks since start_time
        ticks_query = """
            SELECT timestamp, price
            FROM price_ticks
            WHERE token_pair_id = %s AND timestamp >= %s
            ORDER BY timestamp ASC
        """
        ticks = db_connection.execute_query(
            ticks_query,
            params=(token_pair_id, start_time),
            fetch_all=True
        )
        
        if not ticks:
            return 0
        
        # Group ticks into candles
        candles_created = 0
        current_candle_start = None
        current_candle_data = None
        
        for tick in ticks:
            tick_time = tick['timestamp']
            price = float(tick['price'])
            
            # Calculate candle start time (round down to interval)
            if isinstance(tick_time, str):
                tick_time = datetime.fromisoformat(tick_time.replace('Z', '+00:00'))
            
            candle_start = self._round_to_interval(tick_time, interval)
            
            # New candle period
            if current_candle_start is None or candle_start != current_candle_start:
                # Save previous candle if exists
                if current_candle_data:
                    self._save_candle(token_pair_id, timeframe, current_candle_data)
                    candles_created += 1
                
                # Start new candle
                current_candle_start = candle_start
                current_candle_data = {
                    'timestamp': candle_start,
                    'open': price,
                    'high': price,
                    'low': price,
                    'close': price,
                    'volume': 0,
                    'trade_count': 1
                }
            else:
                # Update current candle
                current_candle_data['high'] = max(current_candle_data['high'], price)
                current_candle_data['low'] = min(current_candle_data['low'], price)
                current_candle_data['close'] = price
                current_candle_data['trade_count'] += 1
        
        # Save last candle
        if current_candle_data:
            self._save_candle(token_pair_id, timeframe, current_candle_data)
            candles_created += 1
        
        if candles_created > 0:
            logger.info(f"Aggregated {candles_created} {timeframe} candles for token_pair_id: {token_pair_id}")
        
        return candles_created
    
    def _round_to_interval(self, dt: datetime, interval: timedelta) -> datetime:
        """Round datetime down to the nearest interval."""
        # For minutes/hours, round down
        if interval <= timedelta(hours=1):
            # Round down to the minute/hour
            if interval == timedelta(minutes=1):
                return dt.replace(second=0, microsecond=0)
            elif interval == timedelta(minutes=5):
                return dt.replace(minute=(dt.minute // 5) * 5, second=0, microsecond=0)
            elif interval == timedelta(minutes=15):
                return dt.replace(minute=(dt.minute // 15) * 15, second=0, microsecond=0)
            elif interval == timedelta(hours=1):
                return dt.replace(minute=0, second=0, microsecond=0)
        elif interval == timedelta(hours=4):
            return dt.replace(hour=(dt.hour // 4) * 4, minute=0, second=0, microsecond=0)
        elif interval == timedelta(days=1):
            return dt.replace(hour=0, minute=0, second=0, microsecond=0)
        return dt
    
    def _save_candle(
        self,
        token_pair_id: str,
        timeframe: str,
        candle_data: Dict
    ) -> bool:
        """Save or update an OHLCV candle."""
        query = """
            INSERT INTO ohlcv_candles (
                token_pair_id, timestamp, timeframe,
                open_price, high_price, low_price, close_price,
                volume, trade_count
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (token_pair_id, timestamp, timeframe)
            DO UPDATE SET
                open_price = EXCLUDED.open_price,
                high_price = EXCLUDED.high_price,
                low_price = EXCLUDED.low_price,
                close_price = EXCLUDED.close_price,
                volume = EXCLUDED.volume,
                trade_count = EXCLUDED.trade_count
        """
        
        try:
            db_connection.execute_query(
                query,
                params=(
                    token_pair_id,
                    candle_data['timestamp'],
                    timeframe,
                    candle_data['open'],
                    candle_data['high'],
                    candle_data['low'],
                    candle_data['close'],
                    candle_data['volume'],
                    candle_data['trade_count']
                ),
                fetch_all=False
            )
            return True
        except Exception as e:
            logger.error(f"Failed to save candle: {e}", exc_info=True)
            return False
    
    async def collect_loop(self):
        """Main collection loop - polls Switchboard and stores data."""
        logger.info(f"Starting OHLCV collection loop (interval: {self.poll_interval}s)")
        self.is_running = True
        
        while self.is_running:
            try:
                # Get active token pairs
                pairs = await self.get_active_token_pairs()
                
                if not pairs:
                    logger.debug("No active token pairs to monitor")
                    await asyncio.sleep(self.poll_interval)
                    continue
                
                # Collect price data for each pair
                for pair in pairs:
                    try:
                        token_pair_id = pair['id']
                        feed_id = pair['switchboard_feed_id']
                        
                        # Fetch current price from Switchboard
                        price_data = await fetch_switchboard_price_from_blockchain(feed_id)
                        
                        if price_data and 'token_a_price' in price_data:
                            price = price_data['token_a_price']
                            timestamp = datetime.fromtimestamp(price_data.get('timestamp', datetime.now().timestamp()))
                            
                            # Store price tick
                            await self.collect_price_tick(
                                token_pair_id,
                                price,
                                feed_id,
                                timestamp
                            )
                            
                            # Aggregate into 1-minute candles (most frequent)
                            await self.aggregate_candles(token_pair_id, '1m')
                            
                            logger.debug(f"Collected price for pair {token_pair_id}: {price}")
                        
                    except Exception as e:
                        logger.error(f"Error collecting data for pair {pair.get('id')}: {e}", exc_info=True)
                        continue
                
                # Sleep until next poll
                await asyncio.sleep(self.poll_interval)
                
            except Exception as e:
                logger.error(f"Error in collection loop: {e}", exc_info=True)
                await asyncio.sleep(self.poll_interval)
    
    async def start(self):
        """Start the collection loop in background."""
        if self.is_running:
            logger.warning("Collector is already running")
            return
        
        self.task = asyncio.create_task(self.collect_loop())
        logger.info("OHLCV collector started")
    
    async def stop(self):
        """Stop the collection loop."""
        self.is_running = False
        if self.task:
            await self.task
        logger.info("OHLCV collector stopped")


# Global collector instance
ohlcv_collector = OHLCVCollector(poll_interval_seconds=10)

