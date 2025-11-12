import os
import sys
import getpass
import datetime
import logging
from typing import List, Dict
import webbrowser

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

# Initialize logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("SecureShare")

# Load environment variables and create the Supabase client
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error("SUPABASE_URL and SUPABASE_KEY must be set in the environment")
    sys.exit(1)
supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)


class SecureShareCLI:
    """Main CLI application"""

    def __init__(self):
        self.client = supabase_client  
        self.auth = Auth(supabase_client)
        self.org_manager = OrganizationManager(supabase_client, self.auth)
        self.file_manager = FileManager(supabase_client, self.auth, self.org_manager)
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
        """Handle cloud storage disconnection"""
        try:
            user_id = self.auth.get_user_id()
            
            # Update user profile
            self.client.from_('users').update({
                'cloud_connected': False,
                'cloud_provider': None,
                'cloud_credentials': None,
                'updated_at': datetime.datetime.now().isoformat()
            }).eq('id', user_id).execute()
            
            print(f"{Fore.GREEN}Successfully disconnected cloud storage!{Style.RESET_ALL}")
            
        except Exception as e:
            print(f"{Fore.RED}Failed to disconnect cloud storage: {e}{Style.RESET_ALL}")
        
        input("Press Enter to continue...")

    def _clear_screen(self) -> None:
        clear_screen()

    def _create_organization(self) -> None:
        create_organization(self)

    def _join_organization(self) -> None:
        join_organization(self)

    def _upload_file(self, org_id: str) -> None:
        """Handle file upload"""
        self._clear_screen()
        print(f"{Fore.CYAN}===== UPLOAD FILE ====={Style.RESET_ALL}\n")

        # Check eligibility first
        eligibility = self.org_manager.check_encryption_eligibility(org_id)
        if not eligibility['eligible']:
            print(f"{Fore.RED}Cannot upload file - Organization requirements not met:{Style.RESET_ALL}")
            if not eligibility['member_count_met']:
                print(f" - Need {eligibility['required_count']} members (current: {eligibility['member_count']})")
            if not eligibility['cloud_storage_met']:
                print(" - The following members need to connect cloud storage:")
                for member in eligibility['members_without_cloud']:
                    print(f"   - {member['display_name']} ({member['email']})")
            input("\nPress Enter to continue...")
            return

        print("Choose upload method:")
        print("1. Enter file path")
        print("2. Select file using file dialog")
        print("0. Cancel")

        try:
            choice = input("\nEnter choice: ")
        except (KeyboardInterrupt, EOFError):
            print(f"\n{Fore.YELLOW}Returning to file management menu...{Style.RESET_ALL}")
            input("Press Enter to continue...")
            return

        if choice == '0':
            return

        file_path = None
        if choice == '1':
            file_path = input("Enter file path: ")
        elif choice == '2':
            try:
                import tkinter as tk
                from tkinter import filedialog
                
                root = tk.Tk()
                root.withdraw()
                root.attributes('-topmost', True)
                file_path = filedialog.askopenfilename(
                    title="Select file to upload",
                    filetypes=[
                        ("All files", "*.*"),
                        ("Text files", "*.txt"),
                        ("PDF files", "*.pdf"),
                        ("Image files", "*.jpg *.jpeg *.png *.gif")
                    ]
                )
                root.destroy()
                if not file_path:
                    print(f"{Fore.YELLOW}File selection canceled{Style.RESET_ALL}")
                    input("Press Enter to continue...")
                    return
                    
            except Exception as e:
                print(f"{Fore.RED}Failed to open file dialog: {e}{Style.RESET_ALL}")
                print("Please try entering the file path manually.")
                input("Press Enter to continue...")
                return
        else:
            print(f"{Fore.RED}Invalid choice{Style.RESET_ALL}")
            input("Press Enter to continue...")
            return

        if not file_path:
            print(f"{Fore.YELLOW}No file selected{Style.RESET_ALL}")
            input("Press Enter to continue...")
            return

        if not os.path.exists(file_path):
            print(f"{Fore.RED}File not found: {file_path}{Style.RESET_ALL}")
            input("Press Enter to continue...")
            return

        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)
        print(f"\nSelected file:")
        print(f"Name: {file_name}")
        print(f"Size: {file_size} bytes")
        print(f"Path: {file_path}")

        confirm = input("\nProceed with this file? (y/n): ")
        if confirm.lower() != 'y':
            return

        threshold = input("\nEnter decryption threshold (minimum number of shares required): ")
        try:
            threshold = int(threshold)
            if threshold < 3:
                print(f"{Fore.RED}Threshold must be at least 3{Style.RESET_ALL}")
                input("Press Enter to continue...")
                return
        except ValueError:
            print(f"{Fore.RED}Invalid threshold{Style.RESET_ALL}")
            input("Press Enter to continue...")
            return

        password = getpass.getpass("Enter encryption password: ")
        confirm_password = getpass.getpass("Confirm encryption password: ")

        if password != confirm_password:
            print(f"{Fore.RED}Passwords do not match{Style.RESET_ALL}")
            input("Press Enter to continue...")
            return

        try:
            self.file_manager.upload_file(file_path, org_id, threshold, password)
            input("Press Enter to continue...")
        except Exception as e:
            print(f"{Fore.RED}Upload failed: {e}{Style.RESET_ALL}")
            input("Press Enter to continue...")

    def _request_decryption(self, org_id: str, files: List[Dict]) -> None:
        """Handle decryption request"""
        if not files:
            print(f"{Fore.YELLOW}No files available{Style.RESET_ALL}")
            input("Press Enter to continue...")
            return

        print("\nSelect file to decrypt:")
        for i, file in enumerate(files, 1):
            print(f"{i}. {file['name']}")

        try:
            choice = int(input("\nEnter file number: "))
            file = files[choice - 1]
            reason = input("Enter reason for decryption (optional): ")
            self.file_manager.request_decryption(file['id'], reason)
            input("Press Enter to continue...")
        except (ValueError, IndexError):
            print(f"{Fore.RED}Invalid file selection{Style.RESET_ALL}")
            input("Press Enter to continue...")

    def _submit_key_share(self, org_id: str) -> None:
        """Handle key share submission"""
        self._clear_screen()
        print(f"{Fore.CYAN}===== SUBMIT KEY SHARE ====={Style.RESET_ALL}\n")

        try:
            requests = self.client.from_('decryption_requests')\
                .select('*, files!inner(name, organization_id, id), users!requester_id(display_name)')\
                .eq('status', 'pending')\
                .eq('files.organization_id', org_id)\
                .execute()

            if not requests.data:
                print(f"{Fore.YELLOW}No pending decryption requests found.{Style.RESET_ALL}")
                input("Press Enter to continue...")
                return

            print("Pending Decryption Requests:")
            for i, req in enumerate(requests.data, 1):
                file_name = req['files']['name']
                requester = req['users']['display_name']
                shares = f"{req['current_shares']}/{req['threshold']}"
                expires = datetime.datetime.fromisoformat(req['expires_at'])
                time_left = expires - datetime.datetime.now()
                hours_left = time_left.total_seconds() / 3600

                print(f"\n{i}. File: {file_name}")
                print(f"   Requested by: {requester}")
                print(f"   Shares collected: {shares}")
                print(f"   Expires in: {hours_left:.1f} hours")
                if req.get('message'):
                    print(f"   Reason: {req['message']}")

            choice = input("\nEnter request number (0 to cancel): ")
            if choice == '0':
                return

            try:
                index = int(choice) - 1
                if 0 <= index < len(requests.data):
                    selected_request = requests.data[index]
                    file_id = selected_request['files']['id']
                    print(f"\n{Fore.CYAN}Retrieving your key share...{Style.RESET_ALL}")
                    
                    user_id = self.auth.get_user_id()
                    user = self.client.from_('users').select('*').eq('id', user_id).single().execute()
                    
                    if not user.data.get('cloud_connected'):
                        print(f"{Fore.RED}You need to connect your cloud storage first{Style.RESET_ALL}")
                        return

                    existing_share = self.client.from_('key_shares')\
                        .select('status')\
                        .eq('file_id', file_id)\
                        .eq('user_id', user_id)\
                        .eq('status', 'retrieved')\
                        .single()\
                        .execute()

                    if existing_share.data:
                        print(f"{Fore.YELLOW}You have already submitted your share for this file{Style.RESET_ALL}")
                        return

                    try:
                        self.file_manager.submit_key_share(selected_request['id'])
                        print(f"{Fore.GREEN}Share submitted successfully!{Style.RESET_ALL}")
                    except Exception as e:
                        print(f"{Fore.RED}Failed to submit share: {str(e)}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}Invalid selection{Style.RESET_ALL}")

            except ValueError:
                print(f"{Fore.RED}Invalid input{Style.RESET_ALL}")

        except Exception as e:
            print(f"{Fore.RED}Error retrieving decryption requests: {str(e)}{Style.RESET_ALL}")

        input("Press Enter to continue...")

    def _check_decrypted_file(self, org_id: str, files: List[Dict]) -> None:
        """Handle checking decrypted file status"""
        if not files:
            print(f"{Fore.YELLOW}No files available{Style.RESET_ALL}")
            input("Press Enter to continue...")
            return

        print("\nSelect file to check:")
        for i, file in enumerate(files, 1):
            print(f"{i}. {file['name']}")

        try:
            choice = int(input("\nEnter file number: "))
            file = files[choice - 1]
            status = self.file_manager.check_decrypted_file(file['id'])
            
            if status['status'] == 'decrypted':
                print(f"\nFile is decrypted and available at: {status['path']}")
                print(f"File expires in: {status['expires_in']}")
            else:
                print(f"\nFile status: {status['status']}")

            input("Press Enter to continue...")
        except (ValueError, IndexError):
            print(f"{Fore.RED}Invalid file selection{Style.RESET_ALL}")
            input("Press Enter to continue...")

    def _verify_file_encryption(self, org_id: str, files: List[Dict]) -> None:
        """Handle manual file encryption verification"""
        if not files:
            print(f"{Fore.YELLOW}No files available{Style.RESET_ALL}")
            input("Press Enter to continue...")
            return

        print("\nSelect file to verify:")
        for i, file in enumerate(files, 1):
            print(f"{i}. {file['name']}")

        try:
            choice = int(input("\nEnter file number: "))
            file = files[choice - 1]
            
            result = self.file_manager.verify_file_encryption(file['id'])
            
            print(f"\n{Fore.CYAN}Encryption Verification Results:{Style.RESET_ALL}")
            print(f"File: {result['name']}")
            print(f"Size: {result['size']} bytes")
            print(f"Entropy: {result['entropy']:.2f} bits/byte")
            print(f"Appears Encrypted: {Fore.GREEN if result['appears_encrypted'] else Fore.RED}{result['appears_encrypted']}{Style.RESET_ALL}")
            print(f"Share Distribution: {result['total_shares']}/{result['threshold']} shares")
            print(f"Current Status: {result['status']}")

        except (ValueError, IndexError) as e:
            print(f"{Fore.RED}Invalid file selection: {e}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Verification failed: {e}{Style.RESET_ALL}")
        
        input("Press Enter to continue...")

    def _delete_file(self, org_id: str, files: List[Dict]) -> None:
        """Handle file deletion"""
        if not files:
            print(f"{Fore.YELLOW}No files available{Style.RESET_ALL}")
            input("Press Enter to continue...")
            return

        print("\nSelect file to delete:")
        for i, file in enumerate(files, 1):
            print(f"{i}. {file['name']}")

        try:
            choice = int(input("\nEnter file number: "))
            file = files[choice - 1]
            
            confirm = input(f"\n{Fore.RED}WARNING: This will permanently delete the file and all shares.{Style.RESET_ALL}\nType 'DELETE' to confirm: ")
            if confirm != 'DELETE':
                print("Deletion cancelled.")
                return

            self.file_manager.delete_file(file['id'], org_id)
            print(f"{Fore.GREEN}File successfully deleted!{Style.RESET_ALL}")

        except ValueError as e:
            print(f"{Fore.RED}Invalid selection: {e}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Deletion failed: {e}{Style.RESET_ALL}")
        
        input("Press Enter to continue...")

    def _connect_cloud_storage(self) -> None:
        """Handle cloud storage connection"""
        self._clear_screen()
        print(f"{Fore.CYAN}===== CONNECT CLOUD STORAGE ====={Style.RESET_ALL}\n")
        
        user_id = self.auth.get_user_id()
        if not user_id:
            print(f"{Fore.RED}You must be logged in to connect cloud storage{Style.RESET_ALL}")
            input("Press Enter to continue...")
            return

        print("Select Cloud Provider:")
        print("1. Google Drive")
        print("2. Dropbox")
        print("3. Microsoft OneDrive")
        print("0. Back")

        choice = input("\nEnter choice: ")

        try:
            if choice == '1':
                self._connect_google_drive()
            elif choice == '2':
                self._connect_dropbox()
            elif choice == '3':
                self._connect_onedrive()
                
        except Exception as e:
            print(f"{Fore.RED}Failed to connect cloud storage: {e}{Style.RESET_ALL}")
            input("Press Enter to continue...")

    def _connect_google_drive(self) -> None:
        """Connect Google Drive using localhost"""
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build

            client_id = os.getenv('GOOGLE_CLIENT_ID')
            client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
            
            if not client_id or not client_secret:
                raise ValueError("Google Drive credentials not found in environment variables")

            flow = InstalledAppFlow.from_client_config(
                {
                    "installed": {
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "redirect_uris": ["http://localhost:8080"],
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs"
                    }
                },
                scopes=['https://www.googleapis.com/auth/drive.file']
            )

            print(f"{Fore.CYAN}Opening browser for Google Drive authentication...{Style.RESET_ALL}")
            credentials = flow.run_local_server(
                host='localhost',
                port=8080,
                authorization_prompt_message='Please visit this URL to authorize access:',
                success_message='Authentication successful! You may close this window.',
                open_browser=True,
                access_type='offline',
                prompt='consent'
            )

            creds_dict = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': client_id,
                'client_secret': client_secret,
                'scopes': credentials.scopes,
                'expiry': credentials.expiry.isoformat() if credentials.expiry else None
            }

            required_fields = ['token', 'refresh_token', 'token_uri', 'client_id', 'client_secret']
            missing_fields = [field for field in required_fields if not creds_dict.get(field)]
            if missing_fields:
                raise ValueError(f"Missing required credential fields: {', '.join(missing_fields)}")

            user_id = self.auth.get_user_id()
            if not user_id:
                raise ValueError("User not authenticated")

            self.client.from_('users').update({
                'cloud_connected': True,
                'cloud_provider': 'google_drive',
                'cloud_credentials': creds_dict,
                'updated_at': datetime.datetime.now().isoformat()
            }).eq('id', user_id).execute()

            service = build('drive', 'v3', credentials=credentials)
            about = service.about().get(fields="user").execute()
            
            print(f"{Fore.GREEN}Successfully connected Google Drive!{Style.RESET_ALL}")
            
        except Exception as e:
            print(f"{Fore.RED}Failed to connect Google Drive: {e}{Style.RESET_ALL}")
        
        input("Press Enter to continue...")

    def _connect_dropbox(self) -> None:
        """Connect Dropbox"""
        try:
            import dropbox

            APP_KEY = os.getenv('DROPBOX_APP_KEY')
            APP_SECRET = os.getenv('DROPBOX_APP_SECRET')
            
            auth_flow = dropbox.DropboxOAuth2FlowNoRedirect(
                APP_KEY,
                APP_SECRET,
                token_access_type='offline'
            )
            
            auth_url = auth_flow.start()
            print(f"\nPlease visit this URL to authorize access to Dropbox:")
            print(f"{Fore.CYAN}{auth_url}{Style.RESET_ALL}")
            webbrowser.open(auth_url)
            
            auth_code = input("\nEnter the authorization code: ")
            oauth_result = auth_flow.finish(auth_code)
            
            user_id = self.auth.get_user_id()
            self.client.table('users').update({
                'cloud_connected': True,
                'cloud_provider': 'dropbox',
                'cloud_credentials': {
                    'access_token': oauth_result.access_token,
                    'refresh_token': oauth_result.refresh_token,
                    'account_id': oauth_result.account_id
                },
                'updated_at': datetime.datetime.now().isoformat()
            }).eq('id', user_id).execute()
            
            print(f"{Fore.GREEN}Successfully connected Dropbox!{Style.RESET_ALL}")
            
        except Exception as e:
            print(f"{Fore.RED}Failed to connect Dropbox: {e}{Style.RESET_ALL}")
        
        input("Press Enter to continue...")

    def _connect_onedrive(self) -> None:
        """Connect Microsoft OneDrive"""
        try:
            import msal

            CLIENT_ID = os.getenv('ONEDRIVE_CLIENT_ID')
            SCOPES = ['Files.ReadWrite.AppFolder']
            
            msal_app = msal.PublicClientApplication(
                CLIENT_ID,
                authority="https://login.microsoftonline.com/common"
            )
            
            auth_url = msal_app.get_authorization_request_url(
                SCOPES,
                redirect_uri="http://localhost:8080"
            )
            
            print(f"\nPlease visit this URL to authorize access to OneDrive:")
            print(f"{Fore.CYAN}{auth_url}{Style.RESET_ALL}")
            webbrowser.open(auth_url)
            
            auth_code = input("\nEnter the authorization code: ")
            result = msal_app.acquire_token_by_authorization_code(
                auth_code,
                SCOPES,
                redirect_uri="http://localhost:8080"
            )
            
            user_id = self.auth.get_user_id()
            self.client.table('users').update({
                'cloud_connected': True,
                'cloud_provider': 'onedrive',
                'cloud_credentials': {
                    'access_token': result['access_token'],
                    'refresh_token': result.get('refresh_token'),
                    'expires_in': result['expires_in']
                },
                'updated_at': datetime.datetime.now().isoformat()
            }).eq('id', user_id).execute()
            
            print(f"{Fore.GREEN}Successfully connected OneDrive!{Style.RESET_ALL}")
            
        except Exception as e:
            print(f"{Fore.RED}Failed to connect OneDrive: {e}{Style.RESET_ALL}")
        
        input("Press Enter to continue...")

    def _view_organization(self, organizations: List[Dict]) -> None:
        view_organization(self, organizations)

    def _manage_organization(self, organizations: List[Dict]) -> None:
        manage_organization(self, organizations)

    def _verify_file_encryption(self, org_id: str, files: List[Dict]) -> None:
        """Handle manual file encryption verification"""
        if not files:
            print(f"{Fore.YELLOW}No files available{Style.RESET_ALL}")
            input("Press Enter to continue...")
            return

        print("\nSelect file to verify:")
        for i, file in enumerate(files, 1):
            print(f"{i}. {file['name']}")

        try:
            choice = int(input("\nEnter file number: "))
            file = files[choice - 1]
            
            result = self.file_manager.verify_file_encryption(file['id'])
            
            print(f"\n{Fore.CYAN}Encryption Verification Results:{Style.RESET_ALL}")
            print(f"File: {result['name']}")
            print(f"Size: {result['size']} bytes")
            print(f"Entropy: {result['entropy']:.2f} bits/byte")
            print(f"Appears Encrypted: {Fore.GREEN if result['appears_encrypted'] else Fore.RED}{result['appears_encrypted']}{Style.RESET_ALL}")
            print(f"Share Distribution: {result['total_shares']}/{result['threshold']} shares")
            print(f"Current Status: {result['status']}")

        except (ValueError, IndexError) as e:
            print(f"{Fore.RED}Invalid file selection: {e}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Verification failed: {e}{Style.RESET_ALL}")
        
        input("Press Enter to continue...")

    def _delete_file(self, org_id: str, files: List[Dict]) -> None:
        """Handle file deletion"""
        if not files:
            print(f"{Fore.YELLOW}No files available{Style.RESET_ALL}")
            input("Press Enter to continue...")
            return

        print("\nSelect file to delete:")
        for i, file in enumerate(files, 1):
            print(f"{i}. {file['name']}")

        try:
            choice = int(input("\nEnter file number: "))
            file = files[choice - 1]
            
            confirm = input(f"\n{Fore.RED}WARNING: This will permanently delete the file and all shares.{Style.RESET_ALL}\nType 'DELETE' to confirm: ")
            if confirm != 'DELETE':
                print("Deletion cancelled.")
                return

            self.file_manager.delete_file(file['id'], org_id)
            print(f"{Fore.GREEN}File successfully deleted!{Style.RESET_ALL}")

        except ValueError as e:
            print(f"{Fore.RED}Invalid selection: {e}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Deletion failed: {e}{Style.RESET_ALL}")
        
        input("Press Enter to continue...")

if __name__ == "__main__":
    cli = SecureShareCLI()
    try:
        cli.main_menu()
    except (KeyboardInterrupt, EOFError):
        print(f"\n{Fore.YELLOW}Exiting application...{Style.RESET_ALL}")
