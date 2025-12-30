"""
Trading Graph - LangGraph Workflow Definition
Orchestrates all trading agents in a stateful workflow
"""
from typing import Literal
from langgraph.graph import StateGraph, END
from app.agents.state import TradingState
from app.agents.base_agent import AgentNode
from app.agents.market_data_agent import market_data_agent
from app.agents.portfolio_agent import portfolio_agent
from app.agents.monitoring_agent import monitoring_agent
from app.agents.risk_agent import risk_agent
from app.agents.analysis_agent import analysis_agent
from app.agents.decision_agent import decision_agent
from app.agents.execution_agent import execution_agent
from app.utils.logger import logger


# Node names (constants) - must not conflict with state keys
MARKET_DATA = "fetch_market_data"
PORTFOLIO = "update_portfolio"
MONITORING = "monitor_positions"
RISK = "assess_risk"
ANALYSIS = "analyze_market"
DECISION = "make_decision"
EXECUTION = "execute_trade"


def should_retry_market_data(state: TradingState) -> Literal["fetch_market_data", "update_portfolio"]:
    """
    Decide whether to retry market data gathering or proceed.
    
    Returns:
        "fetch_market_data" to retry, "update_portfolio" to proceed
    """
    data_complete = state.get('data_complete', False)
    retry_count = state.get('retry_count', 0)
    max_retries = state.get('max_retries', 3)
    
    if not data_complete and retry_count < max_retries:
        logger.info(f"[TradingGraph] Market data incomplete, retrying ({retry_count}/{max_retries})")
        return MARKET_DATA
    
    logger.info(f"[TradingGraph] Market data gathering complete, proceeding to portfolio")
    return PORTFOLIO


def should_exit_positions(state: TradingState) -> Literal["execute_trade", "assess_risk"]:
    """
    Decide whether to execute exit positions or proceed to risk check.
    
    Returns:
        "execute_trade" to exit positions, "assess_risk" to proceed with new trades
    """
    should_exit = state.get('should_exit_positions', False)
    exit_positions = state.get('exit_positions', [])
    
    if should_exit and len(exit_positions) > 0:
        logger.info(f"[TradingGraph] {len(exit_positions)} positions need exit, routing to execution")
        return EXECUTION
    
    logger.info(f"[TradingGraph] No exit positions, proceeding to risk check")
    return RISK


def should_continue_from_risk(state: TradingState) -> str:
    """
    Unified decision function for routing after Risk node.
    Handles both pre-decision (preliminary risk check) and post-decision (final validation) cases.
    
    Returns:
        ANALYSIS if no decision yet and risk passed (continue to analysis)
        EXECUTION if decision exists and warrants trade execution
        "__end__" if risk failed or decision is HOLD/no trade needed
    """
    risk_approved = state.get('risk_approved', False)
    decision = state.get('decision')
    action = state.get('action')
    confidence = state.get('confidence', 0.0)
    
    # Case 1: Risk check failed - end with HOLD
    if not risk_approved:
        logger.info(f"[TradingGraph] Risk check failed, ending execution with HOLD")
        return END
    
    # Case 2: No decision yet - continue to analysis (preliminary risk check passed)
    if not decision:
        logger.info(f"[TradingGraph] Risk check passed, proceeding to analysis")
        return ANALYSIS  # Returns "analyze_market"
    
    # Case 3: Decision exists - check if trade should be executed
    if action in ['BUY', 'SELL', 'CLOSE_POSITION'] and confidence >= 0.70:
        logger.info(f"[TradingGraph] Decision approved: {action} (confidence: {confidence:.2f}), executing trade")
        return EXECUTION  # Returns "execute_trade"
    
    # Case 4: Decision is HOLD or doesn't meet trade criteria - end
    logger.info(f"[TradingGraph] No trade execution needed (action: {action}, confidence: {confidence:.2f})")
    return END


def create_trading_graph() -> StateGraph:
    """
    Create the trading workflow graph.
    
    Returns:
        Compiled StateGraph ready for execution
    """
    # Create graph
    workflow = StateGraph(TradingState)
    
    # Add agent nodes
    workflow.add_node(MARKET_DATA, AgentNode(market_data_agent))
    workflow.add_node(PORTFOLIO, AgentNode(portfolio_agent))
    workflow.add_node(MONITORING, AgentNode(monitoring_agent))
    workflow.add_node(RISK, AgentNode(risk_agent))
    workflow.add_node(ANALYSIS, AgentNode(analysis_agent))
    workflow.add_node(DECISION, AgentNode(decision_agent))
    workflow.add_node(EXECUTION, AgentNode(execution_agent))
    
    # Define workflow edges
    
    # Start -> Market Data
    workflow.set_entry_point(MARKET_DATA)
    
    # Market Data -> Portfolio (with retry logic)
    workflow.add_conditional_edges(
        MARKET_DATA,
        should_retry_market_data,
        {
            MARKET_DATA: MARKET_DATA,  # Retry if data incomplete
            PORTFOLIO: PORTFOLIO        # Proceed if data ready
        }
    )
    
    # Portfolio -> Monitoring
    workflow.add_edge(PORTFOLIO, MONITORING)
    
    # Monitoring -> Execution (exits) or Risk (new trades)
    workflow.add_conditional_edges(
        MONITORING,
        should_exit_positions,
        {
            EXECUTION: EXECUTION,  # Execute exits
            RISK: RISK             # Check risk for new trades
        }
    )
    
    # Risk -> Analysis, Execution, or End
    # Single unified conditional edge that handles both:
    # - Pre-decision: preliminary risk check (no decision yet)
    # - Post-decision: final validation after LLM decision
    workflow.add_conditional_edges(
        RISK,
        should_continue_from_risk,
        {
            ANALYSIS: ANALYSIS,    # No decision yet, risk passed -> continue to analysis
            EXECUTION: EXECUTION,  # Decision approved for trade -> execute
            END: END               # Risk failed OR decision is HOLD -> end
        }
    )
    
    # Analysis -> Decision
    workflow.add_edge(ANALYSIS, DECISION)
    
    # Decision -> Risk (final validation)
    # After LLM makes a decision, Risk agent validates it before execution
    workflow.add_edge(DECISION, RISK)
    
    # Execution -> End
    workflow.add_edge(EXECUTION, END)
    
    # Compile the graph
    app = workflow.compile()
    
    logger.info("[TradingGraph] Trading workflow graph compiled successfully")
    
    return app


# Create the compiled graph (singleton)
trading_graph = create_trading_graph()


async def execute_trading_strategy(
    strategy_id: str,
    user_id: str,
    strategy_config: dict,
    execution_mode: str = "analysis",
    pool_id: int = None,
    pool_address: str = None,
    strategy_description: str = None
) -> dict:
    """
    Execute a trading strategy through the LangGraph workflow.
    
    Args:
        strategy_id: Strategy UUID
        user_id: User UUID
        strategy_config: Strategy configuration
        execution_mode: "analysis" or "trade"
        pool_id: Optional pool ID
        pool_address: Optional pool address
        strategy_description: Optional user's strategy description
    
    Returns:
        Execution result dictionary
    """
    import time
    from app.agents.state import create_initial_state
    
    start_time = time.time()
    
    logger.info(f"[TradingGraph] ===== Starting strategy execution =====")
    logger.info(f"[TradingGraph] Strategy ID: {strategy_id}")
    logger.info(f"[TradingGraph] Execution mode: {execution_mode}")
    
    # Create initial state
    initial_state = create_initial_state(
        strategy_id=strategy_id,
        user_id=user_id,
        strategy_config=strategy_config,
        execution_mode=execution_mode,
        pool_id=pool_id,
        pool_address=pool_address,
        strategy_description=strategy_description
    )
    
    try:
        # Execute the graph
        logger.info(f"[TradingGraph] Invoking trading graph...")
        final_state = await trading_graph.ainvoke(initial_state)
        
        execution_duration = time.time() - start_time
        
        # Extract results
        decision = final_state.get('decision', {})
        action = decision.get('action', 'HOLD')
        confidence = decision.get('confidence', 0.0)
        reasoning = decision.get('reasoning', '')
        trade_result = final_state.get('trade_result')
        portfolio_state = final_state.get('portfolio_state', {})
        market_data = final_state.get('market_data', {})
        errors = final_state.get('errors', [])
        agent_path = final_state.get('agent_path', [])
        
        logger.info(f"[TradingGraph] ===== Execution Complete =====")
        logger.info(f"[TradingGraph] Decision: {action} (confidence: {confidence:.2f})")
        logger.info(f"[TradingGraph] Trade executed: {trade_result is not None}")
        logger.info(f"[TradingGraph] Duration: {execution_duration:.2f}s")
        logger.info(f"[TradingGraph] Agent path: {' -> '.join(agent_path)}")
        if errors:
            logger.warning(f"[TradingGraph] Errors: {errors}")
        
        # Build response
        result = {
            "status": "success",
            "decision": decision,
            "trading_state": {
                "strategy_id": strategy_id,
                "balances": portfolio_state.get('balances', []),
                "total_portfolio_value": float(portfolio_state.get('total_value', 0)),
                "initial_capital": float(portfolio_state.get('initial_capital', 1000)),
                "unrealized_pnl": float(portfolio_state.get('unrealized_pnl', 0)),
                "realized_pnl": float(portfolio_state.get('realized_pnl', 0)),
                "total_pnl": float(portfolio_state.get('total_pnl', 0)),
                "unrealized_pnl_pct": portfolio_state.get('unrealized_pnl_pct', 0),
                "total_pnl_pct": portfolio_state.get('total_pnl_pct', 0),
                "active_positions": len(final_state.get('active_positions', []))
            },
            "trade_executed": trade_result is not None,
            "trade_result": trade_result,
            "market_data": market_data,
            "duration": execution_duration,
            "agent_path": agent_path,
            "errors": errors
        }
        
        return result
        
    except Exception as e:
        execution_duration = time.time() - start_time
        logger.error(f"[TradingGraph] Error executing strategy: {e}", exc_info=True)
        
        return {
            "status": "error",
            "error": str(e),
            "duration": execution_duration,
            "agent_path": initial_state.get('agent_path', []),
            "errors": initial_state.get('errors', []) + [str(e)]
        }

