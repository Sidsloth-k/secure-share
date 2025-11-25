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

For detailed technical process workflows, see [Technical Process Workflow](docs/technical_process_workflow.md).

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

For detailed database schema documentation, see [Database Schema](database/database_schema.md).

---

## 🔄 Data Flow Diagrams

For detailed data flow diagrams, see [Data Flow Diagrams](docs/data_flow_diagrams.md).

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

#### Google Drive token expiry blocks share uploads (identified 25 Nov 2025)
- **Symptom:** File uploads fail during “Upload share to cloud” and roll back with logs similar to `invalid_grant: Token has been expired or revoked`.
- **Root Cause:** Members with stale Google Drive refresh tokens inside `users.cloud_credentials` trigger a 401 from Google Drive when `_upload_to_google_drive` tries to create/find the `SecureShare_KeyShares` folder. The batch operation aborts before any shares reach cloud storage.
- **Immediate Remediation:** Ask affected members to reconnect Google Drive (clearing their stored credentials or running `_reauthenticate_google_drive`) so a fresh refresh token is saved. Once reconnected, retry the upload.
- **Longer-Term Fix:** Improve `_upload_to_google_drive` to trap `invalid_grant` errors, automatically invoke `_reauthenticate_google_drive`, and retry; add a preflight credential validation step before starting `batch_operation_with_rollback` so uploads warn early when a member’s cloud credentials have expired. Full task list lives in `docs/TODO.md`.

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