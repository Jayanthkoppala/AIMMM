"""
Strategy Executor - Core execution engine for DEX spot trading strategies
Orchestrates market data gathering, LLM decisions, and Mosaic swaps
Supports both legacy execution and new LangGraph agent-based execution
"""
import time
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, timezone
from app.utils.database import db_connection
from app.utils.logger import logger
from app.config import settings
from app.services import mosaic, llm, risk_management, oracle
from app.services.paper_trading_dex import paper_trading_dex
from app.services.ohlcv import ohlcv_service
from app.services.technical_indicators import technical_indicators_calculator
from app.services import sentiment


class StrategyExecutor:
    """Executes trading strategies with market data, LLM decisions, and paper trading"""
    
    async def execute_strategy(
        self,
        strategy_id: str,
        user_id: str,
        execution_mode: str = "analysis"
    ) -> Dict[str, Any]:
        """
        Execute a trading strategy.
        
        Args:
            strategy_id: Strategy UUID
            user_id: User ID (Privy)
            execution_mode: "analysis" (paper trading) or "trade" (live)
        
        Returns:
            Execution result with decision, trading state, and metadata
        """
        start_time = time.time()
        
        logger.info(f"=" * 80)
        logger.info(f"[Strategy Execution] Starting execution for strategy_id: {strategy_id}")
        logger.info(f"[Strategy Execution] Execution mode: {execution_mode}")
        
        # Check if LangGraph agents are enabled
        if settings.USE_LANGGRAPH_AGENTS:
            logger.info(f"[Strategy Execution] Using LangGraph agent system")
            logger.info(f"=" * 80)
            return await self._execute_with_langgraph(strategy_id, user_id, execution_mode)
        else:
            logger.info(f"[Strategy Execution] Using legacy execution system")
        
        logger.info(f"=" * 80)
        
        try:
            # 1. Fetch strategy config
            logger.info(f"[Strategy Execution] Fetching strategy configuration...")
            strategy = await self._get_strategy(strategy_id, user_id)
            if not strategy:
                logger.error(f"[Strategy Execution] Strategy not found: {strategy_id}")
                return {
                    "status": "error",
                    "error": "Strategy not found"
                }
            
            strategy_config = strategy.get('strategy_config', {})
            strategy_name = strategy.get('name', 'Unknown')
            strategy_description = strategy.get('description', '')
            pool_id = strategy.get('pool_id')
            logger.info(f"[Strategy Execution] Strategy loaded: '{strategy_name}' (id: {strategy_id}, pool_id: {pool_id})")
            if strategy_description:
                logger.info(f"[Strategy Execution] Strategy description: {strategy_description[:100]}...")
            
            # Get pool info early for exit signals check
            pool_address = None
            if pool_id:
                try:
                    pool_query = "SELECT pool_address FROM pools WHERE id = %s"
                    pool_result = db_connection.execute_query(pool_query, (pool_id,), fetch_one=True)
                    if pool_result:
                        pool_address = pool_result.get('pool_address')
                        logger.info(f"[Strategy Execution] Pool address: {pool_address[:20]}..." if pool_address else "[Strategy Execution] Pool address: None")
                except Exception as e:
                    logger.error(f"[Strategy Execution] Error fetching pool address: {e}")
            
            # 2. Initialize paper trading balances if needed
            initial_capital = strategy_config.get('paper_trading_config', {}).get('initial_capital_usdc', 1000)
            logger.info(f"[Strategy Execution] Initializing paper trading with ${initial_capital} USDC")
            balance_initialized = await paper_trading_dex.initialize_strategy_balances(
                strategy_id,
                initial_capital
            )
            
            # Verify balance was initialized correctly
            if balance_initialized:
                usdc_balance = await paper_trading_dex.get_balance(strategy_id, paper_trading_dex.USDC_ADDRESS, "USDC")
                logger.info(f"[Strategy Execution] Paper trading balance verified: {usdc_balance} USDC available")
                if usdc_balance == 0:
                    logger.warning(f"[Strategy Execution] Balance is 0 after initialization - checking all balances...")
                    all_balances = await paper_trading_dex.get_balances(strategy_id)
                    logger.warning(f"[Strategy Execution] All balances: {all_balances}")
            else:
                logger.warning(f"[Strategy Execution] Paper trading balance initialization may have failed")
            
            # 3. Check for exit signals (stop-loss/take-profit)
            exit_positions = await paper_trading_dex.check_exit_signals(
                strategy_id,
                strategy_config,
                pool_address=pool_address  # Pass pool_address for accurate price fetching
            )
            
            # 4. Execute exits first
            for exit_pos in exit_positions:
                await self._execute_exit(
                    strategy_id,
                    user_id,
                    exit_pos,
                    strategy_config,
                    execution_mode
                )
            
            # 5. Gather market data (using pool_id from strategy)
            pool_id = strategy.get('pool_id')
            logger.info(f"[Strategy Execution] Gathering market data for pool_id: {pool_id}")
            market_data = await self._gather_market_data(strategy_config, pool_id=pool_id)
            
            if not market_data:
                logger.error(f"[Strategy Execution] Failed to gather market data for strategy {strategy_id}")
                return {
                    "status": "error",
                    "error": "Failed to gather market data"
                }
            
            # Log what data was gathered
            ohlcv_length = len(market_data.get('ohlcv', ''))
            technical_length = len(market_data.get('technical', ''))
            sentiment_length = len(market_data.get('sentiment', ''))
            current_price = market_data.get('current_price', 0)
            
            logger.info(f"[Strategy Execution] Market data gathered:")
            logger.info(f"  - OHLCV data: {'✓' if ohlcv_length > 0 else '✗'} ({ohlcv_length} chars)")
            logger.info(f"  - Technical indicators: {'✓' if technical_length > 0 else '✗'} ({technical_length} chars)")
            logger.info(f"  - Sentiment data: {'✓' if sentiment_length > 0 else '✗'} ({sentiment_length} chars)")
            logger.info(f"  - Current price: ${current_price:.6f}")
            
            # 6. Get current portfolio state (using current market price)
            logger.info(f"[Strategy Execution] Calculating portfolio state...")
            current_price = market_data.get('current_price', 0)
            pool_address = market_data.get('pool_address')
            portfolio_state = await paper_trading_dex.calculate_portfolio_value(
                strategy_id,
                pool_address=pool_address,
                current_price=current_price if current_price > 0 else None
            )
            logger.info(f"[Strategy Execution] Portfolio value: ${portfolio_state.get('total_value', 0):.2f} (P&L: {portfolio_state.get('unrealized_pnl_pct', 0):.2f}%)")
            
            # 7. Make LLM decision
            logger.info(f"[Strategy Execution] Sending data to LLM for decision making...")
            logger.info(f"[Strategy Execution] Data summary being sent to LLM:")
            logger.info(f"  - OHLCV: {'Present' if ohlcv_length > 0 else 'Missing'}")
            logger.info(f"  - Technical Indicators: {'Present' if technical_length > 0 else 'Missing'}")
            logger.info(f"  - Sentiment: {'Present' if sentiment_length > 0 else 'Missing'}")
            
            decision = await llm.get_strategy_decision(
                portfolio_state=portfolio_state,
                market_data=market_data,
                strategy_config=strategy_config,
                strategy_description=strategy_description,  # Pass user's strategy description
                llm_model=strategy_config.get('llm_provider')
            )
            
            logger.info(f"[Strategy Execution] LLM decision received: action={decision.get('action')}, confidence={decision.get('confidence', 0):.2f}")
            
            # 8. Calculate dynamic parameters based on confidence
            confidence = decision.get('confidence', 0.5)
            active_positions = await paper_trading_dex.get_active_positions_count(strategy_id)
            
            # Use dynamic trade amount based on confidence (if not specified by LLM)
            if decision.get('action') == 'BUY' and not decision.get('amount_usdc'):
                dynamic_amount = paper_trading_dex.calculate_dynamic_trade_amount(
                    strategy_config, confidence, active_positions
                )
                decision['amount_usdc'] = dynamic_amount
                logger.info(f"[Strategy Execution] Dynamic trade amount calculated: ${dynamic_amount:.2f} (confidence: {confidence:.2f})")
            
            # Calculate dynamic stop-loss and take-profit (for logging/reference)
            dynamic_sl = paper_trading_dex.calculate_dynamic_stop_loss(strategy_config, confidence)
            dynamic_tp = paper_trading_dex.calculate_dynamic_take_profit(strategy_config, confidence)
            logger.info(f"[Strategy Execution] Dynamic risk params: SL={dynamic_sl*100:.1f}%, TP={dynamic_tp*100:.1f}%")
            
            # 9. Enforce safety rules
            decision = await self._enforce_safety_rules(
                strategy_id,
                decision,
                portfolio_state,
                strategy_config
            )
            
            # 9. Execute trade if valid
            trade_result = None
            if decision['action'] != 'HOLD' and decision['confidence'] >= 0.70:
                trade_result = await self._execute_trade(
                    strategy_id,
                    decision,
                    market_data,
                    execution_mode
                )
            
            # 10. Log execution
            execution_id = await self._log_execution(
                strategy_id=strategy_id,
                user_id=user_id,
                decision=decision,
                trade_result=trade_result,
                market_data=market_data,
                execution_mode=execution_mode,
                duration=time.time() - start_time,
                llm_model=strategy_config.get('llm_provider', 'openai/gpt-4o-mini')
            )
            
            # 11. Update last_execution timestamp
            await self._update_last_execution(strategy_id)
            
            # 12. Get updated trading state (recalculate with current price after trade)
            updated_portfolio = await paper_trading_dex.calculate_portfolio_value(
                strategy_id,
                pool_address=market_data.get('pool_address'),
                current_price=market_data.get('current_price', 0) if market_data.get('current_price', 0) > 0 else None
            )
            
            execution_duration = time.time() - start_time
            
            # Final execution summary
            logger.info(f"=" * 80)
            logger.info(f"[Strategy Execution] Execution completed in {execution_duration:.2f}s")
            logger.info(f"[Strategy Execution] Final decision: {decision.get('action')} (confidence: {decision.get('confidence', 0):.2f})")
            logger.info(f"[Strategy Execution] Trade executed: {'YES' if trade_result is not None else 'NO'}")
            logger.info(f"[Strategy Execution] Portfolio value: ${updated_portfolio['total_value']:.2f} (P&L: {updated_portfolio['unrealized_pnl_pct']:+.2f}%)")
            logger.info(f"=" * 80)
            
            return {
                "status": "success",
                "execution_id": execution_id,
                "decision": decision,
                "trading_state": {
                    "strategy_id": strategy_id,
                    "balances": updated_portfolio['balances'],
                    "total_portfolio_value": float(updated_portfolio['total_value']),
                    "initial_capital": float(updated_portfolio['initial_capital']),
                    "unrealized_pnl": float(updated_portfolio['unrealized_pnl']),
                    "realized_pnl": float(updated_portfolio.get('realized_pnl', 0)),
                    "total_pnl": float(updated_portfolio.get('total_pnl', updated_portfolio['unrealized_pnl'])),
                    "unrealized_pnl_pct": updated_portfolio['unrealized_pnl_pct'],
                    "total_pnl_pct": updated_portfolio.get('total_pnl_pct', updated_portfolio['unrealized_pnl_pct']),
                    "active_positions": await paper_trading_dex.get_active_positions_count(strategy_id)
                },
                "trade_executed": trade_result is not None,
                "duration": execution_duration
            }
            
        except Exception as e:
            logger.error(f"Error executing strategy {strategy_id}: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "duration": time.time() - start_time
            }
    
    async def _execute_with_langgraph(
        self,
        strategy_id: str,
        user_id: str,
        execution_mode: str = "analysis"
    ) -> Dict[str, Any]:
        """
        Execute strategy using LangGraph agent system.
        
        Args:
            strategy_id: Strategy UUID
            user_id: User ID
            execution_mode: "analysis" or "trade"
        
        Returns:
            Execution result from LangGraph workflow
        """
        try:
            # Import the trading graph
            from app.agents.trading_graph import execute_trading_strategy
            
            # Fetch strategy config
            strategy = await self._get_strategy(strategy_id, user_id)
            if not strategy:
                logger.error(f"Strategy not found: {strategy_id}")
                return {
                    "status": "error",
                    "error": "Strategy not found"
                }
            
            strategy_config = strategy.get('strategy_config', {})
            strategy_description = strategy.get('description', '')
            pool_id = strategy.get('pool_id')
            pool_address = strategy.get('pool_address')
            
            logger.info(f"[LangGraph] Executing strategy: {strategy.get('name')} (pool_id: {pool_id})")
            
            # Execute through LangGraph workflow
            result = await execute_trading_strategy(
                strategy_id=strategy_id,
                user_id=user_id,
                strategy_config=strategy_config,
                execution_mode=execution_mode,
                pool_id=pool_id,
                pool_address=pool_address,
                strategy_description=strategy_description
            )
            
            # Log execution to database (if successful)
            if result.get('status') == 'success':
                execution_id = await self._log_execution(
                    strategy_id=strategy_id,
                    user_id=user_id,
                    decision=result.get('decision', {}),
                    trade_result=result.get('trade_result'),  # Use actual trade result dict or None
                    market_data=result.get('market_data', {}),  # Use actual market data
                    execution_mode=execution_mode,
                    duration=result.get('duration', 0),
                    llm_model=strategy_config.get('llm_provider', 'openai/gpt-4o-mini')
                )
                result['execution_id'] = execution_id
                
                logger.info(f"[LangGraph] Execution logged to database: {execution_id}")
                
                # Calculate and log statistics (async, don't block)
                try:
                    from app.services.paper_trading_dex import paper_trading_dex
                    stats = await paper_trading_dex.get_trade_statistics(strategy_id)
                    logger.info(f"[LangGraph] Statistics updated: {stats.get('total_trades', 0)} trades, "
                              f"P&L: {stats.get('total_pnl', 0):.2f}%")
                except Exception as e:
                    logger.warning(f"[LangGraph] Error calculating statistics: {e}")
            
            # Update last_execution timestamp
            await self._update_last_execution(strategy_id)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in LangGraph execution: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "duration": time.time() - time.time()
            }
    
    async def _get_strategy(self, strategy_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Fetch strategy from database"""
        try:
            query = """
                SELECT *
                FROM user_strategies
                WHERE id = %s AND user_id = %s
            """
            return db_connection.execute_query(query, (strategy_id, user_id), fetch_one=True)
        except Exception as e:
            logger.error(f"Error fetching strategy: {e}", exc_info=True)
            return None
    
    async def _gather_market_data(self, strategy_config: Dict[str, Any], pool_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Gather OHLCV, technical indicators, and sentiment data from database"""
        logger.info(f"[Market Data Gathering] Starting data collection for pool_id: {pool_id}")
        try:
            agent_configs = strategy_config.get('agent_configs', {})
            ohlcv_config = agent_configs.get('ohlcv', {})
            technical_config = agent_configs.get('technical', {})
            
            # Get pool information from database if pool_id is provided
            pool_info = None
            token_symbol = 'MOVE'
            token_a_address = None
            token_b_address = None
            pool_address = None
            
            if pool_id:
                try:
                    logger.info(f"[Market Data Gathering] Fetching pool information from database...")
                    pool_query = """
                        SELECT pool_address, token_a_symbol, token_b_symbol, 
                               token_a_address, token_b_address
                        FROM pools
                        WHERE id = %s
                    """
                    pool_info = db_connection.execute_query(pool_query, (pool_id,), fetch_one=True)
                    if pool_info:
                        token_a_sym = pool_info.get('token_a_symbol') or ''
                        token_b_sym = pool_info.get('token_b_symbol') or ''
                        token_a_address = pool_info.get('token_a_address')
                        token_b_address = pool_info.get('token_b_address')
                        pool_address = pool_info.get('pool_address')
                        
                        # IMPORTANT: Trading token should be the NON-USDC token
                        # We always trade token vs USDC, so pick the non-stablecoin
                        # Normalize stablecoin set to handle case variations (.e, .E, etc.)
                        stablecoins_normalized = {'USDC', 'USDC.E', 'USDC.e', 'USDT', 'DAI'}
                        
                        # Normalize token symbols for comparison (handle .e/.E variations)
                        def normalize_token(symbol: str) -> str:
                            """Normalize token symbol for comparison"""
                            if not symbol:
                                return ''
                            normalized = symbol.upper()
                            # Handle .e/.E variations
                            normalized = normalized.replace('.E', '.E')  # Already uppercase
                            return normalized
                        
                        token_a_norm = normalize_token(token_a_sym)
                        token_b_norm = normalize_token(token_b_sym)
                        
                        if token_a_norm in stablecoins_normalized and token_b_norm not in stablecoins_normalized:
                            # token_a is stablecoin, use token_b as trading token
                            token_symbol = token_b_sym
                            logger.info(f"[Market Data Gathering] token_a ({token_a_sym}) is stablecoin, using token_b ({token_b_sym}) as trading token")
                        elif token_b_norm in stablecoins_normalized and token_a_norm not in stablecoins_normalized:
                            # token_b is stablecoin, use token_a as trading token
                            token_symbol = token_a_sym
                            logger.info(f"[Market Data Gathering] token_b ({token_b_sym}) is stablecoin, using token_a ({token_a_sym}) as trading token")
                        else:
                            # Neither or both are stablecoins - try to pick the non-stablecoin
                            # If both are stablecoins or neither, default to token_a (or first non-stablecoin)
                            if token_a_norm not in stablecoins_normalized:
                                token_symbol = token_a_sym
                            elif token_b_norm not in stablecoins_normalized:
                                token_symbol = token_b_sym
                            else:
                                # Both are stablecoins (shouldn't happen, but fallback)
                                token_symbol = token_a_sym or 'MOVE'
                            logger.warning(f"[Market Data Gathering] Could not determine trading token from {token_a_sym}/{token_b_sym}, using {token_symbol}")
                        
                        logger.info(f"[Market Data Gathering] Pool info retrieved: {token_a_sym}/{token_b_sym} - Trading token: {token_symbol} (address: {pool_address[:20]}...)")
                    else:
                        logger.warning(f"[Market Data Gathering] Pool not found in database for pool_id: {pool_id}")
                except Exception as e:
                    logger.error(f"[Market Data Gathering] Error fetching pool info: {e}", exc_info=True)
            
            # Fallback to config if pool_id not available
            if not pool_id or not pool_info:
                tokens = ohlcv_config.get('tokens', ['MOVE-USDC'])
                token_symbol = tokens[0].split('-')[0] if tokens else 'MOVE'
                logger.warning(f"[Market Data Gathering] No pool_id provided, using fallback token symbol: {token_symbol}")
            
            # Gather OHLCV data from database
            ohlcv_data = ""
            ohlcv_success = False
            if pool_id:
                try:
                    logger.info(f"[Market Data Gathering] Fetching OHLCV data from database for pool_id: {pool_id}...")
                    ohlcv_data = await ohlcv_service.format_for_llm(pool_id=pool_id)
                    if ohlcv_data and len(ohlcv_data) > 0:
                        ohlcv_success = True
                        logger.info(f"[Market Data Gathering] ✓ OHLCV data retrieved successfully ({len(ohlcv_data)} characters)")
                        # Log first few lines for verification
                        ohlcv_preview = ohlcv_data.split('\n')[:3]
                        logger.debug(f"[Market Data Gathering] OHLCV preview: {', '.join(ohlcv_preview)}")
                    else:
                        logger.warning(f"[Market Data Gathering] ✗ OHLCV data is empty")
                except Exception as e:
                    logger.error(f"[Market Data Gathering] ✗ Error fetching OHLCV data: {e}", exc_info=True)
            else:
                logger.warning(f"[Market Data Gathering] ✗ Skipping OHLCV data - no pool_id available")
            
            # Gather technical indicators from database
            technical_data = ""
            technical_success = False
            if pool_id:
                try:
                    indicator_names = [ind.get('name', '').upper() for ind in technical_config.get('indicators', [])]
                    if not indicator_names:
                        indicator_names = ['RSI', 'MACD', 'SMA_20', 'SMA_50', 'EMA_50']
                    
                    logger.info(f"[Market Data Gathering] Fetching technical indicators from database for pool_id: {pool_id}...")
                    logger.info(f"[Market Data Gathering] Requested indicators: {', '.join(indicator_names)}")
                    technical_data = technical_indicators_calculator.format_for_llm(
                        pool_id=pool_id,
                        indicators=indicator_names
                    )
                    if technical_data and len(technical_data) > 0:
                        technical_success = True
                        logger.info(f"[Market Data Gathering] ✓ Technical indicators retrieved successfully ({len(technical_data)} characters)")
                        # Log first few lines for verification
                        technical_preview = technical_data.split('\n')[:3]
                        logger.debug(f"[Market Data Gathering] Technical indicators preview: {', '.join(technical_preview)}")
                    else:
                        logger.warning(f"[Market Data Gathering] ✗ Technical indicators data is empty")
                except Exception as e:
                    logger.error(f"[Market Data Gathering] ✗ Error fetching technical indicators: {e}", exc_info=True)
            else:
                logger.warning(f"[Market Data Gathering] ✗ Skipping technical indicators - no pool_id available")
            
            # Gather sentiment data from database
            sentiment_data = ""
            sentiment_success = False
            if token_a_address and token_b_address:
                try:
                    logger.info(f"[Market Data Gathering] Fetching sentiment data from database...")
                    logger.info(f"[Market Data Gathering] Token addresses: {token_a_address[:20]}... / {token_b_address[:20]}...")
                    sentiment_result = await sentiment.sentiment_analyzer.analyze_token_pair_sentiment(
                        token_a_address=token_a_address,
                        token_b_address=token_b_address,
                        token_a_symbol=pool_info.get('token_a_symbol') if pool_info else token_symbol,
                        token_b_symbol=pool_info.get('token_b_symbol') if pool_info else 'USDC',
                        timeframe="24h"
                    )
                    if sentiment_result:
                        # Format sentiment for LLM using the formatter method (await since it's async)
                        sentiment_data = await sentiment.sentiment_analyzer.format_sentiment_for_llm(sentiment_result)
                        if sentiment_data and len(sentiment_data) > 0:
                            sentiment_success = True
                            logger.info(f"[Market Data Gathering] ✓ Sentiment data retrieved successfully ({len(sentiment_data)} characters)")
                            # Log preview
                            sentiment_preview = sentiment_data.split('\n')[:2]
                            logger.debug(f"[Market Data Gathering] Sentiment preview: {', '.join(sentiment_preview)}")
                        else:
                            logger.warning(f"[Market Data Gathering] ✗ Sentiment data is empty after formatting")
                    else:
                        logger.warning(f"[Market Data Gathering] ✗ Sentiment result is None")
                except Exception as e:
                    logger.error(f"[Market Data Gathering] ✗ Error fetching sentiment data: {e}", exc_info=True)
            else:
                logger.warning(f"[Market Data Gathering] ✗ Skipping sentiment data - missing token addresses (token_a: {bool(token_a_address)}, token_b: {bool(token_b_address)})")
            
            # Get current price from database (latest OHLCV candle)
            current_price = 0.0
            price_success = False
            if pool_id:
                try:
                    logger.info(f"[Market Data Gathering] Fetching current price from database...")
                    price_query = """
                        SELECT close_price
                        FROM ohlcv_candles
                        WHERE pool_id = %s
                        ORDER BY timestamp DESC
                        LIMIT 1
                    """
                    price_result = db_connection.execute_query(price_query, (pool_id,), fetch_one=True)
                    if price_result:
                        current_price = float(price_result.get('close_price', 0))
                        price_success = True
                        logger.info(f"[Market Data Gathering] ✓ Current price retrieved: ${current_price:.6f}")
                    else:
                        logger.warning(f"[Market Data Gathering] ✗ No price data found in database")
                except Exception as e:
                    logger.error(f"[Market Data Gathering] ✗ Error fetching current price: {e}", exc_info=True)
            else:
                logger.warning(f"[Market Data Gathering] ✗ Skipping current price - no pool_id available")
            
            # Summary log (handle None values safely)
            logger.info(f"[Market Data Gathering] Data collection summary:")
            logger.info(f"  OHLCV: {'✓ SUCCESS' if ohlcv_success else '✗ FAILED'} ({len(ohlcv_data) if ohlcv_data else 0} chars)")
            logger.info(f"  Technical Indicators: {'✓ SUCCESS' if technical_success else '✗ FAILED'} ({len(technical_data) if technical_data else 0} chars)")
            logger.info(f"  Sentiment: {'✓ SUCCESS' if sentiment_success else '✗ FAILED'} ({len(sentiment_data) if sentiment_data else 0} chars)")
            logger.info(f"  Current Price: {'✓ SUCCESS' if price_success else '✗ FAILED'} (${current_price:.6f})")
            
            # Ensure all data fields are strings (not None) for LLM
            return {
                "ohlcv": ohlcv_data or "",
                "technical": technical_data or "",
                "sentiment": sentiment_data or "",
                "current_price": current_price,
                "token_symbol": token_symbol,
                "pool_address": pool_address,
                "pool_id": pool_id
            }
            
        except Exception as e:
            logger.error(f"Error gathering market data: {e}", exc_info=True)
            return None
    
    async def _enforce_safety_rules(
        self,
        strategy_id: str,
        decision: Dict[str, Any],
        portfolio_state: Dict[str, Any],
        strategy_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enforce safety rules on LLM decision"""
        try:
            action = decision.get('action')
            confidence = decision.get('confidence', 0.0)
            
            # Rule 1: Minimum confidence gate
            if action in ['BUY', 'SELL'] and confidence < 0.70:
                logger.info(f"Confidence {confidence:.2f} below minimum 0.70, forcing HOLD")
                decision['action'] = 'HOLD'
                decision['reasoning'] = f"Confidence too low ({confidence:.2f}). " + decision.get('reasoning', '')
                return decision
            
            # Rule 2: Check position limits
            # Use database query for accurate count (more reliable than portfolio_state balances)
            paper_config = strategy_config.get('paper_trading_config', {})
            max_positions = paper_config.get('max_concurrent_positions', 5)
            
            # Get portfolio balances for both position counting and USDC balance lookup
            active_positions = portfolio_state.get('balances', [])
            
            # Get active positions count directly from database (most accurate)
            try:
                active_count = await paper_trading_dex.get_active_positions_count(strategy_id)
                logger.info(
                    f"[Safety Rules] Position check (from DB): {active_count}/{max_positions} positions active"
                )
            except Exception as e:
                logger.error(f"[Safety Rules] Error querying active positions from DB: {e}")
                # Fallback to portfolio_state if DB query fails
                active_count = sum(1 for b in active_positions if b['token_symbol'] != 'USDC' and b['balance'] > 0)
                logger.warning(
                    f"[Safety Rules] Using fallback count from portfolio_state: {active_count}/{max_positions}"
                )
            
            if action == 'BUY':
                if active_count >= max_positions:
                    logger.warning(
                        f"[Safety Rules] BLOCKED: Max positions limit reached ({active_count}/{max_positions}). "
                        f"Changing action from BUY to HOLD."
                    )
                    decision['action'] = 'HOLD'
                    decision['reasoning'] = f"Max positions limit reached ({active_count}/{max_positions}). " + decision.get('reasoning', '')
                    return decision
                else:
                    logger.info(
                        f"[Safety Rules] BUY allowed: {active_count}/{max_positions} positions "
                        f"(limit not reached, will double-check in _execute_trade)"
                    )
            
            # Rule 3: Check available capital
            usdc_balance = next((b['balance'] for b in active_positions if b['token_symbol'] == 'USDC'), 0)
            capital_per_trade = paper_config.get('capital_per_trade', 100)
            
            if action == 'BUY' and usdc_balance < capital_per_trade:
                logger.info(f"Insufficient USDC ({usdc_balance:.2f} < {capital_per_trade}), forcing HOLD")
                decision['action'] = 'HOLD'
                decision['reasoning'] = f"Insufficient capital (need ${capital_per_trade}, have ${usdc_balance:.2f}). " + decision.get('reasoning', '')
                return decision
            
            # Rule 4: Validate gas efficiency
            if action == 'BUY':
                amount_usdc = decision.get('amount_usdc', capital_per_trade)
                is_efficient, warning = risk_management.risk_agent.check_min_trade_size_for_gas(amount_usdc)
                if not is_efficient:
                    logger.warning(f"Trade not gas-efficient: {warning}")
                    decision['action'] = 'HOLD'
                    decision['reasoning'] = warning + ". " + decision.get('reasoning', '')
            
            return decision
            
        except Exception as e:
            logger.error(f"Error enforcing safety rules: {e}", exc_info=True)
            # Default to HOLD on error
            decision['action'] = 'HOLD'
            decision['reasoning'] = f"Safety check failed: {str(e)}"
            return decision
    
    async def _execute_trade(
        self,
        strategy_id: str,
        decision: Dict[str, Any],
        market_data: Dict[str, Any],
        execution_mode: str
    ) -> Optional[Dict[str, Any]]:
        """Execute paper trading swap"""
        try:
            action = decision.get('action')
            token = decision.get('token', 'MOVE')
            amount_usdc = decision.get('amount_usdc', 100)
            
            # SAFETY CHECK: Prevent swapping same tokens (USDC variants)
            stablecoins = {'USDC', 'USDC.e', 'USDT', 'DAI'}
            if token.upper() in stablecoins:
                logger.error(
                    f"[Trade Safety] Cannot trade stablecoin {token} - would result in same-token swap. "
                    f"Trading token should be the non-USDC token in the pair."
                )
                return None
            
            if action == 'BUY':
                # CRITICAL: Double-check max_concurrent_positions before executing BUY
                # This is a safeguard in case _enforce_safety_rules didn't catch it
                try:
                    # Get strategy config to check max positions
                    strategy_query = """
                        SELECT strategy_config
                        FROM user_strategies
                        WHERE id = %s
                    """
                    strategy_result = db_connection.execute_query(
                        strategy_query,
                        (strategy_id,),
                        fetch_one=True
                    )
                    
                    if strategy_result and strategy_result.get('strategy_config'):
                        strategy_config = strategy_result.get('strategy_config')
                        paper_config = strategy_config.get('paper_trading_config', {})
                        max_positions = paper_config.get('max_concurrent_positions', 5)
                        
                        # Get current active positions count from database (most accurate)
                        active_count = await paper_trading_dex.get_active_positions_count(strategy_id)
                        
                        # Check if we're about to create a new position
                        # If we already have this token, it's not a new position
                        token_balance = await paper_trading_dex.get_balance(
                            strategy_id,
                            paper_trading_dex.get_token_address(token),
                            token
                        )
                        is_new_position = token_balance <= 0
                        
                        if is_new_position and active_count >= max_positions:
                            logger.warning(
                                f"[Trade Safety] BLOCKED BUY: Max positions limit reached "
                                f"({active_count}/{max_positions}). Cannot open new {token} position."
                            )
                            return None
                        elif active_count >= max_positions:
                            logger.info(
                                f"[Trade Safety] Allowing BUY: {active_count}/{max_positions} positions, "
                                f"but {token} position already exists (not a new position)"
                            )
                except Exception as e:
                    logger.error(f"[Trade Safety] Error checking max positions before BUY: {e}")
                    # Don't block the trade if check fails, but log the error
                
                # Buy token with USDC
                # Buy token with USDC
                # Get the destination token address dynamically
                dst_token_address = paper_trading_dex.get_token_address(token)
                
                # Get quote from Mosaic
                quote = await mosaic.get_swap_quote_for_strategy(
                    src_token_symbol='USDC',
                    dst_token_symbol=token,
                    amount_usdc=amount_usdc,
                    sender="0x0000000000000000000000000000000000000000000000000000000000000000"  # Placeholder
                )
                
                if not quote:
                    logger.error("Failed to get swap quote")
                    return None
                
                # Extract amounts from quote (already in smallest units)
                src_amount_units = int(quote.get('srcAmount', 0))  # USDC: 6 decimals
                dst_amount_units = int(quote.get('dstAmount', 0))  # Token: 8 decimals (MOVE/WETH)
                
                # Convert to human-readable amounts
                src_amount = Decimal(str(src_amount_units)) / Decimal('1000000')  # USDC has 6 decimals
                dst_amount = Decimal(str(dst_amount_units)) / Decimal('100000000')  # Most tokens have 8 decimals
                
                # Calculate effective price (USDC per token)
                # This is the price at which we're buying the token
                price = src_amount / dst_amount if dst_amount > 0 else Decimal('0')
                
                logger.debug(
                    f"[Strategy Executor] Price calculation: "
                    f"src_amount={src_amount} USDC, dst_amount={dst_amount} {token}, "
                    f"price={price} USDC per {token}"
                )
                
                # Calculate slippage from quote
                # Mosaic quote already includes slippage in the output amount
                # We can estimate slippage by comparing to a theoretical perfect swap
                expected_output = quote.get('expectedOutput')
                slippage_pct = None
                if expected_output:
                    expected_amount = Decimal(str(expected_output)) / Decimal('100000000')
                    if expected_amount > 0:
                        slippage_pct = float((expected_amount - dst_amount) / expected_amount * 100)
                
                # Estimate gas fee (Movement network typical gas: ~0.001-0.01 USD per swap)
                # For paper trading, we'll use a conservative estimate
                gas_fee_usd = 0.002  # ~$0.002 per swap (can be adjusted based on actual gas costs)
                
                # Validate price calculation
                if price <= 0:
                    logger.error(
                        f"[Strategy Executor] Invalid price calculated: {price} "
                        f"(src_amount={src_amount}, dst_amount={dst_amount})"
                    )
                    return None
                
                # Price should be reasonable for the token (WETH.e ~$2900, MOVE varies)
                # If price is less than $1, something is wrong
                if price < Decimal('1.0') and token not in ['USDC', 'USDT', 'DAI']:
                    logger.error(
                        f"[Strategy Executor] Price {price} seems too low for {token}. "
                        f"Check if src_amount and dst_amount are in correct order/units."
                    )
                    return None
                
                logger.info(
                    f"[Paper Trading] Simulating swap: {src_amount} USDC -> {dst_amount} {token} "
                    f"(price: ${price:.6f} per {token}, slippage: {slippage_pct or 'N/A'}%, gas: ${gas_fee_usd:.4f})"
                )
                
                # Execute paper swap (simulated - updates database only)
                success = await paper_trading_dex.execute_swap(
                    strategy_id=strategy_id,
                    src_token_address=paper_trading_dex.USDC_ADDRESS,
                    src_token_symbol='USDC',
                    dst_token_address=dst_token_address,
                    dst_token_symbol=token,
                    amount_in=src_amount,
                    amount_out=dst_amount,
                    price=price,
                    slippage_pct=slippage_pct,
                    gas_fee_usd=gas_fee_usd,
                    quote_data=quote
                )
                
                if success:
                    return {
                        "trade_executed": True,
                        "symbol": f"{token}-USDC",
                        "side": "buy",
                        "amount_in": float(src_amount),
                        "amount_out": float(dst_amount),
                        "price": float(price)
                    }
            
            elif action == 'SELL' or action == 'CLOSE_POSITION':
                # Sell token for USDC
                # Get the source token address dynamically
                src_token_address = paper_trading_dex.get_token_address(token)
                
                # Get current token balance
                token_balance = await paper_trading_dex.get_balance(
                    strategy_id,
                    src_token_address,
                    token  # Token symbol for migration lookup
                )
                
                if token_balance <= 0:
                    logger.warning(f"No {token} balance to sell")
                    return None
                
                # Get quote with retry logic
                amount_in_units = int(token_balance * Decimal('100000000'))  # Convert to smallest unit
                
                quote = None
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        quote = await mosaic.get_quote(
                            src_asset=src_token_address,
                            dst_asset=paper_trading_dex.USDC_ADDRESS,
                            amount=str(amount_in_units),
                            sender="0x0000000000000000000000000000000000000000000000000000000000000000"
                        )
                        if quote:
                            break
                    except Exception as e:
                        logger.warning(f"[Paper Trading] Mosaic API attempt {attempt + 1}/{max_retries} failed: {e}")
                        if attempt < max_retries - 1:
                            import asyncio
                            await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
                # If API fails, use current price from market_data for paper trading
                if not quote:
                    logger.warning("[Paper Trading] Mosaic API unavailable, using current price from database for simulation")
                    current_price = market_data.get('current_price', 0)
                    if current_price > 0:
                        # Simulate quote using current price
                        src_amount = token_balance
                        dst_amount = src_amount * Decimal(str(current_price))
                        price = Decimal(str(current_price))
                        
                        logger.info(
                            f"[Paper Trading] Simulating sell using database price: {src_amount} {token} -> {dst_amount} USDC "
                            f"(price: ${price:.6f} from DB, gas: $0.0020)"
                        )
                        
                        # Execute paper swap using database price
                        success = await paper_trading_dex.execute_swap(
                            strategy_id=strategy_id,
                            src_token_address=src_token_address,
                            src_token_symbol=token,
                            dst_token_address=paper_trading_dex.USDC_ADDRESS,
                            dst_token_symbol='USDC',
                            amount_in=src_amount,
                            amount_out=dst_amount,
                            price=price,
                            slippage_pct=0.0,  # No slippage data available
                            gas_fee_usd=0.002,
                            quote_data=None
                        )
                        
                        if success:
                            return {
                                "trade_executed": True,
                                "symbol": f"{token}-USDC",
                                "side": "sell",
                                "amount_in": float(src_amount),
                                "amount_out": float(dst_amount),
                                "price": float(price)
                            }
                    else:
                        logger.error("Failed to get swap quote and no current price available")
                        return None
                
                # Extract amounts from quote
                src_amount = token_balance  # Already in human-readable format
                dst_amount_units = int(quote.get('dstAmount', 0))  # USDC: 6 decimals
                dst_amount = Decimal(str(dst_amount_units)) / Decimal('1000000')
                
                # Calculate effective price (USDC per token)
                price = dst_amount / src_amount if src_amount > 0 else Decimal('0')
                
                # Calculate slippage
                expected_output = quote.get('expectedOutput')
                slippage_pct = None
                if expected_output:
                    expected_amount = Decimal(str(expected_output)) / Decimal('1000000')
                    if expected_amount > 0:
                        slippage_pct = float((expected_amount - dst_amount) / expected_amount * 100)
                
                # Estimate gas fee
                gas_fee_usd = 0.002
                
                logger.info(
                    f"[Paper Trading] Simulating sell: {src_amount} {token} -> {dst_amount} USDC "
                    f"(price: ${price:.6f}, slippage: {slippage_pct or 'N/A'}%, gas: ${gas_fee_usd:.4f})"
                )
                
                # Execute paper swap (simulated)
                success = await paper_trading_dex.execute_swap(
                    strategy_id=strategy_id,
                    src_token_address=src_token_address,
                    src_token_symbol=token,
                    dst_token_address=paper_trading_dex.USDC_ADDRESS,
                    dst_token_symbol='USDC',
                    amount_in=src_amount,
                    amount_out=dst_amount,
                    price=price,
                    slippage_pct=slippage_pct,
                    gas_fee_usd=gas_fee_usd,
                    quote_data=quote
                )
                
                if success:
                    return {
                        "trade_executed": True,
                        "symbol": f"{token}-USDC",
                        "side": "sell",
                        "amount_in": float(src_amount),
                        "amount_out": float(dst_amount),
                        "price": float(price)
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error executing trade: {e}", exc_info=True)
            return None
    
    async def _execute_exit(
        self,
        strategy_id: str,
        user_id: str,
        exit_position: Dict[str, Any],
        strategy_config: Dict[str, Any],
        execution_mode: str
    ) -> bool:
        """Execute exit for stop-loss or take-profit"""
        try:
            logger.info(f"Executing exit for {exit_position['token_symbol']}: {exit_position['exit_reason']}")
            
            # Create exit decision
            decision = {
                "action": "CLOSE_POSITION",
                "token": exit_position['token_symbol'],
                "confidence": 1.0,
                "reasoning": f"Auto-exit: {exit_position['exit_reason']} (entry: ${exit_position['entry_price']:.6f}, current: ${exit_position['current_price']:.6f})"
            }
            
            # Execute the exit trade
            market_data = {"current_price": float(exit_position['current_price']), "token_symbol": exit_position['token_symbol']}
            trade_result = await self._execute_trade(strategy_id, decision, market_data, execution_mode)
            
            # Log the exit execution
            if trade_result:
                await self._log_execution(
                    strategy_id=strategy_id,
                    user_id=user_id,
                    decision=decision,
                    trade_result=trade_result,
                    market_data=market_data,
                    execution_mode=execution_mode,
                    duration=0.1,
                    llm_model="auto-exit"
                )
            
            return trade_result is not None
            
        except Exception as e:
            logger.error(f"Error executing exit: {e}", exc_info=True)
            return False
    
    async def _log_execution(
        self,
        strategy_id: str,
        user_id: str,
        decision: Dict[str, Any],
        trade_result: Optional[Dict[str, Any]],
        market_data: Dict[str, Any],
        execution_mode: str,
        duration: float,
        llm_model: str
    ) -> str:
        """Log execution to database"""
        try:
            query = """
                INSERT INTO strategy_executions (
                    strategy_id, user_id, execution_timestamp,
                    llm_model, decision, confidence, reasoning,
                    execution_mode, duration_seconds, llm_cost,
                    trade_executed, tx_hash, symbol, side,
                    amount_in, amount_out, price, market_data
                )
                VALUES (%s, %s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                RETURNING id
            """
            
            import json
            
            result = db_connection.execute_query(
                query,
                (
                    strategy_id,
                    user_id,
                    llm_model,
                    decision.get('action'),
                    decision.get('confidence', 0.0),
                    decision.get('reasoning', ''),
                    execution_mode,
                    duration,
                    0.0,  # LLM cost (would calculate from usage)
                    trade_result is not None,
                    None,  # tx_hash (for live trading)
                    trade_result.get('symbol') if trade_result else None,
                    trade_result.get('side') if trade_result else None,
                    trade_result.get('amount_in') if trade_result else None,
                    trade_result.get('amount_out') if trade_result else None,
                    trade_result.get('price') if trade_result else None,
                    json.dumps(market_data)
                ),
                fetch_one=True
            )
            
            return str(result.get('id')) if result else ""
            
        except Exception as e:
            logger.error(f"Error logging execution: {e}", exc_info=True)
            return ""
    
    async def _update_last_execution(self, strategy_id: str) -> bool:
        """Update last_execution timestamp"""
        try:
            query = """
                UPDATE user_strategies
                SET last_execution = NOW()
                WHERE id = %s
            """
            db_connection.execute_query(query, (strategy_id,))
            return True
        except Exception as e:
            logger.error(f"Error updating last_execution: {e}", exc_info=True)
            return False


# Singleton instance
strategy_executor = StrategyExecutor()

