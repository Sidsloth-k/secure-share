# Critical Issue: Key Share Redistribution When Members Leave Organizations

## 🚨 Status: CRITICAL - Data Loss Risk

**Priority:** HIGH  
**Severity:** CRITICAL  
**Impact:** Permanent data loss if not addressed

---

## Executive Summary

The current system has a **critical flaw** that can result in **permanent data loss** when organization members who hold key shares leave the organization. There is currently **no fallback mechanism** to ensure remaining members can still decrypt files, which can make files permanently inaccessible if the decryption threshold cannot be met.

---

## Problem Statement

### The Issue

When a member is removed from an organization:

1. **Their key shares remain in the database** (linked to `user_id`, not org membership)
2. **Their key shares remain in cloud storage** (in their personal Google Drive/Dropbox/OneDrive)
3. **No redistribution occurs** - remaining members cannot access those shares
4. **No threshold adjustment** - the original threshold remains unchanged
5. **No warnings** - the system doesn't check if removal will break decryption

### Example Scenario

```
Initial State:
- Organization has 5 members
- File uploaded with threshold = 4 (requires 4 shares to decrypt)
- 5 key shares distributed (one per member)

After 2 Members Leave:
- Remaining members: 3
- Threshold still: 4
- Available shares: 3 (from remaining members)
- Result: ❌ CANNOT DECRYPT - Permanently locked!
```

### Current Code Behavior

**File:** `org_manager.py:431-465` - `remove_member()`

```python
def remove_member(self, org_id: str, member_id: str) -> bool:
    # Only removes from organization_members table
    # Updates member count
    # Does NOT handle key shares
    # Does NOT redistribute shares
    # Does NOT adjust thresholds
    # Does NOT check decryption feasibility
```

**What Happens:**
- ✅ Member removed from `organization_members` table
- ✅ Member count decremented
- ❌ Key shares remain in database (linked to `user_id`)
- ❌ Key shares remain in cloud storage
- ❌ No redistribution to remaining members
- ❌ No threshold adjustment
- ❌ No feasibility check

---

## Impact Analysis

### Immediate Risks

1. **Permanent Data Loss**
   - Files become permanently undecryptable if threshold cannot be met
   - No recovery mechanism exists

2. **Silent Failures**
   - Decryption requests fail without clear explanation
   - Users don't understand why decryption is impossible

3. **No Warnings**
   - System doesn't alert admins before removal
   - No prevention of problematic removals

4. **Orphaned Shares**
   - Shares remain in former members' cloud storage indefinitely
   - Database records remain but are inaccessible to remaining members

### Affected Components

- **File Decryption:** Cannot proceed if threshold unreachable
- **Member Management:** No safeguards during removal
- **Key Share Management:** No redistribution mechanism
- **Database Schema:** Key shares linked to `user_id`, not org membership

---

## Root Cause Analysis

### Design Flaws

1. **Key Shares Linked to User ID, Not Membership**
   - Shares are stored with `user_id` foreign key
   - No check for active organization membership
   - Shares persist even after member removal

2. **No Lifecycle Management**
   - Shares created once during upload
   - Never updated or redistributed
   - No mechanism to handle membership changes

3. **Static Thresholds**
   - Thresholds set at upload time
   - Never adjusted for membership changes
   - No dynamic threshold management

4. **No Pre-removal Validation**
   - No check before member removal
   - No calculation of decryption feasibility
   - No warnings or blocking mechanisms

---

## Proposed Solutions

### Solution 1: Pre-Removal Validation & Warnings ⚠️

**Priority:** HIGH (Immediate prevention)

**Implementation:**
- Before removing a member, check all files in the organization
- For each file, calculate: `remaining_members >= threshold`
- If any file would become undecryptable:
  - **Block removal** OR
  - **Require explicit override** with acknowledgment of data loss risk

**Code Location:** `org_manager.py` - `remove_member()`

**Pseudocode:**
```python
def check_decryption_feasibility(org_id: str, member_to_remove: str) -> Dict:
    """Check if removing member would break decryption for any files"""
    files = get_all_org_files(org_id)
    current_members = get_org_members(org_id)
    remaining_count = len(current_members) - 1
    
    problematic_files = []
    for file in files:
        if remaining_count < file['threshold']:
            problematic_files.append({
                'file_id': file['id'],
                'file_name': file['name'],
                'threshold': file['threshold'],
                'remaining_members': remaining_count
            })
    
    return {
        'can_remove': len(problematic_files) == 0,
        'problematic_files': problematic_files
    }
```

**Benefits:**
- Prevents accidental data loss
- Raises awareness of consequences
- Forces explicit decisions

**Limitations:**
- Doesn't solve the problem, only prevents it
- May block legitimate removals

---

### Solution 2: Share Redistribution (Password Required) 🔄

**Priority:** MEDIUM (Requires original password)

**Implementation:**
- When a member is removed, attempt to redistribute their shares
- Requires the **original uploader's password** to reconstruct the encryption key
- Steps:
  1. Collect remaining shares from active members
  2. If enough shares exist to reconstruct key:
     - Use uploader's password + salt to verify/regenerate key
     - Generate new shares for remaining members
     - Distribute new shares to cloud storage
     - Update database records
  3. Delete old shares from former member's cloud storage (if possible)

**Code Location:** `file_manager.py` - New method `redistribute_shares()`

**Pseudocode:**
```python
def redistribute_shares_for_file(
    file_id: str, 
    removed_member_id: str,
    uploader_password: str
) -> bool:
    """Redistribute shares when a member leaves"""
    # Get file metadata
    file = get_file(file_id)
    
    # Get remaining active members
    remaining_members = get_active_org_members(file['organization_id'])
    
    # Collect existing shares from remaining members
    existing_shares = collect_shares_from_members(file_id, remaining_members)
    
    # If we have enough shares, reconstruct key
    if len(existing_shares) >= file['threshold']:
        key = reconstruct_key_from_shares(existing_shares)
        
        # Verify key using password (optional verification)
        # Generate new shares for all remaining members
        new_shares = generate_shares(key, len(remaining_members), file['threshold'])
        
        # Distribute new shares
        for member, share in zip(remaining_members, new_shares):
            upload_share_to_cloud(member, share, file_id)
            update_key_share_record(file_id, member['id'], share)
        
        # Mark old shares as invalid
        mark_shares_invalid(file_id, removed_member_id)
        
        return True
    else:
        raise ValueError("Not enough shares to redistribute")
```

**Benefits:**
- Maintains decryption capability
- Preserves security model
- Active redistribution

**Limitations:**
- Requires original uploader's password
- Complex implementation
- May fail if shares are inaccessible
- Cannot delete shares from former member's cloud storage

---

### Solution 3: Threshold Adjustment (Admin Override) 📊

**Priority:** MEDIUM (Flexible but risky)

**Implementation:**
- Allow admins to **lower thresholds** for files
- Only allow if: `new_threshold <= remaining_members`
- Require explicit confirmation and audit logging
- Warn about security implications

**Code Location:** `file_manager.py` - New method `adjust_file_threshold()`

**Pseudocode:**
```python
def adjust_file_threshold(
    file_id: str, 
    new_threshold: int,
    admin_id: str
) -> bool:
    """Adjust decryption threshold for a file"""
    file = get_file(file_id)
    current_members = get_active_org_members(file['organization_id'])
    
    # Validation
    if new_threshold > len(current_members):
        raise ValueError("Threshold cannot exceed remaining members")
    
    if new_threshold < 3:
        raise ValueError("Threshold must be at least 3")
    
    if new_threshold >= file['threshold']:
        raise ValueError("Can only lower threshold, not increase")
    
    # Update threshold
    update_file_threshold(file_id, new_threshold)
    
    # Audit log
    create_audit_log(
        file['organization_id'],
        file_id,
        'threshold_adjusted',
        {
            'old_threshold': file['threshold'],
            'new_threshold': new_threshold,
            'adjusted_by': admin_id,
            'reason': 'Member removal'
        }
    )
    
    return True
```

**Benefits:**
- Simple to implement
- Immediate solution
- No password required

**Limitations:**
- Reduces security (lower threshold = easier to decrypt)
- May violate original security requirements
- Doesn't redistribute shares (just changes requirement)

---

### Solution 4: Share Recovery from Former Members 👥

**Priority:** LOW (Manual process)

**Implementation:**
- Allow admins to request shares from former members
- Manual process requiring cooperation
- Former members can submit their shares before leaving
- System tracks "recoverable" shares

**Code Location:** New module `cli/files/recover_share.py`

**Benefits:**
- No password required
- Maintains original security model
- Voluntary cooperation

**Limitations:**
- Relies on former member cooperation
- May not be possible if member is unavailable
- Manual and time-consuming

---

### Solution 5: Hybrid Approach (Recommended) 🎯

**Priority:** HIGH (Comprehensive solution)

**Implementation Strategy:**

1. **Immediate Prevention (Solution 1)**
   - Implement pre-removal validation
   - Block or warn about problematic removals

2. **Automatic Redistribution (Solution 2)**
   - Attempt automatic redistribution when possible
   - Require uploader password for verification
   - Fall back to threshold adjustment if redistribution fails

3. **Threshold Adjustment (Solution 3)**
   - Allow as last resort with proper warnings
   - Require admin override and audit logging

4. **Recovery Mechanism (Solution 4)**
   - Provide manual recovery option
   - Track recoverable shares

**Workflow:**
```
Member Removal Request
    ↓
Check Decryption Feasibility
    ↓
If problematic:
    ├─ Attempt Share Redistribution (if password available)
    │   ├─ Success → Complete removal
    │   └─ Failure → Offer threshold adjustment
    │
    ├─ Offer Threshold Adjustment (admin override)
    │   └─ If accepted → Complete removal
    │
    └─ Block Removal (with explanation)
```

---

## Implementation Plan

### Phase 1: Prevention (Week 1)
- [ ] Implement `check_decryption_feasibility()` function
- [ ] Add validation to `remove_member()` method
- [ ] Add warning messages and blocking logic
- [ ] Add unit tests for validation

### Phase 2: Redistribution (Week 2-3)
- [ ] Implement `redistribute_shares_for_file()` method
- [ ] Add password verification mechanism
- [ ] Implement share collection from active members
- [ ] Add cloud storage share deletion (where possible)
- [ ] Add comprehensive error handling

### Phase 3: Threshold Adjustment (Week 3)
- [ ] Implement `adjust_file_threshold()` method
- [ ] Add admin override UI/CLI
- [ ] Add audit logging
- [ ] Add security warnings

### Phase 4: Recovery Tools (Week 4)
- [ ] Implement share recovery interface
- [ ] Add tracking for recoverable shares
- [ ] Add documentation for manual recovery

### Phase 5: Testing & Documentation (Week 5)
- [ ] Comprehensive integration tests
- [ ] Edge case testing
- [ ] User documentation
- [ ] Admin guide

---

## Database Schema Considerations

### Current Schema Issues

```sql
-- Key shares table
CREATE TABLE key_shares (
    id UUID PRIMARY KEY,
    file_id UUID REFERENCES files(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,  -- ❌ Not linked to org membership
    share_index INTEGER NOT NULL,
    status TEXT DEFAULT 'pending',
    cloud_path TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Proposed Enhancements

1. **Add Active Status Tracking**
   ```sql
   ALTER TABLE key_shares 
   ADD COLUMN is_active BOOLEAN DEFAULT TRUE;
   
   -- Update when member leaves
   UPDATE key_shares 
   SET is_active = FALSE 
   WHERE user_id = ? AND file_id IN (
       SELECT id FROM files WHERE organization_id = ?
   );
   ```

2. **Add Redistribution History**
   ```sql
   CREATE TABLE key_share_redistributions (
       id UUID PRIMARY KEY,
       file_id UUID REFERENCES files(id),
       original_user_id UUID REFERENCES users(id),
       redistributed_at TIMESTAMPTZ DEFAULT NOW(),
       redistributed_by UUID REFERENCES users(id),
       reason TEXT
   );
   ```

3. **Add Threshold History**
   ```sql
   ALTER TABLE files 
   ADD COLUMN threshold_history JSONB;
   -- Store: [{"threshold": 4, "changed_at": "...", "changed_by": "..."}]
   ```

---

## Security Considerations

### Risks of Each Solution

1. **Share Redistribution**
   - Risk: Requires password exposure during redistribution
   - Mitigation: Use secure password input, clear from memory immediately

2. **Threshold Adjustment**
   - Risk: Reduces security by lowering threshold
   - Mitigation: Require explicit admin approval, audit all changes

3. **Share Recovery**
   - Risk: Former members may be untrustworthy
   - Mitigation: Verify share authenticity, track recovery attempts

### Best Practices

- Always audit log all share operations
- Require multiple admin approvals for threshold reductions
- Encrypt passwords in memory during redistribution
- Validate shares before accepting them
- Implement rate limiting on redistribution attempts

---

## Testing Requirements

### Unit Tests

- [ ] Test `check_decryption_feasibility()` with various scenarios
- [ ] Test `redistribute_shares_for_file()` with valid/invalid inputs
- [ ] Test `adjust_file_threshold()` validation logic
- [ ] Test edge cases (single member, all members leave, etc.)

### Integration Tests

- [ ] Test complete member removal workflow
- [ ] Test share redistribution end-to-end
- [ ] Test threshold adjustment workflow
- [ ] Test failure scenarios and rollbacks

### Edge Cases

- [ ] Organization with only threshold number of members
- [ ] Multiple members leaving simultaneously
- [ ] Member leaving while decryption request is pending
- [ ] File with threshold = total_shares (all shares required)

---

## Migration Strategy

### For Existing Data

1. **Audit Current State**
   - Identify files with orphaned shares
   - Calculate decryption feasibility for all files
   - Generate report of at-risk files

2. **Gradual Rollout**
   - Deploy prevention first (Solution 1)
   - Add redistribution (Solution 2) after testing
   - Enable threshold adjustment (Solution 3) as needed

3. **Data Cleanup**
   - Mark inactive shares in database
   - Attempt to clean up cloud storage (where possible)
   - Document orphaned shares for manual recovery

---

## Related Issues

- **Key Share Persistence:** Shares remain in cloud storage indefinitely (see: Key Share Lifecycle documentation)
- **Database Schema:** Key shares not linked to organization membership
- **Member Management:** No lifecycle hooks for membership changes

---

## References

- **File:** `org_manager.py:431-465` - `remove_member()`
- **File:** `file_manager.py:106-210` - `upload_file()`
- **File:** `file_manager.py:491-546` - `submit_key_share()`
- **Database Schema:** `database/migrate/001_initial_schema.sql:67-77`

---

## Conclusion

This is a **critical issue** that can result in permanent data loss. The recommended approach is to implement **Solution 5 (Hybrid Approach)** which combines prevention, automatic redistribution, threshold adjustment, and recovery mechanisms.

**Immediate Action Required:**
1. Implement pre-removal validation (Solution 1) to prevent new cases
2. Audit existing files for decryption feasibility
3. Plan implementation of redistribution mechanism (Solution 2)

---

deletion map 

┌─────────────────────────────────────────────────────────────┐
│                   FILE DELETION WORKFLOW                     │
└─────────────────────────────────────────────────────────────┘

Step 1: Authorization & Validation
  ├─ Verify user is org admin
  ├─ Verify file exists and belongs to org
  ├─ Check if file is already deleted
  └─ Create pre-deletion audit log

Step 2: Collect Share Information (Non-blocking)
  ├─ Query all key_shares for file_id
  ├─ Group by cloud_provider (google_drive, dropbox, onedrive)
  ├─ Extract user_id, cloud_credentials, cloud_path
  └─ Prepare deletion tasks

Step 3: Delete Cloud Storage Shares (Best Effort, Async)
  ├─ For each share:
  │   ├─ Get user's cloud credentials
  │   ├─ Authenticate with cloud provider
  │   ├─ Find share file (folder + filename)
  │   ├─ Delete file from cloud storage
  │   └─ Log success/failure
  ├─ Continue even if some deletions fail
  └─ Track deletion status for reporting

Step 4: Delete Encrypted File from Supabase Storage (Critical)
  ├─ Use storage_client.from_("encrypted-files").remove()
  ├─ Delete using storage_path from files table
  └─ MUST succeed or abort deletion

Step 5: Delete Database Records (Critical, with CASCADE)
  ├─ Delete from files table
  ├─ CASCADE automatically deletes:
  │   ├─ key_shares (all shares for file_id)
  │   └─ decryption_requests (all requests for file_id)
  └─ MUST succeed or rollback

Step 6: Post-Deletion Actions
  ├─ Create audit log with deletion summary
  ├─ Report deletion status:
  │   ├─ Database: ✅ Deleted
  │   ├─ Storage: ✅ Deleted
  │   ├─ Cloud shares: X/Y deleted successfully
  │   └─ Failures: List any failed share deletions
  └─ Return detailed status report

**Last Updated:** 2025-01-12  
**Status:** 🔴 CRITICAL - Requires Immediate Attention  
**Assigned To:** [To be assigned]  
**Estimated Effort:** 4-5 weeks for full implementation

