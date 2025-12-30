"""
Execution Agent
Executes trades, manages order flow, and handles trade execution
"""
from typing import Dict, Any
from decimal import Decimal
from app.agents.base_agent import BaseAgent
from app.agents.state import TradingState
from app.services.paper_trading_dex import paper_trading_dex
from app.services import mosaic


class ExecutionAgent(BaseAgent):
    """
    Executes trading orders.
    
    Responsibilities:
    - Execute BUY/SELL orders
    - Handle exit position orders
    - Manage slippage and gas fees
    - Validate execution results
    - Log trade details
    """
    
    def __init__(self):
        super().__init__("ExecutionAgent")
    
    async def process(self, state: TradingState) -> Dict[str, Any]:
        """
        Execute trading order based on decision.
        
        Args:
            state: Current trading state
        
        Returns:
            State updates with execution results
        """
        self.log_entry(state, "Executing trade order")
        
        # Check if there are exit positions to handle first
        exit_positions = state.get('exit_positions', [])
        if exit_positions and len(exit_positions) > 0:
            return await self._execute_exits(state, exit_positions)
        
        # Otherwise execute the main decision
        # Validate required fields
        validation_error = self.validate_required_fields(
            state,
            ['strategy_id', 'decision', 'market_data', 'risk_approved']
        )
        if validation_error:
            self.log_error(state, validation_error)
            return self.add_error(state, validation_error)
        
        # Check if risk approved
        if not state.get('risk_approved', False):
            self.log_warning(state, "Trade blocked by risk agent")
            return {
                'trade_result': None,
                'should_execute_trade': False
            }
        
        strategy_id = state['strategy_id']
        decision = state['decision']
        market_data = state['market_data']
        execution_mode = state.get('execution_mode', 'analysis')
        
        action = decision.get('action')
        
        # Only execute if action is BUY or SELL and confidence is high enough
        if action not in ['BUY', 'SELL', 'CLOSE_POSITION']:
            self.log_info(state, f"No trade to execute (action: {action})")
            return {
                'trade_result': None,
                'should_execute_trade': False
            }
        
        confidence = decision.get('confidence', 0.0)
        if confidence < 0.70:
            self.log_info(state, f"Confidence {confidence:.2f} below minimum 0.70, skipping trade")
            return {
                'trade_result': None,
                'should_execute_trade': False
            }
        
        # Execute the trade
        try:
            self.log_info(state, f"Executing {action} trade (confidence: {confidence:.2f})...")
            
            trade_result = await self._execute_trade(
                strategy_id,
                decision,
                market_data,
                execution_mode
            )
            
            if trade_result:
                self.log_info(state, f"✓ Trade executed: {trade_result.get('side')} "
                                    f"{trade_result.get('symbol')} "
                                    f"(${trade_result.get('amount_in'):.2f} → "
                                    f"${trade_result.get('amount_out'):.2f})")
            else:
                self.log_warning(state, "Trade execution returned None")
            
            return {
                'trade_result': trade_result,
                'should_execute_trade': trade_result is not None
            }
            
        except Exception as e:
            self.log_error(state, f"Error executing trade: {e}")
            import traceback
            traceback.print_exc()
            return self.add_error(state, f"Execution error: {str(e)}")
    
    async def _execute_exits(
        self,
        state: TradingState,
        exit_positions: list
    ) -> Dict[str, Any]:
        """Execute exit orders for positions that hit stop-loss/take-profit."""
        self.log_info(state, f"Executing {len(exit_positions)} exit orders...")
        
        strategy_id = state['strategy_id']
        execution_mode = state.get('execution_mode', 'analysis')
        
        executed_exits = []
        
        for exit_pos in exit_positions:
            try:
                self.log_info(state, f"Exiting {exit_pos['token_symbol']}: {exit_pos['exit_reason']}")
                
                # Create exit decision
                decision = {
                    "action": "CLOSE_POSITION",
                    "token": exit_pos['token_symbol'],
                    "confidence": 1.0,
                    "reasoning": f"Auto-exit: {exit_pos['exit_reason']}"
                }
                
                # Create market data context
                market_data = {
                    "current_price": float(exit_pos['current_price']),
                    "token_symbol": exit_pos['token_symbol']
                }
                
                # Execute the exit
                trade_result = await self._execute_trade(
                    strategy_id,
                    decision,
                    market_data,
                    execution_mode
                )
                
                if trade_result:
                    executed_exits.append(trade_result)
                    self.log_info(state, f"✓ Exit executed for {exit_pos['token_symbol']}")
                
            except Exception as e:
                self.log_error(state, f"Error executing exit for {exit_pos['token_symbol']}: {e}")
        
        return {
            'trade_result': executed_exits[0] if len(executed_exits) > 0 else None,
            'exit_positions': [],  # Clear exit positions after execution
            'should_exit_positions': False
        }
    
    async def _execute_trade(
        self,
        strategy_id: str,
        decision: Dict[str, Any],
        market_data: Dict[str, Any],
        execution_mode: str
    ) -> Dict[str, Any]:
        """Execute a single trade (BUY or SELL)."""
        action = decision.get('action')
        token = decision.get('token', 'MOVE')
        amount_usdc = decision.get('amount_usdc', 100)
        
        # Safety: Prevent swapping stablecoins
        stablecoins = {'USDC', 'USDC.e', 'USDT', 'DAI'}
        if token.upper() in stablecoins:
            self.log_error(None, f"Cannot trade stablecoin {token}")
            return None
        
        if action == 'BUY':
            return await self._execute_buy(strategy_id, token, amount_usdc)
            
        elif action in ['SELL', 'CLOSE_POSITION']:
            return await self._execute_sell(strategy_id, token, market_data)
        
        return None
    
    async def _execute_buy(
        self,
        strategy_id: str,
        token: str,
        amount_usdc: float
    ) -> Dict[str, Any]:
        """Execute BUY order."""
        # Get token address
        dst_token_address = paper_trading_dex.get_token_address(token)
        
        # Get quote from Mosaic
        quote = await mosaic.get_swap_quote_for_strategy(
            src_token_symbol='USDC',
            dst_token_symbol=token,
            amount_usdc=amount_usdc,
            sender="0x0000000000000000000000000000000000000000000000000000000000000000"
        )
        
        if not quote:
            self.log_error(None, "Failed to get swap quote")
            return None
        
        # Extract amounts
        src_amount_units = int(quote.get('srcAmount', 0))
        dst_amount_units = int(quote.get('dstAmount', 0))
        
        src_amount = Decimal(str(src_amount_units)) / Decimal('1000000')
        dst_amount = Decimal(str(dst_amount_units)) / Decimal('100000000')
        
        price = src_amount / dst_amount if dst_amount > 0 else Decimal('0')
        
        if price <= 0:
            self.log_error(None, f"Invalid price: {price}")
            return None
        
        # Calculate slippage
        expected_output = quote.get('expectedOutput')
        slippage_pct = None
        if expected_output:
            expected_amount = Decimal(str(expected_output)) / Decimal('100000000')
            if expected_amount > 0:
                slippage_pct = float((expected_amount - dst_amount) / expected_amount * 100)
        
        gas_fee_usd = 0.002
        
        # Execute paper swap
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
        
        return None
    
    async def _execute_sell(
        self,
        strategy_id: str,
        token: str,
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute SELL order."""
        src_token_address = paper_trading_dex.get_token_address(token)
        
        # Get current token balance
        token_balance = await paper_trading_dex.get_balance(
            strategy_id,
            src_token_address,
            token
        )
        
        if token_balance <= 0:
            self.log_warning(None, f"No {token} balance to sell")
            return None
        
        # Get quote
        amount_in_units = int(token_balance * Decimal('100000000'))
        
        quote = await mosaic.get_quote(
            src_asset=src_token_address,
            dst_asset=paper_trading_dex.USDC_ADDRESS,
            amount=str(amount_in_units),
            sender="0x0000000000000000000000000000000000000000000000000000000000000000"
        )
        
        # Fallback to current price if quote fails
        if not quote:
            current_price = market_data.get('current_price', 0)
            if current_price > 0:
                src_amount = token_balance
                dst_amount = src_amount * Decimal(str(current_price))
                price = Decimal(str(current_price))
                
                success = await paper_trading_dex.execute_swap(
                    strategy_id=strategy_id,
                    src_token_address=src_token_address,
                    src_token_symbol=token,
                    dst_token_address=paper_trading_dex.USDC_ADDRESS,
                    dst_token_symbol='USDC',
                    amount_in=src_amount,
                    amount_out=dst_amount,
                    price=price,
                    slippage_pct=0.0,
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
            return None
        
        # Extract amounts from quote
        src_amount = token_balance
        dst_amount_units = int(quote.get('dstAmount', 0))
        dst_amount = Decimal(str(dst_amount_units)) / Decimal('1000000')
        
        price = dst_amount / src_amount if src_amount > 0 else Decimal('0')
        
        # Calculate slippage
        expected_output = quote.get('expectedOutput')
        slippage_pct = None
        if expected_output:
            expected_amount = Decimal(str(expected_output)) / Decimal('1000000')
            if expected_amount > 0:
                slippage_pct = float((expected_amount - dst_amount) / expected_amount * 100)
        
        gas_fee_usd = 0.002
        
        # Execute paper swap
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


# Singleton instance
execution_agent = ExecutionAgent()

