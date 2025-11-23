# Technical Process Workflow

## Technical Process Flow

### 1. File Upload & Encryption Process

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

### 2. Threshold Secret Sharing (Shamir's Scheme)

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

### 3. Decryption Workflow

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

### 4. Distributed Storage Model

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

