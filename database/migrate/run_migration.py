#!/usr/bin/env python3
"""
Migration runner script for Secure Share application.
This script automatically runs SQL migrations against the Supabase database.
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("SecureShare")

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
DATABASE_URL = os.getenv("SUPABASE_DB_URL")  # Direct PostgreSQL connection string

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error("SUPABASE_URL and SUPABASE_KEY must be set in the environment")
    sys.exit(1)


def get_database_connection():
    """Get direct PostgreSQL connection from Supabase URL."""
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    except ImportError:
        logger.error("psycopg2-binary is required for migrations. Install it with: pip install psycopg2-binary")
        sys.exit(1)
    
    if DATABASE_URL:
        # Use direct database URL if provided
        try:
            return psycopg2.connect(DATABASE_URL)
        except Exception as e:
            logger.error(f"Failed to connect using DATABASE_URL: {e}")
            sys.exit(1)
    
    # Extract database connection info from Supabase URL
    # Supabase URL format: https://project-ref.supabase.co
    # We need to construct the PostgreSQL connection string
    # Format: postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres
    
    # Try to get from environment
    db_password = os.getenv("DATABASE_PASSWORD")
    db_host = os.getenv("DATABASE_HOST")
    
    if not db_password or not db_host:
        logger.error("DATABASE_URL or DATABASE_PASSWORD and DATABASE_HOST must be set")
        logger.error("For Supabase, you can find these in: Project Settings > Database")
        logger.error("Or set DATABASE_URL directly: postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres")
        sys.exit(1)
    
    try:
        conn = psycopg2.connect(
            host=db_host,
            database="postgres",
            user="postgres",
            password=db_password,
            port=5432,
            sslmode="require"
        )
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        logger.error("Please check your database credentials in .env file")
        sys.exit(1)


def run_migration():
    """
    Run all SQL migration files in this directory in alphabetical order.
    
    Files are expected to be named with a numeric prefix, e.g.:
      001_initial_schema.sql
      002_some_change.sql
      003_user_grant_creation.sql
    """
    script_dir = Path(__file__).parent
    sql_files = sorted(script_dir.glob("*.sql"))

    if not sql_files:
        logger.error(f"No .sql migration files found in {script_dir}")
        sys.exit(1)

    logger.info("Connecting to database...")
    try:
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

        conn = get_database_connection()
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        for migration_file in sql_files:
            logger.info(f"Running migration: {migration_file.name}")
            try:
                with open(migration_file, "r", encoding="utf-8") as f:
                    migration_sql = f.read()
                cursor.execute(migration_sql)
                logger.info(f"✓ Migration {migration_file.name} completed successfully")
            except Exception as file_err:
                logger.error(f"Migration {migration_file.name} failed: {file_err}")
                cursor.close()
                conn.close()
                return False

        cursor.close()
        conn.close()
        logger.info("✓ All migrations completed successfully")
        return True

    except ImportError:
        logger.error("psycopg2-binary is required for migrations. Install it with: pip install psycopg2-binary")
        return False
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False


def create_storage_bucket():
    """Create storage bucket using Supabase service role or S3 API."""
    bucket_name = "encrypted-files"
    
    # Try using service role key first (has admin permissions)
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if service_role_key:
        try:
            logger.info(f"Attempting to create bucket using service role key...")
            admin_client = create_client(SUPABASE_URL, service_role_key)
            
            # Check if bucket exists
            buckets = admin_client.storage.list_buckets()
            existing_buckets = [b.name for b in buckets]
            
            if bucket_name in existing_buckets:
                logger.info(f"✓ Storage bucket '{bucket_name}' already exists")
                return True
            
            # Create bucket with service role
            logger.info(f"Creating storage bucket: {bucket_name}...")
            result = admin_client.storage.create_bucket(
                bucket_name,
                options={
                    "public": False,
                    "file_size_limit": 52428800,  # 50MB
                    "allowed_mime_types": None
                }
            )
            
            logger.info(f"✓ Created storage bucket: {bucket_name}")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to create bucket with service role: {e}")
    
    # Fallback to S3 API if credentials are available
    s3_access_key = os.getenv("S3_ACCESS_KEY_ID")
    s3_secret_key = os.getenv("S3_SECRET_ACCESS_KEY")
    s3_endpoint = os.getenv("S3_ENDPOINT")
    s3_region = os.getenv("S3_REGION", "eu-north-1")
    
    if all([s3_access_key, s3_secret_key, s3_endpoint]):
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            logger.info(f"Attempting to create bucket using S3 API...")
            
            # Create S3 client
            s3_client = boto3.client(
                's3',
                endpoint_url=s3_endpoint,
                aws_access_key_id=s3_access_key,
                aws_secret_access_key=s3_secret_key,
                region_name=s3_region
            )
            
            # Check if bucket exists
            try:
                s3_client.head_bucket(Bucket=bucket_name)
                logger.info(f"✓ Storage bucket '{bucket_name}' already exists")
                return True
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == '404':
                    # Bucket doesn't exist, create it
                    try:
                        s3_client.create_bucket(Bucket=bucket_name)
                        logger.info(f"✓ Created storage bucket: {bucket_name}")
                        return True
                    except ClientError as create_error:
                        logger.error(f"Failed to create bucket via S3: {create_error}")
                else:
                    logger.error(f"Error checking bucket: {e}")
                    
        except ImportError:
            logger.warning("boto3 not installed. Install with: pip install boto3")
        except Exception as e:
            logger.warning(f"Failed to create bucket via S3 API: {e}")
    
    # If all methods fail, provide instructions
    logger.warning("=" * 60)
    logger.warning("Could not create storage bucket automatically.")
    logger.warning("Please create it manually:")
    logger.warning("1. Go to Supabase Dashboard > Storage")
    logger.warning("2. Click 'New bucket'")
    logger.warning(f"3. Name: {bucket_name}")
    logger.warning("4. Public: No")
    logger.warning("5. File size limit: 50MB (or as needed)")
    logger.warning("=" * 60)
    logger.warning("Alternatively, set SUPABASE_SERVICE_ROLE_KEY in .env")
    logger.warning("(Find it in: Project Settings > API > service_role key)")
    logger.warning("=" * 60)
    return False


def main():
    """Main migration function."""
    print("=" * 60)
    print("Secure Share - Database Migration")
    print("=" * 60)
    
    # Run SQL migration
    if not run_migration():
        print("❌ Migration failed. Please check the errors above.")
        sys.exit(1)
    
    # Create storage bucket
    create_storage_bucket()
    
    print("\n" + "=" * 60)
    print("Migration completed successfully!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Run the seed script: python database/seed/seed_data.py")
    print("2. Ensure S3 credentials are set in .env file")
    print("3. Create 'encrypted-files' bucket in Supabase Storage if not created automatically")


if __name__ == "__main__":
    main()

