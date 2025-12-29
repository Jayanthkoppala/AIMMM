"""
DEX Spot Paper Trading Engine
Manages token balances, P&L tracking, and position management for paper trading

In paper trading mode:
- Trades are simulated (database updates only, no on-chain transactions)
- Slippage and gas fees are calculated from Mosaic quotes
- Portfolio value is tracked and updated in real-time
"""
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime, timezone
from app.utils.database import db_connection
from app.utils.logger import logger
from app.services import oracle


class PaperTradingDEX:
    """Paper trading engine for DEX spot trading"""
    
    # Standard token addresses (Movement testnet)
    # IMPORTANT: These are Mosaic token IDs, NOT module paths!
    # For Mosaic API, use the token ID directly (e.g., "0xa" for MOVE, not "0x1::aptos_coin::AptosCoin")
    USDC_ADDRESS = "0x83121c9f9b0527d1f056e21a950d6bf3b9e9e2e8353d0e95ccea726713cbea39"  # USDC.e token ID
    MOVE_ADDRESS = "0x000000000000000000000000000000000000000a"  # MOVE coin ID (full format for consistency)
    WETH_ADDRESS = "0x908828f4fb0213d4034c3ded1630bbd904e8a3a6bf3c63270887f0b06653a376"  # WETH.e token ID
    
    # Token address mapping for dynamic lookup
    TOKEN_ADDRESSES = {
        "USDC": "0x83121c9f9b0527d1f056e21a950d6bf3b9e9e2e8353d0e95ccea726713cbea39",
        "USDC.e": "0x83121c9f9b0527d1f056e21a950d6bf3b9e9e2e8353d0e95ccea726713cbea39",
        "MOVE": "0x000000000000000000000000000000000000000a",
        "WETH": "0x908828f4fb0213d4034c3ded1630bbd904e8a3a6bf3c63270887f0b06653a376",
        "WETH.e": "0x908828f4fb0213d4034c3ded1630bbd904e8a3a6bf3c63270887f0b06653a376",
    }
    
    # ==================== STRATEGY VALIDATION HELPERS ====================
    
    def validate_trade_against_rules(
        self,
        action: str,
        strategy_config: Dict[str, Any],
        current_positions: int,
        usdc_balance: Decimal,
        requested_amount: float
    ) -> tuple[bool, str]:
        """
        Validate a trade against user-defined strategy rules.
        
        Returns:
            (is_valid, reason) - If not valid, reason explains why
        """
        paper_config = strategy_config.get('paper_trading_config', {})
        
        # Rule 1: Check max concurrent positions
        max_positions = paper_config.get('max_concurrent_positions', 5)
        if action == 'BUY' and current_positions >= max_positions:
            return False, f"Max positions ({max_positions}) reached"
        
        # Rule 2: Check per-trade amount is within configured range
        per_trade_range = paper_config.get('per_trade_range', {})
        min_trade = per_trade_range.get('min', paper_config.get('capital_per_trade', 50))
        max_trade = per_trade_range.get('max', paper_config.get('capital_per_trade', 200))
        
        if action == 'BUY':
            if requested_amount < min_trade:
                return False, f"Trade amount ${requested_amount} below minimum ${min_trade}"
            if requested_amount > max_trade:
                return False, f"Trade amount ${requested_amount} exceeds maximum ${max_trade}"
        
        # Rule 3: Check sufficient balance
        if action == 'BUY' and usdc_balance < Decimal(str(requested_amount)):
            return False, f"Insufficient USDC: need ${requested_amount}, have ${float(usdc_balance):.2f}"
        
        return True, "Trade validated"
    
    def calculate_dynamic_trade_amount(
        self,
        strategy_config: Dict[str, Any],
        confidence: float,
        current_positions: int
    ) -> float:
        """
        Calculate trade amount dynamically based on confidence and strategy config.
        Higher confidence = larger trade within the configured range.
        
        Args:
            strategy_config: User's strategy configuration
            confidence: LLM confidence score (0.0 - 1.0)
            current_positions: Number of current open positions
        
        Returns:
            Calculated trade amount in USD
        """
        paper_config = strategy_config.get('paper_trading_config', {})
        per_trade_range = paper_config.get('per_trade_range', {})
        
        min_trade = per_trade_range.get('min', paper_config.get('capital_per_trade', 50))
        max_trade = per_trade_range.get('max', paper_config.get('capital_per_trade', 200))
        
        # Scale trade amount based on confidence
        # confidence 0.7 (minimum) = min_trade
        # confidence 1.0 = max_trade
        # Linear interpolation between min and max
        normalized_confidence = max(0.0, min(1.0, (confidence - 0.7) / 0.3))  # 0.7-1.0 -> 0-1
        
        trade_amount = min_trade + (max_trade - min_trade) * normalized_confidence
        
        # Reduce position size if many positions already open (risk management)
        max_positions = paper_config.get('max_concurrent_positions', 5)
        if current_positions > 0 and max_positions > 1:
            position_factor = 1 - (current_positions / max_positions) * 0.3  # Reduce by up to 30%
            trade_amount *= position_factor
        
        return round(trade_amount, 2)
    
    def calculate_dynamic_stop_loss(
        self,
        strategy_config: Dict[str, Any],
        confidence: float,
        volatility: Optional[float] = None
    ) -> float:
        """
        Calculate stop-loss percentage dynamically based on confidence.
        Higher confidence = tighter stop-loss (more aggressive)
        Lower confidence = wider stop-loss (more conservative)
        
        Returns:
            Stop-loss percentage (e.g., 0.05 for 5%)
        """
        paper_config = strategy_config.get('paper_trading_config', {})
        stop_loss_range = paper_config.get('stop_loss_range', {})
        
        min_sl = stop_loss_range.get('min', paper_config.get('stop_loss_pct', 0.05))
        max_sl = stop_loss_range.get('max', 0.15)
        
        # Higher confidence = tighter stop (closer to min)
        # Lower confidence = wider stop (closer to max)
        normalized_confidence = max(0.0, min(1.0, (confidence - 0.7) / 0.3))
        
        # Inverse relationship: high confidence = tight stop
        stop_loss = max_sl - (max_sl - min_sl) * normalized_confidence
        
        # Adjust for volatility if provided (higher volatility = wider stop)
        if volatility and volatility > 0:
            volatility_factor = min(1.5, 1 + volatility)  # Up to 50% wider
            stop_loss *= volatility_factor
        
        return min(max_sl, max(min_sl, stop_loss))
    
    def calculate_dynamic_take_profit(
        self,
        strategy_config: Dict[str, Any],
        confidence: float,
        volatility: Optional[float] = None
    ) -> float:
        """
        Calculate take-profit percentage dynamically based on confidence.
        Higher confidence = higher take-profit target
        Lower confidence = lower take-profit target (take profits earlier)
        
        Returns:
            Take-profit percentage (e.g., 0.10 for 10%)
        """
        paper_config = strategy_config.get('paper_trading_config', {})
        take_profit_range = paper_config.get('take_profit_range', {})
        
        min_tp = take_profit_range.get('min', paper_config.get('take_profit_pct', 0.10))
        max_tp = take_profit_range.get('max', 0.30)
        
        # Higher confidence = higher target (closer to max)
        normalized_confidence = max(0.0, min(1.0, (confidence - 0.7) / 0.3))
        
        take_profit = min_tp + (max_tp - min_tp) * normalized_confidence
        
        return min(max_tp, max(min_tp, take_profit))
    
    def get_token_address(self, symbol: str) -> str:
        """Get token address by symbol, with fallback to database lookup"""
        # Check static mapping first
        symbol_upper = symbol.upper().replace(".E", ".e")  # Normalize
        if symbol_upper in self.TOKEN_ADDRESSES:
            return self.TOKEN_ADDRESSES[symbol_upper]
        if symbol in self.TOKEN_ADDRESSES:
            return self.TOKEN_ADDRESSES[symbol]
        
        # Try database lookup
        try:
            query = """
                SELECT token_a_address, token_b_address, token_a_symbol, token_b_symbol
                FROM pools
                WHERE token_a_symbol = %s OR token_b_symbol = %s
                LIMIT 1
            """
            result = db_connection.execute_query(query, (symbol, symbol), fetch_one=True)
            if result:
                if result.get('token_a_symbol') == symbol:
                    return result.get('token_a_address')
                elif result.get('token_b_symbol') == symbol:
                    return result.get('token_b_address')
        except Exception as e:
            logger.warning(f"Could not lookup token address for {symbol}: {e}")
        
        # Fallback to MOVE address
        logger.warning(f"Unknown token symbol {symbol}, defaulting to MOVE address")
        return self.MOVE_ADDRESS
    
    async def initialize_strategy_balances(
        self,
        strategy_id: str,
        initial_capital_usdc: float = 1000.0
    ) -> bool:
        """
        Initialize paper trading balances for a new strategy.
        Starts with USDC as the base currency.
        """
        try:
            # Check if balances already exist
            check_query = """
                SELECT COUNT(*) as count 
                FROM paper_trading_balances 
                WHERE strategy_id = %s
            """
            result = db_connection.execute_query(
                check_query,
                (strategy_id,),
                fetch_one=True
            )
            
            if result and result.get('count', 0) > 0:
                logger.info(f"Balances already initialized for strategy {strategy_id}")
                return True
            
            # Initialize with USDC balance
            insert_query = """
                INSERT INTO paper_trading_balances 
                (strategy_id, token_address, token_symbol, balance, usd_value, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """
            
            db_connection.execute_query(
                insert_query,
                (strategy_id, self.USDC_ADDRESS, "USDC", Decimal(str(initial_capital_usdc)), Decimal(str(initial_capital_usdc)))
            )
            
            logger.info(f"Initialized paper trading balances for strategy {strategy_id} with ${initial_capital_usdc} USDC")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing strategy balances: {e}", exc_info=True)
            return False
    
    async def get_balances(self, strategy_id: str) -> List[Dict[str, Any]]:
        """Get all token balances for a strategy"""
        try:
            query = """
                SELECT token_address, token_symbol, balance, usd_value, updated_at
                FROM paper_trading_balances
                WHERE strategy_id = %s
                ORDER BY token_symbol
            """
            
            results = db_connection.execute_query(
                query,
                (strategy_id,),
                fetch_all=True
            )
            
            return results or []
            
        except Exception as e:
            logger.error(f"Error fetching balances: {e}", exc_info=True)
            return []
    
    async def get_balance(
        self,
        strategy_id: str,
        token_address: str,
        token_symbol: Optional[str] = None
    ) -> Decimal:
        """
        Get balance for a specific token.
        Handles migration from old address formats to new Mosaic token ID format.
        
        Args:
            strategy_id: Strategy UUID
            token_address: Token address (Mosaic token ID format)
            token_symbol: Optional token symbol for migration lookup
        """
        try:
            # Try exact match first (Mosaic token ID format)
            query = """
                SELECT balance, token_symbol, usd_value
                FROM paper_trading_balances
                WHERE strategy_id = %s AND token_address = %s
            """
            
            result = db_connection.execute_query(
                query,
                (strategy_id, token_address),
                fetch_one=True
            )
            
            if result:
                return Decimal(str(result.get('balance', 0)))
            
            # If not found and we have a token symbol, search by symbol to find old format balances
            if token_symbol:
                migration_query = """
                    SELECT balance, token_symbol, usd_value, token_address as old_address
                    FROM paper_trading_balances
                    WHERE strategy_id = %s AND token_symbol = %s
                    LIMIT 1
                """
                
                old_balance = db_connection.execute_query(
                    migration_query,
                    (strategy_id, token_symbol),
                    fetch_one=True
                )
                
                if old_balance:
                    balance = Decimal(str(old_balance.get('balance', 0)))
                    old_address = old_balance.get('old_address')
                    old_usd_value = old_balance.get('usd_value')
                    
                    # Only migrate if the old address is different from the new one
                    if old_address != token_address:
                        logger.info(
                            f"[Paper Trading] Found {token_symbol} balance with old address format "
                            f"({old_address}), migrating to new format ({token_address})"
                        )
                        
                        # Migrate: create new entry with new address format
                        usd_value = old_usd_value if old_usd_value else balance
                        await self.update_balance(
                            strategy_id,
                            token_address,
                            token_symbol,
                            balance,
                            usd_value
                        )
                        
                        # Delete old address entry (only if addresses are different)
                        delete_query = """
                            DELETE FROM paper_trading_balances
                            WHERE strategy_id = %s AND token_address = %s
                        """
                        db_connection.execute_query(
                            delete_query,
                            (strategy_id, old_address)
                        )
                        
                        logger.info(f"[Paper Trading] Migration complete: {balance} {token_symbol} from {old_address} to {token_address}")
                    
                    return balance
            
            return Decimal('0')
            
        except Exception as e:
            logger.error(f"Error fetching balance: {e}", exc_info=True)
            return Decimal('0')
    
    async def update_balance(
        self,
        strategy_id: str,
        token_address: str,
        token_symbol: str,
        new_balance: Decimal,
        usd_value: Optional[Decimal] = None
    ) -> bool:
        """Update token balance (upsert)"""
        try:
            query = """
                INSERT INTO paper_trading_balances 
                (strategy_id, token_address, token_symbol, balance, usd_value, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT (strategy_id, token_address) 
                DO UPDATE SET 
                    balance = EXCLUDED.balance,
                    usd_value = EXCLUDED.usd_value,
                    updated_at = NOW()
            """
            
            db_connection.execute_query(
                query,
                (strategy_id, token_address, token_symbol, new_balance, usd_value)
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating balance: {e}", exc_info=True)
            return False
    
    async def execute_swap(
        self,
        strategy_id: str,
        src_token_address: str,
        src_token_symbol: str,
        dst_token_address: str,
        dst_token_symbol: str,
        amount_in: Decimal,
        amount_out: Decimal,
        price: Decimal,
        slippage_pct: Optional[float] = None,
        gas_fee_usd: Optional[float] = None,
        quote_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Execute a paper trading swap (simulated - updates database only).
        Calculates slippage and fees, then updates balances in database.
        
        Args:
            strategy_id: Strategy UUID
            src_token_address: Source token address (Mosaic token ID)
            src_token_symbol: Source token symbol
            dst_token_address: Destination token address (Mosaic token ID)
            dst_token_symbol: Destination token symbol
            amount_in: Input amount (in source token units)
            amount_out: Output amount (in destination token units, after slippage/fees)
            price: Effective price (amount_in / amount_out)
            slippage_pct: Slippage percentage (optional, will calculate if not provided)
            gas_fee_usd: Gas fee in USD (optional, will estimate if not provided)
            quote_data: Full quote data from Mosaic (optional, for detailed fee calculation)
        """
        try:
            # Get current balance (will auto-migrate from old format if needed)
            src_balance = await self.get_balance(strategy_id, src_token_address, src_token_symbol)
            
            logger.debug(
                f"[Paper Trading] Balance check: strategy={strategy_id}, "
                f"token={src_token_symbol}, address={src_token_address}, balance={src_balance}"
            )
            
            if src_balance < amount_in:
                logger.error(
                    f"[Paper Trading] Insufficient balance for swap: need {amount_in} {src_token_symbol}, "
                    f"have {src_balance}. Strategy portfolio may need re-initialization."
                )
                return False
            
            dst_balance = await self.get_balance(strategy_id, dst_token_address, dst_token_symbol)
            
            # Calculate slippage if not provided
            if slippage_pct is None and quote_data:
                # Calculate slippage from quote
                expected_output = Decimal(str(quote_data.get('expectedOutput', amount_out)))
                if expected_output > 0:
                    slippage_pct = float((expected_output - amount_out) / expected_output * 100)
                else:
                    slippage_pct = 0.0
            
            # Estimate gas fee if not provided (typical Movement network gas: ~0.001-0.01 USD)
            if gas_fee_usd is None:
                # Estimate based on transaction complexity
                # Simple swap: ~0.001 USD, complex routing: ~0.005 USD
                gas_fee_usd = 0.002  # Default estimate for DEX swap
            
            # Calculate total cost (amount_in + gas fee)
            total_cost_usd = float(amount_in) + gas_fee_usd if src_token_symbol == "USDC" else float(amount_in * price) + gas_fee_usd
            
            # Deduct gas fee from USDC balance
            if gas_fee_usd and gas_fee_usd > 0:
                usdc_balance = await self.get_balance(strategy_id, self.USDC_ADDRESS, "USDC")
                if usdc_balance >= Decimal(str(gas_fee_usd)):
                    new_usdc_for_gas = usdc_balance - Decimal(str(gas_fee_usd))
                    # Only update if this isn't already a USDC source transaction
                    if src_token_symbol != "USDC":
                        await self.update_balance(
                            strategy_id,
                            self.USDC_ADDRESS,
                            "USDC",
                            new_usdc_for_gas,
                            new_usdc_for_gas
                        )
                        logger.debug(f"[Paper Trading] Deducted gas fee ${gas_fee_usd:.4f} from USDC balance")
            
            # Update source token (decrease)
            new_src_balance = src_balance - amount_in
            src_usd_value = None
            if src_token_symbol == "USDC":
                src_usd_value = new_src_balance
            else:
                # Calculate USD value using current price
                src_usd_value = new_src_balance * price
            
            await self.update_balance(
                strategy_id,
                src_token_address,
                src_token_symbol,
                new_src_balance,
                src_usd_value
            )
            
            # Update destination token (increase)
            new_dst_balance = dst_balance + amount_out
            dst_usd_value = None
            if dst_token_symbol == "USDC":
                dst_usd_value = new_dst_balance
            else:
                # Use the effective price from the swap
                dst_usd_value = new_dst_balance * price
            
            await self.update_balance(
                strategy_id,
                dst_token_address,
                dst_token_symbol,
                new_dst_balance,
                dst_usd_value
            )
            
            # Log swap execution with slippage and fees
            logger.info(
                f"[Paper Trading] Executed simulated swap for strategy {strategy_id}: "
                f"{amount_in} {src_token_symbol} → {amount_out} {dst_token_symbol} "
                f"(price: ${price:.6f}, slippage: {slippage_pct or 0:.2f}%, gas: ${gas_fee_usd:.4f})"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"[Paper Trading] Error executing paper swap: {e}", exc_info=True)
            return False
    
    async def calculate_portfolio_value(
        self,
        strategy_id: str,
        pool_address: Optional[str] = None,
        current_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculate total portfolio value and P&L using current market prices.
        Tracks both realized P&L (from closed positions) and unrealized P&L (from open positions).
        
        Args:
            strategy_id: Strategy UUID
            pool_address: Optional pool address for price lookup
            current_price: Optional current market price (if already fetched)
        
        Returns:
            {
                "total_value": Decimal,
                "initial_capital": Decimal,
                "unrealized_pnl": Decimal,
                "realized_pnl": Decimal,
                "total_pnl": Decimal,
                "unrealized_pnl_pct": float,
                "total_pnl_pct": float,
                "balances": List[Dict]
            }
        """
        try:
            balances = await self.get_balances(strategy_id)
            
            if not balances:
                return {
                    "total_value": Decimal('0'),
                    "initial_capital": Decimal('1000'),
                    "unrealized_pnl": Decimal('0'),
                    "realized_pnl": Decimal('0'),
                    "total_pnl": Decimal('0'),
                    "unrealized_pnl_pct": 0.0,
                    "total_pnl_pct": 0.0,
                    "balances": []
                }
            
            # Get initial capital from strategy config
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
            
            initial_capital = Decimal('1000')
            if strategy_result and strategy_result.get('strategy_config'):
                config = strategy_result.get('strategy_config')
                paper_config = config.get('paper_trading_config', {})
                initial_capital = Decimal(str(paper_config.get('initial_capital_usdc', 1000)))
            
            # Calculate REALIZED P&L from completed SELL trades
            # Realized P&L = (Sell Amount Received) - (Cost Basis of Sold Tokens)
            realized_pnl = await self._calculate_realized_pnl(strategy_id)
            
            # Calculate total portfolio value using CURRENT market prices
            total_value = Decimal('0')
            total_unrealized_pnl = Decimal('0')
            updated_balances = []
            
            for balance in balances:
                token_symbol = balance.get('token_symbol')
                token_balance = Decimal(str(balance.get('balance', 0)))
                entry_price = None
                unrealized_pnl = Decimal('0')
                
                if token_symbol == "USDC":
                    # USDC is 1:1 with USD
                    usd_value = token_balance
                    token_price = Decimal('1.0')  # USDC price is always 1
                else:
                    # For non-USDC tokens, always get current market price
                    token_price = None
                    
                    # Use provided current_price if available
                    if current_price and current_price > 0:
                        token_price = Decimal(str(current_price))
                    else:
                        # Try to get current price from oracle
                        try:
                            token_address = balance.get('token_address')
                            prices = await oracle.get_token_prices(
                                token_address,
                                self.USDC_ADDRESS,
                                pool_address=pool_address
                            )
                            if prices:
                                token_price = Decimal(str(prices.get('token_a_price', 0)))
                        except Exception as e:
                            logger.warning(f"Could not get current price for {token_symbol}: {e}")
                            # Fallback to stored price if available
                            stored_usd_value = Decimal(str(balance.get('usd_value', 0)))
                            if stored_usd_value > 0 and token_balance > 0:
                                token_price = stored_usd_value / token_balance
                            else:
                                token_price = Decimal('0')
                    
                    # Calculate current USD value
                    if token_price and token_price > 0:
                        usd_value = token_balance * token_price
                    else:
                        # If we can't get price, use stored value as fallback
                        usd_value = Decimal(str(balance.get('usd_value', 0)))
                        token_price = usd_value / token_balance if token_balance > 0 else Decimal('0')
                    
                    # Calculate DCA (Dollar-Cost Averaging) entry price from ALL BUY executions
                    # DCA Formula: Average Entry Price = Total USD Spent on Buys / Total Tokens Bought
                    # Note: SELLs reduce position size but don't change the cost basis of remaining tokens
                    dca_query = """
                        SELECT 
                            COALESCE(SUM(amount_in), 0) as total_usd_spent,
                            COALESCE(SUM(amount_out), 0) as total_tokens_bought,
                            COUNT(*) as buy_count
                        FROM strategy_executions
                        WHERE strategy_id = %s 
                            AND symbol LIKE %s
                            AND decision = 'BUY'
                            AND trade_executed = TRUE
                            AND amount_in IS NOT NULL
                            AND amount_out IS NOT NULL
                    """
                    dca_result = db_connection.execute_query(
                        dca_query,
                        (strategy_id, f"%{token_symbol}%"),
                        fetch_one=True
                    )
                    
                    # Calculate average entry price using DCA formula
                    if dca_result and dca_result.get('total_usd_spent') and dca_result.get('total_tokens_bought'):
                        total_usd_spent = Decimal(str(dca_result.get('total_usd_spent', 0)))
                        total_tokens_bought = Decimal(str(dca_result.get('total_tokens_bought', 0)))
                        buy_count = dca_result.get('buy_count', 0)
                        
                        if total_tokens_bought > 0 and buy_count > 0:
                            # Calculate weighted average entry price (DCA)
                            # This is the average cost per token across all BUY executions
                            avg_entry_price = total_usd_spent / total_tokens_bought
                            
                            # Calculate cost basis for current position
                            # The cost basis is proportional to remaining tokens
                            # If we bought 1000 tokens for $1000 (avg $1/token) and sold 200,
                            # remaining 800 tokens still have $1/token cost basis
                            # Cost basis = (current_balance / total_bought) * total_spent
                            # OR simpler: current_balance * avg_entry_price
                            total_cost_basis = token_balance * avg_entry_price
                            
                            # Calculate unrealized P&L: Current Market Value - Cost Basis
                            unrealized_pnl = usd_value - total_cost_basis
                            
                            entry_price = avg_entry_price
                            
                            logger.debug(
                                f"[DCA] {token_symbol}: Avg Entry=${avg_entry_price:.6f}, "
                                f"Balance={token_balance:.6f}, Cost Basis=${total_cost_basis:.2f}, "
                                f"Current Value=${usd_value:.2f}, P&L=${unrealized_pnl:.2f} "
                                f"({buy_count} buys, ${total_usd_spent:.2f} spent on {total_tokens_bought:.6f} tokens)"
                            )
                        else:
                            entry_price = None
                            unrealized_pnl = Decimal('0')
                    else:
                        # No BUY executions found, assume break-even
                        entry_price = None
                        unrealized_pnl = Decimal('0')
                    
                    # Update stored USD value in database with current market value
                    if token_price > 0:
                        await self.update_balance(
                            strategy_id,
                            balance.get('token_address'),
                            token_symbol,
                            token_balance,
                            usd_value
                        )
                
                total_value += usd_value
                total_unrealized_pnl += unrealized_pnl
                
                updated_balances.append({
                    "token_address": balance.get('token_address'),
                    "token_symbol": token_symbol,
                    "balance": float(token_balance),
                    "usd_value": float(usd_value),
                    "current_price": float(token_price) if token_price else (1.0 if token_symbol == "USDC" else 0.0),
                    "entry_price": float(entry_price) if entry_price else None,
                    "unrealized_pnl": float(unrealized_pnl)
                })
            
            # Calculate total P&L = Realized + Unrealized
            # Total P&L can also be verified as: current portfolio value - initial capital
            total_pnl = realized_pnl + total_unrealized_pnl
            total_pnl_from_value = total_value - initial_capital
            
            # Use the value-based calculation for consistency (it's more accurate)
            # The sum of realized + unrealized should equal this, but may have small rounding differences
            unrealized_pnl_pct = float(total_unrealized_pnl / initial_capital * 100) if initial_capital > 0 else 0.0
            total_pnl_pct = float(total_pnl_from_value / initial_capital * 100) if initial_capital > 0 else 0.0
            
            logger.info(
                f"[Paper Trading] Portfolio value calculated: ${total_value:.2f} "
                f"(Initial: ${initial_capital:.2f}, Realized P&L: ${realized_pnl:.2f}, "
                f"Unrealized P&L: ${total_unrealized_pnl:.2f}, Total P&L: ${total_pnl_from_value:.2f} ({total_pnl_pct:+.2f}%))"
            )
            
            return {
                "total_value": total_value,
                "initial_capital": initial_capital,
                "unrealized_pnl": total_pnl_from_value,  # For backward compatibility, use total P&L here
                "realized_pnl": realized_pnl,
                "position_unrealized_pnl": total_unrealized_pnl,  # Per-position unrealized
                "total_pnl": total_pnl_from_value,
                "unrealized_pnl_pct": total_pnl_pct,  # For backward compatibility, use total P&L %
                "total_pnl_pct": total_pnl_pct,
                "balances": updated_balances
            }
            
        except Exception as e:
            logger.error(f"Error calculating portfolio value: {e}", exc_info=True)
            return {
                "total_value": Decimal('0'),
                "initial_capital": Decimal('1000'),
                "unrealized_pnl": Decimal('0'),
                "realized_pnl": Decimal('0'),
                "total_pnl": Decimal('0'),
                "unrealized_pnl_pct": 0.0,
                "total_pnl_pct": 0.0,
                "balances": []
            }
    
    async def _calculate_realized_pnl(self, strategy_id: str) -> Decimal:
        """
        Calculate realized P&L from all completed SELL trades.
        
        Realized P&L = Sum of (Sell Proceeds - Cost Basis for Sold Tokens)
        
        For each SELL:
        - Sell Proceeds = amount_out (USDC received)
        - Cost Basis = amount_in (tokens sold) * avg_entry_price_at_time_of_sell
        
        Since we use DCA entry price, we calculate:
        - Total tokens bought and total USD spent on buys
        - Average entry price = total USD spent / total tokens bought
        - For each sell: realized P&L = sell_proceeds - (tokens_sold * avg_entry_price)
        """
        try:
            # Get all SELL executions
            sell_query = """
                SELECT 
                    symbol,
                    amount_in as tokens_sold,
                    amount_out as usdc_received,
                    price,
                    execution_timestamp
                FROM strategy_executions
                WHERE strategy_id = %s 
                    AND (decision = 'SELL' OR decision = 'CLOSE_POSITION')
                    AND trade_executed = TRUE
                    AND amount_in IS NOT NULL
                    AND amount_out IS NOT NULL
                ORDER BY execution_timestamp ASC
            """
            sell_results = db_connection.execute_query(
                sell_query,
                (strategy_id,),
                fetch_all=True
            )
            
            if not sell_results:
                return Decimal('0')
            
            total_realized_pnl = Decimal('0')
            
            for sell in sell_results:
                tokens_sold = Decimal(str(sell.get('tokens_sold', 0)))
                usdc_received = Decimal(str(sell.get('usdc_received', 0)))
                symbol = sell.get('symbol', '')
                
                # Extract token symbol from "TOKEN-USDC" format
                token_symbol = symbol.split('-')[0] if '-' in symbol else symbol
                
                # Get DCA entry price for this token at the time of sale
                # (sum of all buys before this sell)
                sell_timestamp = sell.get('execution_timestamp')
                
                dca_query = """
                    SELECT 
                        COALESCE(SUM(amount_in), 0) as total_usd_spent,
                        COALESCE(SUM(amount_out), 0) as total_tokens_bought
                    FROM strategy_executions
                    WHERE strategy_id = %s 
                        AND symbol LIKE %s
                        AND decision = 'BUY'
                        AND trade_executed = TRUE
                        AND amount_in IS NOT NULL
                        AND amount_out IS NOT NULL
                        AND execution_timestamp <= %s
                """
                dca_result = db_connection.execute_query(
                    dca_query,
                    (strategy_id, f"%{token_symbol}%", sell_timestamp),
                    fetch_one=True
                )
                
                if dca_result and dca_result.get('total_tokens_bought'):
                    total_usd_spent = Decimal(str(dca_result.get('total_usd_spent', 0)))
                    total_tokens_bought = Decimal(str(dca_result.get('total_tokens_bought', 0)))
                    
                    if total_tokens_bought > 0:
                        avg_entry_price = total_usd_spent / total_tokens_bought
                        cost_basis = tokens_sold * avg_entry_price
                        realized_pnl = usdc_received - cost_basis
                        total_realized_pnl += realized_pnl
                        
                        logger.debug(
                            f"[Realized P&L] SELL {tokens_sold:.6f} {token_symbol}: "
                            f"Received ${usdc_received:.2f}, Cost Basis ${cost_basis:.2f}, "
                            f"Realized P&L ${realized_pnl:.2f}"
                        )
            
            return total_realized_pnl
            
        except Exception as e:
            logger.error(f"Error calculating realized P&L: {e}", exc_info=True)
            return Decimal('0')
    
    async def check_exit_signals(
        self,
        strategy_id: str,
        strategy_config: Dict[str, Any],
        pool_address: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Check if any positions need to be closed due to stop-loss or take-profit.
        
        Returns list of positions needing exit:
        [
            {
                "token_address": str,
                "token_symbol": str,
                "balance": Decimal,
                "exit_reason": "STOP_LOSS_HIT" | "TAKE_PROFIT_HIT",
                "current_price": Decimal,
                "entry_price": Decimal
            }
        ]
        """
        try:
            positions_to_exit = []
            
            # Get paper trading config
            paper_config = strategy_config.get('paper_trading_config', {})
            stop_loss_pct = float(paper_config.get('stop_loss_pct', 0.05))
            take_profit_pct = float(paper_config.get('take_profit_pct', 0.10))
            
            # Get all non-USDC balances
            balances = await self.get_balances(strategy_id)
            
            for balance in balances:
                token_symbol = balance.get('token_symbol')
                if token_symbol == "USDC":
                    continue  # Skip USDC
                
                token_address = balance.get('token_address')
                token_balance = Decimal(str(balance.get('balance', 0)))
                
                if token_balance <= 0:
                    continue  # No position
                
                # Calculate DCA (Dollar-Cost Averaging) entry price from ALL BUY executions
                dca_query = """
                    SELECT 
                        COALESCE(SUM(amount_in), 0) as total_usd_spent,
                        COALESCE(SUM(amount_out), 0) as total_tokens_bought
                    FROM strategy_executions
                    WHERE strategy_id = %s 
                        AND symbol LIKE %s
                        AND decision = 'BUY'
                        AND trade_executed = TRUE
                        AND amount_in IS NOT NULL
                        AND amount_out IS NOT NULL
                """
                
                dca_result = db_connection.execute_query(
                    dca_query,
                    (strategy_id, f"%{token_symbol}%"),
                    fetch_one=True
                )
                
                if not dca_result or not dca_result.get('total_usd_spent') or not dca_result.get('total_tokens_bought'):
                    continue  # No entry price found
                
                total_usd_spent = Decimal(str(dca_result.get('total_usd_spent', 0)))
                total_tokens_bought = Decimal(str(dca_result.get('total_tokens_bought', 0)))
                
                if total_tokens_bought <= 0:
                    continue
                
                # Calculate weighted average entry price (DCA)
                # Average Entry Price = Total USD Spent / Total Tokens Bought
                entry_price = total_usd_spent / total_tokens_bought
                
                if entry_price <= 0:
                    continue
                
                # Get current price
                try:
                    prices = await oracle.get_token_prices(
                        token_address,
                        self.USDC_ADDRESS,
                        pool_address=pool_address
                    )
                    current_price = Decimal(str(prices.get('token_a_price', 0)))
                except Exception as e:
                    logger.warning(f"Could not get current price for {token_symbol}: {e}")
                    continue
                
                if current_price <= 0:
                    logger.warning(f"Invalid current price ({current_price}) for {token_symbol}, skipping exit check")
                    continue
                
                # CRITICAL: Validate price is reasonable compared to entry price
                # If price differs by more than 90% from entry, it's likely a data error
                price_ratio = float(current_price / entry_price)
                if price_ratio < 0.1 or price_ratio > 10:
                    logger.error(
                        f"Price validation failed for {token_symbol}: "
                        f"current=${current_price:.6f} vs entry=${entry_price:.6f} (ratio: {price_ratio:.4f}). "
                        f"Skipping exit check to prevent false trigger - likely data/oracle error."
                    )
                    continue
                
                # Calculate price change percentage based on DCA entry price
                price_change_pct = float((current_price - entry_price) / entry_price)
                
                # Check stop-loss
                if price_change_pct <= -stop_loss_pct:
                    positions_to_exit.append({
                        "token_address": token_address,
                        "token_symbol": token_symbol,
                        "balance": token_balance,
                        "exit_reason": "STOP_LOSS_HIT",
                        "current_price": current_price,
                        "entry_price": entry_price,
                        "price_change_pct": price_change_pct
                    })
                
                # Check take-profit
                elif price_change_pct >= take_profit_pct:
                    positions_to_exit.append({
                        "token_address": token_address,
                        "token_symbol": token_symbol,
                        "balance": token_balance,
                        "exit_reason": "TAKE_PROFIT_HIT",
                        "current_price": current_price,
                        "entry_price": entry_price,
                        "price_change_pct": price_change_pct
                    })
            
            return positions_to_exit
            
        except Exception as e:
            logger.error(f"Error checking exit signals: {e}", exc_info=True)
            return []
    
    async def get_active_positions_count(self, strategy_id: str) -> int:
        """Get count of active non-USDC positions"""
        try:
            query = """
                SELECT COUNT(*) as count
                FROM paper_trading_balances
                WHERE strategy_id = %s 
                    AND token_symbol != 'USDC'
                    AND balance > 0
            """
            
            result = db_connection.execute_query(
                query,
                (strategy_id,),
                fetch_one=True
            )
            
            return result.get('count', 0) if result else 0
            
        except Exception as e:
            logger.error(f"Error getting active positions count: {e}", exc_info=True)
            return 0
    
    # ==================== TRADE HISTORY & ANALYTICS ====================
    
    async def get_trade_statistics(self, strategy_id: str) -> Dict[str, Any]:
        """
        Get comprehensive trading performance statistics for a strategy.
        Includes standard metrics: Win Rate, Sharpe Ratio, Sortino Ratio, Max Drawdown, etc.
        """
        import math
        
        try:
            # Get all completed round-trips (buy then sell)
            query = """
                SELECT 
                    COUNT(*) FILTER (WHERE decision IN ('SELL', 'CLOSE_POSITION') AND trade_executed = TRUE) as total_sells,
                    COUNT(*) FILTER (WHERE decision = 'BUY' AND trade_executed = TRUE) as total_buys
                FROM strategy_executions
                WHERE strategy_id = %s
            """
            counts = db_connection.execute_query(query, (strategy_id,), fetch_one=True)
            total_sells = counts.get('total_sells', 0) if counts else 0
            total_buys = counts.get('total_buys', 0) if counts else 0
            
            # Get initial capital from paper trading state
            state_query = "SELECT initial_capital FROM paper_trading_states WHERE strategy_id = %s"
            state = db_connection.execute_query(state_query, (strategy_id,), fetch_one=True)
            initial_capital = float(state.get('initial_capital', 1000)) if state else 1000.0
            
            # Get detailed sell trades for win/loss analysis
            sell_query = """
                SELECT 
                    symbol,
                    amount_in as tokens_sold,
                    amount_out as usdc_received,
                    price,
                    execution_timestamp
                FROM strategy_executions
                WHERE strategy_id = %s 
                    AND decision IN ('SELL', 'CLOSE_POSITION')
                    AND trade_executed = TRUE
                ORDER BY execution_timestamp ASC
            """
            sells = db_connection.execute_query(sell_query, (strategy_id,), fetch_all=True) or []
            
            winning_trades = 0
            losing_trades = 0
            total_profit = Decimal('0')
            total_loss = Decimal('0')
            largest_win = Decimal('0')
            largest_loss = Decimal('0')
            
            # For advanced metrics
            trade_returns: List[float] = []  # Individual trade returns (percentage)
            trade_pnls: List[float] = []  # Individual trade P&L (absolute)
            trade_durations: List[float] = []  # Duration in minutes
            
            # Running equity for drawdown calculation
            running_equity = initial_capital
            peak_equity = initial_capital
            max_drawdown = 0.0
            max_drawdown_pct = 0.0
            
            for sell in sells:
                tokens_sold = Decimal(str(sell.get('tokens_sold', 0)))
                usdc_received = Decimal(str(sell.get('usdc_received', 0)))
                symbol = sell.get('symbol', '')
                token_symbol = symbol.split('-')[0] if '-' in symbol else symbol
                sell_timestamp = sell.get('execution_timestamp')
                
                # Get entry price for this trade
                dca_query = """
                    SELECT 
                        COALESCE(SUM(amount_in), 0) as total_usd_spent,
                        COALESCE(SUM(amount_out), 0) as total_tokens_bought,
                        MIN(execution_timestamp) as first_buy_time
                    FROM strategy_executions
                    WHERE strategy_id = %s 
                        AND symbol LIKE %s
                        AND decision = 'BUY'
                        AND trade_executed = TRUE
                        AND execution_timestamp <= %s
                """
                dca_result = db_connection.execute_query(
                    dca_query,
                    (strategy_id, f"%{token_symbol}%", sell_timestamp),
                    fetch_one=True
                )
                
                if dca_result and dca_result.get('total_tokens_bought'):
                    total_usd_spent = Decimal(str(dca_result.get('total_usd_spent', 0)))
                    total_tokens_bought = Decimal(str(dca_result.get('total_tokens_bought', 0)))
                    first_buy_time = dca_result.get('first_buy_time')
                    
                    if total_tokens_bought > 0:
                        avg_entry = total_usd_spent / total_tokens_bought
                        cost_basis = tokens_sold * avg_entry
                        trade_pnl = usdc_received - cost_basis
                        
                        # Calculate return percentage
                        if cost_basis > 0:
                            trade_return_pct = float((trade_pnl / cost_basis) * 100)
                            trade_returns.append(trade_return_pct)
                        
                        trade_pnls.append(float(trade_pnl))
                        
                        # Update running equity and drawdown
                        running_equity += float(trade_pnl)
                        if running_equity > peak_equity:
                            peak_equity = running_equity
                        current_drawdown = peak_equity - running_equity
                        current_drawdown_pct = (current_drawdown / peak_equity) * 100 if peak_equity > 0 else 0
                        max_drawdown = max(max_drawdown, current_drawdown)
                        max_drawdown_pct = max(max_drawdown_pct, current_drawdown_pct)
                        
                        # Calculate trade duration
                        if first_buy_time and sell_timestamp:
                            duration = (sell_timestamp - first_buy_time).total_seconds() / 60
                            trade_durations.append(duration)
                        
                        if trade_pnl > 0:
                            winning_trades += 1
                            total_profit += trade_pnl
                            largest_win = max(largest_win, trade_pnl)
                        else:
                            losing_trades += 1
                            total_loss += abs(trade_pnl)
                            largest_loss = max(largest_loss, abs(trade_pnl))
            
            total_completed_trades = winning_trades + losing_trades
            win_rate = (winning_trades / total_completed_trades * 100) if total_completed_trades > 0 else 0
            net_pnl = total_profit - total_loss
            avg_profit = total_profit / winning_trades if winning_trades > 0 else Decimal('0')
            avg_loss = total_loss / losing_trades if losing_trades > 0 else Decimal('0')
            
            # =============== ADVANCED METRICS ===============
            
            # Profit Factor = Gross Profit / Gross Loss
            profit_factor = float(total_profit / total_loss) if total_loss > 0 else float('inf') if total_profit > 0 else 0.0
            
            # Expectancy = (Win Rate * Avg Win) - (Loss Rate * Avg Loss)
            loss_rate = (losing_trades / total_completed_trades) if total_completed_trades > 0 else 0
            expectancy = (win_rate/100 * float(avg_profit)) - (loss_rate * float(avg_loss)) if total_completed_trades > 0 else 0.0
            
            # Risk/Reward Ratio = Avg Win / Avg Loss
            risk_reward_ratio = float(avg_profit / avg_loss) if avg_loss > 0 else 0.0
            
            # Average Trade Duration
            avg_trade_duration_mins = sum(trade_durations) / len(trade_durations) if trade_durations else 0
            avg_trade_duration_hours = avg_trade_duration_mins / 60
            
            # Return on Investment (ROI)
            roi_pct = (float(net_pnl) / initial_capital) * 100 if initial_capital > 0 else 0
            
            # Sharpe Ratio (simplified: using trade returns, assuming risk-free rate = 0)
            # Sharpe = Mean Return / Std Dev of Returns
            sharpe_ratio = 0.0
            if len(trade_returns) >= 2:
                mean_return = sum(trade_returns) / len(trade_returns)
                variance = sum((r - mean_return) ** 2 for r in trade_returns) / len(trade_returns)
                std_dev = math.sqrt(variance) if variance > 0 else 0
                sharpe_ratio = mean_return / std_dev if std_dev > 0 else 0.0
            
            # Sortino Ratio (only considers downside deviation)
            sortino_ratio = 0.0
            if len(trade_returns) >= 2:
                mean_return = sum(trade_returns) / len(trade_returns)
                negative_returns = [r for r in trade_returns if r < 0]
                if negative_returns:
                    downside_variance = sum(r ** 2 for r in negative_returns) / len(trade_returns)
                    downside_dev = math.sqrt(downside_variance) if downside_variance > 0 else 0
                    sortino_ratio = mean_return / downside_dev if downside_dev > 0 else 0.0
            
            # Calmar Ratio = Annualized Return / Max Drawdown
            calmar_ratio = 0.0
            if max_drawdown_pct > 0 and len(trade_durations) > 0:
                # Estimate annualized return
                total_trading_days = sum(trade_durations) / (60 * 24)  # Convert to days
                if total_trading_days > 0:
                    annualized_return = (roi_pct / total_trading_days) * 365
                    calmar_ratio = annualized_return / max_drawdown_pct
            
            # Average Return per Trade
            avg_return_pct = sum(trade_returns) / len(trade_returns) if trade_returns else 0
            
            # Payoff Ratio (same as risk/reward)
            payoff_ratio = risk_reward_ratio
            
            return {
                # Basic Stats
                "total_trades": total_completed_trades,
                "total_buys": total_buys,
                "total_sells": total_sells,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": round(win_rate, 2),
                
                # P&L Stats
                "total_profit": round(float(total_profit), 2),
                "total_loss": round(float(total_loss), 2),
                "net_pnl": round(float(net_pnl), 2),
                "avg_profit_per_trade": round(float(avg_profit), 2),
                "avg_loss_per_trade": round(float(avg_loss), 2),
                "largest_win": round(float(largest_win), 2),
                "largest_loss": round(float(largest_loss), 2),
                
                # Return Stats
                "roi_pct": round(roi_pct, 2),
                "avg_return_pct": round(avg_return_pct, 2),
                
                # Risk Metrics
                "sharpe_ratio": round(sharpe_ratio, 2),
                "sortino_ratio": round(sortino_ratio, 2),
                "calmar_ratio": round(calmar_ratio, 2),
                "max_drawdown": round(max_drawdown, 2),
                "max_drawdown_pct": round(max_drawdown_pct, 2),
                
                # Trade Quality Metrics
                "profit_factor": round(profit_factor, 2) if profit_factor != float('inf') else 999.99,
                "expectancy": round(expectancy, 2),
                "risk_reward_ratio": round(risk_reward_ratio, 2),
                "payoff_ratio": round(payoff_ratio, 2),
                
                # Duration Stats
                "avg_trade_duration_mins": round(avg_trade_duration_mins, 1),
                "avg_trade_duration_hours": round(avg_trade_duration_hours, 2),
            }
            
        except Exception as e:
            logger.error(f"Error calculating trade statistics: {e}", exc_info=True)
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_profit": 0.0,
                "total_loss": 0.0,
                "net_pnl": 0.0,
                "sharpe_ratio": 0.0,
                "sortino_ratio": 0.0,
                "max_drawdown_pct": 0.0,
                "profit_factor": 0.0,
            }
    
    async def check_trade_cooldown(
        self,
        strategy_id: str,
        cooldown_minutes: int = 1
    ) -> tuple[bool, Optional[int]]:
        """
        Check if strategy is in trade cooldown period.
        Prevents overtrading by enforcing minimum time between trades.
        
        Args:
            strategy_id: Strategy UUID
            cooldown_minutes: Minimum minutes between trades
        
        Returns:
            (can_trade, seconds_remaining) - If can't trade, seconds until cooldown ends
        """
        try:
            query = """
                SELECT execution_timestamp
                FROM strategy_executions
                WHERE strategy_id = %s 
                    AND trade_executed = TRUE
                ORDER BY execution_timestamp DESC
                LIMIT 1
            """
            result = db_connection.execute_query(query, (strategy_id,), fetch_one=True)
            
            if not result or not result.get('execution_timestamp'):
                return True, None  # No trades yet, can trade
            
            last_trade_time = result.get('execution_timestamp')
            if last_trade_time.tzinfo is None:
                last_trade_time = last_trade_time.replace(tzinfo=timezone.utc)
            
            now = datetime.now(timezone.utc)
            time_since_trade = now - last_trade_time
            cooldown_seconds = cooldown_minutes * 60
            
            if time_since_trade.total_seconds() >= cooldown_seconds:
                return True, None
            else:
                remaining = int(cooldown_seconds - time_since_trade.total_seconds())
                return False, remaining
                
        except Exception as e:
            logger.error(f"Error checking trade cooldown: {e}", exc_info=True)
            return True, None  # Default to allowing trade
    
    async def liquidate_to_usdc(
        self,
        strategy_id: str,
        reason: str = "EMERGENCY_LIQUIDATION"
    ) -> bool:
        """
        Emergency liquidation: Close all positions and convert to USDC.
        Used when risk conditions are met (e.g., strategy says 'always end in USDC during high risk').
        
        Args:
            strategy_id: Strategy UUID
            reason: Reason for liquidation (for logging)
        
        Returns:
            True if successful
        """
        try:
            logger.warning(f"[Paper Trading] Initiating liquidation for strategy {strategy_id}: {reason}")
            
            balances = await self.get_balances(strategy_id)
            
            for balance in balances:
                token_symbol = balance.get('token_symbol')
                if token_symbol == "USDC":
                    continue
                
                token_balance = Decimal(str(balance.get('balance', 0)))
                if token_balance <= 0:
                    continue
                
                token_address = balance.get('token_address')
                usd_value = Decimal(str(balance.get('usd_value', 0)))
                
                # Calculate approximate price
                price = usd_value / token_balance if token_balance > 0 else Decimal('0')
                
                # Execute swap to USDC
                success = await self.execute_swap(
                    strategy_id=strategy_id,
                    src_token_address=token_address,
                    src_token_symbol=token_symbol,
                    dst_token_address=self.USDC_ADDRESS,
                    dst_token_symbol="USDC",
                    amount_in=token_balance,
                    amount_out=usd_value,  # Approximate
                    price=price,
                    slippage_pct=0.5,  # Higher slippage for emergency
                    gas_fee_usd=0.005  # Higher gas for urgency
                )
                
                if success:
                    logger.info(f"[Liquidation] Closed {token_balance} {token_symbol} for ~${usd_value:.2f}")
                else:
                    logger.error(f"[Liquidation] Failed to close {token_symbol} position")
            
            return True
            
        except Exception as e:
            logger.error(f"Error during liquidation: {e}", exc_info=True)
            return False
    
    def get_position_exposure(
        self,
        balances: List[Dict[str, Any]],
        initial_capital: float
    ) -> Dict[str, Any]:
        """
        Calculate position exposure metrics.
        
        Returns:
            {
                "total_exposure_usd": float,
                "exposure_pct": float (% of capital exposed),
                "usdc_available_pct": float (% in USDC/cash),
                "largest_position_pct": float,
                "positions": List with per-position exposure
            }
        """
        total_exposure = 0.0
        usdc_balance = 0.0
        position_exposures = []
        
        for balance in balances:
            token_symbol = balance.get('token_symbol')
            usd_value = float(balance.get('usd_value', 0))
            
            if token_symbol == "USDC":
                usdc_balance = usd_value
            else:
                total_exposure += usd_value
                position_exposures.append({
                    "token": token_symbol,
                    "value_usd": usd_value,
                    "pct_of_capital": (usd_value / initial_capital * 100) if initial_capital > 0 else 0
                })
        
        total_value = total_exposure + usdc_balance
        largest_position_pct = max((p['pct_of_capital'] for p in position_exposures), default=0)
        
        return {
            "total_exposure_usd": total_exposure,
            "exposure_pct": (total_exposure / initial_capital * 100) if initial_capital > 0 else 0,
            "usdc_available": usdc_balance,
            "usdc_available_pct": (usdc_balance / total_value * 100) if total_value > 0 else 100,
            "largest_position_pct": largest_position_pct,
            "positions": position_exposures
        }


# Singleton instance
paper_trading_dex = PaperTradingDEX()

