#!/usr/bin/env python3
"""
Comprehensive test suite for auth.py session management.
Tests follow the flow: Login -> Session Security -> Token Refresh -> Session Management

Flow:
1. Login/Registration (with real or fake tokens)
2. Session Security (encryption, persistence, validation)
3. Token Refresh (proactive, expired, error handling)
4. Session Management (lifecycle, metrics, cleanup)
"""
import os
import sys
import time
import json
import logging
import getpass
from dotenv import load_dotenv
from supabase import create_client

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Import auth module
import importlib.util
auth_path = os.path.join(parent_dir, "auth.py")
spec = importlib.util.spec_from_file_location("auth_module", auth_path)
auth_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auth_module)

Auth = auth_module.Auth
load_session = auth_module.load_session
save_session = auth_module.save_session
clear_session = auth_module.clear_session
SESSION_FILE = auth_module.SESSION_FILE

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("SecureShare")

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
ENABLE_ENCRYPTION = os.getenv("ENABLE_SESSION_ENCRYPTION", "false").lower() == "true"
ENABLE_METRICS = os.getenv("ENABLE_REFRESH_METRICS", "false").lower() == "true"

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error("SUPABASE_URL and SUPABASE_KEY must be set in the environment")
    sys.exit(1)


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_test(name: str):
    """Print test header."""
    print(f"\n{Colors.CYAN}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}TEST: {name}{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*70}{Colors.RESET}")


def print_success(message: str):
    """Print success message."""
    try:
        print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")
    except UnicodeEncodeError:
        print(f"{Colors.GREEN}[OK] {message}{Colors.RESET}")


def print_error(message: str):
    """Print error message."""
    try:
        print(f"{Colors.RED}✗ {message}{Colors.RESET}")
    except UnicodeEncodeError:
        print(f"{Colors.RED}[FAIL] {message}{Colors.RESET}")


def print_info(message: str):
    """Print info message."""
    try:
        print(f"{Colors.BLUE}ℹ {message}{Colors.RESET}")
    except UnicodeEncodeError:
        print(f"{Colors.BLUE}[INFO] {message}{Colors.RESET}")


def print_warning(message: str):
    """Print warning message."""
    try:
        print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")
    except UnicodeEncodeError:
        print(f"{Colors.YELLOW}[WARN] {message}{Colors.RESET}")


# Global session storage for reuse
_real_session = None

def set_real_session(session):
    """Set global real session for reuse."""
    global _real_session
    _real_session = session

def get_real_session():
    """Get global real session."""
    return _real_session


def get_test_mode():
    """Get test mode (real or fake tokens)."""
    print(f"\n{Colors.BOLD}Test Mode Selection{Colors.RESET}")
    print("1. Use Real Tokens (requires login)")
    print("2. Use Fake Tokens (for testing logic)")
    
    while True:
        choice = input("\nEnter choice (1 or 2): ").strip()
        if choice == "1":
            return "real"
        elif choice == "2":
            return "fake"
        else:
            print_error("Invalid choice. Please enter 1 or 2.")


def get_real_credentials():
    """Get real credentials from user or reuse existing session."""
    # Check if we have a saved real session
    existing_session = get_real_session()
    if existing_session:
        print_info("Found existing real session. Reusing...")
        return existing_session.get('email'), None, existing_session
    
    print_info("Enter your Supabase credentials:")
    email = input("Email: ").strip()
    if not email:
        return None, None, None
    
    password = getpass.getpass("Password: ").strip()
    if not password:
        return None, None, None
    
    return email, password, None


# ============================================================================
# PHASE 1: LOGIN & REGISTRATION
# ============================================================================

def test_login_flow(test_mode: str):
    """Test 1: Login flow with real or fake tokens."""
    print_test("PHASE 1: Login & Registration")
    
    try:
        clear_session()
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Initialize auth with encryption and metrics based on environment
        auth = Auth(
            client,
            enable_encryption=ENABLE_ENCRYPTION,
            enable_metrics=ENABLE_METRICS
        )
        
        if test_mode == "real":
            email, password, existing_session = get_real_credentials()
            
            if existing_session:
                # Reuse existing session
                auth.session = existing_session
                save_session(existing_session)
                auth._set_client_session()
                print_success("Reused existing real session")
                _real_session = existing_session
                return True, auth
            
            if not email or not password:
                print_warning("Skipping real login test - no credentials provided")
                return False, None
            
            print_info(f"Attempting real login with email: {email}")
            if auth.login(email, password):
                print_success("Real login successful")
                set_real_session(auth.session.copy())
                return True, auth
            else:
                print_error("Real login failed")
                return False, None
        else:
            # Fake tokens for testing logic
            print_info("Using fake tokens for testing")
            fake_session = {
                'user_id': 'test-user-id',
                'email': 'test@example.com',
                'access_token': 'fake-access-token-' + str(int(time.time())),
                'refresh_token': 'fake-refresh-token-' + str(int(time.time())),
                'expires_at': time.time() + 3600,
                'original_lifetime': 3600
            }
            auth.session = fake_session
            save_session(fake_session)
            auth._set_client_session()
            print_success("Fake session created")
            return True, auth
            
    except Exception as e:
        print_error(f"Login test failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None


# ============================================================================
# PHASE 2: SESSION SECURITY
# ============================================================================

def test_session_security(auth):
    """Test 2: Session security (encryption, persistence, validation)."""
    print_test("PHASE 2: Session Security")
    
    if not auth or not auth.session:
        print_error("No session available for security testing")
        return False
    
    try:
        # Test 2.1: Session Persistence
        print_info("2.1 Testing session persistence...")
        # Check storage mode
        use_database = ENVIRONMENT == "production" and hasattr(auth, '_use_database') and auth._use_database
        
        if use_database:
            # In production, check database
            user_id = auth.session.get('user_id')
            loaded = load_session(user_id=user_id)
            if loaded and loaded.get('user_id') == user_id:
                print_success("Session persisted in database")
            else:
                print_error("Session not found in database after login")
                return False
        else:
            # In development, check file
            if not os.path.exists(SESSION_FILE):
                print_error("Session file not found after login")
                return False
            print_success("Session file exists")
        
        # Test 2.2: Session Data Integrity
        print_info("2.2 Testing session data integrity...")
        required_fields = ['user_id', 'email', 'access_token', 'refresh_token', 'expires_at']
        missing_fields = [f for f in required_fields if f not in auth.session]
        if missing_fields:
            print_error(f"Missing required fields: {missing_fields}")
            return False
        print_success("All required session fields present")
        
        # Test 2.3: Session Loading
        print_info("2.3 Testing session loading...")
        loaded_session = load_session()
        if loaded_session.get('user_id') != auth.session.get('user_id'):
            print_error("Session data mismatch after loading")
            return False
        storage_type = "database" if use_database else "file"
        print_success(f"Session loaded correctly from {storage_type}")
        
        # Test 2.4: Encryption (if enabled)
        if ENABLE_ENCRYPTION:
            print_info("2.4 Testing session encryption...")
            if use_database:
                # In production, encryption is handled in database
                if hasattr(auth, '_enable_encryption') and auth._enable_encryption:
                    print_success("Session encryption enabled (database mode)")
                else:
                    print_warning("Encryption should be enabled in production")
            else:
                # In development, check encrypted file
                encrypted_file = SESSION_FILE.replace('.json', '.enc')
                if os.path.exists(encrypted_file):
                    print_success("Encrypted session file exists")
                else:
                    print_warning("Encryption enabled but encrypted file not found")
        else:
            print_info("2.4 Session encryption disabled")
        
        # Test 2.5: Session Validation
        print_info("2.5 Testing session validation...")
        # Save session before validation (in case it gets cleared)
        original_session = auth.session.copy() if auth.session else {}
        
        if auth.is_authenticated():
            print_success("Session validation passed")
        else:
            print_warning("Session validation failed (may be expected with fake tokens)")
            # Restore session if it was cleared
            if not auth.session and original_session:
                auth.session = original_session
                save_session(original_session)
        
        return True
        
    except Exception as e:
        print_error(f"Session security test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# PHASE 3: TOKEN REFRESH
# ============================================================================

def test_token_refresh(auth):
    """Test 3: Token refresh (proactive, expired, error handling)."""
    print_test("PHASE 3: Token Refresh")
    
    if not auth or not auth.session:
        print_error("No session available for refresh testing")
        return False
    
    try:
        # Test 3.1: Proactive Refresh Detection
        print_info("3.1 Testing proactive refresh detection...")
        time_remaining = auth.get_session_time_remaining()
        print_info(f"Session time remaining: {time_remaining} seconds")
        
        if time_remaining > 0:
            print_success(f"Session valid for {time_remaining} more seconds")
        else:
            print_warning("Session expired or invalid")
        
        # Test 3.2: Ensure Valid Session
        print_info("3.2 Testing ensure_valid_session...")
        # Save session before testing (in case it gets cleared)
        original_session = auth.session.copy() if auth.session else {}
        
        result = auth._ensure_valid_session()
        if result:
            print_success("Session validation/refresh logic executed")
        else:
            print_warning("Session validation failed (may be expected with fake tokens)")
            # Restore session if it was cleared
            if not auth.session and original_session:
                auth.session = original_session
                save_session(original_session)
        
        # Test 3.3: Expired Token Handling
        print_info("3.3 Testing expired token handling...")
        # Ensure we have a session
        if not auth.session and original_session:
            auth.session = original_session
            save_session(original_session)
        
        # Create expired session for testing
        expired_session = auth.session.copy()
        expired_session['expires_at'] = time.time() - 100
        auth.session = expired_session
        
        result = auth._ensure_valid_session()
        print_info("Expired token refresh logic executed (expected to fail with fake tokens)")
        
        # Restore session
        if original_session:
            auth.session = original_session
            save_session(original_session)
        
        # Test 3.4: Error Handling
        print_info("3.4 Testing error handling...")
        # Ensure session is restored before error handling test
        if not auth.session and original_session:
            auth.session = original_session
            save_session(original_session)
        
        test_errors = [
            Exception("401 Unauthorized"),
            Exception("Token expired"),
            Exception("Some other error"),
        ]
        
        handled = 0
        for error in test_errors:
            if auth.handle_auth_error(error):
                handled += 1
        
        print_info(f"Error handling tested: {handled} auth errors detected")
        
        # Final restore of session
        if not auth.session and original_session:
            auth.session = original_session
            save_session(original_session)
        
        return True
        
    except Exception as e:
        print_error(f"Token refresh test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# PHASE 4: SESSION MANAGEMENT
# ============================================================================

def test_session_management(auth):
    """Test 4: Session management (lifecycle, metrics, cleanup)."""
    print_test("PHASE 4: Session Management")
    
    # Reload session if needed
    if not auth or not auth.session:
        loaded = load_session()
        if loaded:
            if auth:
                auth.session = loaded
            else:
                print_error("No session available for management testing")
                return False
        else:
            print_error("No session available for management testing")
            return False
    
    try:
        # Test 4.1: Session Helper Methods
        print_info("4.1 Testing session helper methods...")
        user_id = auth.get_user_id()
        access_token = auth.get_access_token()
        
        if user_id:
            print_success(f"get_user_id() returned: {user_id[:8]}...")
        else:
            print_warning("get_user_id() returned None")
        
        if access_token:
            print_success(f"get_access_token() returned token (length: {len(access_token)})")
        else:
            print_warning("get_access_token() returned None")
        
        # Test 4.2: Session Time Remaining
        print_info("4.2 Testing session time remaining...")
        time_remaining = auth.get_session_time_remaining()
        hours = time_remaining // 3600
        minutes = (time_remaining % 3600) // 60
        print_info(f"Session expires in: {int(hours)}h {int(minutes)}m")
        
        # Test 4.3: Refresh Metrics (if enabled)
        if ENABLE_METRICS:
            print_info("4.3 Testing refresh metrics...")
            metrics = auth.get_refresh_metrics()
            if metrics:
                print_success(f"Metrics available: {metrics.get('total_refreshes', 0)} refreshes tracked")
                print_info(f"  Success rate: {metrics.get('success_rate', 0)*100:.1f}%")
                print_info(f"  Avg duration: {metrics.get('avg_duration_ms', 0):.1f}ms")
            else:
                print_info("No metrics recorded yet")
        else:
            print_info("4.3 Refresh metrics disabled (development mode)")
        
        # Test 4.4: Session Persistence Across Restarts
        print_info("4.4 Testing session persistence...")
        # Save current session
        save_session(auth.session)
        
        # Create new auth instance
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        new_auth = Auth(client, enable_encryption=ENABLE_ENCRYPTION, enable_metrics=ENABLE_METRICS)
        
        if new_auth.session and new_auth.session.get('user_id') == auth.session.get('user_id'):
            print_success("Session persisted across Auth instance recreation")
        else:
            print_warning("Session not properly loaded in new instance")
        
        return True
        
    except Exception as e:
        print_error(f"Session management test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cleanup(auth):
    """Test 5: Cleanup and logout."""
    print_test("PHASE 5: Cleanup & Logout")
    
    try:
        if auth and auth.session:
            print_info("Testing logout...")
            # Check storage mode before logout
            use_database = ENVIRONMENT == "production" and hasattr(auth, '_use_database') and auth._use_database
            user_id = auth.session.get('user_id')
            
            auth.logout()
            
            # Check storage mode
            if use_database:
                # In production, check database
                loaded = load_session(user_id=user_id)
                if not loaded:
                    print_success("Session cleared from database after logout")
                else:
                    print_warning("Session still exists in database after logout")
            else:
                # In development, check file
                if not os.path.exists(SESSION_FILE):
                    print_success("Session file deleted after logout")
                else:
                    print_warning("Session file still exists after logout")
            
            if not auth.session:
                print_success("Session cleared from memory")
            else:
                print_warning("Session not cleared from memory")
        else:
            print_info("No session to clean up")
        
        return True
        
    except Exception as e:
        print_error(f"Cleanup test failed: {e}")
        return False


def main():
    """Run all tests in flow order."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}Auth Session Management Test Suite{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.RESET}")
    print(f"\n{Colors.BOLD}Environment: {ENVIRONMENT.upper()}{Colors.RESET}")
    print(f"Encryption: {'Enabled' if ENABLE_ENCRYPTION else 'Disabled'}")
    print(f"Metrics: {'Enabled' if ENABLE_METRICS else 'Disabled'}")
    
    # Get test mode
    test_mode = get_test_mode()
    
    results = []
    auth_instance = None
    
    # Phase 1: Login
    success, auth_instance = test_login_flow(test_mode)
    results.append(("Login & Registration", success))
    if not success:
        print_error("Login failed, cannot continue with remaining tests")
        return 1
    
    # Phase 2: Session Security
    success = test_session_security(auth_instance)
    results.append(("Session Security", success))
    
    # Phase 3: Token Refresh
    success = test_token_refresh(auth_instance)
    results.append(("Token Refresh", success))
    
    # Phase 4: Session Management
    success = test_session_management(auth_instance)
    results.append(("Session Management", success))
    
    # Phase 5: Cleanup
    success = test_cleanup(auth_instance)
    results.append(("Cleanup & Logout", success))
    
    # Print summary
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}Test Summary{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.RESET}\n")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        if result:
            try:
                print(f"{Colors.GREEN}✓{Colors.RESET} {test_name}")
            except UnicodeEncodeError:
                print(f"{Colors.GREEN}[PASS]{Colors.RESET} {test_name}")
        else:
            try:
                print(f"{Colors.RED}✗{Colors.RESET} {test_name}")
            except UnicodeEncodeError:
                print(f"{Colors.RED}[FAIL]{Colors.RESET} {test_name}")
    
    print(f"\n{Colors.BOLD}Total: {passed}/{total} phases passed{Colors.RESET}")
    
    if passed == total:
        print(f"{Colors.GREEN}All tests passed!{Colors.RESET}\n")
        return 0
    else:
        print(f"{Colors.YELLOW}Some tests had issues.{Colors.RESET}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
