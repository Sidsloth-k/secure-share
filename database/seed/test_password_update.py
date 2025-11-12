#!/usr/bin/env python3
"""
Test script to verify password updates for existing users.
Run this to check if password updates are working correctly.
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("❌ SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    sys.exit(1)

client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def test_password_update(email: str, new_password: str):
    """Test updating password for a user."""
    print(f"\nTesting password update for: {email}")
    print("=" * 60)
    
    # 1. Check if user exists in auth.users
    print("1. Checking auth.users...")
    try:
        auth_users_response = client.auth.admin.list_users()
        # list_users() returns a list directly, not an object with .users attribute
        auth_users = auth_users_response if isinstance(auth_users_response, list) else getattr(auth_users_response, 'users', [])
        user_id = None
        for auth_user in auth_users:
            # Handle both dict and object formats
            user_email = auth_user.email if hasattr(auth_user, 'email') else auth_user.get('email')
            if user_email == email:
                user_id = auth_user.id if hasattr(auth_user, 'id') else auth_user.get('id')
                print(f"   ✓ Found in auth.users: {user_id}")
                break
        
        if not user_id:
            print(f"   ❌ User not found in auth.users")
            return False
    except Exception as e:
        print(f"   ❌ Error checking auth.users: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 2. Update password
    print("2. Updating password...")
    try:
        result = client.auth.admin.update_user_by_id(user_id, {"password": new_password})
        print(f"   ✓ Password updated successfully")
        print(f"   User ID: {result.user.id if hasattr(result, 'user') else user_id}")
    except Exception as e:
        print(f"   ❌ Failed to update password: {e}")
        return False
    
    # 3. Check if user exists in public.users
    print("3. Checking public.users table...")
    try:
        user_response = client.table('users').select('*').eq('email', email).execute()
        if user_response.data:
            print(f"   ✓ Found in public.users table")
            print(f"   User ID: {user_response.data[0]['id']}")
        else:
            print(f"   ⚠ User not found in public.users table (exists only in auth)")
    except Exception as e:
        print(f"   ⚠ Error checking public.users: {e}")
    
    print("\n✅ Password update test completed!")
    print(f"   You can now try logging in with email: {email}")
    print(f"   Password: {new_password}")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python test_password_update.py <email> <new_password>")
        print("\nExample:")
        print("  python test_password_update.py user@example.com MyNewPassword123")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    
    test_password_update(email, password)

