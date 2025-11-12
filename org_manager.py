import uuid
import datetime
import json
import logging
from typing import List, Dict, Optional

from colorama import Fore, Style

# Import Auth from your auth module. Adjust the import if your project structure is different.
from auth import Auth

# Define a constant for the minimum organization members required.
MIN_ORG_MEMBERS = 5

logger = logging.getLogger("SecureShare")

class OrganizationManager:
    """Handles organization management operations"""
    
    def __init__(self, client, auth: Auth):
        self.client = client
        self.auth = auth
        logger.debug("Organization manager initialized")
    
    def get_user_organizations(self) -> List[Dict]:
        """Get organizations the user is a member of"""
        user_id = self.auth.get_user_id()
        if not user_id:
            logger.warning("Cannot get organizations: User not authenticated")
            return []
            
        try:
            logger.info("Fetching user organizations")
            response = self.client.from_('organization_members').select(
                '*, organizations(*)'
            ).eq('user_id', user_id).execute()
                
            organizations = []
            if response.data:
                for item in response.data:
                    org = item.get('organizations', {})
                    if not org:
                        continue
                    org_id = org.get('id')
                    org['role'] = item.get('role')
                    if org_id:
                        org['member_count'] = self.get_member_count(org_id)
                    organizations.append(org)
                logger.debug(f"Found {len(organizations)} organizations for user")
            
            return organizations
        except Exception as e:
            logger.error(f"Failed to fetch user organizations: {e}")
            return []

    def get_member_count(self, org_id: str) -> int:
        """Get current member count for an organization"""
        try:
            response = self.client.table('organization_members')\
                .select('id', count='exact')\
                .eq('organization_id', org_id)\
                .execute()

            if hasattr(response, 'count') and response.count is not None:
                return response.count

            return len(response.data or [])
        except Exception as e:
            logger.warning(f"Failed to fetch member count for organization {org_id}: {e}")
            return 0

    def get_organization(self, org_id: str) -> Optional[Dict]:
        """Fetch latest organization details"""
        user_id = self.auth.get_user_id()
        if not user_id:
            logger.warning("Cannot get organization: User not authenticated")
            return None

        try:
            response = self.client.table('organizations').select('*').eq('id', org_id).execute()
            if response.data:
                return response.data[0]
        except Exception as e:
            logger.error(f"Failed to fetch organization {org_id}: {e}")
        return None
    
    def create_organization(self, name: str) -> Dict:
        """Create a new organization"""
        user_id = self.auth.get_user_id()
        if not user_id:
            logger.warning("Cannot create organization: User not authenticated")
            raise ValueError("User not authenticated")
            
        try:
            logger.info(f"Creating organization: {name}")
            
            # Generate invite code
            invite_code = str(uuid.uuid4())[:8].upper()
            invite_expires_at = datetime.datetime.now() + datetime.timedelta(days=20)
            
            # Create organization with explicit user_id
            org_data = {
                'name': name,
                'invite_code': invite_code,
                'invite_code_expires_at': invite_expires_at.isoformat(),
                'invite_enabled': True,
                'admin_id': user_id,
                'member_count': 1,
                'created_at': datetime.datetime.now().isoformat(),
                'updated_at': datetime.datetime.now().isoformat()
            }
            
            response = self.client.table('organizations').insert(org_data).execute()
            
            if not response.data:
                raise Exception("Failed to create organization")
            
            org = response.data[0]
            org_id = org['id']
            
            # Add creator as admin member
            member_data = {
                'organization_id': org_id,
                'user_id': user_id,
                'joined_at': datetime.datetime.now().isoformat(),
                'role': 'admin',
                'status': 'active'
            }
            
            self.client.table('organization_members').insert(member_data).execute()
            logger.debug(f"Added creator as admin member to organization: {org_id}")
            
            # Create audit log
            self._create_audit_log(org_id, None, 'organization_created')
            
            print(f"{Fore.GREEN}Successfully created organization: {name}{Style.RESET_ALL}")
            print(f"Invite code: {Fore.YELLOW}{invite_code}{Style.RESET_ALL}")
                
            return org
                
        except Exception as e:
            logger.error(f"Failed to create organization: {e}")
            raise
    
    def join_organization(self, invite_code: str) -> bool:
        """Join an organization using invite code"""
        user_id = self.auth.get_user_id()
        if not user_id:
            logger.warning("Cannot join organization: User not authenticated")
            raise ValueError("User not authenticated")
            
        try:
            logger.info(f"Joining organization with invite code: {invite_code}")
            
            # Find organization by invite code
            response = self.client.table('organizations').select('*').eq('invite_code', invite_code).execute()
            
            if not response.data:
                logger.warning(f"No organization found with invite code: {invite_code}")
                print(f"{Fore.RED}Invalid invite code{Style.RESET_ALL}")
                return False
                
            org = response.data[0]
            org_id = org['id']
            
            # Check if invite is enabled
            if not org.get('invite_enabled', False):
                logger.warning(f"Invites are disabled for organization: {org_id}")
                print(f"{Fore.RED}Invites are currently disabled for this organization{Style.RESET_ALL}")
                return False
                
            # Check if invite code is expired
            expires_at_raw = org.get('invite_code_expires_at')
            if expires_at_raw:
                try:
                    expires_at = datetime.datetime.fromisoformat(expires_at_raw.replace('Z', '+00:00'))
                except ValueError:
                    logger.warning(f"Invalid invite expiry format for organization: {org_id}")
                    expires_at = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
            else:
                expires_at = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)

            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=datetime.timezone.utc)

            now_utc = datetime.datetime.now(datetime.timezone.utc)

            if expires_at < now_utc:
                logger.warning(f"Invite code expired for organization: {org_id}")
                print(f"{Fore.RED}Invite code has expired{Style.RESET_ALL}")
                return False
                
            # Check if user is already a member
            member_response = self.client.table('organization_members').select('*').eq('organization_id', org_id).eq('user_id', user_id).execute()
            if member_response.data:
                logger.warning(f"User is already a member of organization: {org_id}")
                print(f"{Fore.YELLOW}You are already a member of this organization{Style.RESET_ALL}")
                return False
                
            # Add user as member
            member_data = {
                'organization_id': org_id,
                'user_id': user_id,
                'joined_at': datetime.datetime.now().isoformat(),
                'role': 'member',
                'status': 'active'
            }
            
            self.client.table('organization_members').insert(member_data).execute()
            logger.debug(f"Added user as member to organization: {org_id}")
            
            # Update member count
            self.client.table('organizations').update({
                'member_count': org.get('member_count', 0) + 1,
                'updated_at': datetime.datetime.now().isoformat()
            }).eq('id', org_id).execute()
            
            # Create audit log
            self._create_audit_log(org_id, None, 'organization_joined')
            
            print(f"{Fore.GREEN}Successfully joined organization: {org['name']}{Style.RESET_ALL}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to join organization: {e}")
            print(f"{Fore.RED}Failed to join organization: {e}{Style.RESET_ALL}")
            return False
    
    def list_organization_members(self, org_id: str) -> List[Dict]:
        """List members of an organization"""
        user_id = self.auth.get_user_id()
        if not user_id:
            logger.warning("Cannot list members: User not authenticated")
            return []
            
        try:
            logger.info(f"Listing members for organization: {org_id}")
            
            # Verify user is a member of the organization
            member_check = self.client.table('organization_members').select('*').eq('organization_id', org_id).eq('user_id', user_id).execute()
            if not member_check.data:
                logger.warning(f"User is not a member of organization: {org_id}")
                print(f"{Fore.RED}You are not a member of this organization{Style.RESET_ALL}")
                return []
                
            # Get members with user information
            response = self.client.from_('organization_members').select(
                '*, users!inner(id, display_name, email)').eq('organization_id', org_id).execute()
                
            members = []
            if response.data:
                for item in response.data:
                    member = {
                        'id': item.get('user_id'),
                        'display_name': item.get('users', {}).get('display_name'),
                        'email': item.get('users', {}).get('email'),
                        'role': item.get('role'),
                        'joined_at': item.get('joined_at')
                    }
                    members.append(member)
                logger.debug(f"Found {len(members)} members in organization")
            
            return members
        except Exception as e:
            logger.error(f"Failed to list organization members: {e}")
            return []
    
    def regenerate_invite_code(self, org_id: str) -> Optional[str]:
        """Regenerate invite code for an organization"""
        user_id = self.auth.get_user_id()
        if not user_id:
            logger.warning("Cannot regenerate invite code: User not authenticated")
            return None
            
        try:
            logger.info(f"Regenerating invite code for organization: {org_id}")
            
            # Verify user is admin of the organization
            admin_check = self.client.table('organization_members').select('*')\
                .eq('organization_id', org_id).eq('user_id', user_id).eq('role', 'admin').execute()
            if not admin_check.data:
                logger.warning(f"User is not an admin of organization: {org_id}")
                print(f"{Fore.RED}You must be an admin to regenerate the invite code{Style.RESET_ALL}")
                return None
                
            # Generate new invite code
            invite_code = str(uuid.uuid4())[:8].upper()
            invite_expires_at = datetime.datetime.now() + datetime.timedelta(days=20)
            
            # Update organization
            self.client.table('organizations').update({
                'invite_code': invite_code,
                'invite_code_expires_at': invite_expires_at.isoformat(),
                'updated_at': datetime.datetime.now().isoformat()
            }).eq('id', org_id).execute()
            
            # Create audit log
            self._create_audit_log(org_id, None, 'invite_code_regenerated')
            
            logger.debug(f"Regenerated invite code for organization: {org_id}")
            print(f"{Fore.GREEN}Invite code regenerated successfully!{Style.RESET_ALL}")
            print(f"New invite code: {Fore.YELLOW}{invite_code}{Style.RESET_ALL}")
            
            return invite_code
            
        except Exception as e:
            logger.error(f"Failed to regenerate invite code: {e}")
            print(f"{Fore.RED}Failed to regenerate invite code: {e}{Style.RESET_ALL}")
            return None
    
    def toggle_invites(self, org_id: str, enabled: bool) -> bool:
        """Enable or disable invites for an organization"""
        user_id = self.auth.get_user_id()
        if not user_id:
            logger.warning("Cannot toggle invites: User not authenticated")
            return False
            
        try:
            logger.info(f"{'Enabling' if enabled else 'Disabling'} invites for organization: {org_id}")
            
            # Verify user is admin of the organization
            admin_check = self.client.table('organization_members').select('*')\
                .eq('organization_id', org_id).eq('user_id', user_id).eq('role', 'admin').execute()
            if not admin_check.data:
                logger.warning(f"User is not an admin of organization: {org_id}")
                print(f"{Fore.RED}You must be an admin to modify invite settings{Style.RESET_ALL}")
                return False
                
            # Update organization
            self.client.table('organizations').update({
                'invite_enabled': enabled,
                'updated_at': datetime.datetime.now().isoformat()
            }).eq('id', org_id).execute()
            
            # Create audit log
            self._create_audit_log(org_id, None, 'invites_toggled')
            
            logger.debug(f"{'Enabled' if enabled else 'Disabled'} invites for organization: {org_id}")
            print(f"{Fore.GREEN}Invites are now {'enabled' if enabled else 'disabled'}{Style.RESET_ALL}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to toggle invites: {e}")
            print(f"{Fore.RED}Failed to toggle invites: {e}{Style.RESET_ALL}")
            return False
    
    def check_encryption_eligibility(self, org_id: str) -> Dict:
        """Check if the organization is eligible for encryption"""
        user_id = self.auth.get_user_id()
        if not user_id:
            return {
                'eligible': False,
                'member_count_met': False,
                'cloud_storage_met': False,
                'member_count': 0,
                'required_count': MIN_ORG_MEMBERS,
                'members_without_cloud': []
            }
            
        try:
            logger.info(f"Checking encryption eligibility for organization: {org_id}")
            
            # Get organization members
            members_response = self.client.from_('organization_members').select(
                '*, users!inner(id, display_name, email, cloud_connected)'
            ).eq('organization_id', org_id).execute()
            
            if not members_response.data:
                return {
                    'eligible': False,
                    'member_count_met': False,
                    'cloud_storage_met': False,
                    'member_count': 0,
                    'required_count': MIN_ORG_MEMBERS,
                    'members_without_cloud': []
                }
            
            members = members_response.data
            member_count = len(members)
            member_count_met = member_count >= MIN_ORG_MEMBERS
            
            # Check cloud storage status for all members
            members_without_cloud = []
            for member in members:
                user_data = member['users']
                if not user_data.get('cloud_connected', False):
                    members_without_cloud.append({
                        'display_name': user_data.get('display_name'),
                        'email': user_data.get('email')
                    })
            
            cloud_storage_met = len(members_without_cloud) == 0
            
            return {
                'eligible': member_count_met and cloud_storage_met,
                'member_count_met': member_count_met,
                'cloud_storage_met': cloud_storage_met,
                'member_count': member_count,
                'required_count': MIN_ORG_MEMBERS,
                'members_without_cloud': members_without_cloud
            }
                
        except Exception as e:
            logger.error(f"Failed to check encryption eligibility: {e}")
            raise
    
    def _create_audit_log(self, org_id: str, file_id: Optional[str], action: str, details: Dict = None) -> None:
        """Create an audit log entry"""
        user_id = self.auth.get_user_id()
        if not user_id:
            return
            
        try:
            log_data = {
                'user_id': user_id,
                'organization_id': org_id,
                'action': action,
                'timestamp': datetime.datetime.now().isoformat(),
                'details': json.dumps(details) if details else None
            }
            
            if file_id:
                log_data['file_id'] = file_id
                
            self.client.table('audit_logs').insert(log_data).execute()
            logger.debug(f"Created audit log: {action}")
        except Exception as e:
            logger.warning(f"Failed to create audit log: {e}")

    def remove_member(self, org_id: str, member_id: str) -> bool:
        """Remove a member from an organization"""
        user_id = self.auth.get_user_id()
        if not user_id:
            logger.warning("Cannot remove member: User not authenticated")
            raise ValueError("User not authenticated")
            
        try:
            logger.info(f"Removing member {member_id} from organization {org_id}")
            
            # Verify user is admin of the organization
            admin_check = self.client.table('organization_members').select('*')\
                .eq('organization_id', org_id).eq('user_id', user_id).eq('role', 'admin').execute()
            if not admin_check.data:
                logger.warning(f"User is not an admin of organization: {org_id}")
                raise ValueError("You must be an admin to remove members")
            
            # Remove member
            self.client.table('organization_members').delete().eq('organization_id', org_id).eq('user_id', member_id).execute()
            
            # Update member count
            self.client.table('organizations').update({
                'member_count': self.client.raw(f"member_count - 1"),
                'updated_at': datetime.datetime.now().isoformat()
            }).eq('id', org_id).execute()
            
            # Create audit log
            self._create_audit_log(org_id, None, 'member_removed', {'removed_user_id': member_id})
            
            logger.info("Successfully removed member from organization")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove member: {e}")
            raise
