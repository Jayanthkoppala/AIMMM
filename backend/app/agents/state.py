"""
Trading State Schema for LangGraph Agents
Defines the shared state that flows through the agent workflow
"""
from typing import Dict, List, Optional, Any, TypedDict
from decimal import Decimal


class TradingState(TypedDict, total=False):
    """
    Shared state that flows through the agent workflow.
    Each agent reads from and writes to this state.
    """
    # Strategy context
    strategy_id: str
    user_id: str
    strategy_config: Dict[str, Any]
    strategy_description: Optional[str]
    execution_mode: str  # "analysis" or "trade"
    pool_id: Optional[int]
    pool_address: Optional[str]
    
    # Market data
    market_data: Optional[Dict[str, Any]]
    data_complete: bool
    data_errors: List[str]
    
    # Portfolio state
    portfolio_state: Optional[Dict[str, Any]]
    active_positions: List[Dict[str, Any]]
    usdc_balance: float
    total_value: float
    
    # Analysis
    analysis: Optional[Dict[str, Any]]
    market_conditions: Optional[str]
    trend_analysis: Optional[str]
    
    # Decision making
    decision: Optional[Dict[str, Any]]
    confidence: float
    action: Optional[str]  # "BUY", "SELL", "HOLD", "CLOSE_POSITION"
    reasoning: Optional[str]
    
    # Risk assessment
    risk_checks: Dict[str, bool]
    risk_approved: bool
    risk_warnings: List[str]
    
    # Execution
    trade_result: Optional[Dict[str, Any]]
    execution_id: Optional[str]
    exit_positions: List[Dict[str, Any]]
    
    # Workflow control
    should_exit_positions: bool
    should_analyze: bool
    should_execute_trade: bool
    
    # Error handling
    errors: List[str]
    retry_count: int
    max_retries: int
    
    # Metadata
    start_time: float
    execution_duration: Optional[float]
    agent_path: List[str]  # Track which agents have processed this state


def create_initial_state(
    strategy_id: str,
    user_id: str,
    strategy_config: Dict[str, Any],
    execution_mode: str = "analysis",
    pool_id: Optional[int] = None,
    pool_address: Optional[str] = None,
    strategy_description: Optional[str] = None
) -> TradingState:
    """
    Create initial trading state for a new execution.
    
    Args:
        strategy_id: Strategy UUID
        user_id: User UUID
        strategy_config: Strategy configuration dict
        execution_mode: "analysis" or "trade"
        pool_id: Optional pool ID
        pool_address: Optional pool address
        strategy_description: Optional user's strategy description
    
    Returns:
        Initialized TradingState
    """
    import time
    
    return TradingState(
        # Strategy context
        strategy_id=strategy_id,
        user_id=user_id,
        strategy_config=strategy_config,
        strategy_description=strategy_description,
        execution_mode=execution_mode,
        pool_id=pool_id,
        pool_address=pool_address,
        
        # Market data
        market_data=None,
        data_complete=False,
        data_errors=[],
        
        # Portfolio state
        portfolio_state=None,
        active_positions=[],
        usdc_balance=0.0,
        total_value=0.0,
        
        # Analysis
        analysis=None,
        market_conditions=None,
        trend_analysis=None,
        
        # Decision making
        decision=None,
        confidence=0.0,
        action=None,
        reasoning=None,
        
        # Risk assessment
        risk_checks={},
        risk_approved=False,
        risk_warnings=[],
        
        # Execution
        trade_result=None,
        execution_id=None,
        exit_positions=[],
        
        # Workflow control
        should_exit_positions=False,
        should_analyze=True,
        should_execute_trade=False,
        
        # Error handling
        errors=[],
        retry_count=0,
        max_retries=3,
        
        # Metadata
        start_time=time.time(),
        execution_duration=None,
        agent_path=[]
    )

