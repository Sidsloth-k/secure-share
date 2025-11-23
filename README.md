# Secure Share

**A Revolutionary Collaborative File Sharing Platform with Threshold Cryptography**

---

## 📋 Table of Contents

1. [What is Secure Share?](#-what-is-secure-share)
2. [How It Works](#-how-it-works)
3. [Problems It Solves](#-problems-it-solves)
4. [Technical Architecture](#-technical-architecture)
5. [Database Schema](#-database-schema)
6. [Data Flow Diagrams](#-data-flow-diagrams)
7. [Getting Started](#-getting-started)
8. [Current Issues & Limitations](#-current-issues--limitations)
9. [Future Vision](#-future-vision)
10. [Impact on Society](#-impact-on-society)
11. [Project History](#-project-history)

---

## 🌟 What is Secure Share?

Secure Share is an advanced command-line application that revolutionizes how teams exchange sensitive files. Born from a university research project, this application has evolved into a dedicated effort to push the boundaries of secure, collaborative file sharing. By combining client-side encryption, threshold secret sharing (Shamir's Secret Sharing), and distributed cloud storage, Secure Share ensures that **no single actor—not even the platform administrators—can decrypt files on their own**.

### Core Concept

Secure Share addresses a critical problem in modern digital collaboration: **How can teams securely share sensitive files when no single person should have complete access?**

Traditional file sharing solutions have fundamental security flaws:
- **Centralized storage** means administrators can access your files
- **Single encryption keys** create a single point of failure
- **Trust requirements** force you to trust platform providers completely
- **Data breaches** expose all files if one key is compromised

Secure Share solves these problems by implementing a **distributed trust model** where:
- Files are encrypted **locally** before upload (zero-knowledge architecture)
- Encryption keys are split into multiple shares using **threshold cryptography**
- Each organization member stores their share in their **personal cloud storage** (Google Drive, Dropbox, OneDrive)
- A **minimum threshold** of members must cooperate to decrypt files
- **No single person or system** can decrypt files alone

---

## 🔐 How It Works

### Core Architecture

Secure Share uses a three-layer architecture:

```
┌─────────────────────────────────────────────┐
│         Secure Share CLI (UI Layer)          │
│  • Main Menu Navigation                      │
│  • User Input/Output                         │
│  • Terminal Interface                        │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│      Application Services (Logic Layer)      │
│  ┌──────────────────────────────────────┐   │
│  │  Auth Module                        │   │
│  │  • User Authentication              │   │
│  │  • Session Management               │   │
│  │  • Token Refresh                    │   │
│  └──────────────────────────────────────┘   │
│  ┌──────────────────────────────────────┐   │
│  │  Organization Manager               │   │
│  │  • Create/Join Organizations        │   │
│  │  • Member Management                │   │
│  │  • Invite Code Generation            │   │
│  └──────────────────────────────────────┘   │
│  ┌──────────────────────────────────────┐   │
│  │  File Manager                        │   │
│  │  • File Encryption/Decryption         │   │
│  │  • Shamir Secret Sharing             │   │
│  │  • Cloud Storage Integration         │   │
│  │  • Share Distribution                │   │
│  └──────────────────────────────────────┘   │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│      External Systems (Infrastructure)       │
│  ┌──────────────────────────────────────┐   │
│  │  Supabase                            │   │
│  │  • PostgreSQL Database               │   │
│  │  • Supabase Auth                     │   │
│  │  • Supabase Storage (encrypted files)│   │
│  └──────────────────────────────────────┘   │
│  ┌──────────────────────────────────────┐   │
│  │  Cloud Storage Providers             │   │
│  │  • Google Drive (✅ Implemented)     │   │
│  │  • Dropbox (🚧 Planned)              │   │
│  │  • OneDrive (🚧 Planned)             │   │
│  └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

### Technical Process Flow

#### 1. File Upload & Encryption Process

```
┌─────────────────────────────────────────────────────────────┐
│                    FILE UPLOAD WORKFLOW                      │
└─────────────────────────────────────────────────────────────┘

Step 1: User Initiates Upload
    │
    ├─► User selects file from local system
    ├─► User selects organization
    ├─► User sets decryption threshold (e.g., 4 out of 5 members)
    └─► User provides password for key derivation
    │
    ▼
Step 2: Local Encryption
    │
    ├─► Generate encryption key from password using PBKDF2-HMAC-SHA256
    │   • Salt: 16 random bytes
    │   • Iterations: 100,000
    │   • Key length: 32 bytes (256 bits)
    │
    ├─► Encrypt file using AES-256-GCM
    │   • Algorithm: AES-GCM (Galois/Counter Mode)
    │   • Nonce: 12 random bytes (96 bits)
    │   • Authenticated encryption with associated data
    │
    └─► Store encrypted file temporarily
    │
    ▼
Step 3: Key Share Generation
    │
    ├─► Get organization member list
    ├─► Validate: members >= threshold
    │
    ├─► Generate shares using Shamir's Secret Sharing
    │   • Prime modulus: 2²⁵⁶ - 189
    │   • Number of shares (n): Number of organization members
    │   • Threshold (t): Minimum shares required (user-specified)
    │   • Each share: (x, y) where x = share_index, y = 32-byte value
    │
    └─► Create share records in database
    │
    ▼
Step 4: Share Distribution
    │
    ├─► For each organization member:
    │   │
    │   ├─► Retrieve member's cloud storage credentials
    │   ├─► Package share as ZIP file
    │   ├─► Upload to member's personal cloud storage
    │   │   • Google Drive: SecureShare_KeyShares/ folder
    │   │   • File name: share_{file_id}.zip
    │   │
    │   └─► Update key_shares table:
    │       • status = 'pending'
    │       • cloud_path = path in cloud storage
    │
    ▼
Step 5: Encrypted File Storage
    │
    ├─► Upload encrypted file to Supabase Storage
    │   • Bucket: encrypted-files
    │   • Path: {file_id}/{original_filename}
    │
    └─► Create file record in database:
        • id, name, size, type
        • organization_id, uploader_id
        • storage_path, threshold, total_shares
        • nonce (base64), salt (base64)
        • status = 'available'
    │
    ▼
Step 6: Completion
    │
    └─► File encrypted and shares distributed
        All members notified (via database records)
```

#### 2. Threshold Secret Sharing (Shamir's Scheme)

**Mathematical Foundation:**

Secure Share uses **Shamir's Secret Sharing** algorithm with the following parameters:

| Parameter | Value | Description |
|-----------|-------|-------------|
| **Prime Modulus** | 2²⁵⁶ - 189 | Large prime for finite field arithmetic |
| **Secret** | 32 bytes (256 bits) | AES-256 encryption key |
| **Shares (n)** | Number of org members | Total shares generated |
| **Threshold (t)** | User-specified (≥3) | Minimum shares required for reconstruction |

**How It Works:**

1. **Share Generation:**
   - Convert 32-byte encryption key to integer
   - Generate random polynomial: `P(x) = secret + a₁x + a₂x² + ... + aₜ₋₁xᵗ⁻¹` (mod prime)
   - Evaluate polynomial at points x = 1, 2, 3, ..., n
   - Each share is (x, P(x)) where P(x) is stored as 32 bytes

2. **Share Properties:**
   - **Information-theoretic security**: Any t-1 shares reveal zero information about the secret
   - **Independence**: Shares are mathematically independent
   - **Threshold property**: Exactly t shares are needed (no more, no less)

3. **Reconstruction:**
   - Uses **Lagrange interpolation** to reconstruct the polynomial
   - Formula: `secret = Σ(yᵢ × Lᵢ(0))` where Lᵢ is the i-th Lagrange basis polynomial
   - Result: Original 32-byte encryption key

**Example Scenario:**

```
Organization: 5 members
File uploaded with threshold = 4

Share Distribution:
├─ Member 1: Share (1, y₁) → Stored in Member 1's Google Drive
├─ Member 2: Share (2, y₂) → Stored in Member 2's Google Drive
├─ Member 3: Share (3, y₃) → Stored in Member 3's Google Drive
├─ Member 4: Share (4, y₄) → Stored in Member 4's Google Drive
└─ Member 5: Share (5, y₅) → Stored in Member 5's Google Drive

Decryption Requirements:
✓ Any 4 of 5 shares can reconstruct the key
✗ 3 or fewer shares cannot reveal any information
✓ All 5 shares can reconstruct the key
```

#### 3. Decryption Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                  DECRYPTION WORKFLOW                         │
└─────────────────────────────────────────────────────────────┘

Step 1: Decryption Request
    │
    ├─► User selects file to decrypt
    ├─► System creates decryption_request record:
    │   • status = 'pending'
    │   • threshold = file.threshold
    │   • current_shares = 0
    │   • expires_at = now() + 24 hours
    │
    └─► All organization members notified (via database query)
    │
    ▼
Step 2: Share Collection
    │
    ├─► Each member retrieves their share:
    │   │
    │   ├─► Member authenticates with cloud storage
    │   ├─► Locate share file: SecureShare_KeyShares/share_{file_id}.zip
    │   ├─► Download and extract share data
    │   └─► Submit share to system
    │
    ├─► System updates decryption_request:
    │   • current_shares += 1
    │   • Share cached in temp_shares/{request_id}/
    │
    └─► Repeat until threshold reached
    │
    ▼
Step 3: Threshold Check
    │
    ├─► System checks: current_shares >= threshold?
    │
    ├─► If NO: Continue waiting for more shares
    │
    └─► If YES: Proceed to reconstruction
    │
    ▼
Step 4: Key Reconstruction
    │
    ├─► Load all collected shares from cache
    ├─► Apply Lagrange interpolation:
    │   • For each share (xᵢ, yᵢ):
    │     - Calculate Lagrange basis polynomial Lᵢ(0)
    │     - Multiply: yᵢ × Lᵢ(0)
    │   • Sum all terms: secret = Σ(yᵢ × Lᵢ(0))
    │
    └─► Reconstruct 32-byte encryption key
    │
    ▼
Step 5: File Decryption
    │
    ├─► Download encrypted file from Supabase Storage
    ├─► Decrypt using AES-256-GCM:
    │   • Key: Reconstructed key
    │   • Nonce: From file record (base64 decoded)
    │   • Algorithm: AES-GCM decryption
    │
    ├─► Save decrypted file to temp_decrypted/
    │
    └─► Update decryption_request:
        • status = 'ready'
        • File available for download
    │
    ▼
Step 6: File Retrieval
    │
    └─► User downloads decrypted file
        File automatically deleted after expiration (24 hours)
```

#### 4. Distributed Storage Model

```
┌─────────────────────────────────────────────────────────────┐
│              DISTRIBUTED STORAGE ARCHITECTURE                  │
└─────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    SUPABASE (Centralized)                    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │  PostgreSQL Database                               │     │
│  │  • users                                           │     │
│  │  • organizations                                   │     │
│  │  • organization_members                            │     │
│  │  • files (metadata only)                           │     │
│  │  • key_shares (metadata only)                      │     │
│  │  • decryption_requests                             │     │
│  │  • audit_logs                                      │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │  Supabase Storage                                  │     │
│  │  • Bucket: encrypted-files                         │     │
│  │  • Contains: Encrypted file data only               │     │
│  │  • Access: Row-Level Security (RLS) policies       │     │
│  │  • Note: Supabase cannot decrypt files             │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │  Supabase Auth                                    │     │
│  │  • User authentication                             │     │
│  │  • JWT token management                           │     │
│  │  • Session management                              │     │
│  └────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────┘
                            │
                            │ Metadata & Encrypted Files
                            │
┌───────────────────────────┴──────────────────────────────────┐
│              CLOUD STORAGE (Distributed)                    │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Member 1's  │  │ Member 2's  │  │ Member N's  │     │
│  │ Google Drive │  │ Google Drive │  │ Google Drive │     │
│  │              │  │              │  │              │     │
│  │ Share 1      │  │ Share 2      │  │ Share N      │     │
│  │ (Encrypted)  │  │ (Encrypted)  │  │ (Encrypted)  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
│  Key Properties:                                              │
│  • Each member controls their own cloud storage              │
│  • Shares stored in personal accounts                       │
│  • No single point of failure                               │
│  • Platform cannot access shares                            │
└──────────────────────────────────────────────────────────────┘
```

**Security Guarantees:**

| Component | What It Stores | Who Can Access | Security Level |
|-----------|----------------|----------------|----------------|
| **Supabase Database** | Metadata, file records, share records | Organization members (via RLS) | High (encrypted at rest) |
| **Supabase Storage** | Encrypted file data | Organization members (via RLS) | High (encrypted, but platform can see encrypted data) |
| **Cloud Storage** | Key shares (encrypted) | Individual member only | Highest (member controls access) |
| **Local System** | Decrypted files (temporary) | User only | Highest (local control) |

---

## 🎯 Problems It Solves

### 1. Eliminates Single Points of Failure

**Traditional Problem:**
- Single encryption key stored on server
- If key is compromised, all files are exposed
- Server breach = complete data loss

**Secure Share Solution:**
- No single encryption key exists
- Keys split into shares across multiple locations
- Even if one member's cloud storage is breached, files remain secure
- Platform administrators cannot access files

### 2. Enforces Collaborative Access Control

**Traditional Problem:**
- Single admin can access all files
- No requirement for multiple approvals
- Risk of unauthorized access by one person

**Secure Share Solution:**
- Requires multiple trusted parties to agree before decryption
- Threshold cryptography enforces minimum cooperation
- Prevents unauthorized access by any single individual
- Ideal for sensitive documents requiring multi-party approval

### 3. Maintains Privacy in Cloud Environments

**Traditional Problem:**
- Files uploaded to cloud in plaintext or with server-side encryption
- Cloud providers can read file contents
- Metadata and content stored together

**Secure Share Solution:**
- Files encrypted before leaving user's device (zero-knowledge)
- Cloud providers cannot read file contents
- Metadata stored separately from encrypted content
- Platform operates on encrypted data only

### 4. Audit Trail & Transparency

**Traditional Problem:**
- Limited visibility into file access
- No tracking of who accessed what
- Difficult to audit security events

**Secure Share Solution:**
- All operations logged in audit trails
- Decryption requests tracked and visible to organization admins
- Complete history of file access and member actions
- Transparent security model

### 5. Scalable Organization Management

**Traditional Problem:**
- Difficult to manage multi-organization access
- Complex permission systems
- Limited collaboration features

**Secure Share Solution:**
- Create organizations with invite codes
- Manage member roles (admin/member)
- Automatic member counting and validation
- Support for multiple organizations per user
- Simple, intuitive management interface

---

## 🏗️ Technical Architecture

### Module Structure

```
secure-share/
├── main.py                      # Application entrypoint
│
├── auth/                        # Authentication & session management
│   ├── __init__.py
│   ├── async_auth.py           # Async authentication support
│   ├── client_manager.py       # Supabase client management
│   ├── db_storage.py           # Database session storage
│   ├── encryption.py           # Session encryption
│   ├── error_handler.py        # Error handling utilities
│   ├── metrics.py              # Token refresh metrics
│   ├── session_validator.py    # Session validation
│   ├── storage.py              # File-based session storage
│   ├── token_manager.py        # JWT token management
│   └── pages/                  # Login/register UI
│       ├── login.py
│       └── register.py
│
├── org_manager.py              # Organization CRUD operations
│
├── file_manager/               # File encryption & management
│   ├── __init__.py
│   ├── core.py                # Main FileManager class
│   ├── shamir.py              # Shamir's Secret Sharing implementation
│   ├── cloud_storage.py       # Cloud storage integration
│   ├── network_utils.py       # Network retry logic
│   ├── status_tracker.py      # File status tracking
│   └── mixins/                # Feature mixins
│       ├── upload.py          # File upload logic
│       ├── decryption.py     # Decryption workflow
│       ├── verification.py  # File verification
│       └── maintenance.py   # Maintenance operations
│
├── cli/                        # Command-line interface
│   ├── __init__.py
│   ├── main_menu.py           # Main menu handler
│   ├── organization_menu.py   # Organization menu
│   ├── file_menu.py           # File operations menu
│   ├── account_menu.py        # Account settings menu
│   ├── terminal_utils.py      # Terminal utilities
│   ├── exit_handler.py        # Application exit handling
│   ├── organizations/         # Organization operations
│   │   ├── create.py
│   │   ├── join.py
│   │   ├── view.py
│   │   └── manage.py
│   ├── files/                 # File operations
│   │   ├── upload.py
│   │   ├── request_decryption.py
│   │   ├── submit_key_share.py
│   │   ├── check_decrypted.py
│   │   ├── verify_encryption.py
│   │   └── delete_file.py
│   └── cloud/                 # Cloud storage operations
│       ├── connect.py
│       ├── disconnect.py
│       └── providers/
│           ├── google_drive.py
│           ├── dropbox.py
│           └── onedrive.py
│
├── database/                   # Database setup
│   ├── migrate/               # Migration scripts
│   │   ├── 001_initial_schema.sql
│   │   ├── 002_user_sessions.sql
│   │   └── run_migration.py
│   └── seed/                  # Seed data scripts
│       ├── seed_data.py
│       └── test_password_update.py
│
├── docs/                       # Documentation
│   ├── auth/                  # Authentication documentation
│   ├── KEY_SHARE_REDISTRIBUTION_ISSUE.md
│   ├── STORAGE_RLS_SETUP.md
│   └── TODO.md
│
├── tests/                      # Test files
│   └── test_auth_session.py
│
├── utils.py                    # Utility functions (encryption, etc.)
├── requirements.txt            # Python dependencies
├── env.example                 # Environment variable template
└── README.md                   # This file
```

### Key Technologies

| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.10+ | Core application language |
| **Supabase** | 1.2.0 | Backend-as-a-Service (auth, database, storage) |
| **PostgreSQL** | (via Supabase) | Database |
| **Cryptography** | Latest | AES-256-GCM encryption, PBKDF2 key derivation |
| **Google API Client** | 2.86.0 | Google Drive integration |
| **OAuth 2.0** | - | Cloud storage authentication |
| **Colorama** | 0.4.6 | Terminal color output |
| **python-dotenv** | 1.0.1 | Environment variable management |

### Security Features

| Feature | Implementation | Security Level |
|---------|----------------|----------------|
| **Client-Side Encryption** | AES-256-GCM | Military-grade encryption |
| **Threshold Cryptography** | Shamir's Secret Sharing (2²⁵⁶ - 189 prime) | Information-theoretic security |
| **Zero-Knowledge Architecture** | Files encrypted before upload | Platform cannot decrypt |
| **Row-Level Security** | PostgreSQL RLS policies | Database-level access control |
| **Audit Logging** | Complete operation history | Full transparency |
| **Session Encryption** | Optional Fernet encryption | Encrypted at rest |
| **Token Management** | JWT with automatic refresh | Secure authentication |

---

## 📊 Database Schema

### Entity Relationship Diagram

```
┌─────────────┐         ┌──────────────────────┐         ┌─────────────┐
│   users     │         │ organization_members │         │organizations│
├─────────────┤         ├──────────────────────┤         ├─────────────┤
│ id (PK)     │◄──┐     │ id (PK)              │     ┌──►│ id (PK)     │
│ email       │   │     │ organization_id (FK) │     │   │ name        │
│ display_name│   │     │ user_id (FK)          │─────┘   │ admin_id(FK)│
│ cloud_*     │   │     │ role                 │         │ invite_code │
└─────────────┘   │     │ status               │         └─────────────┘
                  │     └──────────────────────┘
                  │
┌─────────────────┴─────────────────────────────────────────────────────┐
│                                                                        │
│  ┌─────────────┐         ┌──────────────┐         ┌──────────────┐  │
│  │   files     │         │  key_shares  │         │decryption_   │  │
│  ├─────────────┤         ├──────────────┤         │  requests    │  │
│  │ id (PK)     │◄─────────│ id (PK)      │         ├──────────────┤  │
│  │ name        │         │ file_id (FK) │         │ id (PK)       │  │
│  │ org_id (FK) │         │ user_id (FK) │         │ file_id (FK) │  │
│  │ uploader_id │         │ share_index  │         │ requester_id  │  │
│  │ threshold   │         │ cloud_path   │         │ status        │  │
│  │ nonce       │         │ status       │         │ current_shares│  │
│  │ salt        │         └──────────────┘         └──────────────┘  │
│  └─────────────┘                                                      │
│                                                                        │
│  ┌─────────────┐                                                      │
│  │ audit_logs  │                                                      │
│  ├─────────────┤                                                      │
│  │ id (PK)     │                                                      │
│  │ user_id(FK) │                                                      │
│  │ org_id (FK) │                                                      │
│  │ file_id(FK)│                                                      │
│  │ action      │                                                      │
│  │ timestamp   │                                                      │
│  │ details     │                                                      │
│  └─────────────┘                                                      │
└────────────────────────────────────────────────────────────────────────┘
```

### Database Tables

#### 1. `users` Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY, DEFAULT uuid_generate_v4() | User unique identifier |
| `email` | TEXT | UNIQUE, NOT NULL | User email address |
| `display_name` | TEXT | NOT NULL | User display name |
| `cloud_connected` | BOOLEAN | DEFAULT FALSE | Whether cloud storage is connected |
| `cloud_provider` | TEXT | CHECK IN ('google_drive', 'dropbox', 'onedrive') | Cloud storage provider |
| `cloud_credentials` | JSONB | - | Encrypted cloud storage credentials |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Account creation timestamp |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last update timestamp |

**Indexes:**
- Primary key on `id`
- Unique index on `email`

#### 2. `organizations` Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY, DEFAULT uuid_generate_v4() | Organization unique identifier |
| `name` | TEXT | NOT NULL | Organization name |
| `invite_code` | TEXT | UNIQUE | Unique invite code for joining |
| `invite_code_expires_at` | TIMESTAMPTZ | - | Invite code expiration time |
| `invite_enabled` | BOOLEAN | DEFAULT TRUE | Whether invites are enabled |
| `admin_id` | UUID | REFERENCES users(id) ON DELETE CASCADE | Organization administrator |
| `member_count` | INTEGER | DEFAULT 0 | Current number of members |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Organization creation timestamp |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last update timestamp |

**Indexes:**
- Primary key on `id`
- Unique index on `invite_code`
- Foreign key index on `admin_id`

#### 3. `organization_members` Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY, DEFAULT uuid_generate_v4() | Membership record ID |
| `organization_id` | UUID | NOT NULL, REFERENCES organizations(id) ON DELETE CASCADE | Organization reference |
| `user_id` | UUID | NOT NULL, REFERENCES users(id) ON DELETE CASCADE | User reference |
| `role` | TEXT | NOT NULL, CHECK IN ('admin', 'member') | Member role |
| `status` | TEXT | NOT NULL, DEFAULT 'active', CHECK IN ('active', 'inactive') | Membership status |
| `joined_at` | TIMESTAMPTZ | DEFAULT NOW() | Join timestamp |

**Indexes:**
- Primary key on `id`
- Unique constraint on (`organization_id`, `user_id`)
- Index on `organization_id`
- Index on `user_id`

#### 4. `files` Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY, DEFAULT uuid_generate_v4() | File unique identifier |
| `name` | TEXT | NOT NULL | Original file name |
| `size` | BIGINT | NOT NULL | File size in bytes |
| `type` | TEXT | - | MIME type |
| `organization_id` | UUID | NOT NULL, REFERENCES organizations(id) ON DELETE CASCADE | Organization reference |
| `uploader_id` | UUID | NOT NULL, REFERENCES users(id) ON DELETE CASCADE | User who uploaded |
| `uploaded_at` | TIMESTAMPTZ | DEFAULT NOW() | Upload timestamp |
| `encrypted_at` | TIMESTAMPTZ | - | Encryption timestamp |
| `storage_path` | TEXT | NOT NULL | Path in Supabase Storage |
| `threshold` | INTEGER | NOT NULL, CHECK (threshold >= 3) | Minimum shares required |
| `total_shares` | INTEGER | NOT NULL | Total number of shares |
| `nonce` | TEXT | NOT NULL | AES-GCM nonce (base64) |
| `salt` | TEXT | NOT NULL | PBKDF2 salt (base64) |
| `status` | TEXT | NOT NULL, DEFAULT 'available', CHECK IN ('available', 'pending_decryption', 'decrypted', 'deleted') | File status |

**Indexes:**
- Primary key on `id`
- Index on `organization_id`
- Index on `uploader_id`

#### 5. `key_shares` Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY, DEFAULT uuid_generate_v4() | Share unique identifier |
| `file_id` | UUID | NOT NULL, REFERENCES files(id) ON DELETE CASCADE | File reference |
| `user_id` | UUID | NOT NULL, REFERENCES users(id) ON DELETE CASCADE | Share owner |
| `share_index` | INTEGER | NOT NULL | Share index (x-coordinate in Shamir scheme) |
| `status` | TEXT | NOT NULL, DEFAULT 'pending', CHECK IN ('pending', 'retrieved') | Share status |
| `cloud_path` | TEXT | NOT NULL | Path in member's cloud storage |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Share creation timestamp |

**Indexes:**
- Primary key on `id`
- Unique constraint on (`file_id`, `user_id`)
- Index on `file_id`
- Index on `user_id`

#### 6. `decryption_requests` Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY, DEFAULT uuid_generate_v4() | Request unique identifier |
| `file_id` | UUID | NOT NULL, REFERENCES files(id) ON DELETE CASCADE | File reference |
| `requester_id` | UUID | NOT NULL, REFERENCES users(id) ON DELETE CASCADE | User requesting decryption |
| `requested_at` | TIMESTAMPTZ | DEFAULT NOW() | Request timestamp |
| `expires_at` | TIMESTAMPTZ | NOT NULL | Request expiration time |
| `status` | TEXT | NOT NULL, DEFAULT 'pending', CHECK IN ('pending', 'ready', 'expired', 'completed') | Request status |
| `current_shares` | INTEGER | DEFAULT 0 | Number of shares collected |
| `threshold` | INTEGER | NOT NULL | Required threshold for decryption |
| `message` | TEXT | - | Optional message from requester |

**Indexes:**
- Primary key on `id`
- Index on `file_id`
- Index on `status`

#### 7. `audit_logs` Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY, DEFAULT uuid_generate_v4() | Log unique identifier |
| `user_id` | UUID | REFERENCES users(id) ON DELETE SET NULL | User who performed action |
| `organization_id` | UUID | REFERENCES organizations(id) ON DELETE CASCADE | Organization reference |
| `file_id` | UUID | REFERENCES files(id) ON DELETE CASCADE | File reference (if applicable) |
| `action` | TEXT | NOT NULL | Action description |
| `timestamp` | TIMESTAMPTZ | DEFAULT NOW() | Action timestamp |
| `details` | JSONB | - | Additional action details |

**Indexes:**
- Primary key on `id`
- Index on `organization_id`
- Index on `file_id`

### Row-Level Security (RLS)

All tables have Row-Level Security enabled with policies that:

- **Users**: Can only read/update their own profile and profiles of organization members
- **Organizations**: Users can only access organizations they belong to
- **Files**: Users can only access files from their organizations
- **Key Shares**: Users can only access their own shares
- **Decryption Requests**: Users can only access requests for files in their organizations
- **Audit Logs**: Users can only read logs for their organizations

---

## 🔄 Data Flow Diagrams

### Complete System Data Flow

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

### Authentication Flow

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

### File Upload Data Flow

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

### Decryption Data Flow

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

---

## 🚀 Getting Started

### Prerequisites

| Requirement | Version | Description |
|-------------|---------|-------------|
| **Python** | 3.10+ | Core application language (tested on 3.10, 3.11, 3.12) |
| **Supabase Account** | - | Free tier works. Create at [supabase.com](https://supabase.com) |
| **Cloud Storage** | - | At least one: Google Drive (✅), Dropbox (🚧), OneDrive (🚧) |
| **Git** | - | Version control |
| **Terminal/Command Prompt** | - | CLI interface |

### Installation Steps

#### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd secure-share
```

#### Step 2: Create Virtual Environment

**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

**Linux/Mac:**
```bash
python -m venv .venv
source .venv/bin/activate
```

#### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

**Key Dependencies:**
- `supabase==1.2.0` - Backend services
- `cryptography` - AES-256-GCM encryption
- `google-api-python-client==2.86.0` - Google Drive integration
- `colorama==0.4.6` - Terminal colors
- `python-dotenv==1.0.1` - Environment variables

#### Step 4: Configure Environment

```bash
cp env.example .env
```

Edit `.env` and add your credentials:

```env
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Database (for migrations)
SUPABASE_DB_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres

# Google Drive OAuth (for cloud storage)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8080

# Environment Mode
ENVIRONMENT=development  # or 'production'
ENABLE_SESSION_ENCRYPTION=false  # true for production
```

#### Step 5: Initialize Database

```bash
# Run database migrations
python database/migrate/run_migration.py
```

This will:
- Create all database tables
- Set up Row-Level Security (RLS) policies
- Create indexes for performance
- Attempt to create `encrypted-files` storage bucket

**Optional: Seed Test Data**

```bash
python database/seed/seed_data.py
```

#### Step 6: Configure Supabase Storage

1. Go to Supabase Dashboard > Storage
2. Create bucket named `encrypted-files`
3. Set to **Private** (not public)
4. Configure RLS policies (see `docs/STORAGE_RLS_SETUP.md`)

**Storage RLS Policies Required:**
- **INSERT**: Allow authenticated users who are organization members
- **SELECT**: Allow authenticated users who are organization members
- **DELETE**: Allow organization admins only

#### Step 7: Start the Application

```bash
python main.py
```

### First-Time Setup

#### 1. Register an Account

1. Launch application: `python main.py`
2. Select "Register" from main menu
3. Enter email and password
4. Account created in Supabase Auth

#### 2. Connect Cloud Storage

1. Go to **Account Settings** > **Connect Cloud Storage**
2. Select provider: **Google Drive** (recommended)
3. Complete OAuth flow:
   - Browser opens for authentication
   - Grant permissions
   - Redirects back to application
4. Cloud storage now linked

**Google Drive Setup:**
- Create OAuth 2.0 credentials at [Google Cloud Console](https://console.cloud.google.com)
- Add redirect URI: `http://localhost:8080`
- Download credentials JSON (optional, can use env vars)

#### 3. Create or Join an Organization

**Create Organization:**
1. Navigate to **Organization Management** > **Create Organization**
2. Enter organization name
3. System generates unique invite code
4. Share invite code with members

**Join Organization:**
1. Navigate to **Organization Management** > **Join Organization**
2. Enter invite code from admin
3. Automatically added as member

**Requirements:**
- Minimum 5 members recommended for file operations
- Threshold must be ≤ number of members

#### 4. Upload Your First File

1. Navigate to **File Management** > **Upload File**
2. Select organization
3. Choose file from local system
4. Set threshold (e.g., 4 means 4 members must cooperate)
5. Enter password (used for key derivation)
6. File encrypted locally
7. Shares distributed to members' cloud storage
8. Encrypted file uploaded to Supabase Storage

---

## ⚠️ Current Issues & Limitations

### 🔴 Critical Issues

#### 1. Key Share Redistribution When Members Leave

**Status:** 🔴 CRITICAL - Data Loss Risk  
**Priority:** HIGH  
**Severity:** CRITICAL  
**Documentation:** `docs/KEY_SHARE_REDISTRIBUTION_ISSUE.md`

**Problem:**
When organization members who hold key shares leave, files can become permanently undecryptable if the threshold cannot be met.

**Example Scenario:**
```
Initial State:
- Organization: 5 members
- File uploaded with threshold = 4
- 5 key shares distributed

After 2 Members Leave:
- Remaining: 3 members
- Threshold still: 4
- Available shares: 3
- Result: ❌ CANNOT DECRYPT - Permanently locked!
```

**Current Workaround:**
- Do not remove members if it would break decryption thresholds
- Manually verify threshold feasibility before member removal
- Consider threshold when planning organization membership

**Planned Solutions:**
- Pre-removal validation with warnings
- Automatic share redistribution (requires uploader password)
- Threshold adjustment mechanism
- Share recovery tools

#### 2. File Deletion with Share Cleanup

**Status:** 🟡 In Progress  
**Priority:** MEDIUM

**Problem:**
When files are deleted, key shares remain in members' cloud storage indefinitely.

**Impact:**
- Orphaned shares consume cloud storage space
- No automatic cleanup mechanism
- Manual cleanup required

**Planned Solution:**
Automatic share deletion from cloud storage when files are deleted.

### 🟡 Known Limitations

| Limitation | Status | Impact |
|------------|--------|--------|
| **Cloud Storage Providers** | | |
| Google Drive | ✅ Fully implemented | Production ready |
| Dropbox | 🚧 Planned | Not yet implemented |
| OneDrive | 🚧 Planned | Not yet implemented |
| **Storage RLS Policies** | ⚠️ Manual setup required | See `docs/STORAGE_RLS_SETUP.md` |
| **Session Management** | ✅ Working | File-based (dev) or database (prod) |
| **Network Resilience** | ✅ Retry logic | Some operations may fail on interruptions |

### 🐛 Known Bugs

None currently tracked. See `docs/TODO.md` for detailed issue tracking.

---

## 🔮 Future Vision

### Current State: Cloud-Based Architecture

Secure Share currently operates on a **cloud-based infrastructure** using:
- **Supabase** for backend services (database, authentication, storage)
- **Personal cloud storage** (Google Drive, Dropbox, OneDrive) for key share distribution
- **Centralized metadata** with distributed key shares

This architecture provides:
- ✅ Fast deployment and scalability
- ✅ User-friendly cloud storage integration
- ✅ Reliable infrastructure
- ✅ Easy maintenance and updates

### Future Vision: Web3 & Blockchain Integration

**Long-term Goal:** Integrate Secure Share with **Web3 and blockchain technology** for enhanced security, decentralization, and immutability.

**Why Blockchain?**
- **True Decentralization**: No single point of control
- **Immutability**: Audit trails cannot be tampered with
- **Smart Contracts**: Automated threshold enforcement
- **Cryptographic Guarantees**: Enhanced security through blockchain cryptography
- **Trustless Architecture**: No need to trust platform providers

**Planned Integration Points:**

1. **Key Share Storage on Blockchain**
   - Store key share metadata on blockchain
   - Use smart contracts for share management
   - Immutable audit trail

2. **Decentralized File Storage**
   - IPFS (InterPlanetary File System) for encrypted file storage
   - Distributed hash table (DHT) for metadata
   - No single storage provider

3. **Smart Contract Threshold Enforcement**
   - Automated threshold checking
   - Automatic share collection
   - Decentralized decryption coordination

4. **Token-Based Access Control**
   - NFT-based organization membership
   - Token-gated file access
   - Decentralized governance

**Timeline:**
- **Phase 1 (Current)**: Perfect cloud-based architecture ✅
- **Phase 2**: Resolve critical issues, expand cloud providers 🚧
- **Phase 3**: Research and design blockchain architecture 📋
- **Phase 4**: Implement Web3 integration 🚧
- **Phase 5**: Hybrid cloud/blockchain deployment 📋

**Why Not Now?**
Blockchain integration requires:
- Complex cryptographic implementations
- Gas fees and transaction costs
- Slower transaction times
- Higher technical complexity
- User education on Web3 concepts

**Strategy:**
1. **First**: Perfect the cloud-based system
2. **Then**: Resolve all critical issues
3. **Next**: Expand cloud provider support
4. **Finally**: Integrate blockchain when cloud architecture is stable

This phased approach ensures:
- ✅ Users have a working, secure system now
- ✅ Critical issues are resolved before complexity increases
- ✅ Blockchain integration builds on a solid foundation
- ✅ Gradual migration path for users

---

## 🌍 Impact on Society

### How Secure Share Helps Society

#### 1. Protecting Sensitive Data

**Healthcare:**
- Medical records shared between specialists
- Patient privacy maintained
- Platform providers cannot access medical data
- Multi-party access control for sensitive cases

**Legal:**
- Confidential documents shared between law firms and clients
- Attorney-client privilege maintained
- No third-party access to legal documents
- Secure collaboration on case files

**Finance:**
- Financial documents requiring multiple approvals
- Board meeting minutes with restricted access
- Financial audits with enforced multi-party access
- Compliance with data protection regulations

**Government:**
- Sensitive information shared across departments
- Classified documents with enforced access control
- Inter-agency collaboration without data exposure
- National security information protection

#### 2. Democratizing Security

**Accessibility:**
- Enterprise-grade security for small teams
- No expensive infrastructure required
- Open-source approach allows security audits
- Free for individuals and small organizations

**Education:**
- Demonstrates practical cryptography
- Educational tool for security courses
- Research platform for threshold cryptography
- Inspires next generation of security professionals

#### 3. Enabling Secure Collaboration

**Remote Work:**
- Secure file sharing for distributed teams
- No VPN required for file access
- Cloud-based but zero-knowledge
- Works with existing cloud storage

**Research Collaboration:**
- Secure sharing of research data
- Multi-institution collaboration
- Intellectual property protection
- Academic research security

#### 4. Future of Security

**Innovation:**
- Demonstrates practical applications of threshold cryptography
- Sets precedent for zero-knowledge collaborative systems
- Inspires next generation of secure communication tools
- Advances the state of the art in distributed security

**Trust:**
- Reduces need to trust third-party platforms
- Mathematical guarantees of security
- Transparent security model
- Open-source for verification

---

## 📖 Project History

### Origins: University Research Project

Secure Share began as a **university research project** exploring practical applications of threshold cryptography and distributed systems. The initial goal was to demonstrate how cryptographic principles could solve real-world security problems in collaborative file sharing.

**Initial Objectives:**
- Implement Shamir's Secret Sharing algorithm
- Create a proof-of-concept file sharing system
- Demonstrate zero-knowledge architecture
- Explore distributed trust models

### Evolution: Dedicated Project

What started as an academic exercise has evolved into a **dedicated project** focused on creating a production-ready, secure file sharing platform. The project now represents a commitment to pushing the boundaries of what's possible in secure, collaborative systems.

**Current State:**
- ✅ Comprehensive error handling and user experience improvements
- ✅ Modular architecture for maintainability
- ✅ Extensive documentation for users and developers
- ✅ Active issue tracking and roadmap planning
- ✅ Production-ready cloud-based infrastructure

**Development Philosophy:**
- **Security First**: Every feature designed with security in mind
- **User Experience**: Complex cryptography made simple for users
- **Open Source**: Transparent, auditable codebase
- **Continuous Improvement**: Regular updates and issue resolution

### The Journey Forward

**Immediate Goals:**
- Resolve critical security issues
- Expand cloud storage provider support
- Improve user experience and documentation
- Build a community of contributors and users

**Long-term Vision:**
- Perfect Secure Share into a robust, production-ready platform
- Integrate Web3 and blockchain technology
- Explore advanced features (mobile apps, web interface)
- Set new standards for secure collaborative systems

**The Commitment:**
This project represents a dedication to creating a future where sensitive data can be shared securely without compromising privacy or requiring blind trust in platform providers. Every improvement, every bug fix, and every feature addition brings us closer to that vision.

---

## 📚 Documentation

### Essential Documentation

| Document | Description |
|----------|-------------|
| **[Database Setup](database/README.md)** | Database migration and seeding guide |
| **[Storage RLS Setup](docs/STORAGE_RLS_SETUP.md)** | Supabase Storage configuration instructions |
| **[Key Share Redistribution Issue](docs/KEY_SHARE_REDISTRIBUTION_ISSUE.md)** | Critical issue documentation and solutions |
| **[TODO & Milestones](docs/TODO.md)** | Project roadmap and issue tracking |
| **[Auth Documentation](docs/auth/README.md)** | Authentication system details |

### Additional Resources

- `docs/auth/HOW_IT_WORKS.md` - Authentication flow details
- `docs/auth/SCALABILITY.md` - Scalability considerations
- `docs/auth/RECOMMENDATIONS.md` - Best practices

---

## 🛠️ Development

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_auth_session.py
```

### Code Style

The project follows standard Python conventions:
- Type hints encouraged for new code
- PEP 8 style guide
- Comprehensive error handling
- Detailed logging

### Contributing

1. Review `docs/TODO.md` for current issues
2. Check critical issues in `docs/KEY_SHARE_REDISTRIBUTION_ISSUE.md`
3. Follow existing code patterns
4. Add tests for new features
5. Update documentation as needed

---

## 🐛 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| **Storage upload fails with RLS error** | Configure storage bucket RLS policies (see `docs/STORAGE_RLS_SETUP.md`) |
| **Cannot decrypt file** | Check: Are enough members submitting shares? (threshold requirement) |
| **Cloud storage connection fails** | Verify OAuth credentials in `.env`, re-authenticate |
| **Database connection errors** | Verify `SUPABASE_URL` and `SUPABASE_KEY` in `.env` |
| **Session expired** | Re-login through main menu, check session storage configuration |

---

## 📄 License

This project is private and confidential. Distribution requires explicit authorization from the project owners.

---

## 👤 Project Owner

**Sidney Kyalo Mwanzai**

This project represents a dedicated effort to advance the state of secure, collaborative file sharing through practical applications of threshold cryptography and distributed systems.

---

## 🙏 Acknowledgments

Secure Share represents the evolution of academic research into practical application. Special thanks to:
- The cryptographic research community for foundational work on threshold secret sharing
- The open-source community for tools and libraries
- University research programs that inspired this project

---

## 📞 Support

For issues, questions, or contributions:
- Review documentation in `docs/` directory
- Check `docs/TODO.md` for known issues and roadmap
- Review critical issues in `docs/KEY_SHARE_REDISTRIBUTION_ISSUE.md`

---

**Last Updated:** 23rd November 2025  
**Version:** Development  
**Status:** Active Development  
**Owner:** Sidney Kyalo Mwanzai