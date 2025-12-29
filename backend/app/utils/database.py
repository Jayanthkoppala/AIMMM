"""
Simple database connection utility for CoinGecko data storage.
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
from app.config import settings
from app.utils.logger import logger


class DatabaseConnection:
    """Simple PostgreSQL database connection manager."""
    
    def __init__(self):
        self.pool: SimpleConnectionPool = None
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize connection pool from DATABASE_URL."""
        try:
            database_url = getattr(settings, 'DATABASE_URL', '') or os.getenv('DATABASE_URL', '')
            
            if database_url:
                self.pool = SimpleConnectionPool(
                    minconn=1,
                    maxconn=10,
                    dsn=database_url
                )
                logger.info("Database connection pool initialized")
            else:
                logger.warning("DATABASE_URL not configured - database features disabled")
                
        except Exception as e:
            logger.error(f"Failed to initialize database connection pool: {e}", exc_info=True)
            self.pool = None
    
    def get_connection(self):
        """Get a connection from the pool."""
        if not self.pool:
            raise Exception("Database connection pool not initialized")
        return self.pool.getconn()
    
    def return_connection(self, conn):
        """Return a connection to the pool."""
        if self.pool:
            self.pool.putconn(conn)
    
    def execute_query(self, query: str, params: tuple = None, fetch_one: bool = False, fetch_all: bool = False, max_retries: int = 0):
        """
        Execute a query and return results.
        
        Args:
            query: SQL query string
            params: Query parameters tuple
            fetch_one: Return single row
            fetch_all: Return all rows
            max_retries: Maximum number of retry attempts (for compatibility, not used in simple version)
        """
        if not self.pool:
            logger.error("Cannot execute query: database pool not initialized")
            return None
        
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(query, params)
            
            if fetch_one:
                result = cursor.fetchone()
                conn.commit()
                return dict(result) if result else None
            elif fetch_all:
                results = cursor.fetchall()
                conn.commit()
                return [dict(row) for row in results]
            else:
                conn.commit()
                return cursor.rowcount
                
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database query error: {e}", exc_info=True)
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                self.return_connection(conn)
    
    def execute_batch(self, query: str, params_list: list):
        """
        Execute a query multiple times with different parameters (batch insert/update).
        
        Args:
            query: SQL query string with placeholders
            params_list: List of parameter tuples, one per execution
            
        Returns:
            Total number of rows affected
        """
        if not self.pool:
            logger.error("Cannot execute batch: database pool not initialized")
            return 0
        
        if not params_list:
            return 0
        
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Use executemany for batch operations
            cursor.executemany(query, params_list)
            conn.commit()
            
            return cursor.rowcount
                
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database batch query error: {e}", exc_info=True)
            return 0
        finally:
            if cursor:
                cursor.close()
            if conn:
                self.return_connection(conn)
    
    def test_connection(self) -> bool:
        """Test database connection."""
        try:
            result = self.execute_query("SELECT NOW() as current_time", fetch_one=True)
            return result is not None
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False


# Global database connection instance
db_connection = DatabaseConnection()

