"""
Agent Metrics Tracking
Tracks performance metrics for individual agents
"""
from typing import Dict, List
from datetime import datetime
from collections import defaultdict
from app.utils.logger import logger


class AgentMetrics:
    """
    Tracks metrics for agent performance.
    
    Metrics tracked:
    - Execution count per agent
    - Average execution time per agent
    - Error count per agent
    - Success rate per agent
    """
    
    def __init__(self):
        self.execution_counts: Dict[str, int] = defaultdict(int)
        self.execution_times: Dict[str, List[float]] = defaultdict(list)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.start_times: Dict[str, datetime] = {}
    
    def start_agent(self, agent_name: str):
        """Mark start of agent execution."""
        self.start_times[agent_name] = datetime.now()
    
    def end_agent(self, agent_name: str, success: bool = True):
        """Mark end of agent execution and record metrics."""
        if agent_name in self.start_times:
            duration = (datetime.now() - self.start_times[agent_name]).total_seconds()
            self.execution_times[agent_name].append(duration)
            self.execution_counts[agent_name] += 1
            
            if not success:
                self.error_counts[agent_name] += 1
            
            del self.start_times[agent_name]
    
    def get_metrics(self, agent_name: str = None) -> Dict:
        """
        Get metrics for a specific agent or all agents.
        
        Args:
            agent_name: Optional agent name, None for all agents
        
        Returns:
            Dictionary of metrics
        """
        if agent_name:
            times = self.execution_times.get(agent_name, [])
            count = self.execution_counts.get(agent_name, 0)
            errors = self.error_counts.get(agent_name, 0)
            
            return {
                "agent": agent_name,
                "executions": count,
                "avg_time": sum(times) / len(times) if times else 0,
                "total_time": sum(times),
                "errors": errors,
                "success_rate": ((count - errors) / count * 100) if count > 0 else 0
            }
        
        # Return metrics for all agents
        all_agents = set(self.execution_counts.keys())
        return {
            agent: self.get_metrics(agent)
            for agent in all_agents
        }
    
    def log_summary(self):
        """Log a summary of all metrics."""
        metrics = self.get_metrics()
        
        if not metrics:
            logger.info("[AgentMetrics] No metrics to report")
            return
        
        logger.info("[AgentMetrics] ===== Agent Performance Summary =====")
        
        for agent_name, agent_metrics in metrics.items():
            logger.info(
                f"[AgentMetrics] {agent_name}: "
                f"{agent_metrics['executions']} executions, "
                f"avg {agent_metrics['avg_time']:.3f}s, "
                f"{agent_metrics['success_rate']:.1f}% success"
            )
        
        logger.info("[AgentMetrics] =====================================")
    
    def reset(self):
        """Reset all metrics."""
        self.execution_counts.clear()
        self.execution_times.clear()
        self.error_counts.clear()
        self.start_times.clear()


# Global metrics instance
agent_metrics = AgentMetrics()

