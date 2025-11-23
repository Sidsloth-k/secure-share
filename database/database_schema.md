# Database Schema

## Entity Relationship Diagram

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

## Database Tables

### 1. `users` Table

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

### 2. `organizations` Table

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

### 3. `organization_members` Table

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

### 4. `files` Table

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

### 5. `key_shares` Table

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

### 6. `decryption_requests` Table

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

### 7. `audit_logs` Table

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

## Row-Level Security (RLS)

All tables have Row-Level Security enabled with policies that:

- **Users**: Can only read/update their own profile and profiles of organization members
- **Organizations**: Users can only access organizations they belong to
- **Files**: Users can only access files from their organizations
- **Key Shares**: Users can only access their own shares
- **Decryption Requests**: Users can only access requests for files in their organizations
- **Audit Logs**: Users can only read logs for their organizations

