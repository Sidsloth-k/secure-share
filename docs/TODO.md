# TODO & Milestones

## 🔴 Critical Issues

### [CRITICAL] Key Share Redistribution When Members Leave
**Status:** 🔴 Not Started  
**Priority:** HIGH  
**Severity:** CRITICAL  
**Documentation:** [docs/KEY_SHARE_REDISTRIBUTION_ISSUE.md](docs/KEY_SHARE_REDISTRIBUTION_ISSUE.md)

**Problem:** Members leaving organizations can make files permanently undecryptable if threshold cannot be met.

**Milestones:**

#### Phase 1: Prevention (Week 1) - 🔴 Not Started
- [ ] Implement `check_decryption_feasibility()` function in `org_manager.py`
- [ ] Add validation to `remove_member()` method
- [ ] Add warning messages and blocking logic
- [ ] Add unit tests for validation
- [ ] Update CLI to show warnings before member removal

#### Phase 2: Share Redistribution (Week 2-3) - 🔴 Not Started
- [ ] Implement `redistribute_shares_for_file()` method in `file_manager.py`
- [ ] Add password verification mechanism
- [ ] Implement share collection from active members
- [ ] Add cloud storage share deletion (where possible)
- [ ] Add comprehensive error handling
- [ ] Add integration tests

#### Phase 3: Threshold Adjustment (Week 3) - 🔴 Not Started
- [ ] Implement `adjust_file_threshold()` method in `file_manager.py`
- [ ] Add admin override CLI interface
- [ ] Add audit logging for threshold changes
- [ ] Add security warnings in UI
- [ ] Add unit and integration tests

#### Phase 4: Recovery Tools (Week 4) - 🔴 Not Started
- [ ] Implement share recovery interface (`cli/files/recover_share.py`)
- [ ] Add tracking for recoverable shares
- [ ] Add documentation for manual recovery process
- [ ] Add admin tools for share recovery

#### Phase 5: Testing & Documentation (Week 5) - 🔴 Not Started
- [ ] Comprehensive integration tests
- [ ] Edge case testing (single member, all members leave, etc.)
- [ ] User documentation
- [ ] Admin guide
- [ ] Migration guide for existing data

**Estimated Total Effort:** 4-5 weeks  
**Dependencies:** None  
**Blocks:** None

---

## 🟡 High Priority Issues

### Storage Upload RLS Policy Error
**Status:** ✅ Completed  
**Priority:** HIGH  
**Issue:** `new row violates row-level security policy` when uploading files to Supabase storage

**What Was Done:**
- ✅ Created comprehensive documentation (`docs/STORAGE_RLS_SETUP.md`) with step-by-step instructions
- ✅ Documented RLS policy requirements for INSERT, SELECT, and DELETE operations on storage bucket
- ✅ Added detailed error handling in `file_manager/mixins/upload.py` (lines 91-102) that detects RLS errors and provides helpful guidance
- ✅ Documented policy conditions for authenticated organization members
- ✅ Added troubleshooting section for common RLS issues

**Bugs Fixed:**
- Fixed: Storage upload failures now show clear error messages pointing to solution
- Fixed: Added helpful error messages that guide users to configure storage bucket policies
- Fixed: Error detection for RLS violations with specific guidance

**Changes Made:**
- `docs/STORAGE_RLS_SETUP.md` - Complete guide for configuring Supabase Storage RLS policies
- `file_manager/mixins/upload.py:91-102` - Enhanced error handling with RLS-specific guidance
- Error messages now include direct links to documentation and step-by-step instructions

**Related Files:**
- `file_manager/mixins/upload.py:91-102` - Storage upload error handling
- `docs/STORAGE_RLS_SETUP.md` - Complete RLS setup documentation
- `database/migrate/001_initial_schema.sql` - Database RLS policies (separate from storage RLS)

---

## 🟢 Medium Priority Issues

### File Deletion with Share Cleanup
**Status:** 🟡 Planning  
**Priority:** MEDIUM  
**Issue:** Key shares persist indefinitely in cloud storage even after file deletion. The `delete_file()` method is currently missing and needs to be implemented with proper cleanup of:
- Database records (files, key_shares, decryption_requests)
- Supabase Storage files (encrypted file)
- Cloud storage shares (Google Drive, Dropbox, OneDrive)

**Current State:**
- Database has CASCADE deletes configured (`ON DELETE CASCADE` on key_shares, decryption_requests)
- CLI calls `file_manager.delete_file()` but method doesn't exist yet
- Cloud storage shares are stored in user's personal cloud storage (Google Drive folder: `SecureShare_KeyShares`)
- No mechanism exists to delete shares from cloud storage when files are deleted

**Roadmap:**

#### Phase 1: Core Delete Method Implementation (Week 1)
**Location:** `file_manager/mixins/maintenance.py` or new `file_manager/mixins/deletion.py`

**Tasks:**
- [ ] Implement `delete_file(file_id: str, org_id: str)` method in FileManager
- [ ] Add authorization check (only org admins can delete files)
- [ ] Mark file as 'deleted' in database (soft delete) OR hard delete
- [ ] Delete encrypted file from Supabase Storage bucket
- [ ] Handle database CASCADE deletes (key_shares, decryption_requests will auto-delete)
- [ ] Add audit logging for file deletion
- [ ] Add error handling and rollback mechanism

**Database Operations:**
- Update `files.status` to 'deleted' OR delete record entirely
- CASCADE will handle: `key_shares`, `decryption_requests` (automatic)
- Delete from Supabase Storage: `storage.objects` where `name = files.storage_path`

#### Phase 2: Cloud Storage Share Cleanup (Week 1-2)
**Location:** `file_manager/cloud_storage.py` - Add deletion methods

**Tasks:**
- [ ] Implement `_delete_from_google_drive(file_id: str, user_id: str)` method
  - Find share file in user's `SecureShare_KeyShares` folder
  - Delete `share_{file_id}.zip` from Google Drive
  - Handle cases where file doesn't exist (already deleted)
  - Handle authentication failures gracefully
- [ ] Implement `_delete_from_dropbox(file_id: str, user_id: str)` method (when Dropbox is implemented)
- [ ] Implement `_delete_from_onedrive(file_id: str, user_id: str)` method (when OneDrive is implemented)
- [ ] Add retry logic with exponential backoff for cloud deletions
- [ ] Add error handling for partial failures (some shares deleted, others not)

**Share Cleanup Strategy:**
1. Query all `key_shares` for the file_id
2. For each share:
   - Get user's `cloud_provider` and `cloud_credentials`
   - Call appropriate deletion method based on provider
   - Log success/failure for each share
   - Continue even if some deletions fail (best effort)
3. Track which shares were successfully deleted vs failed

#### Phase 3: Integration & Error Handling (Week 2)
**Location:** `file_manager/mixins/deletion.py` (new file)

**Tasks:**
- [ ] Integrate cloud storage cleanup into `delete_file()` method
- [ ] Implement transaction-like behavior (best effort, log failures)
- [ ] Add comprehensive error handling:
  - Handle missing cloud credentials
  - Handle expired OAuth tokens
  - Handle network failures
  - Handle files already deleted from cloud
- [ ] Add cleanup status reporting (how many shares deleted successfully)
- [ ] Add rollback capability if critical steps fail
- [ ] Add warning messages for partial cleanup failures

**Error Handling Strategy:**
- Database deletion: Must succeed (critical)
- Supabase Storage deletion: Must succeed (critical)
- Cloud share deletion: Best effort (non-critical, log failures)
- Continue deletion even if some cloud shares fail to delete
- Report summary of cleanup status to user

#### Phase 4: CLI Integration & User Experience (Week 2)
**Location:** `cli/files/delete_file.py`

**Tasks:**
- [ ] Update CLI to show deletion progress
- [ ] Display cleanup status (shares deleted, failures)
- [ ] Add confirmation prompt with details about what will be deleted
- [ ] Show warnings for partial cleanup failures
- [ ] Add option to retry failed share deletions
- [ ] Improve error messages for users

#### Phase 5: Testing & Edge Cases (Week 3)
**Tasks:**
- [ ] Unit tests for `delete_file()` method
- [ ] Integration tests for database cleanup
- [ ] Integration tests for Supabase Storage deletion
- [ ] Integration tests for Google Drive share deletion
- [ ] Test edge cases:
  - File with no shares
  - File with shares in multiple cloud providers
  - File with expired/invalid cloud credentials
  - File already partially deleted
  - Network failures during deletion
  - User not authorized to delete
- [ ] Test CASCADE delete behavior
- [ ] Test audit log creation

#### Phase 6: Manual Cleanup Tools (Week 3-4)
**Location:** `file_manager/mixins/maintenance.py` or new admin tools

**Tasks:**
- [ ] Implement `cleanup_orphaned_shares()` method for admin use
  - Find shares in cloud storage that don't have corresponding file records
  - Optionally delete orphaned shares
- [ ] Implement `list_shares_for_file(file_id: str)` method
  - Show all shares and their locations
  - Show deletion status
- [ ] Add CLI command for manual share cleanup
- [ ] Add admin tools for bulk cleanup operations

**Implementation Notes:**

**File Structure:**
```
file_manager/
  mixins/
    deletion.py (NEW) - Main deletion logic
  cloud_storage.py - Add _delete_from_* methods
```

**Method Signature:**
```python
def delete_file(self, file_id: str, org_id: str) -> Dict[str, Any]:
    """
    Delete a file and all associated resources.
    
    Returns:
        {
            'success': bool,
            'file_deleted': bool,
            'storage_deleted': bool,
            'shares_deleted': int,
            'shares_failed': int,
            'errors': List[str]
        }
    """
```

**Dependencies:**
- Requires cloud storage provider implementations (Google Drive complete, Dropbox/OneDrive pending)
- Requires proper authentication for cloud storage access
- Database CASCADE deletes already configured

**Security Considerations:**
- Only organization admins should be able to delete files
- Audit all deletion operations
- Verify user has permission before deletion
- Don't expose sensitive information in error messages

**Related Files:**
- `file_manager/mixins/maintenance.py` - Maintenance utilities (may add deletion here)
- `file_manager/cloud_storage.py` - Cloud storage operations (add deletion methods)
- `file_manager/mixins/upload.py:212-295` - Cloud storage upload methods (reference for deletion)
- `cli/files/delete_file.py` - CLI interface (calls file_manager.delete_file)
- `database/migrate/001_initial_schema.sql:68-77` - key_shares table (CASCADE delete configured)

---

## 📋 Feature Enhancements

### Database Schema Improvements
**Status:** 📋 Planned  
**Priority:** MEDIUM

**Tasks:**
- [ ] Add `is_active` flag to `key_shares` table
- [ ] Create `key_share_redistributions` table for audit trail
- [ ] Add `threshold_history` to `files` table
- [ ] Create migration script for schema updates

### Enhanced Audit Logging
**Status:** 📋 Planned  
**Priority:** LOW

**Tasks:**
- [ ] Add more detailed audit logs for share operations
- [ ] Add audit log querying interface
- [ ] Add audit log export functionality

### Cloud Storage Provider Expansion
**Status:** 📋 Planned  
**Priority:** LOW

**Tasks:**
- [ ] Complete Dropbox integration (`file_manager.py:382-385`)
- [ ] Complete OneDrive integration (`file_manager.py:387-390`)
- [ ] Add support for additional cloud providers
- [ ] Add cloud provider migration tools

---

## 🐛 Bug Fixes

### None Currently Tracked

---

## 📚 Documentation

### [ ] Complete API Documentation
- [ ] Document all file_manager methods
- [ ] Document all org_manager methods
- [ ] Add code examples

### [ ] User Guides
- [ ] Quick start guide
- [ ] Organization management guide
- [ ] File encryption/decryption guide
- [ ] Troubleshooting guide

### [ ] Developer Documentation
- [ ] Architecture overview
- [ ] Database schema documentation
- [ ] Security model documentation
- [ ] Contributing guidelines

---

## 🔄 Refactoring

### Code Organization
**Status:** 🔄 Planned  
**Priority:** LOW

**Tasks:**
- [ ] Extract cloud storage operations to separate module
- [ ] Improve error handling consistency
- [ ] Add type hints throughout codebase
- [ ] Improve logging consistency

---

## Notes

- Critical issues should be addressed before new features
- All security-related changes require thorough testing
- Database migrations should be tested in development first
- Breaking changes should be documented in CHANGELOG.md

---

**Last Updated:** 2025-01-23

