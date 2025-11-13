# Secure Share

Secure Share is a command-line application for collaborative teams who need to exchange sensitive files safely. It combines client-side encryption, threshold secret sharing, and cloud storage to ensure that no single actor can decrypt a file on their own. The CLI integrates with Supabase for identity and metadata, while each user keeps their encryption keys locally.

## Table of Contents
- Overview
- Architecture
- Data Flow
- Features
- Installation
- Usage
- Development Workflow
- Troubleshooting
- License

---

## Overview
Secure Share enables organization-based file sharing with end-to-end confidentiality. Files are encrypted locally, split into multiple shares using threshold cryptography, and distributed to organization members who meet storage requirements. Users authenticate, manage organizations, upload/download files, and cooperate on decryption requests from within the CLI.

### Key Concepts
- **Organizations** – logical collaboration groups with invite codes and member roles.
- **Members** – users whose Supabase accounts are linked to organizations. Membership grants access to encrypted shares.
- **Threshold Encryption** – files are encrypted with a symmetric key that is split into multiple shares; a minimum number (`threshold`) must be collected to decrypt.
- **Supabase Backend** – stores metadata (users, organizations, files, key shares, audit logs).
- **Cloud Integrations** – each member links a personal storage provider (e.g., OneDrive) where their key shares are stored.

---

## Architecture
The application is split into three major layers:

```
┌────────────────────────────┐
│        Secure Share        │
│          CLI (UI)          │
└──────────────┬─────────────┘
               │ Command calls
┌──────────────▼─────────────┐
│  Application Services      │
│  (org_manager, file_manager│
│   auth, etc.)              │
└──────────────┬─────────────┘
               │ API calls & cryptography
       ┌───────▼────────┐
       │ External Systems│
       │ Supabase REST   │
       │ Cloud Storage   │
       └────────────────┘
```

### Module Responsibilities
- `main.py` – entrypoint and navigation menus for organization, file, and account management.
- `org_manager.py` – handles organization CRUD operations, invites, membership, and auditing.
- `file_manager.py` – encrypts files, distributes shares, handles uploads/downloads, and manages decryption requests.
- `auth.py` – login, registration, session persistence, and Supabase token management.
- `database/` – contains migrations, seed scripts, and helpers for initializing the Supabase schema.

---

## Data Flow
Below is a high-level view of how data moves during key operations.

### User Registration & Login
```
┌──────────┐        Credentials        ┌──────────────┐
│   CLI    │──────────────────────────▶│  Supabase    │
│ (main.py)│   JWT session tokens      │ (Auth API)   │
└──────────┘◀──────────────────────────└──────────────┘
```

### Organization Join
```
┌──────────┐   invite code   ┌───────────────┐
│   User   │────────────────▶│ organizations │
│  CLI     │◀───────────────▶│   table       │
└──────────┘   membership     └───────────────┘
             updates & audit logs
```

### File Upload
```
┌──────────┐   file selected   ┌───────────┐
│   CLI    │──────────────────▶│ Encryption│
│file_menu │     encrypt       │ (local)   │
└──────────┘◀──────────────────└───────────┘
      │             ▲
      │ shares      │ symmetric key
      ▼             │
┌──────────┐  shares metadata  ┌───────────────┐
│Cloud APIs│◀──────────────────│ Supabase      │
└──────────┘                   │ tables        │
                               └───────────────┘
```

### Decryption Request Workflow
```
Requester CLI ──▶ Supabase (decryption_requests)
     ▲                    │
     │ notification       ▼
Members CLI ──▶ Retrieve shares ──▶ Submit to Supabase
     │                                       │
     └───────── Local recombination ◀────────┘
```

---

## Features
- Organization creation, invite-code management, enable/disable invites.
- Member join/leave, automatic member counts, live detail refresh.
- File encryption with configurable thresholds.
- Distribution of key shares to member cloud storage.
- Decryption requests with audit logging.
- Interactive CLI navigation with graceful error handling.

---

## Installation

### Prerequisites
- Python 3.10+
- Supabase project with required tables (see `database/migrate`).
- OneDrive application (for cloud share storage) if testing cloud integrations.
- Git, virtual environment (`python -m venv` or similar), and curl (for Supabase setup scripts).

### Setup Steps
```bash
git clone https://github.com/<your-org>/secure-share.git
cd secure-share

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp env.example .env
```

Update `.env` with Supabase URL, anon key, service role key, and Microsoft application credentials.

### Database Initialization
Run migrations and seed scripts via the helper CLI in `database/`.
```bash
python database/migrate.py upgrade
python database/seed/seed_data.py
```
The seed script provisions sample users and organizations. Use Supabase dashboard to confirm.

---

## Usage
```bash
python main.py
```

The CLI presents the following high-level flow:
1. **Login/Register** – authenticate against Supabase.
2. **Organization Management**
   - Create new organizations.
   - Join existing ones using invite codes.
   - View details, toggle invites, regenerate invite codes.
3. **File Management**
   - Upload encrypted files with threshold settings.
   - List files, request decryption.
   - Submit key shares for pending requests.
4. **Account Settings**
   - Connect/disconnect OneDrive.
   - Manage session.

Press `Ctrl+C` at any prompt to return to the previous menu or exit gracefully.

---

## Development Workflow
- Code style follows standard Python linting (flake8/pylint). Run `pip install -r dev-requirements.txt` if present.
- To run linters:
  ```bash
  pylint main.py org_manager.py file_manager.py auth.py
  ```
- To run tests (if configured):
  ```bash
  pytest
  ```
- Use seed scripts to reset the database state on Supabase during local development.

---

## Troubleshooting
- **Invite code expired** – regenerate via `Manage Organization` > `Regenerate Invite Code`.
- **Cannot upload file** – ensure organization meets minimum member count and cloud storage requirements.
- **Cloud storage errors** – verify OneDrive credentials in `.env` and reauthorize.
- **Supabase access issues** – confirm network connectivity and API keys.
- **KeyboardInterrupt** – the CLI handles `Ctrl+C` gracefully; rerun `python main.py` to continue.

---

## Documentation & Issues

### Critical Issues
- **[Key Share Redistribution Issue](docs/KEY_SHARE_REDISTRIBUTION_ISSUE.md)** – Critical issue affecting file decryption when members leave organizations. **⚠️ Requires immediate attention.**

### Project Management
- **[TODO & Milestones](TODO.md)** – Tracked issues, feature enhancements, and development milestones.

### Additional Documentation
- **[Database README](database/README.md)** – Database setup, migrations, and seeding instructions.

---

## License
This project is private and confidential. Distribution requires explicit authorization from the project owners.