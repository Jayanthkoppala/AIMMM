"""
Analysis Agent
Analyzes market data, identifies patterns, and generates trading insights
"""
from typing import Dict, Any
from app.agents.base_agent import BaseAgent
from app.agents.state import TradingState


class AnalysisAgent(BaseAgent):
    """
    Analyzes market data and generates insights for decision making.
    
    Responsibilities:
    - Analyze trends from OHLCV data
    - Interpret technical indicators
    - Assess sentiment signals
    - Identify patterns and anomalies
    - Generate market condition summary
    """
    
    def __init__(self):
        super().__init__("AnalysisAgent")
    
    async def process(self, state: TradingState) -> Dict[str, Any]:
        """
        Analyze market data and generate insights.
        
        Args:
            state: Current trading state
        
        Returns:
            State updates with analysis insights
        """
        self.log_entry(state, "Analyzing market conditions")
        
        # Validate required fields
        validation_error = self.validate_required_fields(
            state,
            ['market_data', 'portfolio_state']
        )
        if validation_error:
            self.log_error(state, validation_error)
            return self.add_error(state, validation_error)
        
        market_data = state['market_data']
        portfolio_state = state['portfolio_state']
        
        # Extract data
        ohlcv_data = market_data.get('ohlcv', '')
        technical_data = market_data.get('technical', '')
        sentiment_data = market_data.get('sentiment', '')
        current_price = market_data.get('current_price', 0)
        token_symbol = market_data.get('token_symbol', 'MOVE')
        
        analysis = {
            'has_ohlcv': len(ohlcv_data) > 0,
            'has_technical': len(technical_data) > 0,
            'has_sentiment': len(sentiment_data) > 0,
            'current_price': current_price,
            'token_symbol': token_symbol
        }
        
        # Analyze trend from OHLCV (simple analysis from data presence)
        trend_analysis = []
        if ohlcv_data:
            trend_analysis.append("Historical price data available")
            # Extract trend direction from OHLCV if possible
            if 'Upward' in ohlcv_data or 'upward' in ohlcv_data:
                trend_analysis.append("Upward trend detected")
            elif 'Downward' in ohlcv_data or 'downward' in ohlcv_data:
                trend_analysis.append("Downward trend detected")
            else:
                trend_analysis.append("Trend analysis available")
        
        # Analyze technical indicators
        technical_analysis = []
        if technical_data:
            # Parse technical data for key signals
            if 'RSI' in technical_data:
                if 'Overbought' in technical_data:
                    technical_analysis.append("RSI indicates overbought conditions")
                elif 'Oversold' in technical_data:
                    technical_analysis.append("RSI indicates oversold conditions")
                else:
                    technical_analysis.append("RSI in neutral zone")
            
            if 'MACD' in technical_data:
                if 'Bullish' in technical_data:
                    technical_analysis.append("MACD shows bullish signal")
                elif 'Bearish' in technical_data:
                    technical_analysis.append("MACD shows bearish signal")
            
            if 'SMA' in technical_data or 'EMA' in technical_data:
                technical_analysis.append("Moving averages available for trend confirmation")
            
            if 'Bollinger' in technical_data:
                if 'Near Upper' in technical_data:
                    technical_analysis.append("Price near upper Bollinger Band")
                elif 'Near Lower' in technical_data:
                    technical_analysis.append("Price near lower Bollinger Band")
        
        # Analyze sentiment
        sentiment_analysis = []
        if sentiment_data:
            if 'BULLISH' in sentiment_data or 'bullish' in sentiment_data:
                sentiment_analysis.append("Bullish sentiment detected")
            elif 'BEARISH' in sentiment_data or 'bearish' in sentiment_data:
                sentiment_analysis.append("Bearish sentiment detected")
            else:
                sentiment_analysis.append("Neutral sentiment")
        
        # Portfolio analysis
        portfolio_analysis = []
        total_value = portfolio_state.get('total_value', 0)
        initial_capital = portfolio_state.get('initial_capital', 1000)
        pnl_pct = portfolio_state.get('unrealized_pnl_pct', 0)
        
        if pnl_pct > 5:
            portfolio_analysis.append(f"Strong positive performance: {pnl_pct:+.2f}%")
        elif pnl_pct < -5:
            portfolio_analysis.append(f"Negative performance: {pnl_pct:+.2f}%")
        else:
            portfolio_analysis.append(f"Portfolio stable: {pnl_pct:+.2f}%")
        
        # Determine overall market conditions
        market_conditions = []
        
        if len(technical_analysis) > 0:
            bullish_signals = sum(1 for s in technical_analysis if 'bullish' in s.lower() or 'oversold' in s.lower())
            bearish_signals = sum(1 for s in technical_analysis if 'bearish' in s.lower() or 'overbought' in s.lower())
            
            if bullish_signals > bearish_signals:
                market_conditions.append("Technical indicators lean bullish")
            elif bearish_signals > bullish_signals:
                market_conditions.append("Technical indicators lean bearish")
            else:
                market_conditions.append("Technical indicators are mixed")
        
        if 'Bullish sentiment' in sentiment_analysis:
            market_conditions.append("Positive market sentiment")
        elif 'Bearish sentiment' in sentiment_analysis:
            market_conditions.append("Negative market sentiment")
        
        # Create analysis summary
        analysis['trend_analysis'] = trend_analysis
        analysis['technical_analysis'] = technical_analysis
        analysis['sentiment_analysis'] = sentiment_analysis
        analysis['portfolio_analysis'] = portfolio_analysis
        analysis['market_conditions'] = market_conditions
        
        # Create summary strings for LLM
        trend_summary = "; ".join(trend_analysis) if trend_analysis else "No trend data"
        market_condition_summary = "; ".join(market_conditions) if market_conditions else "Mixed signals"
        
        self.log_info(state, f"Analysis complete: {len(market_conditions)} market signals identified")
        self.log_info(state, f"Market conditions: {market_condition_summary[:100]}")
        
        return {
            'analysis': analysis,
            'trend_analysis': trend_summary,
            'market_conditions': market_condition_summary
        }


# Singleton instance
analysis_agent = AnalysisAgent()

