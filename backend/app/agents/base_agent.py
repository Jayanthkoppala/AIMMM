"""
Base Agent Class for Trading Agents
Provides common utilities and interface for all agents
"""
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from app.agents.state import TradingState
from app.utils.logger import logger


class BaseAgent(ABC):
    """
    Base class for all trading agents.
    Each agent implements the process() method to transform state.
    """
    
    def __init__(self, name: str):
        """
        Initialize base agent.
        
        Args:
            name: Agent name for logging
        """
        self.name = name
    
    @abstractmethod
    async def process(self, state: TradingState) -> Dict[str, Any]:
        """
        Process the current state and return updates.
        
        Args:
            state: Current trading state
        
        Returns:
            Dictionary of state updates to merge
        """
        pass
    
    def log_entry(self, state: TradingState, message: str):
        """Log agent entry with context."""
        strategy_id = state.get('strategy_id', 'unknown')
        logger.info(f"[{self.name}] [{strategy_id}] {message}")
    
    def log_info(self, state: TradingState, message: str):
        """Log info message."""
        strategy_id = state.get('strategy_id', 'unknown')
        logger.info(f"[{self.name}] [{strategy_id}] {message}")
    
    def log_warning(self, state: TradingState, message: str):
        """Log warning message."""
        strategy_id = state.get('strategy_id', 'unknown')
        logger.warning(f"[{self.name}] [{strategy_id}] {message}")
    
    def log_error(self, state: TradingState, message: str):
        """Log error message."""
        strategy_id = state.get('strategy_id', 'unknown')
        logger.error(f"[{self.name}] [{strategy_id}] {message}")
    
    def add_error(self, state: TradingState, error: str) -> Dict[str, Any]:
        """Add error to state."""
        errors = state.get('errors', [])
        errors.append(f"[{self.name}] {error}")
        return {'errors': errors}
    
    def track_agent(self, state: TradingState) -> Dict[str, Any]:
        """Track that this agent has processed the state."""
        agent_path = state.get('agent_path', [])
        agent_path.append(self.name)
        return {'agent_path': agent_path}
    
    def validate_required_fields(
        self,
        state: TradingState,
        required_fields: list
    ) -> Optional[str]:
        """
        Validate that required fields are present in state.
        
        Args:
            state: Current state
            required_fields: List of required field names
        
        Returns:
            Error message if validation fails, None otherwise
        """
        missing = []
        for field in required_fields:
            if field not in state or state[field] is None:
                missing.append(field)
        
        if missing:
            return f"Missing required fields: {', '.join(missing)}"
        
        return None
    
    def increment_retry(self, state: TradingState) -> Dict[str, Any]:
        """Increment retry count."""
        retry_count = state.get('retry_count', 0) + 1
        return {'retry_count': retry_count}
    
    def should_retry(self, state: TradingState) -> bool:
        """Check if should retry based on retry count."""
        retry_count = state.get('retry_count', 0)
        max_retries = state.get('max_retries', 3)
        return retry_count < max_retries


class AgentNode:
    """
    Wrapper for agent to use in LangGraph.
    Converts agent.process() into a function that updates state.
    """
    
    def __init__(self, agent: BaseAgent):
        """
        Initialize agent node.
        
        Args:
            agent: BaseAgent instance
        """
        self.agent = agent
    
    async def __call__(self, state: TradingState) -> TradingState:
        """
        Execute agent and merge updates into state.
        
        Args:
            state: Current state
        
        Returns:
            Updated state
        """
        try:
            # Track agent
            updates = self.agent.track_agent(state)
            
            # Process state
            agent_updates = await self.agent.process(state)
            
            # Merge updates
            updates.update(agent_updates)
            
            # Return merged state (LangGraph will handle the actual merging)
            return updates
            
        except Exception as e:
            error_msg = f"Error in {self.agent.name}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'errors': state.get('errors', []) + [error_msg],
                'agent_path': state.get('agent_path', []) + [f"{self.agent.name}:ERROR"]
            }

