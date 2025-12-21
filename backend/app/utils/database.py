"""
Direct PostgreSQL database connection utility.
Can be used as an alternative to Supabase client library.
"""
import os
from typing import Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
from app.config import settings
from app.utils.logger import logger


class DatabaseConnection:
    """Direct PostgreSQL database connection manager."""
    
    def __init__(self):
        self.pool: Optional[SimpleConnectionPool] = None
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize connection pool from DATABASE_URL or individual settings."""
        try:
            # Try DATABASE_URL first (Supabase format)
            database_url = getattr(settings, 'DATABASE_URL', '') or os.getenv('DATABASE_URL', '')
            
            if database_url:
                # Parse and create connection pool
                self.pool = SimpleConnectionPool(
                    minconn=1,
                    maxconn=10,
                    dsn=database_url
                )
                logger.info("Database connection pool initialized from DATABASE_URL")
                return
            
            # Fallback to individual settings
            user = getattr(settings, 'DB_USER', '') or os.getenv('DB_USER', '')
            password = getattr(settings, 'DB_PASSWORD', '') or os.getenv('DB_PASSWORD', '')
            host = getattr(settings, 'DB_HOST', '') or os.getenv('DB_HOST', '')
            port = getattr(settings, 'DB_PORT', '') or os.getenv('DB_PORT', '5432')
            dbname = getattr(settings, 'DB_NAME', '') or os.getenv('DB_NAME', '')
            
            if all([user, password, host, dbname]):
                self.pool = SimpleConnectionPool(
                    minconn=1,
                    maxconn=10,
                    user=user,
                    password=password,
                    host=host,
                    port=port,
                    dbname=dbname
                )
                logger.info("Database connection pool initialized from individual settings")
            else:
                logger.warning("Database credentials not configured. Running without direct database connection.")
                
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
    
    def execute_query(self, query: str, params: tuple = None, fetch_one: bool = False, fetch_all: bool = True):
        """
        Execute a query and return results.
        
        Args:
            query: SQL query string
            params: Query parameters tuple
            fetch_one: Return single row
            fetch_all: Return all rows (default)
        
        Returns:
            Query results as list of dicts or single dict
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
                return dict(result) if result else None
            elif fetch_all:
                results = cursor.fetchall()
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
    
    def test_connection(self) -> bool:
        """Test database connection."""
        try:
            result = self.execute_query("SELECT NOW() as current_time", fetch_one=True)
            if result:
                logger.info(f"Database connection test successful. Server time: {result.get('current_time')}")
                return True
            return False
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def close_all(self):
        """Close all connections in the pool."""
        if self.pool:
            self.pool.closeall()
            logger.info("All database connections closed")


# Global database connection instance
db_connection = DatabaseConnection()

