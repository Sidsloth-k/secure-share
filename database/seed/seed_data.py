#!/usr/bin/env python3
"""
Seed script for Secure Share application.
This script creates users and an organization with those users.
"""

import os
import sys
import getpass
import datetime
import logging
from typing import List
from dotenv import load_dotenv
from supabase import create_client

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("SecureShare")

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error("SUPABASE_URL and SUPABASE_KEY must be set in the environment")
    sys.exit(1)

# Use service role key if available (bypasses RLS for admin operations)
# Otherwise use anon key (will need to work with RLS policies)
HAS_SERVICE_ROLE = bool(SUPABASE_SERVICE_ROLE_KEY)
if HAS_SERVICE_ROLE:
    logger.info("Using service role key for seeding (bypasses RLS)")
    client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
else:
    logger.warning("Service role key not found. Using anon key (may have RLS restrictions)")
    client = create_client(SUPABASE_URL, SUPABASE_KEY)


def create_users(emails: List[str], password: str) -> List[dict]:
    """Create users with the provided emails and password."""
    created_users = []
    
    print(f"\nCreating {len(emails)} users...")
    
    for email in emails:
        try:
            # Register user in Supabase Auth
            response = client.auth.sign_up({
                "email": email,
                "password": password
            })
            
            if response and response.user:
                user_id = response.user.id
                
                # Create user profile in database
                user_data = {
                    'id': user_id,
                    'email': email,
                    'display_name': email.split('@')[0],  # Use email prefix as display name
                    'created_at': datetime.datetime.now().isoformat(),
                    'cloud_connected': False
                }
                
                result = client.table('users').insert(user_data).execute()
                
                if result.data:
                    created_users.append({
                        'id': user_id,
                        'email': email,
                        'display_name': user_data['display_name']
                    })
                    print(f"✓ Created user: {email}")
                else:
                    logger.warning(f"Failed to create profile for user: {email}")
            else:
                logger.warning(f"Failed to register user: {email}")
                
        except Exception as e:
            logger.error(f"Error creating user {email}: {e}")
            # Check if user already exists
            if "already registered" in str(e).lower() or "user already exists" in str(e).lower():
                print(f"⚠ User {email} already exists, fetching existing user...")
                try:
                    existing_user = None
                    user_id = None
                    
                    # First, try to get user from auth.users using admin API (if service role available)
                    if HAS_SERVICE_ROLE:
                        try:
                            # List all users and find by email
                            auth_users_response = client.auth.admin.list_users()
                            # list_users() returns a list directly, not an object with .users attribute
                            auth_users = auth_users_response if isinstance(auth_users_response, list) else getattr(auth_users_response, 'users', [])
                            for auth_user in auth_users:
                                # Handle both dict and object formats
                                user_email = auth_user.email if hasattr(auth_user, 'email') else auth_user.get('email')
                                if user_email == email:
                                    user_id = auth_user.id if hasattr(auth_user, 'id') else auth_user.get('id')
                                    # Update password immediately
                                    try:
                                        client.auth.admin.update_user_by_id(user_id, {"password": password})
                                        print(f"✓ Updated password for existing user: {email}")
                                    except Exception as update_error:
                                        logger.error(f"Failed to update password for {email}: {update_error}")
                                        print(f"⚠ Failed to update password for {email}: {update_error}")
                                    break
                        except Exception as auth_error:
                            logger.warning(f"Could not fetch from auth.users: {auth_error}")
                    
                    # Try to fetch existing user from public.users table
                    user_response = client.table('users').select('*').eq('email', email).execute()
                    
                    if user_response.data:
                        # User exists in public.users table
                        existing_user = user_response.data[0]
                        user_id = existing_user['id']
                    elif user_id:
                        # User exists in auth but not in public.users - create profile
                        print(f"⚠ User exists in auth but not in public.users, creating profile...")
                        user_data = {
                            'id': user_id,
                            'email': email,
                            'display_name': email.split('@')[0],
                            'created_at': datetime.datetime.now().isoformat(),
                            'cloud_connected': False
                        }
                        try:
                            result = client.table('users').insert(user_data).execute()
                            if result.data:
                                existing_user = result.data[0]
                                print(f"✓ Created profile for existing auth user: {email}")
                            else:
                                # Create dict manually if insert didn't return data
                                existing_user = user_data
                        except Exception as insert_error:
                            logger.error(f"Failed to create profile: {insert_error}")
                            # Still proceed with user_id if we have it
                            if user_id:
                                existing_user = {
                                    'id': user_id,
                                    'email': email,
                                    'display_name': email.split('@')[0]
                                }
                    else:
                        # User might exist but we can't find them - try to get from auth if we haven't already
                        if not user_id and HAS_SERVICE_ROLE:
                            try:
                                auth_users_response = client.auth.admin.list_users()
                                # list_users() returns a list directly, not an object with .users attribute
                                auth_users = auth_users_response if isinstance(auth_users_response, list) else getattr(auth_users_response, 'users', [])
                                for auth_user in auth_users:
                                    # Handle both dict and object formats
                                    user_email = auth_user.email if hasattr(auth_user, 'email') else auth_user.get('email')
                                    if user_email == email:
                                        user_id = auth_user.id if hasattr(auth_user, 'id') else auth_user.get('id')
                                        # Update password
                                        try:
                                            client.auth.admin.update_user_by_id(user_id, {"password": password})
                                            print(f"✓ Updated password for existing user: {email}")
                                        except Exception as update_error:
                                            logger.error(f"Failed to update password: {update_error}")
                                        # Create profile
                                        user_data = {
                                            'id': user_id,
                                            'email': email,
                                            'display_name': email.split('@')[0],
                                            'created_at': datetime.datetime.now().isoformat(),
                                            'cloud_connected': False
                                        }
                                        try:
                                            result = client.table('users').insert(user_data).execute()
                                            existing_user = result.data[0] if result.data else user_data
                                            print(f"✓ Created profile for existing auth user: {email}")
                                        except Exception as insert_error:
                                            logger.error(f"Failed to create profile: {insert_error}")
                                            existing_user = user_data
                                        break
                            except Exception as auth_error:
                                logger.error(f"Could not fetch from auth.users: {auth_error}")
                    
                    if existing_user or user_id:
                        created_users.append({
                            'id': user_id or (existing_user['id'] if existing_user else None),
                            'email': email,
                            'display_name': (existing_user.get('display_name') if existing_user else email.split('@')[0]) if existing_user else email.split('@')[0]
                        })
                        print(f"✓ Found/created user: {email}")
                    else:
                        logger.error(f"Could not find or create user profile for {email}")
                        print(f"⚠ Could not process existing user: {email}")
                        
                except Exception as fetch_error:
                    logger.error(f"Failed to fetch existing user {email}: {fetch_error}")
                    print(f"⚠ Error processing existing user {email}: {fetch_error}")
    
    return created_users


def create_organization(users: List[dict], org_name: str = None) -> dict:
    """Create an organization with the provided users."""
    if not users:
        raise ValueError("Cannot create organization without users")
    
    if not org_name:
        org_name = f"Organization_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Use first user as admin
    admin = users[0]
    
    print(f"\nCreating organization: {org_name}")
    print(f"Admin: {admin['email']}")
    print(f"Members: {len(users)}")
    
    # Generate invite code
    import uuid
    invite_code = str(uuid.uuid4())[:8].upper()
    invite_expires_at = datetime.datetime.now() + datetime.timedelta(days=20)
    
    # Create organization
    org_data = {
        'name': org_name,
        'invite_code': invite_code,
        'invite_code_expires_at': invite_expires_at.isoformat(),
        'invite_enabled': True,
        'admin_id': admin['id'],
        'member_count': len(users),
        'created_at': datetime.datetime.now().isoformat(),
        'updated_at': datetime.datetime.now().isoformat()
    }
    
    try:
        org_result = client.table('organizations').insert(org_data).execute()
        
        if not org_result.data:
            raise Exception("Failed to create organization: No data returned")
        
        org = org_result.data[0]
        org_id = org['id']
        
        print(f"✓ Created organization: {org['name']} (ID: {org_id})")
        print(f"  Invite code: {invite_code}")
        
    except Exception as e:
        error_msg = str(e)
        if 'row-level security' in error_msg.lower() or '42501' in error_msg:
            logger.error("RLS policy violation. Ensure SUPABASE_SERVICE_ROLE_KEY is set in .env")
            logger.error("Service role key bypasses RLS policies.")
        logger.error(f"Failed to create organization: {e}")
        raise
    
    # Add all users as members
    print(f"\nAdding {len(users)} members to organization...")
    
    failed_members = []
    for i, user in enumerate(users):
        member_data = {
            'organization_id': org_id,
            'user_id': user['id'],
            'joined_at': datetime.datetime.now().isoformat(),
            'role': 'admin' if i == 0 else 'member',
            'status': 'active'
        }
        
        try:
            client.table('organization_members').insert(member_data).execute()
            role_label = "admin" if i == 0 else "member"
            print(f"✓ Added {user['email']} as {role_label}")
        except Exception as e:
            logger.error(f"Failed to add member {user['email']}: {e}")
            failed_members.append(user['email'])
    
    if failed_members:
        logger.warning(f"Failed to add {len(failed_members)} members: {', '.join(failed_members)}")
        if len(failed_members) == len(users):
            raise Exception("Failed to add any members to organization. Cannot proceed.")
    
    # Create audit log
    try:
        audit_data = {
            'user_id': admin['id'],
            'organization_id': org_id,
            'action': 'organization_created',
            'timestamp': datetime.datetime.now().isoformat(),
            'details': {'name': org_name, 'member_count': len(users)}
        }
        client.table('audit_logs').insert(audit_data).execute()
    except Exception as e:
        logger.warning(f"Failed to create audit log: {e}")
    
    return org


def create_s3_bucket():
    """Create S3 bucket for encrypted files using Supabase Storage API."""
    bucket_name = "encrypted-files"
    
    try:
        # First try using Supabase Storage API
        print(f"\nCreating storage bucket: {bucket_name}...")
        
        # Check if bucket exists
        try:
            buckets = client.storage.list_buckets()
            existing_buckets = [b.name for b in buckets]
            
            if bucket_name in existing_buckets:
                print(f"✓ Storage bucket '{bucket_name}' already exists")
                return True
            
            # Create bucket using Supabase Storage API
            result = client.storage.create_bucket(
                bucket_name,
                options={
                    "public": False,
                    "file_size_limit": 52428800,  # 50MB
                    "allowed_mime_types": None
                }
            )
            
            print(f"✓ Created storage bucket: {bucket_name}")
            return True
            
        except Exception as api_error:
            logger.warning(f"Failed to create bucket via Supabase API: {api_error}")
            
            # Fallback to boto3 if credentials are available
            try:
                import boto3
                from botocore.exceptions import ClientError
                
                # Get S3 credentials from environment
                s3_access_key = os.getenv("S3_ACCESS_KEY_ID")
                s3_secret_key = os.getenv("S3_SECRET_ACCESS_KEY")
                s3_endpoint = os.getenv("S3_ENDPOINT")
                s3_region = os.getenv("S3_REGION", "eu-north-1")
                
                if not all([s3_access_key, s3_secret_key, s3_endpoint]):
                    logger.warning("S3 credentials not found in environment. Skipping bucket creation.")
                    logger.warning("Please create the 'encrypted-files' bucket manually in Supabase Storage.")
                    return False
                
                print(f"Trying to create bucket using S3 API...")
                
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
                    print(f"✓ Bucket '{bucket_name}' already exists")
                    return True
                except ClientError as e:
                    error_code = e.response['Error']['Code']
                    if error_code == '404':
                        # Bucket doesn't exist, create it
                        try:
                            s3_client.create_bucket(Bucket=bucket_name)
                            print(f"✓ Created bucket: {bucket_name}")
                            return True
                        except ClientError as create_error:
                            logger.error(f"Failed to create bucket: {create_error}")
                            return False
                    else:
                        logger.error(f"Error checking bucket: {e}")
                        return False
                        
            except ImportError:
                logger.warning("boto3 not installed. Skipping S3 bucket creation.")
                logger.warning("Install boto3 with: pip install boto3")
                logger.warning("Please create the 'encrypted-files' bucket manually in Supabase Storage.")
                return False
            except Exception as boto_error:
                logger.error(f"Error creating S3 bucket with boto3: {boto_error}")
                return False
                
    except Exception as e:
        logger.error(f"Error creating storage bucket: {e}")
        logger.warning("Please create the 'encrypted-files' bucket manually in Supabase Storage.")
        return False


def main():
    """Main seed function."""
    print("=" * 60)
    print("Secure Share - Database Seeding")
    print("=" * 60)
    
    # Get user emails
    print("\nEnter email addresses for users to seed (one per line).")
    print("Press Enter on an empty line when done.")
    print("Minimum 5 users required for encryption eligibility.")
    
    emails = []
    while True:
        email = input(f"Email {len(emails) + 1} (or press Enter to finish): ").strip()
        if not email:
            if len(emails) < 5:
                print(f"\n⚠ Warning: You have {len(emails)} users. Minimum 5 users are required for encryption eligibility.")
                continue_anyway = input("Continue anyway? (y/n): ").strip().lower()
                if continue_anyway != 'y':
                    continue
            break
        if '@' not in email:
            print("⚠ Invalid email format. Please try again.")
            continue
        if email in emails:
            print("⚠ Email already entered. Please try again.")
            continue
        emails.append(email)
    
    if not emails:
        print("No emails provided. Exiting.")
        sys.exit(1)
    
    # Get password
    print(f"\nEnter password for all users (same password will be used for all):")
    password = getpass.getpass("Password: ")
    password_confirm = getpass.getpass("Confirm Password: ")
    
    if password != password_confirm:
        print("❌ Passwords do not match. Exiting.")
        sys.exit(1)
    
    if len(password) < 6:
        print("⚠ Warning: Password is less than 6 characters. Supabase requires at least 6 characters.")
        continue_anyway = input("Continue anyway? (y/n): ").strip().lower()
        if continue_anyway != 'y':
            sys.exit(1)
    
    # Get organization name
    org_name = input(f"\nEnter organization name (or press Enter for default): ").strip()
    if not org_name:
        org_name = None
    
    # Create users
    try:
        users = create_users(emails, password)
        
        if not users:
            print("❌ Failed to create any users. Exiting.")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Critical error creating users: {e}")
        print(f"❌ Critical error: {e}")
        print("Exiting.")
        sys.exit(1)
    
    print(f"\n✓ Successfully created {len(users)} users")
    
    # Create organization
    try:
        org = create_organization(users, org_name)
        print(f"\n✓ Successfully created organization: {org['name']}")
        print(f"  Organization ID: {org['id']}")
        print(f"  Invite Code: {org['invite_code']}")
    except Exception as e:
        logger.error(f"Failed to create organization: {e}")
        print(f"\n❌ Failed to create organization: {e}")
        print("\nThis is a critical error. Exiting.")
        sys.exit(1)
    
    # Create S3 bucket
    bucket_created = create_s3_bucket()
    
    print("\n" + "=" * 60)
    print("Seeding completed!")
    print("=" * 60)
    print(f"\nSummary:")
    print(f"  - Users created: {len(users)}")
    print(f"  - Organization: {org['name']}")
    print(f"  - S3 Bucket: {'Created' if bucket_created else 'Please create manually'}")
    print(f"\nNote: Cloud storage connection is left for manual setup.")
    print(f"Users can connect their cloud storage through the application.")


if __name__ == "__main__":
    main()

