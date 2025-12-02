import os
import sys
import logging
from typing import List, Dict

from colorama import Fore, Style
from dotenv import load_dotenv
from supabase import create_client

# Import our modularized components with updated paths
from auth import Auth
from org_manager import OrganizationManager
from file_manager import FileManager
from cli.exit_handler import exit_application
from cli.main_menu import handle_main_menu
from auth.pages.login import login_page
from auth.pages.register import register_page
from cli.terminal_utils import clear_screen
from cli.organization_menu import handle_organization_menu
from cli.file_menu import handle_file_menu
from cli.account_menu import handle_account_menu
from cli.organizations import (
    create_organization,
    join_organization,
    view_organization,
    manage_organization,
)
from cli.files import (
    upload_file,
    request_decryption,
    submit_key_share,
    check_decrypted_file,
    verify_file_encryption,
    delete_file,
)
from cli.cloud import (
    connect_cloud_storage,
    disconnect_cloud_storage,
    connect_google_drive,
    connect_dropbox,
    connect_onedrive,
)

# Initialize logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("SecureShare")

# Load environment variables and create the Supabase client
# Explicitly load .env file from current directory
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(dotenv_path=env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error("SUPABASE_URL and SUPABASE_KEY must be set in the environment")
    sys.exit(1)

supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)

storage_service_client = None
if SUPABASE_SERVICE_ROLE_KEY:
    try:
        storage_service_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        logger.info("✓ Initialized Supabase storage service client with service role key (will bypass RLS)")
        logger.info(f"Service role key loaded: {len(SUPABASE_SERVICE_ROLE_KEY)} characters")
        # Verify the client is different from regular client
        if storage_service_client == supabase_client:
            logger.warning("⚠ WARNING: Storage service client appears to be the same as regular client!")
        else:
            logger.debug("✓ Storage service client is distinct from regular client")
    except Exception as exc:
        logger.warning(f"Failed to initialize storage service client: {exc}")
        storage_service_client = None
else:
    logger.warning("⚠ SUPABASE_SERVICE_ROLE_KEY not set - storage operations may fail due to RLS. Please set it in your .env file.")
    logger.warning(f"Current working directory: {os.getcwd()}")
    logger.warning(f"Looking for .env at: {env_path}")
    logger.warning(f".env file exists: {os.path.exists(env_path)}")


class SecureShareCLI:
    """Main CLI application"""

    def __init__(self):
        self.client = supabase_client  
        self.auth = Auth(supabase_client)
        self.org_manager = OrganizationManager(supabase_client, self.auth)
        self.file_manager = FileManager(
            supabase_client,
            self.auth,
            self.org_manager,
            storage_client=storage_service_client or supabase_client
        )
        logger.info("SecureShare CLI initialized")

    def main_menu(self) -> None:
        handle_main_menu(self)
    
    def login(self) -> None:
        login_page(self)
    
    def register(self) -> None:
        register_page(self)
    
    def organization_menu(self) -> None:
        handle_organization_menu(self)
    
    def file_menu(self) -> None:
        handle_file_menu(self)

    def account_menu(self) -> None:
        handle_account_menu(self)

    def _disconnect_cloud_storage(self) -> None:
        disconnect_cloud_storage(self)

    def _clear_screen(self) -> None:
        clear_screen()

    def _create_organization(self) -> None:
        create_organization(self)

    def _join_organization(self) -> None:
        join_organization(self)

    def _upload_file(self, org_id: str) -> None:
        upload_file(self, org_id)

    def _request_decryption(self, org_id: str, files: List[Dict]) -> None:
        request_decryption(self, org_id, files)

    def _submit_key_share(self, org_id: str) -> None:
        submit_key_share(self, org_id)

    def _check_decrypted_file(self, org_id: str, files: List[Dict]) -> None:
        check_decrypted_file(self, org_id, files)

    def _verify_file_encryption(self, org_id: str, files: List[Dict]) -> None:
        verify_file_encryption(self, org_id, files)

    def _delete_file(self, org_id: str, files: List[Dict]) -> None:
        delete_file(self, org_id, files)

    def _connect_cloud_storage(self) -> None:
        connect_cloud_storage(self)

    def _connect_google_drive(self) -> None:
        connect_google_drive(self)

    def _connect_dropbox(self) -> None:
        connect_dropbox(self)

    def _connect_onedrive(self) -> None:
        connect_onedrive(self)

    def _view_organization(self, organizations: List[Dict]) -> None:
        view_organization(self, organizations)

    def _manage_organization(self, organizations: List[Dict]) -> None:
        manage_organization(self, organizations)

if __name__ == "__main__":
    cli = SecureShareCLI()
    try:
        cli.main_menu()
    except (KeyboardInterrupt, EOFError):
        # Ensure we log out and clear session before exiting on Ctrl+C / EOF
        exit_application(cli)
