#!/usr/bin/env python3
"""
Database Seed Script
Creates test users and a sample organization with all requirements met.
"""
import os
import sys
import uuid
import datetime
import logging
import getpass
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Seed")

# Minimum organization members required
MIN_ORG_MEMBERS = 5

def get_user_input(prompt: str, required: bool = True) -> str:
    """Get user input with validation"""
    while True:
        value = input(prompt).strip()
        if value or not required:
            return value
        print(f"{Fore.RED}This field is required{Style.RESET_ALL}")

def create_user(client, email: str, password: str, display_name: str) -> dict:
    """Create a user in Supabase Auth and database"""
    try:
        # Register user in Supabase Auth
        auth_response = client.auth.sign_up({
            "email": email,
            "password": password
        })
        
        if not auth_response.user:
            raise Exception("Failed to create user in Auth")
        
        user_id = auth_response.user.id
        
        # Create user profile in database
        user_data = {
            'id': user_id,
            'email': email,
            'display_name': display_name,
            'cloud_connected': False,  # Users will connect cloud storage manually
            'created_at': datetime.datetime.now().isoformat(),
            'updated_at': datetime.datetime.now().isoformat()
        }
        
        response = client.table('users').insert(user_data).execute()
        
        if not response.data:
            raise Exception("Failed to create user profile")
        
        logger.info(f"Created user: {email} ({display_name})")
        return response.data[0]
    
    except Exception as e:
        logger.error(f"Failed to create user {email}: {e}")
        # Check if user already exists
        if "already registered" in str(e).lower() or "already exists" in str(e).lower():
            logger.warning(f"User {email} already exists, fetching existing user...")
            # Try to get existing user
            user_response = client.table('users').select('*').eq('email', email).execute()
            if user_response.data:
                return user_response.data[0]
        raise

def create_organization(client, name: str, admin_id: str, member_ids: list) -> dict:
    """Create an organization with members"""
    try:
        # Generate invite code
        invite_code = str(uuid.uuid4())[:8].upper()
        invite_expires_at = datetime.datetime.now() + datetime.timedelta(days=20)
        
        # Create organization
        org_data = {
            'name': name,
            'invite_code': invite_code,
            'invite_code_expires_at': invite_expires_at.isoformat(),
            'invite_enabled': True,
            'admin_id': admin_id,
            'member_count': len(member_ids),
            'created_at': datetime.datetime.now().isoformat(),
            'updated_at': datetime.datetime.now().isoformat()
        }
        
        response = client.table('organizations').insert(org_data).execute()
        
        if not response.data:
            raise Exception("Failed to create organization")
        
        org = response.data[0]
        org_id = org['id']
        
        # Add all members to organization
        members_data = []
        for i, member_id in enumerate(member_ids):
            role = 'admin' if member_id == admin_id else 'member'
            members_data.append({
                'organization_id': org_id,
                'user_id': member_id,
                'joined_at': datetime.datetime.now().isoformat(),
                'role': role,
                'status': 'active'
            })
        
        # Insert all members at once
        client.table('organization_members').insert(members_data).execute()
        
        logger.info(f"Created organization: {name} with {len(member_ids)} members")
        logger.info(f"Invite code: {Fore.YELLOW}{invite_code}{Style.RESET_ALL}")
        
        return org
    
    except Exception as e:
        logger.error(f"Failed to create organization: {e}")
        raise

def main():
    """Main seed function"""
    print(f"{Fore.CYAN}===== DATABASE SEED SCRIPT ====={Style.RESET_ALL}\n")
    
    # Load environment variables
    load_dotenv()
    
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("SUPABASE_URL and SUPABASE_KEY must be set in .env file")
        sys.exit(1)
    
    # Create Supabase client
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print(f"{Fore.YELLOW}This script will create test users and a sample organization.{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Minimum {MIN_ORG_MEMBERS} members are required for encryption eligibility.{Style.RESET_ALL}\n")
    
    # Get organization name
    org_name = get_user_input("Enter organization name: ")
    
    # Get number of users to create
    while True:
        try:
            num_users = int(get_user_input(f"Enter number of users to create (minimum {MIN_ORG_MEMBERS}): "))
            if num_users < MIN_ORG_MEMBERS:
                print(f"{Fore.RED}At least {MIN_ORG_MEMBERS} users are required{Style.RESET_ALL}")
                continue
            break
        except ValueError:
            print(f"{Fore.RED}Please enter a valid number{Style.RESET_ALL}")
    
    # Get common password
    print(f"\n{Fore.YELLOW}All users will have the same password for testing.{Style.RESET_ALL}")
    password = getpass.getpass("Enter password for all users: ")
    password_confirm = getpass.getpass("Confirm password: ")
    
    if password != password_confirm:
        print(f"{Fore.RED}Passwords do not match{Style.RESET_ALL}")
        sys.exit(1)
    
    if len(password) < 6:
        print(f"{Fore.RED}Password must be at least 6 characters{Style.RESET_ALL}")
        sys.exit(1)
    
    # Get user emails
    print(f"\n{Fore.CYAN}Enter email addresses for {num_users} users:{Style.RESET_ALL}")
    emails = []
    for i in range(num_users):
        email = get_user_input(f"User {i+1} email: ")
        if email in emails:
            print(f"{Fore.RED}Email already entered. Please enter a different email.{Style.RESET_ALL}")
            i -= 1
            continue
        emails.append(email)
    
    # Get display names
    print(f"\n{Fore.CYAN}Enter display names for users:{Style.RESET_ALL}")
    display_names = []
    for i, email in enumerate(emails):
        # Extract name from email as default
        default_name = email.split('@')[0].replace('.', ' ').title()
        name_prompt = f"User {i+1} display name ({default_name}): "
        name = get_user_input(name_prompt, required=False)
        if not name:
            name = default_name
        display_names.append(name)
    
    # Confirm
    print(f"\n{Fore.CYAN}Summary:{Style.RESET_ALL}")
    print(f"Organization: {Fore.YELLOW}{org_name}{Style.RESET_ALL}")
    print(f"Users to create: {Fore.YELLOW}{num_users}{Style.RESET_ALL}")
    print("\nUsers:")
    for i, (email, name) in enumerate(zip(emails, display_names), 1):
        print(f"  {i}. {name} ({email})")
    
    confirm = input(f"\n{Fore.YELLOW}Proceed with seeding? (y/n): {Style.RESET_ALL}").lower()
    if confirm != 'y':
        print(f"{Fore.RED}Seeding cancelled{Style.RESET_ALL}")
        sys.exit(0)
    
    # Create users
    print(f"\n{Fore.CYAN}Creating users...{Style.RESET_ALL}")
    users = []
    for email, display_name in zip(emails, display_names):
        try:
            user = create_user(client, email, password, display_name)
            users.append(user)
        except Exception as e:
            logger.error(f"Skipping user {email}: {e}")
            # Continue with other users
    
    if len(users) < MIN_ORG_MEMBERS:
        print(f"{Fore.RED}Failed to create enough users. Need at least {MIN_ORG_MEMBERS}, got {len(users)}{Style.RESET_ALL}")
        sys.exit(1)
    
    # Create organization
    print(f"\n{Fore.CYAN}Creating organization...{Style.RESET_ALL}")
    admin_id = users[0]['id']
    member_ids = [user['id'] for user in users]
    
    try:
        org = create_organization(client, org_name, admin_id, member_ids)
        
        print(f"\n{Fore.GREEN}✓ Seeding completed successfully!{Style.RESET_ALL}")
        print(f"\n{Fore.CYAN}Organization Details:{Style.RESET_ALL}")
        print(f"  Name: {org['name']}")
        print(f"  ID: {org['id']}")
        print(f"  Members: {org['member_count']}")
        print(f"  Invite Code: {Fore.YELLOW}{org['invite_code']}{Style.RESET_ALL}")
        
        print(f"\n{Fore.CYAN}User Credentials:{Style.RESET_ALL}")
        print(f"  All users have password: {Fore.YELLOW}{'*' * len(password)}{Style.RESET_ALL}")
        print(f"\n  Users:")
        for user in users:
            print(f"    - {user['display_name']} ({user['email']})")
        
        print(f"\n{Fore.YELLOW}Note: Users need to connect cloud storage manually to meet encryption requirements.{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Once all users connect cloud storage, the organization will be eligible for encryption.{Style.RESET_ALL}")
        
    except Exception as e:
        logger.error(f"Failed to create organization: {e}")
        print(f"{Fore.RED}Seeding failed: {e}{Style.RESET_ALL}")
        sys.exit(1)

if __name__ == "__main__":
    main()

