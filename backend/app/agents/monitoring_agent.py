"""
Monitoring Agent
Monitors positions, checks exit signals, and tracks performance
"""
from typing import Dict, Any
from app.agents.base_agent import BaseAgent
from app.agents.state import TradingState
from app.services.paper_trading_dex import paper_trading_dex


class MonitoringAgent(BaseAgent):
    """
    Monitors open positions and checks for exit conditions.
    
    Responsibilities:
    - Monitor all open positions
    - Check stop-loss triggers
    - Check take-profit triggers
    - Track performance metrics
    - Generate position alerts
    """
    
    def __init__(self):
        super().__init__("MonitoringAgent")
    
    async def process(self, state: TradingState) -> Dict[str, Any]:
        """
        Monitor positions and check exit signals.
        
        Args:
            state: Current trading state
        
        Returns:
            State updates with monitoring results
        """
        self.log_entry(state, "Monitoring positions for exit signals")
        
        # Validate required fields
        validation_error = self.validate_required_fields(
            state,
            ['strategy_id', 'strategy_config']
        )
        if validation_error:
            self.log_error(state, validation_error)
            return self.add_error(state, validation_error)
        
        strategy_id = state['strategy_id']
        strategy_config = state['strategy_config']
        pool_address = state.get('pool_address')
        
        try:
            # Check for positions that need to be exited
            self.log_info(state, "Checking for stop-loss and take-profit triggers...")
            
            exit_positions = await paper_trading_dex.check_exit_signals(
                strategy_id,
                strategy_config,
                pool_address=pool_address
            )
            
            if exit_positions and len(exit_positions) > 0:
                self.log_info(state, f"Found {len(exit_positions)} positions to exit:")
                
                for exit_pos in exit_positions:
                    token = exit_pos.get('token_symbol')
                    reason = exit_pos.get('exit_reason')
                    entry = exit_pos.get('entry_price', 0)
                    current = exit_pos.get('current_price', 0)
                    change = ((current - entry) / entry * 100) if entry > 0 else 0
                    
                    self.log_info(state, f"  - {token}: {reason} "
                                        f"(entry: ${entry:.6f}, current: ${current:.6f}, "
                                        f"change: {change:+.2f}%)")
                
                return {
                    'exit_positions': exit_positions,
                    'should_exit_positions': True
                }
            else:
                self.log_info(state, "No exit signals detected")
                
                return {
                    'exit_positions': [],
                    'should_exit_positions': False
                }
            
        except Exception as e:
            self.log_error(state, f"Error monitoring positions: {e}")
            import traceback
            traceback.print_exc()
            return {
                'exit_positions': [],
                'should_exit_positions': False,
                'errors': state.get('errors', []) + [f"Monitoring error: {str(e)}"]
            }


# Singleton instance
monitoring_agent = MonitoringAgent()

