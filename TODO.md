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
**Status:** 🟡 In Progress  
**Priority:** HIGH  
**Issue:** `new row violates row-level security policy` when uploading files to Supabase storage

**Tasks:**
- [ ] Review Supabase storage bucket RLS policies
- [ ] Update storage bucket policies to allow authenticated uploads
- [ ] Verify file upload works correctly
- [ ] Add error handling for storage upload failures

**Related Files:**
- `file_manager.py:130-142` - Storage upload code
- `database/migrate/001_initial_schema.sql` - RLS policies

---

## 🟢 Medium Priority Issues

### Key Share Lifecycle Management
**Status:** 🟢 Not Started  
**Priority:** MEDIUM  
**Issue:** Key shares persist indefinitely in cloud storage even after file deletion

**Tasks:**
- [ ] Implement cloud storage cleanup when files are deleted
- [ ] Add expiration mechanism for key shares (optional)
- [ ] Add manual cleanup tools for admins
- [ ] Document key share lifecycle

**Related Files:**
- `file_manager.py:627-649` - `delete_file()` method
- `file_manager.py:212-295` - Cloud storage upload methods

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

**Last Updated:** 2025-01-12

