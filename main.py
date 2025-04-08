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
        """Display main menu and handle user input"""
        while True:
            self._clear_screen()
            print(f"{Fore.CYAN}===== SECURE FILE SHARING APPLICATION ====={Style.RESET_ALL}")
            
            if not self.auth.is_authenticated():
                print("\n1. Login")
                print("2. Register")
                print("0. Exit")
                
                choice = input("\nEnter choice: ")
                
                if choice == '1':
                    self.login()
                elif choice == '2':
                    self.register()
                elif choice == '0':
                    print("\nExiting application...")
                    break
                else:
                    print(f"{Fore.RED}Invalid choice{Style.RESET_ALL}")
                    input("Press Enter to continue...")
            else:
                print("\n1. Organization Management")
                print("2. File Management")
                print("3. Account Settings")
                print("4. Log Out")
                print("0. Exit")
                
                choice = input("\nEnter choice: ")
                
                if choice == '1':
                    self.organization_menu()
                elif choice == '2':
                    self.file_menu()
                elif choice == '3':
                    self.account_menu()
                elif choice == '4':
                    self.auth.logout()
                elif choice == '0':
                    print("\nExiting application...")
                    break
                else:
                    print(f"{Fore.RED}Invalid choice{Style.RESET_ALL}")
                    input("Press Enter to continue...")
    
    def login(self) -> None:
        """Handle user login"""
        self._clear_screen()
        print(f"{Fore.CYAN}===== LOGIN ====={Style.RESET_ALL}\n")
        
        email = input("Email: ")
        password = getpass.getpass("Password: ")
        
        if self.auth.login(email, password):
            input(f"{Fore.GREEN}Login successful!{Style.RESET_ALL} Press Enter to continue...")
        else:
            input(f"{Fore.RED}Login failed.{Style.RESET_ALL} Press Enter to try again...")
    
    def register(self) -> None:
        """Handle user registration"""
        self._clear_screen()
        print(f"{Fore.CYAN}===== REGISTER ====={Style.RESET_ALL}\n")
        
        email = input("Email: ")
        display_name = input("Display Name: ")
        password = getpass.getpass("Password: ")
        password_confirm = getpass.getpass("Confirm Password: ")
        
        if password != password_confirm:
            input(f"{Fore.RED}Passwords do not match.{Style.RESET_ALL} Press Enter to try again...")
            return
            
        if self.auth.register(email, password, display_name):
            input("Press Enter to continue...")
    
    def organization_menu(self) -> None:
        """Display organization menu and handle user input"""
        while True:
            self._clear_screen()
            print(f"{Fore.CYAN}===== ORGANIZATION MANAGEMENT ====={Style.RESET_ALL}\n")
            
            organizations = self.org_manager.get_user_organizations()
            
            if organizations:
                print("Your Organizations:")
                for i, org in enumerate(organizations, 1):
                    print(f"{i}. {org['name']} ({org['member_count']} members) - {org['role']}")
            else:
                print("You are not a member of any organizations.")
                
            print("\n1. Create New Organization")
            print("2. Join Organization")
            print("3. View Organization Details")
            print("4. Manage Organization")
            print("0. Back to Main Menu")
            
            choice = input("\nEnter choice: ")
            
            if choice == '1':
                self._create_organization()
            elif choice == '2':
                self._join_organization()
            elif choice == '3':
                self._view_organization(organizations)
            elif choice == '4':
                self._manage_organization(organizations)
            elif choice == '0':
                break
            else:
                print(f"{Fore.RED}Invalid choice{Style.RESET_ALL}")
                input("Press Enter to continue...")
    
    def file_menu(self) -> None:
        """Display file menu and handle user input"""
        while True:
            self._clear_screen()
            print(f"{Fore.CYAN}===== FILE MANAGEMENT ====={Style.RESET_ALL}\n")
            
            organizations = self.org_manager.get_user_organizations()
            
            if not organizations:
                print(f"{Fore.YELLOW}You must be a member of an organization to manage files.{Style.RESET_ALL}")
                input("Press Enter to continue...")
                break
                
            print("Select Organization:")
            for i, org in enumerate(organizations, 1):
                print(f"{i}. {org['name']} ({org['member_count']} members)")
                
            org_choice = input("\nEnter organization number (0 to go back): ")
            
            if org_choice == '0':
                break
                
            try:
                org_index = int(org_choice) - 1
                if org_index < 0 or org_index >= len(organizations):
                    raise ValueError("Invalid organization index")
                    
                selected_org = organizations[org_index]
                org_id = selected_org['id']
                
                # Check encryption eligibility
                eligibility = self.org_manager.check_encryption_eligibility(org_id)
                
                while True:
                    self._clear_screen()
                    print(f"{Fore.CYAN}===== FILE MANAGEMENT: {selected_org['name']} ====={Style.RESET_ALL}\n")
                    
                    if not eligibility['eligible']:
                        print(f"{Fore.YELLOW}Organization does not meet encryption requirements:{Style.RESET_ALL}")
                        
                        if not eligibility['member_count_met']:
                            print(f" - Organization must have at least {eligibility['required_count']} members")
                            print(f"   (current: {eligibility['member_count']})")
                        
                        if not eligibility['cloud_storage_met']:
                            print("\n The following members need to connect cloud storage:")
                            for member in eligibility['members_without_cloud']:
                                print(f" - {member['display_name']} ({member['email']})")
                        print("")
                    
                    files = self.file_manager.list_files(org_id)
                    
                    if files:
                        print("Files:")
                        for i, file in enumerate(files, 1):
                            status_color = Fore.GREEN if file['status'] == 'available' else (
                                Fore.YELLOW if file['status'] == 'pending_decryption' else Fore.CYAN
                            )
                            print(f"{i}. {file['name']} ({file['size']} bytes) - " +
                                  f"Uploaded by: {file['uploader']} - " +
                                  f"Status: {status_color}{file['status']}{Style.RESET_ALL}")
                    else:
                        print("No files found in this organization.")
                        
                    print("\n1. Upload and Encrypt File")
                    print("2. Request File Decryption")
                    print("3. Submit Key Share")
                    print("4. Check Decrypted File")
                    print("5. Verify File Encryption") 
                    print("6. Delete File")          
                    print("0. Back to Organizations")
                    
                    choice = input("\nEnter choice: ")

                    if choice == '1':
                        if eligibility['eligible']:
                            self._upload_file(org_id)
                        else:
                            print(f"{Fore.RED}Organization does not meet requirements for encryption{Style.RESET_ALL}")
                            input("Press Enter to continue...")
                    elif choice == '2':
                        self._request_decryption(org_id, files)
                    elif choice == '3':
                        self._submit_key_share(org_id)
                    elif choice == '4':
                        self._check_decrypted_file(org_id, files)
                    elif choice == '5':
                        self._verify_file_encryption(org_id, files)
                    elif choice == '6':
                        self._delete_file(org_id, files)
                    elif choice == '0':
                        break
                    else:
                        print(f"{Fore.RED}Invalid choice{Style.RESET_ALL}")
                        input("Press Enter to continue...")

            except (ValueError, IndexError):
                print(f"{Fore.RED}Invalid organization selection{Style.RESET_ALL}")
                input("Press Enter to continue...")

    def account_menu(self) -> None:
        """Display account settings menu and handle user input"""
        while True:
            self._clear_screen()
            print(f"{Fore.CYAN}===== ACCOUNT SETTINGS ====={Style.RESET_ALL}\n")
            
            # Get user profile and cloud status
            user_id = self.auth.get_user_id()
            user_profile = self.client.from_('users').select('*').eq('id', user_id).single().execute()
            
            if user_profile.data:
                profile = user_profile.data
                print(f"Email: {profile['email']}")
                print(f"Display Name: {profile['display_name']}")
                print("\nCloud Storage Status:")
                
                if profile['cloud_connected']:
                    provider = profile['cloud_provider']
                    provider_color = {
                        'google_drive': f"{Fore.BLUE}Google Drive{Style.RESET_ALL}",
                        'dropbox': f"{Fore.CYAN}Dropbox{Style.RESET_ALL}",
                        'onedrive': f"{Fore.GREEN}OneDrive{Style.RESET_ALL}"
                    }.get(provider, provider)
                    print(f"Connected to: {provider_color}")
                    print(f"Status: {Fore.GREEN}Connected{Style.RESET_ALL}")
                else:
                    print(f"Status: {Fore.YELLOW}Not Connected{Style.RESET_ALL}")
            
            print("\n1. Connect Cloud Storage")
            if user_profile.data.get('cloud_connected'):
                print("2. Disconnect Cloud Storage")
            print("0. Back to Main Menu")

            choice = input("\nEnter choice: ")

            if choice == '1':
                if user_profile.data.get('cloud_connected'):
                    print(f"{Fore.YELLOW}You are already connected to a cloud provider.{Style.RESET_ALL}")
                    print("Please disconnect current provider before connecting a new one.")
                    input("Press Enter to continue...")
                else:
                    self._connect_cloud_storage()
            elif choice == '2' and user_profile.data.get('cloud_connected'):
                self._disconnect_cloud_storage()
            elif choice == '0':
                break
            else:
                print(f"{Fore.RED}Invalid choice{Style.RESET_ALL}")
                input("Press Enter to continue...")

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
        """Clear terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def _create_organization(self) -> None:
        """Handle organization creation"""
        self._clear_screen()
        print(f"{Fore.CYAN}===== CREATE ORGANIZATION ====={Style.RESET_ALL}\n")

        name = input("Organization Name: ")
        if name:
            try:
                self.org_manager.create_organization(name)
            except Exception as e:
                print(f"{Fore.RED}Failed to create organization: {e}{Style.RESET_ALL}")
            input("Press Enter to continue...")

    def _join_organization(self) -> None:
        """Handle joining an organization"""
        self._clear_screen()
        print(f"{Fore.CYAN}===== JOIN ORGANIZATION ====={Style.RESET_ALL}\n")

        invite_code = input("Enter Invite Code: ")
        if invite_code:
            try:
                self.org_manager.join_organization(invite_code)
            except Exception as e:
                print(f"{Fore.RED}Failed to join organization: {e}{Style.RESET_ALL}")
            input("Press Enter to continue...")

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

        choice = input("\nEnter choice: ")

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
        """Handle viewing organization details"""
        self._clear_screen()
        print(f"{Fore.CYAN}===== VIEW ORGANIZATION ====={Style.RESET_ALL}\n")

        if not organizations:
            print(f"{Fore.YELLOW}You are not a member of any organizations.{Style.RESET_ALL}")
            input("Press Enter to continue...")
            return

        print("Select organization to view:")
        for i, org in enumerate(organizations, 1):
            print(f"{i}. {org['name']}")

        try:
            choice = int(input("\nEnter organization number: "))
            if choice < 1 or choice > len(organizations):
                raise ValueError("Invalid organization number")

            org = organizations[choice - 1]
            org_id = org['id']
            members = self.org_manager.list_organization_members(org_id)

            self._clear_screen()
            print(f"{Fore.CYAN}===== ORGANIZATION DETAILS ====={Style.RESET_ALL}\n")
            print(f"Name: {org['name']}")
            print(f"Member Count: {org['member_count']}")
            print(f"Invite Code: {org.get('invite_code', 'N/A')}")
            print(f"Invites Enabled: {'Yes' if org.get('invite_enabled', False) else 'No'}")
            
            if members:
                print("\nMembers:")
                for member in members:
                    role_color = Fore.GREEN if member['role'] == 'admin' else Fore.BLUE
                    print(f"- {member['display_name']} ({member['email']}) - Role: {role_color}{member['role']}{Style.RESET_ALL}")
            else:
                print("\nNo members found.")

            if org['role'] == 'admin':
                print("\nAdmin Options:")
                print("1. Toggle Invites")
                print("2. Regenerate Invite Code")
                print("0. Back")

                admin_choice = input("\nEnter choice: ")
                if admin_choice == '1':
                    new_state = not org.get('invite_enabled', False)
                    self.org_manager.toggle_invites(org_id, new_state)
                elif admin_choice == '2':
                    self.org_manager.regenerate_invite_code(org_id)

        except (ValueError, IndexError):
            print(f"{Fore.RED}Invalid organization selection{Style.RESET_ALL}")
        
        input("Press Enter to continue...")

    def _manage_organization(self, organizations: List[Dict]) -> None:
        """Handle admin organization management"""
        self._clear_screen()
        print(f"{Fore.CYAN}===== MANAGE ORGANIZATION ====={Style.RESET_ALL}\n")

        admin_orgs = [org for org in organizations if org['role'] == 'admin']
        
        if not admin_orgs:
            print(f"{Fore.YELLOW}You are not an admin of any organizations.{Style.RESET_ALL}")
            input("Press Enter to continue...")
            return

        print("Select organization to manage:")
        for i, org in enumerate(admin_orgs, 1):
            print(f"{i}. {org['name']} ({org['member_count']} members)")

        try:
            choice = int(input("\nEnter organization number: "))
            if choice < 1 or choice > len(admin_orgs):
                raise ValueError("Invalid organization number")

            org = admin_orgs[choice - 1]
            org_id = org['id']

            while True:
                self._clear_screen()
                print(f"{Fore.CYAN}===== MANAGE {org['name'].upper()} ====={Style.RESET_ALL}\n")
                members = self.org_manager.list_organization_members(org_id)
                
                print("Members:")
                for i, member in enumerate(members, 1):
                    role_color = Fore.GREEN if member['role'] == 'admin' else Fore.BLUE
                    print(f"{i}. {member['display_name']} ({member['email']}) - {role_color}{member['role']}{Style.RESET_ALL}")

                print("\nAdmin Actions:")
                print("1. Remove Member")
                print("0. Back")

                admin_choice = input("\nEnter choice: ")
                
                if admin_choice == '1':
                    member_num = int(input("Enter member number to remove: "))
                    if member_num < 1 or member_num > len(members):
                        print(f"{Fore.RED}Invalid member number{Style.RESET_ALL}")
                    else:
                        member = members[member_num - 1]
                        if member['id'] == self.auth.get_user_id():
                            print(f"{Fore.RED}You cannot remove yourself from the organization{Style.RESET_ALL}")
                        else:
                            confirm = input(f"Are you sure you want to remove {member['display_name']}? (y/n): ")
                            if confirm.lower() == 'y':
                                try:
                                    self.org_manager.remove_member(org_id, member['id'])
                                    print(f"{Fore.GREEN}Member removed successfully{Style.RESET_ALL}")
                                except Exception as e:
                                    print(f"{Fore.RED}Failed to remove member: {e}{Style.RESET_ALL}")
                    input("Press Enter to continue...")
                elif admin_choice == '0':
                    break
                else:
                    print(f"{Fore.RED}Invalid choice{Style.RESET_ALL}")
                    input("Press Enter to continue...")

        except (ValueError, IndexError):
            print(f"{Fore.RED}Invalid selection{Style.RESET_ALL}")
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

if __name__ == "__main__":
    cli = SecureShareCLI()
    cli.main_menu()
