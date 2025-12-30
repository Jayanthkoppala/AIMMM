"""
Risk Agent
Evaluates risk, enforces safety rules, and validates trading decisions
"""
from typing import Dict, Any
from app.agents.base_agent import BaseAgent
from app.agents.state import TradingState
from app.services.paper_trading_dex import paper_trading_dex
from app.services import risk_management


class RiskAgent(BaseAgent):
    """
    Enforces risk management rules and validates trades.
    
    Responsibilities:
    - Check position limits
    - Validate available capital
    - Enforce confidence thresholds
    - Check gas efficiency
    - Act as safety gatekeeper
    """
    
    def __init__(self):
        super().__init__("RiskAgent")
    
    async def process(self, state: TradingState) -> Dict[str, Any]:
        """
        Evaluate risk and enforce safety rules.
        
        Args:
            state: Current trading state
        
        Returns:
            State updates with risk assessment
        """
        self.log_entry(state, "Evaluating risk and safety rules")
        
        # Validate required fields
        validation_error = self.validate_required_fields(
            state,
            ['strategy_id', 'strategy_config', 'portfolio_state']
        )
        if validation_error:
            self.log_error(state, validation_error)
            return self.add_error(state, validation_error)
        
        strategy_id = state['strategy_id']
        strategy_config = state['strategy_config']
        portfolio_state = state['portfolio_state']
        decision = state.get('decision')
        
        risk_checks = {}
        risk_warnings = []
        risk_approved = True
        
        # Get paper trading config
        paper_config = strategy_config.get('paper_trading_config', {})
        max_positions = paper_config.get('max_concurrent_positions', 5)
        capital_per_trade = paper_config.get('capital_per_trade', 100)
        min_confidence = 0.70
        
        # If no decision yet, just do preliminary checks
        if not decision:
            self.log_info(state, "No decision yet, performing preliminary risk checks")
            
            # Check 1: Active positions
            try:
                active_count = await paper_trading_dex.get_active_positions_count(strategy_id)
                risk_checks['position_limit'] = active_count < max_positions
                
                if active_count >= max_positions:
                    risk_warnings.append(f"At max position limit ({active_count}/{max_positions})")
                    self.log_warning(state, f"At max positions: {active_count}/{max_positions}")
                else:
                    self.log_info(state, f"Position check: {active_count}/{max_positions}")
                    
            except Exception as e:
                self.log_error(state, f"Error checking positions: {e}")
                risk_checks['position_limit'] = False
                risk_warnings.append(f"Position check failed: {str(e)}")
            
            # Check 2: Available capital
            balances = portfolio_state.get('balances', [])
            usdc_balance = next(
                (b['balance'] for b in balances if b['token_symbol'] == 'USDC'),
                0
            )
            
            risk_checks['sufficient_capital'] = usdc_balance >= capital_per_trade
            
            if usdc_balance < capital_per_trade:
                risk_warnings.append(f"Low capital: ${usdc_balance:.2f} < ${capital_per_trade}")
                self.log_warning(state, f"Low capital: ${usdc_balance:.2f}")
            else:
                self.log_info(state, f"Capital check: ${usdc_balance:.2f} available")
            
            return {
                'risk_checks': risk_checks,
                'risk_warnings': risk_warnings,
                'risk_approved': True  # Preliminary checks don't block
            }
        
        # Decision exists, perform full validation
        action = decision.get('action')
        confidence = decision.get('confidence', 0.0)
        amount_usdc = decision.get('amount_usdc', capital_per_trade)
        
        self.log_info(state, f"Validating decision: {action} (confidence: {confidence:.2f})")
        
        # Rule 1: Minimum confidence
        risk_checks['confidence'] = confidence >= min_confidence
        if action in ['BUY', 'SELL'] and confidence < min_confidence:
            risk_approved = False
            risk_warnings.append(f"Confidence {confidence:.2f} below minimum {min_confidence}")
            self.log_warning(state, f"Confidence too low: {confidence:.2f} < {min_confidence}")
        else:
            self.log_info(state, f"Confidence check: {confidence:.2f} >= {min_confidence}")
        
        # Rule 2: Position limits (for BUY orders)
        if action == 'BUY':
            try:
                active_count = await paper_trading_dex.get_active_positions_count(strategy_id)
                risk_checks['position_limit'] = active_count < max_positions
                
                if active_count >= max_positions:
                    risk_approved = False
                    risk_warnings.append(f"Max positions reached ({active_count}/{max_positions})")
                    self.log_warning(state, f"BLOCKED: Max positions reached {active_count}/{max_positions}")
                else:
                    self.log_info(state, f"Position limit: {active_count}/{max_positions} OK")
                    
            except Exception as e:
                risk_approved = False
                risk_checks['position_limit'] = False
                risk_warnings.append(f"Position check error: {str(e)}")
                self.log_error(state, f"Position check failed: {e}")
        
        # Rule 3: Sufficient capital (for BUY orders)
        if action == 'BUY':
            balances = portfolio_state.get('balances', [])
            usdc_balance = next(
                (b['balance'] for b in balances if b['token_symbol'] == 'USDC'),
                0
            )
            
            risk_checks['sufficient_capital'] = usdc_balance >= amount_usdc
            
            if usdc_balance < amount_usdc:
                risk_approved = False
                risk_warnings.append(f"Insufficient capital: ${usdc_balance:.2f} < ${amount_usdc}")
                self.log_warning(state, f"BLOCKED: Insufficient capital ${usdc_balance:.2f} < ${amount_usdc}")
            else:
                self.log_info(state, f"Capital check: ${usdc_balance:.2f} >= ${amount_usdc} OK")
        
        # Rule 4: Gas efficiency
        if action == 'BUY':
            is_efficient, warning = risk_management.risk_agent.check_min_trade_size_for_gas(
                amount_usdc,
                estimated_gas_usd=0.002
            )
            
            risk_checks['gas_efficient'] = is_efficient
            
            if not is_efficient:
                risk_approved = False
                risk_warnings.append(warning)
                self.log_warning(state, f"BLOCKED: {warning}")
            else:
                self.log_info(state, "Gas efficiency check: OK")
        
        # Summary
        if risk_approved:
            self.log_info(state, "✓ All risk checks passed")
        else:
            self.log_warning(state, f"✗ Risk checks failed: {', '.join(risk_warnings)}")
        
        return {
            'risk_checks': risk_checks,
            'risk_warnings': risk_warnings,
            'risk_approved': risk_approved
        }


# Singleton instance
risk_agent = RiskAgent()

