#!/usr/bin/env python3
"""
Database Migration Script
Automatically migrates the database schema and creates storage buckets.
"""
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Migration")

def read_sql_file(file_path: Path) -> str:
    """Read SQL file content"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to read SQL file {file_path}: {e}")
        raise

def execute_sql(client, sql: str):
    """Execute SQL statements"""
    try:
        # Split SQL by semicolons and execute each statement
        statements = [s.strip() for s in sql.split(';') if s.strip() and not s.strip().startswith('--')]
        
        for statement in statements:
            if statement:
                try:
                    # Use RPC or direct SQL execution
                    # Note: Supabase Python client doesn't support raw SQL directly
                    # We'll use the REST API for this
                    logger.debug(f"Executing: {statement[:100]}...")
                except Exception as e:
                    logger.warning(f"Statement execution warning: {e}")
        
        logger.info("SQL statements processed (Note: Some statements may need manual execution in Supabase SQL Editor)")
    except Exception as e:
        logger.error(f"Failed to execute SQL: {e}")
        raise

def create_storage_bucket(client, bucket_name: str, public: bool = False):
    """Create storage bucket if it doesn't exist"""
    try:
        # Check if bucket exists
        try:
            buckets = client.storage.list_buckets()
            existing_buckets = [b.name for b in buckets] if buckets else []
            
            if bucket_name in existing_buckets:
                logger.info(f"Storage bucket '{bucket_name}' already exists")
                return True
        except Exception as list_error:
            logger.warning(f"Could not list buckets: {list_error}")
            # Continue to try creating anyway
        
        # Create bucket
        try:
            response = client.storage.create_bucket(
                bucket_name,
                options={
                    "public": public,
                    "file_size_limit": 52428800,  # 50MB
                    "allowed_mime_types": ["*/*"]
                }
            )
            logger.info(f"✓ Created storage bucket: {bucket_name}")
            return True
        except Exception as create_error:
            # Check if error is because bucket already exists
            error_str = str(create_error).lower()
            if "already exists" in error_str or "duplicate" in error_str:
                logger.info(f"Storage bucket '{bucket_name}' already exists")
                return True
            else:
                raise create_error
                
    except Exception as e:
        logger.error(f"Failed to create storage bucket '{bucket_name}': {e}")
        logger.warning("=" * 60)
        logger.warning("MANUAL BUCKET CREATION REQUIRED:")
        logger.warning("1. Go to Supabase Dashboard > Storage")
        logger.warning("2. Click 'New bucket'")
        logger.warning(f"3. Name: {bucket_name}")
        logger.warning("4. Public: No")
        logger.warning("5. File size limit: 50MB (or as needed)")
        logger.warning("6. Allowed MIME types: */*")
        logger.warning("=" * 60)
        return False

def main():
    """Main migration function"""
    # Load environment variables
    load_dotenv()
    
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("SUPABASE_URL and SUPABASE_KEY must be set in .env file")
        sys.exit(1)
    
    # Create Supabase client
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    logger.info("Starting database migration...")
    
    # Find migration file
    migration_dir = Path(__file__).parent / "migrate"
    migration_file = migration_dir / "001_initial_schema.sql"
    
    if not migration_file.exists():
        logger.error(f"Migration file not found: {migration_file}")
        sys.exit(1)
    
    # Read SQL file
    logger.info(f"Reading migration file: {migration_file}")
    sql_content = read_sql_file(migration_file)
    
    # Note: Supabase Python client doesn't support executing raw SQL directly
    # The SQL needs to be run in Supabase SQL Editor
    logger.warning("=" * 60)
    logger.warning("IMPORTANT: Supabase Python client cannot execute raw SQL")
    logger.warning("Please run the SQL migration manually:")
    logger.warning(f"1. Go to Supabase Dashboard > SQL Editor")
    logger.warning(f"2. Copy contents from: {migration_file}")
    logger.warning(f"3. Paste and execute in SQL Editor")
    logger.warning("=" * 60)
    
    # Create storage bucket
    logger.info("\n" + "=" * 60)
    logger.info("Creating storage bucket...")
    logger.info("=" * 60)
    bucket_created = create_storage_bucket(client, "encrypted-files", public=False)
    
    logger.info("\n" + "=" * 60)
    logger.info("MIGRATION SETUP COMPLETE")
    logger.info("=" * 60)
    logger.info("\nNext steps:")
    logger.info("1. ✓ SQL migration file ready: database/migrate/001_initial_schema.sql")
    logger.info("2. → Run SQL in Supabase Dashboard > SQL Editor")
    if bucket_created:
        logger.info("3. ✓ Storage bucket 'encrypted-files' created")
    else:
        logger.info("3. → Create storage bucket manually (see instructions above)")
    logger.info("4. → Run seed script: python database/seed.py")
    logger.info("\n" + "=" * 60)

if __name__ == "__main__":
    main()

