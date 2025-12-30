"""
Decision Agent
Makes trading decisions using LLM with comprehensive market context
"""
from typing import Dict, Any
from app.agents.base_agent import BaseAgent
from app.agents.state import TradingState
from app.services import llm


class DecisionAgent(BaseAgent):
    """
    Makes informed trading decisions using LLM.
    
    Responsibilities:
    - Aggregate all available context
    - Call LLM for decision making
    - Parse and validate decision
    - Support decision refinement iterations
    """
    
    def __init__(self):
        super().__init__("DecisionAgent")
    
    async def process(self, state: TradingState) -> Dict[str, Any]:
        """
        Make trading decision using LLM.
        
        Args:
            state: Current trading state
        
        Returns:
            State updates with trading decision
        """
        self.log_entry(state, "Making trading decision with LLM")
        
        # Validate required fields
        validation_error = self.validate_required_fields(
            state,
            ['portfolio_state', 'market_data', 'strategy_config', 'analysis']
        )
        if validation_error:
            self.log_error(state, validation_error)
            return self.add_error(state, validation_error)
        
        portfolio_state = state['portfolio_state']
        market_data = state['market_data']
        strategy_config = state['strategy_config']
        strategy_description = state.get('strategy_description')
        analysis = state.get('analysis')
        
        try:
            self.log_info(state, "Preparing context for LLM decision...")
            
            # Log data availability
            self.log_info(state, f"Context: OHLCV={'✓' if len(market_data.get('ohlcv', '')) > 0 else '✗'}, "
                                f"Technical={'✓' if len(market_data.get('technical', '')) > 0 else '✗'}, "
                                f"Sentiment={'✓' if len(market_data.get('sentiment', '')) > 0 else '✗'}")
            
            # Get LLM decision
            self.log_info(state, "Calling LLM for decision...")
            decision = await llm.get_strategy_decision(
                portfolio_state=portfolio_state,
                market_data=market_data,
                strategy_config=strategy_config,
                strategy_description=strategy_description,
                llm_model=strategy_config.get('llm_provider')
            )
            
            # Extract decision details
            action = decision.get('action', 'HOLD')
            confidence = decision.get('confidence', 0.0)
            reasoning = decision.get('reasoning', 'No reasoning provided')
            token = decision.get('token')
            amount_usdc = decision.get('amount_usdc')
            
            self.log_info(state, f"LLM decision: {action} (confidence: {confidence:.2f})")
            self.log_info(state, f"Reasoning: {reasoning[:200]}...")
            
            # Validate decision
            if action not in ['BUY', 'SELL', 'HOLD', 'CLOSE_POSITION']:
                self.log_warning(state, f"Invalid action '{action}', forcing HOLD")
                action = 'HOLD'
                decision['action'] = 'HOLD'
            
            # Ensure confidence is within bounds
            confidence = max(0.0, min(1.0, confidence))
            decision['confidence'] = confidence
            
            # For BUY decisions, ensure amount is specified
            if action == 'BUY' and not amount_usdc:
                paper_config = strategy_config.get('paper_trading_config', {})
                capital_per_trade = paper_config.get('capital_per_trade', 100)
                decision['amount_usdc'] = capital_per_trade
                self.log_info(state, f"Using default trade amount: ${capital_per_trade}")
            
            return {
                'decision': decision,
                'confidence': confidence,
                'action': action,
                'reasoning': reasoning
            }
            
        except Exception as e:
            self.log_error(state, f"Error making decision: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback to HOLD on error
            return {
                'decision': {
                    'action': 'HOLD',
                    'confidence': 0.3,
                    'reasoning': f"Error making decision: {str(e)}",
                    'token': None,
                    'amount_usdc': 0
                },
                'confidence': 0.3,
                'action': 'HOLD',
                'reasoning': f"Error: {str(e)}",
                'errors': state.get('errors', []) + [f"Decision error: {str(e)}"]
            }


# Singleton instance
decision_agent = DecisionAgent()

