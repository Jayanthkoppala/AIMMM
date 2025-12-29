"""
Risk Management Agent
Calculates position sizing, stop-loss, and take-profit levels dynamically.
"""
from typing import Dict, Optional, Tuple
from app.utils.logger import logger


class RiskManagementAgent:
    """Manages risk for trading positions"""
    
    def __init__(self):
        # Default risk parameters
        self.default_risk_per_trade = 0.02  # 2% of account per trade
        self.default_reward_ratio = 2.0  # 2:1 reward to risk
        self.max_position_size_pct = 0.10  # Max 10% of account in single position
        self.min_position_size_usd = 10.0  # Minimum $10 position
    
    def calculate_position_size(
        self,
        account_balance: float,
        entry_price: float,
        stop_loss_price: float,
        risk_per_trade: Optional[float] = None,
        max_position_pct: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Calculate optimal position size based on risk management rules.
        
        Args:
            account_balance: Total account balance in USD
            entry_price: Entry price for the trade
            stop_loss_price: Stop loss price level
            risk_per_trade: Percentage of account to risk (default: 2%)
            max_position_pct: Maximum position size as % of account (default: 10%)
        
        Returns:
            Dict with position_size, risk_amount, and position_value
        """
        if account_balance <= 0:
            logger.warning("Account balance is zero or negative, using minimum position")
            return {
                "position_size": self.min_position_size_usd / entry_price if entry_price > 0 else 0,
                "risk_amount": 0,
                "position_value": self.min_position_size_usd
            }
        
        risk_per_trade = risk_per_trade or self.default_risk_per_trade
        max_position_pct = max_position_pct or self.max_position_size_pct
        
        # Calculate risk per unit (price difference)
        if entry_price <= 0 or stop_loss_price <= 0:
            logger.warning("Invalid prices for position sizing, using minimum")
            return {
                "position_size": self.min_position_size_usd / entry_price if entry_price > 0 else 0,
                "risk_amount": account_balance * risk_per_trade,
                "position_value": self.min_position_size_usd
            }
        
        # Determine if long or short based on stop loss position
        is_long = stop_loss_price < entry_price
        
        if is_long:
            # Long position: stop loss below entry
            risk_per_unit = entry_price - stop_loss_price
        else:
            # Short position: stop loss above entry
            risk_per_unit = stop_loss_price - entry_price
        
        if risk_per_unit <= 0:
            logger.warning("Stop loss is at or beyond entry price, using minimum position")
            return {
                "position_size": self.min_position_size_usd / entry_price if entry_price > 0 else 0,
                "risk_amount": account_balance * risk_per_trade,
                "position_value": self.min_position_size_usd
            }
        
        # Calculate risk amount (dollar amount to risk)
        risk_amount = account_balance * risk_per_trade
        
        # Calculate position size based on risk
        position_size = risk_amount / risk_per_unit
        
        # Calculate position value
        position_value = position_size * entry_price
        
        # Apply maximum position size limit
        max_position_value = account_balance * max_position_pct
        if position_value > max_position_value:
            logger.info(f"Position size capped at {max_position_pct*100}% of account")
            position_value = max_position_value
            position_size = position_value / entry_price
            # Recalculate actual risk
            risk_amount = position_size * risk_per_unit
        
        # Ensure minimum position size
        if position_value < self.min_position_size_usd:
            logger.info(f"Position size below minimum, using minimum ${self.min_position_size_usd}")
            position_value = self.min_position_size_usd
            position_size = position_value / entry_price
            risk_amount = position_size * risk_per_unit
        
        return {
            "position_size": position_size,
            "risk_amount": risk_amount,
            "position_value": position_value,
            "risk_percentage": (risk_amount / account_balance) * 100 if account_balance > 0 else 0,
            "position_percentage": (position_value / account_balance) * 100 if account_balance > 0 else 0
        }
    
    def calculate_stop_loss(
        self,
        entry_price: float,
        volatility: Optional[float] = None,
        risk_tolerance: str = "moderate",
        atr_value: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Calculate stop loss price based on volatility and risk tolerance.
        
        Args:
            entry_price: Entry price for the trade
            volatility: Price volatility (optional, for advanced calculation)
            risk_tolerance: "conservative", "moderate", or "aggressive"
            atr_value: Average True Range value (optional, for volatility-based stop)
        
        Returns:
            Dict with stop_loss_price and stop_loss_percentage
        """
        # Risk tolerance multipliers
        tolerance_multipliers = {
            "conservative": 0.02,  # 2% stop loss
            "moderate": 0.03,      # 3% stop loss
            "aggressive": 0.05     # 5% stop loss
        }
        
        multiplier = tolerance_multipliers.get(risk_tolerance.lower(), 0.03)
        
        # Use ATR if available for volatility-based stop
        if atr_value and atr_value > 0:
            # Stop loss at 1.5x ATR below/above entry
            stop_distance = atr_value * 1.5
            stop_loss_long = entry_price - stop_distance
            stop_loss_short = entry_price + stop_distance
            
            # Use percentage-based as fallback if ATR gives extreme values
            pct_stop_long = entry_price * (1 - multiplier)
            pct_stop_short = entry_price * (1 + multiplier)
            
            # Use the more conservative (tighter) stop
            stop_loss_long = max(stop_loss_long, pct_stop_long)
            stop_loss_short = min(stop_loss_short, pct_stop_short)
        else:
            # Percentage-based stop loss
            stop_loss_long = entry_price * (1 - multiplier)
            stop_loss_short = entry_price * (1 + multiplier)
        
        return {
            "stop_loss_long": max(stop_loss_long, 0),  # Ensure non-negative
            "stop_loss_short": stop_loss_short,
            "stop_loss_percentage": multiplier * 100
        }
    
    def calculate_take_profit(
        self,
        entry_price: float,
        stop_loss_price: float,
        reward_ratio: Optional[float] = None,
        take_profit_pct: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Calculate take profit price based on reward:risk ratio.
        
        Args:
            entry_price: Entry price for the trade
            stop_loss_price: Stop loss price level
            reward_ratio: Reward to risk ratio (default: 2.0)
            take_profit_pct: Alternative: fixed percentage take profit
        
        Returns:
            Dict with take_profit_long, take_profit_short, and reward_ratio
        """
        reward_ratio = reward_ratio or self.default_reward_ratio
        
        # Determine if long or short
        is_long = stop_loss_price < entry_price
        
        if is_long:
            # Long position
            risk_distance = entry_price - stop_loss_price
            take_profit_long = entry_price + (risk_distance * reward_ratio)
            take_profit_short = None
        else:
            # Short position
            risk_distance = stop_loss_price - entry_price
            take_profit_short = entry_price - (risk_distance * reward_ratio)
            take_profit_long = None
        
        # Alternative: use fixed percentage if provided
        if take_profit_pct:
            if is_long:
                take_profit_long = entry_price * (1 + take_profit_pct)
            else:
                take_profit_short = entry_price * (1 - take_profit_pct)
        
        result = {
            "take_profit_long": take_profit_long if take_profit_long else None,
            "take_profit_short": take_profit_short if take_profit_short else None,
            "reward_ratio": reward_ratio,
            "risk_distance": abs(entry_price - stop_loss_price),
            "reward_distance": abs(entry_price - (take_profit_long or take_profit_short or entry_price))
        }
        
        return result
    
    def validate_trade_risk(
        self,
        account_balance: float,
        position_value: float,
        risk_amount: float,
        max_drawdown_pct: Optional[float] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate if trade meets risk management criteria.
        
        Args:
            account_balance: Total account balance
            position_value: Value of the position
            risk_amount: Amount at risk
            max_drawdown_pct: Maximum allowed drawdown percentage
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if account_balance <= 0:
            return False, "Account balance is zero or negative"
        
        # Check position size
        position_pct = (position_value / account_balance) * 100
        if position_pct > self.max_position_size_pct * 100:
            return False, f"Position size ({position_pct:.2f}%) exceeds maximum ({self.max_position_size_pct*100}%)"
        
        # Check risk amount
        risk_pct = (risk_amount / account_balance) * 100
        if risk_pct > 5.0:  # Max 5% risk per trade
            return False, f"Risk amount ({risk_pct:.2f}%) exceeds maximum (5%)"
        
        # Check minimum position
        if position_value < self.min_position_size_usd:
            return False, f"Position value (${position_value:.2f}) below minimum (${self.min_position_size_usd})"
        
        return True, None
    
    def calculate_portfolio_diversification_score(
        self,
        balances: list,
        total_value: float
    ) -> Dict[str, float]:
        """
        Calculate portfolio diversification score for DEX spot trading.
        
        Args:
            balances: List of token balances with usd_value
            total_value: Total portfolio value
        
        Returns:
            Dict with diversification_score (0-1) and concentration_risk
        """
        if not balances or total_value <= 0:
            return {
                "diversification_score": 0.0,
                "concentration_risk": 1.0,
                "largest_position_pct": 0.0
            }
        
        # Calculate Herfindahl-Hirschman Index (HHI) for concentration
        # HHI = sum of squared market shares
        hhi = 0
        largest_position_pct = 0
        
        for balance in balances:
            usd_value = float(balance.get('usd_value', 0))
            position_pct = (usd_value / total_value) if total_value > 0 else 0
            hhi += position_pct ** 2
            largest_position_pct = max(largest_position_pct, position_pct * 100)
        
        # Diversification score: 1 - HHI (higher is better)
        # Perfect diversification (many equal positions) = 0 HHI = 1 score
        # Full concentration (1 position) = 1 HHI = 0 score
        diversification_score = 1 - hhi
        
        return {
            "diversification_score": diversification_score,
            "concentration_risk": hhi,
            "largest_position_pct": largest_position_pct
        }
    
    def check_min_trade_size_for_gas(
        self,
        trade_value_usd: float,
        estimated_gas_usd: float = 0.05
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if trade size is worth the gas cost (DEX spot trading).
        
        Args:
            trade_value_usd: Trade value in USD
            estimated_gas_usd: Estimated gas cost in USD
        
        Returns:
            Tuple of (is_efficient, warning_message)
        """
        if trade_value_usd <= 0:
            return False, "Trade value must be positive"
        
        # Gas should be less than 5% of trade value
        gas_ratio = (estimated_gas_usd / trade_value_usd) * 100
        
        if gas_ratio > 5.0:
            return False, f"Gas cost ({gas_ratio:.2f}% of trade) is too high. Consider larger trade size."
        elif gas_ratio > 2.0:
            return True, f"Gas cost is {gas_ratio:.2f}% of trade value (acceptable but high)"
        
        return True, None
    
    def validate_slippage_tolerance(
        self,
        expected_output: float,
        min_output_with_slippage: float,
        max_slippage_pct: float = 1.0
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate slippage is within acceptable range for DEX swaps.
        
        Args:
            expected_output: Expected output amount
            min_output_with_slippage: Minimum output with slippage
            max_slippage_pct: Maximum acceptable slippage percentage
        
        Returns:
            Tuple of (is_acceptable, warning_message)
        """
        if expected_output <= 0:
            return False, "Expected output must be positive"
        
        slippage_pct = ((expected_output - min_output_with_slippage) / expected_output) * 100
        
        if slippage_pct > max_slippage_pct:
            return False, f"Slippage ({slippage_pct:.2f}%) exceeds maximum ({max_slippage_pct}%)"
        
        if slippage_pct > max_slippage_pct * 0.7:
            return True, f"Slippage is {slippage_pct:.2f}% (near limit of {max_slippage_pct}%)"
        
        return True, None


# Create singleton instance
risk_agent = RiskManagementAgent()

