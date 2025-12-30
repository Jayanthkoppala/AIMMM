"""
Market Data Agent
Gathers OHLCV, technical indicators, and sentiment data for trading decisions
"""
from typing import Dict, Any
from app.agents.base_agent import BaseAgent
from app.agents.state import TradingState
from app.services.ohlcv import ohlcv_service
from app.services.technical_indicators import technical_indicators_calculator
from app.services import sentiment


class MarketDataAgent(BaseAgent):
    """
    Gathers comprehensive market data for trading decisions.
    
    Responsibilities:
    - Fetch OHLCV data from database
    - Fetch technical indicators
    - Fetch sentiment analysis
    - Validate data completeness
    """
    
    def __init__(self):
        super().__init__("MarketDataAgent")
    
    async def process(self, state: TradingState) -> Dict[str, Any]:
        """
        Gather market data from various sources.
        
        Args:
            state: Current trading state
        
        Returns:
            State updates with market data
        """
        self.log_entry(state, "Starting market data gathering")
        
        # Validate required fields
        validation_error = self.validate_required_fields(
            state,
            ['strategy_config', 'pool_id']
        )
        if validation_error:
            self.log_error(state, validation_error)
            return {
                'data_complete': False,
                'errors': state.get('errors', []) + [validation_error]
            }
        
        strategy_config = state['strategy_config']
        pool_id = state['pool_id']
        
        # Initialize market data dict
        market_data = {
            'ohlcv': '',
            'technical': '',
            'sentiment': '',
            'current_price': 0.0,
            'token_symbol': 'MOVE',
            'pool_address': state.get('pool_address'),
            'pool_id': pool_id
        }
        
        data_errors = []
        
        # Get pool information for token symbols and addresses
        token_a_address = None
        token_b_address = None
        token_symbol = 'MOVE'
        
        if pool_id:
            try:
                from app.utils.database import db_connection
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
                    market_data['pool_address'] = pool_address
                    
                    # Determine trading token (non-stablecoin)
                    stablecoins = {'USDC', 'USDC.E', 'USDC.e', 'USDT', 'DAI'}
                    token_a_norm = token_a_sym.upper()
                    token_b_norm = token_b_sym.upper()
                    
                    if token_a_norm in stablecoins and token_b_norm not in stablecoins:
                        token_symbol = token_b_sym
                    elif token_b_norm in stablecoins and token_a_norm not in stablecoins:
                        token_symbol = token_a_sym
                    else:
                        token_symbol = token_a_sym or 'MOVE'
                    
                    market_data['token_symbol'] = token_symbol
                    self.log_info(state, f"Pool info: {token_a_sym}/{token_b_sym}, trading token: {token_symbol}")
                    
            except Exception as e:
                self.log_error(state, f"Error fetching pool info: {e}")
                data_errors.append(f"Pool info error: {str(e)}")
        
        # 1. Fetch OHLCV data
        try:
            self.log_info(state, "Fetching OHLCV data...")
            ohlcv_data = await ohlcv_service.format_for_llm(pool_id=pool_id)
            if ohlcv_data and len(ohlcv_data) > 0:
                market_data['ohlcv'] = ohlcv_data
                self.log_info(state, f"OHLCV data retrieved ({len(ohlcv_data)} chars)")
            else:
                self.log_warning(state, "OHLCV data is empty")
                data_errors.append("OHLCV data is empty")
        except Exception as e:
            self.log_error(state, f"Error fetching OHLCV: {e}")
            data_errors.append(f"OHLCV error: {str(e)}")
        
        # 2. Fetch technical indicators
        try:
            self.log_info(state, "Fetching technical indicators...")
            agent_configs = strategy_config.get('agent_configs', {})
            technical_config = agent_configs.get('technical', {})
            indicator_names = [ind.get('name', '').upper() for ind in technical_config.get('indicators', [])]
            
            if not indicator_names:
                indicator_names = ['RSI', 'MACD', 'SMA_20', 'SMA_50', 'EMA_50']
            
            technical_data = technical_indicators_calculator.format_for_llm(
                pool_id=pool_id,
                indicators=indicator_names
            )
            
            if technical_data and len(technical_data) > 0:
                market_data['technical'] = technical_data
                self.log_info(state, f"Technical indicators retrieved ({len(technical_data)} chars)")
            else:
                self.log_warning(state, "Technical indicators data is empty")
                data_errors.append("Technical indicators data is empty")
        except Exception as e:
            self.log_error(state, f"Error fetching technical indicators: {e}")
            data_errors.append(f"Technical indicators error: {str(e)}")
        
        # 3. Fetch sentiment data
        if token_a_address and token_b_address:
            try:
                self.log_info(state, "Fetching sentiment data...")
                sentiment_result = await sentiment.sentiment_analyzer.analyze_token_pair_sentiment(
                    token_a_address=token_a_address,
                    token_b_address=token_b_address,
                    token_a_symbol=token_symbol,
                    token_b_symbol='USDC',
                    timeframe="24h"
                )
                
                if sentiment_result:
                    sentiment_data = await sentiment.sentiment_analyzer.format_sentiment_for_llm(sentiment_result)
                    if sentiment_data and len(sentiment_data) > 0:
                        market_data['sentiment'] = sentiment_data
                        self.log_info(state, f"Sentiment data retrieved ({len(sentiment_data)} chars)")
                    else:
                        self.log_warning(state, "Sentiment data is empty after formatting")
                else:
                    self.log_warning(state, "Sentiment result is None")
            except Exception as e:
                self.log_error(state, f"Error fetching sentiment: {e}")
                data_errors.append(f"Sentiment error: {str(e)}")
        else:
            self.log_warning(state, "Skipping sentiment - missing token addresses")
        
        # 4. Get current price
        if pool_id:
            try:
                from app.utils.database import db_connection
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
                    market_data['current_price'] = current_price
                    self.log_info(state, f"Current price: ${current_price:.6f}")
                else:
                    self.log_warning(state, "No price data found")
                    data_errors.append("No current price available")
            except Exception as e:
                self.log_error(state, f"Error fetching current price: {e}")
                data_errors.append(f"Price error: {str(e)}")
        
        # Determine data completeness
        data_complete = (
            len(market_data['ohlcv']) > 0 and
            len(market_data['technical']) > 0 and
            market_data['current_price'] > 0
        )
        
        self.log_info(state, f"Data gathering complete: {data_complete}")
        self.log_info(state, f"Data summary: OHLCV={'✓' if market_data['ohlcv'] else '✗'}, "
                            f"Technical={'✓' if market_data['technical'] else '✗'}, "
                            f"Sentiment={'✓' if market_data['sentiment'] else '✗'}, "
                            f"Price={market_data['current_price']:.6f}")
        
        return {
            'market_data': market_data,
            'data_complete': data_complete,
            'data_errors': data_errors
        }


# Singleton instance
market_data_agent = MarketDataAgent()

