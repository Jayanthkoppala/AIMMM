"""
Sentiment Analysis Scheduler
Fetches and stores sentiment analysis for all active token pairs every 24 hours.
"""
import asyncio
import json
from typing import List, Optional, Dict
from datetime import datetime, timedelta, timezone
from app.config import settings
from app.utils.logger import logger
from app.utils.database import db_connection
from app.services.sentiment import GrokSentimentClient


class SentimentScheduler:
    """
    Background scheduler that fetches sentiment analysis every 24 hours.
    Stores results in database for agents to query.
    """
    
    def __init__(self):
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.grok_client = GrokSentimentClient()
        self.interval_hours = 24  # Run once every 24 hours
    
    def start(self):
        """Start the sentiment scheduler."""
        if self.running:
            logger.warning("Sentiment scheduler is already running")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._run_scheduler())
        logger.info("Sentiment scheduler started - will run every 24 hours")
    
    def stop(self):
        """Stop the sentiment scheduler."""
        self.running = False
        if self.task:
            self.task.cancel()
            logger.info("Sentiment scheduler stopped")
    
    async def _run_scheduler(self):
        """Main scheduler loop."""
        while self.running:
            try:
                await self._analyze_all_pools()
                # Wait 24 hours before next run
                await asyncio.sleep(self.interval_hours * 3600)
            except asyncio.CancelledError:
                logger.info("Sentiment scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Error in sentiment scheduler: {e}", exc_info=True)
                # Wait 1 hour before retrying on error
                await asyncio.sleep(3600)
    
    def _get_active_token_pairs(self) -> List[Dict]:
        """Get all active token pairs from database."""
        if not db_connection.pool:
            logger.warning("Database connection not available")
            return []
        
        try:
            query = """
                SELECT 
                    id as pool_id,
                    token_a_address, 
                    token_b_address,
                    token_a_symbol,
                    token_b_symbol
                FROM pools
                WHERE is_active = TRUE
                AND token_a_address IS NOT NULL
                AND token_b_address IS NOT NULL
            """
            results = db_connection.execute_query(query, fetch_all=True)
            
            if not results:
                logger.debug("No active token pairs found")
                return []
            
            pairs = []
            for row in results:
                pairs.append({
                    "pool_id": row.get("pool_id"),
                    "token_a_address": row.get("token_a_address"),
                    "token_b_address": row.get("token_b_address"),
                    "token_a_symbol": row.get("token_a_symbol"),
                    "token_b_symbol": row.get("token_b_symbol")
                })
            
            logger.info(f"Found {len(pairs)} active token pairs for sentiment analysis")
            return pairs
            
        except Exception as e:
            logger.error(f"Error fetching active token pairs: {e}", exc_info=True)
            return []
    
    async def _analyze_all_pools(self):
        """Analyze sentiment for all active token pairs."""
        logger.info("Starting sentiment analysis for all active pools...")
        
        pairs = self._get_active_token_pairs()
        if not pairs:
            logger.info("No token pairs to analyze")
            return
        
        analyzed = 0
        failed = 0
        
        for pair in pairs:
            try:
                pool_id = pair["pool_id"]
                token_a_address = pair["token_a_address"]
                token_b_address = pair["token_b_address"]
                token_a_symbol = pair.get("token_a_symbol")
                token_b_symbol = pair.get("token_b_symbol")
                
                # Check if we already have recent sentiment (within 24 hours)
                if self._has_recent_sentiment(pool_id):
                    logger.debug(f"Skipping pool {pool_id} ({token_a_symbol or token_a_address[:8]}/{token_b_symbol or token_b_address[:8]}) - recent sentiment exists")
                    continue
                
                # Prepare tokens for Grok API
                tokens = [
                    {
                        "symbol": (token_a_symbol or token_a_address[:8]).upper(),
                        "address": token_a_address
                    },
                    {
                        "symbol": (token_b_symbol or token_b_address[:8]).upper(),
                        "address": token_b_address
                    }
                ]
                
                # Get sentiment from Grok
                grok_sentiment = await self.grok_client.get_token_sentiment(tokens, timeframe="24h")
                
                # Process and store results
                token_a_symbol_lower = tokens[0]["symbol"].lower()
                token_b_symbol_lower = tokens[1]["symbol"].lower()
                
                token_a_data = grok_sentiment.get(token_a_symbol_lower, {})
                token_b_data = grok_sentiment.get(token_b_symbol_lower, {})
                
                # Validate that we got actual data (not just fallback)
                if not token_a_data or token_a_data.get('sentiment_score') == 0.0 and token_a_data.get('confidence', 1.0) < 0.4:
                    logger.warning(f"Received fallback/empty sentiment data for {tokens[0]['symbol']}/{tokens[1]['symbol']}. Response keys: {list(grok_sentiment.keys())}")
                    failed += 1
                    continue
                
                # Log what we're storing
                logger.info(f"Got sentiment for {tokens[0]['symbol']}/{tokens[1]['symbol']}: "
                          f"A={token_a_data.get('sentiment_score', 0):.2f} ({token_a_data.get('sentiment_label', 'unknown')}), "
                          f"B={token_b_data.get('sentiment_score', 0):.2f} ({token_b_data.get('sentiment_label', 'unknown')})")
                
                # Store in database
                success = self._store_sentiment(
                    pool_id=pool_id,
                    token_a_address=token_a_address,
                    token_b_address=token_b_address,
                    token_a_symbol=token_a_symbol,
                    token_b_symbol=token_b_symbol,
                    token_a_data=token_a_data,
                    token_b_data=token_b_data
                )
                
                if success:
                    analyzed += 1
                    logger.info(f"Stored sentiment for {tokens[0]['symbol']}/{tokens[1]['symbol']}")
                else:
                    failed += 1
                    logger.warning(f"Failed to store sentiment for {tokens[0]['symbol']}/{tokens[1]['symbol']}")
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(2)
                
            except Exception as e:
                failed += 1
                logger.error(f"Error analyzing sentiment for pair {pair}: {e}", exc_info=True)
        
        logger.info(f"Sentiment analysis complete: {analyzed} analyzed, {failed} failed")
    
    def _has_recent_sentiment(self, pool_id: int) -> bool:
        """Check if we have sentiment data from the last 24 hours."""
        if not db_connection.pool:
            return False
        
        try:
            query = """
                SELECT analyzed_at
                FROM sentiment_analysis
                WHERE pool_id = %s
                AND analyzed_at >= NOW() - INTERVAL '24 hours'
                ORDER BY analyzed_at DESC
                LIMIT 1
            """
            result = db_connection.execute_query(
                query,
                (pool_id,),
                fetch_one=True
            )
            
            return result is not None
            
        except Exception as e:
            logger.debug(f"Error checking recent sentiment: {e}")
            return False
    
    def _store_sentiment(
        self,
        pool_id: int,
        token_a_address: str,
        token_b_address: str,
        token_a_symbol: Optional[str],
        token_b_symbol: Optional[str],
        token_a_data: Dict,
        token_b_data: Dict
    ) -> bool:
        """Store sentiment analysis in database."""
        if not db_connection.pool:
            return False
        
        try:
            query = """
                INSERT INTO sentiment_analysis (
                    pool_id,
                    token_a_address, token_b_address,
                    token_a_symbol, token_b_symbol,
                    token_a_sentiment_score, token_a_sentiment_label, token_a_confidence,
                    token_a_key_factors, token_a_social_volume, token_a_mentions_24h, token_a_dominant_emotion,
                    token_b_sentiment_score, token_b_sentiment_label, token_b_confidence,
                    token_b_key_factors, token_b_social_volume, token_b_mentions_24h, token_b_dominant_emotion,
                    timeframe, analyzed_at
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, NOW()
                )
                ON CONFLICT (pool_id, analyzed_at) DO NOTHING
            """
            
            params = (
                pool_id,
                token_a_address, token_b_address,
                token_a_symbol, token_b_symbol,
                token_a_data.get('sentiment_score', 0.0),
                token_a_data.get('sentiment_label', 'neutral'),
                token_a_data.get('confidence', 0.5),
                json.dumps(token_a_data.get('key_factors', [])),
                token_a_data.get('social_volume', 0),
                token_a_data.get('mentions_24h', 0),
                token_a_data.get('dominant_emotion', 'neutral'),
                token_b_data.get('sentiment_score', 0.0),
                token_b_data.get('sentiment_label', 'neutral'),
                token_b_data.get('confidence', 0.5),
                json.dumps(token_b_data.get('key_factors', [])),
                token_b_data.get('social_volume', 0),
                token_b_data.get('mentions_24h', 0),
                token_b_data.get('dominant_emotion', 'neutral'),
                '24h'
            )
            
            result = db_connection.execute_query(query, params, fetch_all=False)
            return result is not None
            
        except Exception as e:
            logger.error(f"Error storing sentiment: {e}", exc_info=True)
            return False


# Create singleton instance
sentiment_scheduler = SentimentScheduler()

