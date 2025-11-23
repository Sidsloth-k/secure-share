# Data Flow Diagrams

## Complete System Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SECURE SHARE DATA FLOW                            │
└─────────────────────────────────────────────────────────────────────┘

┌──────────┐
│   User   │
└────┬─────┘
     │
     │ 1. Register/Login
     ▼
┌─────────────────┐
│  Supabase Auth  │◄─────────────────┐
│  (JWT Tokens)   │                 │
└────┬────────────┘                 │
     │                              │
     │ 2. Authenticated Session     │
     ▼
┌─────────────────────────────────┐
│   Secure Share CLI Application   │
│   • Main Menu                    │
│   • Organization Management      │
│   • File Management              │
│   • Account Settings             │
└────┬────────────────────────────┘
     │
     │ 3. User Operations
     ▼
┌─────────────────────────────────────────────────────────────┐
│                    OPERATION FLOWS                            │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  FILE UPLOAD:                                                 │
│  User → Select File → Encrypt Locally → Generate Shares      │
│       → Upload Encrypted File (Supabase Storage)             │
│       → Distribute Shares (Cloud Storage)                    │
│       → Store Metadata (Supabase Database)                   │
│                                                               │
│  FILE DECRYPTION:                                             │
│  User → Request Decryption → Members Submit Shares           │
│       → Collect Shares (Threshold Check)                     │
│       → Reconstruct Key (Lagrange Interpolation)             │
│       → Decrypt File → Download Decrypted File               │
│                                                               │
│  ORGANIZATION MANAGEMENT:                                     │
│  User → Create/Join Org → Invite Members                     │
│       → Manage Roles → Connect Cloud Storage                 │
└─────────────────────────────────────────────────────────────┘
     │
     │ 4. Data Storage
     ▼
┌─────────────────────────────────────────────────────────────┐
│                    STORAGE LAYERS                             │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  SUPABASE DATABASE (Metadata)                        │   │
│  │  • users, organizations, files                       │   │
│  │  • key_shares (metadata only)                        │   │
│  │  • decryption_requests, audit_logs                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  SUPABASE STORAGE (Encrypted Files)                  │   │
│  │  • Bucket: encrypted-files                            │   │
│  │  • Contains: AES-256-GCM encrypted file data         │   │
│  │  • Access: RLS policies enforce organization access  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  CLOUD STORAGE (Key Shares - Distributed)            │   │
│  │  • Google Drive: Member 1's account                  │   │
│  │  • Google Drive: Member 2's account                   │   │
│  │  • Google Drive: Member N's account                  │   │
│  │  • Each member controls their own shares              │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Authentication Flow

```
┌─────────────────────────────────────────────────────────────┐
│                  AUTHENTICATION FLOW                         │
└─────────────────────────────────────────────────────────────┘

┌──────────┐
│   User   │
└────┬─────┘
     │
     │ 1. Start Application
     ▼
┌─────────────────────┐
│  Secure Share CLI   │
│  (main.py)          │
└────┬────────────────┘
     │
     │ 2. Check Session
     ▼
┌─────────────────────────────────┐
│  Session Storage                │
│  • Development: File-based       │
│  • Production: Database         │
└────┬────────────────────────────┘
     │
     │ 3a. Session Valid?
     │     YES → Continue to Main Menu
     │
     │ 3b. Session Invalid/Expired
     ▼
┌─────────────────────┐
│  Login/Register     │
│  (auth/pages/)      │
└────┬────────────────┘
     │
     │ 4. User Credentials
     ▼
┌─────────────────────┐
│  Supabase Auth      │
│  • Email/Password    │
│  • JWT Token        │
└────┬────────────────┘
     │
     │ 5. Token Received
     ▼
┌─────────────────────────────────┐
│  Token Manager                  │
│  • Store JWT                    │
│  • Auto-refresh before expiry    │
│  • Session encryption (optional) │
└────┬────────────────────────────┘
     │
     │ 6. Authenticated
     ▼
┌─────────────────────┐
│  Main Menu          │
│  • Organizations    │
│  • Files            │
│  • Account          │
└─────────────────────┘
```

## File Upload Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                  FILE UPLOAD DATA FLOW                        │
└─────────────────────────────────────────────────────────────┘

┌──────────┐
│   User   │
└────┬─────┘
     │
     │ 1. Select File + Organization + Threshold + Password
     ▼
┌─────────────────────────────────┐
│  File Manager (UploadMixin)      │
│  • Validate organization         │
│  • Get member list               │
│  • Check: members >= threshold  │
└────┬────────────────────────────┘
     │
     │ 2. Generate Encryption Key
     ▼
┌─────────────────────────────────┐
│  Key Generation (utils.py)       │
│  • Password + Salt               │
│  • PBKDF2-HMAC-SHA256            │
│  • 100,000 iterations            │
│  • Output: 32-byte key           │
└────┬────────────────────────────┘
     │
     │ 3. Encrypt File
     ▼
┌─────────────────────────────────┐
│  File Encryption (utils.py)      │
│  • AES-256-GCM                   │
│  • 12-byte nonce                 │
│  • Authenticated encryption      │
│  • Output: encrypted_data + nonce │
└────┬────────────────────────────┘
     │
     │ 4. Generate Shares
     ▼
┌─────────────────────────────────┐
│  Shamir Secret Sharing          │
│  (file_manager/shamir.py)       │
│  • Prime: 2²⁵⁶ - 189            │
│  • Generate n shares (n=members)│
│  • Threshold: t (user-specified) │
│  • Output: [(x₁,y₁),...,(xₙ,yₙ)]│
└────┬────────────────────────────┘
     │
     │ 5. Distribute Shares
     ▼
┌─────────────────────────────────────────────────────────────┐
│  For Each Member:                                             │
│  ├─► Get cloud credentials                                   │
│  ├─► Package share as ZIP                                    │
│  ├─► Upload to member's cloud storage                        │
│  │   • Google Drive: SecureShare_KeyShares/share_{id}.zip   │
│  └─► Store metadata in key_shares table                     │
└────┬────────────────────────────────────────────────────────┘
     │
     │ 6. Upload Encrypted File
     ▼
┌─────────────────────────────────┐
│  Supabase Storage               │
│  • Bucket: encrypted-files      │
│  • Path: {file_id}/{filename}   │
│  • RLS: Organization members    │
└────┬────────────────────────────┘
     │
     │ 7. Store Metadata
     ▼
┌─────────────────────────────────┐
│  Supabase Database              │
│  • files table: File metadata   │
│  • key_shares table: Share refs │
│  • audit_logs: Upload event     │
└─────────────────────────────────┘
```

## Decryption Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                  DECRYPTION DATA FLOW                         │
└─────────────────────────────────────────────────────────────┘

┌──────────┐
│ Requester│
└────┬─────┘
     │
     │ 1. Request Decryption
     ▼
┌─────────────────────────────────┐
│  Create Decryption Request      │
│  • decryption_requests table    │
│  • status = 'pending'           │
│  • threshold = file.threshold    │
│  • expires_at = now() + 24h    │
└────┬────────────────────────────┘
     │
     │ 2. Members Notified
     ▼
┌─────────────────────────────────────────────────────────────┐
│  For Each Organization Member:                               │
│  ├─► Member sees pending request                            │
│  ├─► Member retrieves share from cloud storage              │
│  │   • Authenticate with cloud provider                     │
│  │   • Locate: SecureShare_KeyShares/share_{file_id}.zip   │
│  │   • Download and extract share data                      │
│  └─► Member submits share                                   │
└────┬────────────────────────────────────────────────────────┘
     │
     │ 3. Share Submission
     ▼
┌─────────────────────────────────┐
│  Share Collection               │
│  • Cache share in temp_shares/  │
│  • Update current_shares count  │
│  • Check: current_shares >= threshold?                      │
└────┬────────────────────────────┘
     │
     │ 4a. Threshold NOT Met
     │     → Continue waiting
     │
     │ 4b. Threshold Met
     ▼
┌─────────────────────────────────┐
│  Key Reconstruction              │
│  (file_manager/shamir.py)       │
│  • Load all collected shares    │
│  • Lagrange interpolation       │
│  • Reconstruct 32-byte key     │
└────┬────────────────────────────┘
     │
     │ 5. Download Encrypted File
     ▼
┌─────────────────────────────────┐
│  Supabase Storage               │
│  • Download: {file_id}/{name}   │
│  • Returns: encrypted_data      │
└────┬────────────────────────────┘
     │
     │ 6. Decrypt File
     ▼
┌─────────────────────────────────┐
│  File Decryption (utils.py)     │
│  • AES-256-GCM decryption       │
│  • Key: Reconstructed key       │
│  • Nonce: From file record       │
│  • Output: Decrypted file data  │
└────┬────────────────────────────┘
     │
     │ 7. Save Decrypted File
     ▼
┌─────────────────────────────────┐
│  Local Storage                  │
│  • Path: temp_decrypted/        │
│  • Status: 'ready'              │
│  • Available for download       │
│  • Auto-delete after 24h        │
└─────────────────────────────────┘
```

