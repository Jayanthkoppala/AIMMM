"""
Test script to verify PostgreSQL database connection.
Run with: python test_db_connection.py
"""
import psycopg2
from dotenv import load_dotenv
import os
from app.config import settings
from app.utils.logger import logger

# Load environment variables from .env
load_dotenv()

def test_connection_with_individual_settings():
    """Test connection using individual environment variables."""
    user = os.getenv("DB_USER") or getattr(settings, 'DB_USER', '')
    password = os.getenv("DB_PASSWORD") or getattr(settings, 'DB_PASSWORD', '')
    host = os.getenv("DB_HOST") or getattr(settings, 'DB_HOST', '')
    port = os.getenv("DB_PORT") or getattr(settings, 'DB_PORT', '5432')
    dbname = os.getenv("DB_NAME") or getattr(settings, 'DB_NAME', '')
    
    if not all([user, password, host, dbname]):
        logger.warning("Individual DB settings not configured")
        return False
    
    try:
        connection = psycopg2.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            dbname=dbname
        )
        logger.info("✓ Connection successful using individual settings!")
        
        cursor = connection.cursor()
        cursor.execute("SELECT NOW();")
        result = cursor.fetchone()
        logger.info(f"✓ Current database time: {result[0]}")
        
        cursor.close()
        connection.close()
        logger.info("✓ Connection closed successfully")
        return True
        
    except Exception as e:
        logger.error(f"✗ Failed to connect with individual settings: {e}")
        return False


def test_connection_with_database_url():
    """Test connection using DATABASE_URL."""
    database_url = os.getenv("DATABASE_URL") or getattr(settings, 'DATABASE_URL', '')
    
    if not database_url:
        logger.warning("DATABASE_URL not configured")
        return False
    
    try:
        connection = psycopg2.connect(database_url)
        logger.info("✓ Connection successful using DATABASE_URL!")
        
        cursor = connection.cursor()
        cursor.execute("SELECT NOW();")
        result = cursor.fetchone()
        logger.info(f"✓ Current database time: {result[0]}")
        
        # Test query to check tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            LIMIT 5;
        """)
        tables = cursor.fetchall()
        if tables:
            logger.info(f"✓ Found {len(tables)} tables in database")
            for table in tables:
                logger.info(f"  - {table[0]}")
        
        cursor.close()
        connection.close()
        logger.info("✓ Connection closed successfully")
        return True
        
    except Exception as e:
        logger.error(f"✗ Failed to connect with DATABASE_URL: {e}")
        return False


def test_connection_with_supabase_url():
    """Test connection using Supabase URL and key (if available)."""
    supabase_url = os.getenv("SUPABASE_URL") or getattr(settings, 'SUPABASE_URL', '')
    
    if not supabase_url:
        logger.warning("SUPABASE_URL not configured")
        return False
    
    # Extract database connection info from Supabase URL
    # Supabase URL format: https://xxx.supabase.co
    # Database host: db.xxx.supabase.co
    # This is a fallback - prefer DATABASE_URL
    logger.info("Note: Use DATABASE_URL for direct PostgreSQL connection")
    return False


if __name__ == "__main__":
    logger.info("Testing database connection...")
    logger.info("=" * 50)
    
    # Try DATABASE_URL first (recommended)
    success = test_connection_with_database_url()
    
    # Fallback to individual settings
    if not success:
        logger.info("\nTrying individual settings...")
        success = test_connection_with_individual_settings()
    
    if not success:
        logger.error("\n✗ All connection methods failed!")
        logger.info("\nTo fix:")
        logger.info("1. Create .env file: cp .env.example .env")
        logger.info("2. Edit .env and add DATABASE_URL:")
        logger.info("   DATABASE_URL=postgresql://postgres:[PASSWORD]@db.xxx.supabase.co:5432/postgres")
        logger.info("3. Or add individual settings: DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME")
        exit(1)
    else:
        logger.info("\n✓ Database connection test completed successfully!")

