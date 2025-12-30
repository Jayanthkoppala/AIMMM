"""
Autonomous Trading Scheduler
Monitors market and executes trades for users with autonomous mode enabled
"""
import asyncio
from typing import List, Dict, Optional
from app.config import settings
from app.utils.logger import logger
from app.utils.database import db_connection
from app.services import oracle, llm, sentiment, risk_management, autonomous_wallet
from app.services.ohlcv import ohlcv_service
from app.services.technical_indicators import technical_indicators_calculator


class AutonomousScheduler:
    """Scheduler for autonomous trading execution"""
    
    def __init__(self):
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.interval_seconds = 300  # Check every 5 minutes
    
    def start(self):
        """Start autonomous trading scheduler"""
        if self.running:
            return
        
        self.running = True
        self.task = asyncio.create_task(self._run())
        logger.info("Autonomous trading scheduler started")
    
    def stop(self):
        """Stop autonomous trading scheduler"""
        self.running = False
        if self.task:
            self.task.cancel()
        logger.info("Autonomous trading scheduler stopped")
    
    async def _run(self):
        """Main scheduler loop"""
        while self.running:
            try:
                await self._check_and_execute_trades()
                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in autonomous trading scheduler: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    def _get_active_users(self) -> List[Dict]:
        """Get users with autonomous trading enabled"""
        if not db_connection.pool:
            return []
        
        try:
            query = """
                SELECT 
                    aw.privy_user_id,
                    aw.wallet_address,
                    aw.risk_per_trade,
                    aw.max_position_size,
                    utp.preferred_pool_address,
                    utp.token_a_address,
                    utp.token_b_address,
                    utp.min_confidence_threshold
                FROM autonomous_wallets aw
                LEFT JOIN user_trading_preferences utp 
                    ON aw.privy_user_id = utp.privy_user_id
                WHERE aw.autonomous_enabled = TRUE
            """
            return db_connection.execute_query(query, fetch_all=True) or []
        except Exception as e:
            logger.error(f"Error fetching autonomous users: {e}", exc_info=True)
            return []
    
    async def _check_and_execute_trades(self):
        """Check market conditions and execute trades for autonomous users"""
        users = self._get_active_users()
        
        if not users:
            logger.debug("No autonomous trading users found")
            return
        
        logger.info(f"Checking market conditions for {len(users)} autonomous users")
        
        for user in users:
            try:
                await self._execute_trade_for_user(user)
            except Exception as e:
                logger.error(f"Error executing autonomous trade for user {user.get('privy_user_id', 'unknown')}: {e}", exc_info=True)
    
    async def _execute_trade_for_user(self, user: Dict):
        """Execute autonomous trade for a single user"""
        privy_user_id = user.get('privy_user_id')
        pool_address = user.get('preferred_pool_address')
        token_a_address = user.get('token_a_address')
        token_b_address = user.get('token_b_address')
        
        if not privy_user_id or not pool_address or not token_a_address or not token_b_address:
            logger.warning(f"Incomplete user preferences for {privy_user_id}")
            return
        
        try:
            # Get market data
            ohlcv_context = await ohlcv_service.format_for_llm(pool_address=pool_address)
            technical_context = technical_indicators_calculator.format_for_llm(
                pool_address=pool_address,
                indicators=['RSI', 'MACD', 'SMA_20', 'SMA_50', 'EMA_50', 'BB', 'ATR', 'ADX', 'Stoch', 'OBV', 'MFI', 'VWAP']
            )
            
            # Get sentiment
            sentiment_result = await sentiment.sentiment_analyzer.analyze_token_pair_sentiment(
                token_a_address=token_a_address,
                token_b_address=token_b_address,
                timeframe="24h"
            )
            sentiment_context = await sentiment.sentiment_analyzer.format_sentiment_for_llm(sentiment_result)
            
            # Get prices
            prices = await oracle.get_token_prices(
                token_a_address,
                token_b_address,
                pool_address=pool_address
            )
            
            # Get LLM decision
            decision = await llm.get_llm_decision(
                token_a_price=prices['token_a_price'],
                token_b_price=prices['token_b_price'],
                ohlcv_context=ohlcv_context,
                sentiment_context=sentiment_context,
                technical_context=technical_context
            )
            
            # Execute if confidence meets threshold
            min_confidence = float(user.get('min_confidence_threshold', 0.70))
            if (decision.action != "HOLD" and decision.confidence >= min_confidence):
                # Calculate position size and risk
                account_balance = await autonomous_wallet.autonomous_wallet_service.get_wallet_balance(privy_user_id)
                
                # Calculate stop loss
                stop_loss_info = risk_management.risk_agent.calculate_stop_loss(
                    entry_price=prices['token_a_price'],
                    risk_tolerance="moderate"
                )
                
                # Calculate position size
                risk_per_trade = float(user.get('risk_per_trade', 0.02))
                position_size = risk_management.risk_agent.calculate_position_size(
                    account_balance=account_balance,
                    entry_price=prices['token_a_price'],
                    stop_loss_price=stop_loss_info.get('stop_loss_long') or stop_loss_info.get('stop_loss_short') or prices['token_a_price'] * 0.95,
                    risk_per_trade=risk_per_trade
                )
                
                # Convert to token units
                token_decimals = 6
                amount_in = int(position_size['position_size'] * (10 ** token_decimals))
                min_amount_out = int(amount_in * 0.99)  # 1% slippage
                
                # Determine direction
                direction = "X_TO_Y" if decision.action == "BUY" else "Y_TO_X"
                
                # Sign and execute using autonomous wallet
                tx_hash = await autonomous_wallet.autonomous_wallet_service.sign_and_submit_transaction(
                    privy_user_id=privy_user_id,
                    transaction_payload={
                        "token_a": token_a_address,
                        "token_b": token_b_address,
                        "direction": direction,
                        "amount_in": amount_in,
                        "min_amount_out": min_amount_out
                    }
                )
                
                if tx_hash:
                    logger.info(f"Autonomous trade executed for user {privy_user_id}: {tx_hash}")
                else:
                    logger.warning(f"Failed to execute autonomous trade for user {privy_user_id}")
            else:
                logger.debug(f"Trade not executed for {privy_user_id}: action={decision.action}, confidence={decision.confidence:.2f} < {min_confidence}")
                
        except Exception as e:
            logger.error(f"Error in _execute_trade_for_user: {e}", exc_info=True)


# Create singleton instance
autonomous_scheduler = AutonomousScheduler()



