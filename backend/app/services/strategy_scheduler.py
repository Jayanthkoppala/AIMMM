"""
Strategy Scheduler - Automated execution of active strategies
Checks every minute and executes strategies based on their execution_interval
"""
import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timezone, timedelta
from app.utils.database import db_connection
from app.utils.logger import logger
from app.services.strategy_executor import strategy_executor


class StrategyScheduler:
    """Scheduler for automated strategy execution"""
    
    def __init__(self):
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.check_interval_seconds = 60  # Check every minute
        self.max_concurrent_executions = 5  # Execute max 5 strategies concurrently
    
    def start(self):
        """Start strategy scheduler"""
        if self.running:
            logger.info("Strategy scheduler already running")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._run())
        logger.info("Strategy scheduler started")
    
    def stop(self):
        """Stop strategy scheduler"""
        self.running = False
        if self.task:
            self.task.cancel()
        logger.info("Strategy scheduler stopped")
    
    async def _run(self):
        """Main scheduler loop"""
        while self.running:
            try:
                await self._check_and_execute_strategies()
                await asyncio.sleep(self.check_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in strategy scheduler loop: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    def _get_active_strategies(self) -> List[Dict]:
        """Get all active strategies that need execution"""
        if not db_connection.pool:
            return []
        
        try:
            query = """
                SELECT id, user_id, name, execution_interval, last_execution, strategy_config
                FROM user_strategies
                WHERE is_active = TRUE
                ORDER BY last_execution ASC NULLS FIRST
            """
            
            results = db_connection.execute_query(query, fetch_all=True)
            return results or []
            
        except Exception as e:
            logger.error(f"Error fetching active strategies: {e}", exc_info=True)
            return []
    
    def _should_execute(self, strategy: Dict, now: datetime) -> bool:
        """Check if strategy should be executed based on interval"""
        try:
            interval_minutes = strategy.get('execution_interval', 5)
            last_execution = strategy.get('last_execution')
            
            if not last_execution:
                # Never executed, should execute now
                return True
            
            # Ensure last_execution is timezone-aware
            if last_execution.tzinfo is None:
                last_execution = last_execution.replace(tzinfo=timezone.utc)
            
            # Calculate time since last execution
            time_since_last = now - last_execution
            interval_delta = timedelta(minutes=interval_minutes)
            
            return time_since_last >= interval_delta
            
        except Exception as e:
            logger.error(f"Error checking execution time: {e}", exc_info=True)
            return False
    
    async def _check_and_execute_strategies(self):
        """Check active strategies and execute eligible ones"""
        try:
            strategies = self._get_active_strategies()
            
            if not strategies:
                logger.debug("No active strategies found")
                return
            
            now = datetime.now(timezone.utc)
            strategies_to_execute = []
            
            for strategy in strategies:
                if self._should_execute(strategy, now):
                    strategies_to_execute.append(strategy)
                else:
                    # Log why strategy was skipped
                    interval_minutes = strategy.get('execution_interval', 5)
                    last_execution = strategy.get('last_execution')
                    if last_execution:
                        if last_execution.tzinfo is None:
                            last_execution = last_execution.replace(tzinfo=timezone.utc)
                        time_since_last = now - last_execution
                        time_remaining = timedelta(minutes=interval_minutes) - time_since_last
                        logger.debug(
                            f"Strategy '{strategy.get('name')}' not ready: "
                            f"interval={interval_minutes}min, "
                            f"last_exec={time_since_last.total_seconds():.0f}s ago, "
                            f"next_exec in {time_remaining.total_seconds():.0f}s"
                        )
            
            if not strategies_to_execute:
                logger.debug(f"No strategies ready for execution (checked {len(strategies)} active strategies)")
                return
            
            logger.info(f"Executing {len(strategies_to_execute)} strategies")
            
            # Execute strategies concurrently with semaphore to limit concurrency
            await self._execute_strategies_batch(strategies_to_execute)
            
        except Exception as e:
            logger.error(f"Error checking and executing strategies: {e}", exc_info=True)
    
    async def _execute_strategies_batch(self, strategies: List[Dict]):
        """Execute multiple strategies concurrently with rate limiting"""
        semaphore = asyncio.Semaphore(self.max_concurrent_executions)
        
        async def execute_with_semaphore(strategy: Dict):
            async with semaphore:
                try:
                    strategy_id = str(strategy.get('id'))
                    user_id = strategy.get('user_id')
                    strategy_name = strategy.get('name', 'Unknown')
                    
                    logger.info(f"Executing strategy '{strategy_name}' ({strategy_id}) - interval: {strategy.get('execution_interval', 5)} min")
                    
                    # Get execution mode from strategy config
                    strategy_config = strategy.get('strategy_config', {})
                    execution_mode = strategy_config.get('execution_mode', 'analysis')
                    
                    result = await strategy_executor.execute_strategy(
                        strategy_id=strategy_id,
                        user_id=user_id,
                        execution_mode=execution_mode
                    )
                    
                    if result.get('status') == 'success':
                        decision = result.get('decision', {})
                        logger.info(
                            f"Strategy '{strategy_name}' executed: "
                            f"action={decision.get('action')}, "
                            f"confidence={decision.get('confidence', 0):.2f}, "
                            f"trade_executed={result.get('trade_executed', False)}"
                        )
                    else:
                        logger.error(f"Strategy '{strategy_name}' execution failed: {result.get('error')}")
                    
                except Exception as e:
                    logger.error(f"Error executing strategy {strategy.get('id', 'unknown')}: {e}", exc_info=True)
        
        # Execute all strategies concurrently
        tasks = [execute_with_semaphore(strategy) for strategy in strategies]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_status(self) -> Dict:
        """Get scheduler status"""
        return {
            "running": self.running,
            "check_interval_seconds": self.check_interval_seconds,
            "max_concurrent_executions": self.max_concurrent_executions
        }


# Singleton instance
strategy_scheduler = StrategyScheduler()



