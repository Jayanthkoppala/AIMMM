"""
Portfolio Agent
Tracks portfolio state, calculates P&L, and manages position information
"""
from typing import Dict, Any
from app.agents.base_agent import BaseAgent
from app.agents.state import TradingState
from app.services.paper_trading_dex import paper_trading_dex


class PortfolioAgent(BaseAgent):
    """
    Manages portfolio state and position tracking.
    
    Responsibilities:
    - Initialize paper trading balances if needed
    - Calculate current portfolio value
    - Track active positions
    - Calculate P&L metrics
    """
    
    def __init__(self):
        super().__init__("PortfolioAgent")
    
    async def process(self, state: TradingState) -> Dict[str, Any]:
        """
        Calculate portfolio state and position information.
        
        Args:
            state: Current trading state
        
        Returns:
            State updates with portfolio information
        """
        self.log_entry(state, "Calculating portfolio state")
        
        # Validate required fields
        validation_error = self.validate_required_fields(
            state,
            ['strategy_id', 'strategy_config', 'market_data']
        )
        if validation_error:
            self.log_error(state, validation_error)
            return self.add_error(state, validation_error)
        
        strategy_id = state['strategy_id']
        strategy_config = state['strategy_config']
        market_data = state['market_data']
        
        # Initialize paper trading balances if needed
        paper_config = strategy_config.get('paper_trading_config', {})
        initial_capital = paper_config.get('initial_capital_usdc', 1000)
        
        try:
            self.log_info(state, f"Initializing balances with ${initial_capital} USDC")
            await paper_trading_dex.initialize_strategy_balances(
                strategy_id,
                initial_capital
            )
            
            # Verify balance
            usdc_balance = await paper_trading_dex.get_balance(
                strategy_id,
                paper_trading_dex.USDC_ADDRESS,
                "USDC"
            )
            self.log_info(state, f"USDC balance verified: ${float(usdc_balance):.2f}")
            
        except Exception as e:
            self.log_error(state, f"Error initializing balances: {e}")
            return self.add_error(state, f"Balance initialization error: {str(e)}")
        
        # Calculate portfolio value with current market price
        try:
            current_price = market_data.get('current_price', 0)
            pool_address = market_data.get('pool_address')
            
            self.log_info(state, "Calculating portfolio value...")
            portfolio_state = await paper_trading_dex.calculate_portfolio_value(
                strategy_id,
                pool_address=pool_address,
                current_price=current_price if current_price > 0 else None
            )
            
            total_value = float(portfolio_state.get('total_value', 0))
            unrealized_pnl = float(portfolio_state.get('unrealized_pnl', 0))
            unrealized_pnl_pct = portfolio_state.get('unrealized_pnl_pct', 0)
            
            self.log_info(state, f"Portfolio value: ${total_value:.2f} "
                                f"(P&L: ${unrealized_pnl:+.2f}, {unrealized_pnl_pct:+.2f}%)")
            
            # Get active positions
            balances = portfolio_state.get('balances', [])
            active_positions = [
                b for b in balances
                if b['token_symbol'] != 'USDC' and b['balance'] > 0
            ]
            
            # Get USDC balance
            usdc_balance_value = next(
                (b['balance'] for b in balances if b['token_symbol'] == 'USDC'),
                0.0
            )
            
            self.log_info(state, f"Active positions: {len(active_positions)}, "
                                f"USDC available: ${usdc_balance_value:.2f}")
            
            return {
                'portfolio_state': portfolio_state,
                'active_positions': active_positions,
                'usdc_balance': usdc_balance_value,
                'total_value': total_value
            }
            
        except Exception as e:
            self.log_error(state, f"Error calculating portfolio: {e}")
            import traceback
            traceback.print_exc()
            return self.add_error(state, f"Portfolio calculation error: {str(e)}")


# Singleton instance
portfolio_agent = PortfolioAgent()

