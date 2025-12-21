"""
Script to set up OHLCV database tables.
Run this to create the required tables for OHLCV data collection.
"""
import sys
from app.utils.database import db_connection
from app.utils.logger import logger

def setup_tables():
    """Create OHLCV tables from schema file."""
    
    # Read the schema file (from project root)
    import os
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    schema_path = os.path.join(project_root, "supabase", "ohlcv_schema.sql")
    try:
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
    except FileNotFoundError:
        logger.error(f"Schema file not found: {schema_path}")
        logger.info("Make sure you're running from the project root directory")
        return False
    
    # Execute the entire SQL file at once
    # psycopg2 can handle multiple statements separated by semicolons
    logger.info("Executing SQL schema...")
    
    try:
        # Get a connection from the pool
        conn = db_connection.get_connection()
        cursor = conn.cursor()
        
        # Execute the entire schema
        cursor.execute(schema_sql)
        conn.commit()
        
        cursor.close()
        db_connection.return_connection(conn)
        
        logger.info("✓ SQL schema executed successfully")
        
    except Exception as e:
        error_msg = str(e)
        # Some errors are expected (e.g., table already exists)
        if "already exists" in error_msg.lower():
            logger.info("✓ Tables already exist (this is OK)")
        else:
            logger.error(f"Error executing schema: {error_msg}")
            raise
    
    # Test that tables exist
    logger.info("\nVerifying tables...")
    test_query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name IN ('token_pairs', 'ohlcv_candles', 'price_ticks', 'technical_indicators')
        ORDER BY table_name
    """
    tables = db_connection.execute_query(test_query, fetch_all=True)
    
    if tables:
        logger.info("✓ Tables verified:")
        for table in tables:
            logger.info(f"  - {table['table_name']}")
        return True
    else:
        logger.error("✗ Tables not found after setup")
        return False

if __name__ == "__main__":
    logger.info("Setting up OHLCV database tables...")
    logger.info("=" * 50)
    
    if not db_connection.pool:
        logger.error("Database connection not available. Check your DATABASE_URL in .env")
        sys.exit(1)
    
    success = setup_tables()
    
    if success:
        logger.info("\n" + "=" * 50)
        logger.info("✓ OHLCV tables setup complete!")
        logger.info("You can now register token pairs and start data collection.")
        sys.exit(0)
    else:
        logger.error("\n" + "=" * 50)
        logger.error("✗ Setup failed. Check errors above.")
        sys.exit(1)

