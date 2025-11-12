# Database Setup Guide

This directory contains database migration and seeding scripts for the Secure Share application.

## Structure

- `migrate/` - Database migration files
  - `001_initial_schema.sql` - Initial database schema with all tables
  - `run_migration.py` - Script to automatically run migrations
- `seed/` - Database seeding scripts
  - `seed_data.py` - Script to create users and organizations

## Prerequisites

1. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up your `.env` file (copy from `env.example`):
   ```bash
   cp env.example .env
   ```

3. Fill in your Supabase credentials in `.env`:
   - `SUPABASE_URL` - Your Supabase project URL
   - `SUPABASE_KEY` - Your Supabase anon key
   - `SUPABASE_SERVICE_ROLE_KEY` - Your Supabase service role key (recommended for seeding)
   - `SUPABASE_DB_URL` or `DATABASE_HOST` + `DATABASE_PASSWORD` - For direct database connection
   - `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_ENDPOINT`, `S3_REGION` - For S3-compatible storage

## Running Migrations

Run the migration script to create all database tables:

```bash
python database/migrate/run_migration.py
```

This will:
- Create all necessary tables (users, organizations, files, key_shares, etc.)
- Create indexes for better performance
- Create triggers for automatic timestamp updates
- Enable Row Level Security (RLS) on all tables
- Create RLS policies for secure data access
- Attempt to create the `encrypted-files` storage bucket

**Note:** The migration includes comprehensive Row Level Security policies that:
- Allow users to access only their own data and data from organizations they belong to
- Restrict admin operations to organization admins
- Ensure data isolation between organizations
- Maintain security without blocking application functionality

## Seeding Data

After running migrations, seed the database with initial data:

```bash
python database/seed/seed_data.py
```

The seed script will:
1. Prompt you to enter email addresses for users (minimum 5 recommended)
2. Ask for a password (same password for all users)
3. Ask for an organization name (optional)
4. Create users in Supabase Auth and database
5. Create an organization with all users as members
6. Set the first user as admin
7. Attempt to create the storage bucket

### Example Seed Session

```
Enter email addresses for users to seed (one per line).
Press Enter on an empty line when done.
Email 1: user1@example.com
Email 2: user2@example.com
Email 3: user3@example.com
Email 4: user4@example.com
Email 5: user5@example.com
Email 6: [Enter]

Enter password for all users:
Password: ********
Confirm Password: ********

Enter organization name: My Organization
```

## Database Schema

The migration creates the following tables:

- **users** - User profiles and cloud storage connections
- **organizations** - Organizations with invite codes
- **organization_members** - Many-to-many relationship between users and organizations
- **files** - Encrypted file metadata
- **key_shares** - Shamir secret sharing key shares
- **decryption_requests** - File decryption requests
- **audit_logs** - Audit trail for organization actions

## Storage Bucket

The `encrypted-files` bucket is created automatically if possible. If automatic creation fails, you can create it manually in Supabase Storage:

1. Go to Supabase Dashboard > Storage
2. Click "New bucket"
3. Name: `encrypted-files`
4. Public: No
5. File size limit: 50MB (or as needed)

## Troubleshooting

### Migration fails with connection error
- Check that `DATABASE_URL` or `DATABASE_HOST` + `DATABASE_PASSWORD` are set correctly
- Verify your database credentials in Supabase Dashboard > Settings > Database

### Bucket creation fails
- The script will attempt to create the bucket using Supabase Storage API first
- If that fails, it will try using boto3 with S3 credentials
- If both fail, create the bucket manually in Supabase Storage

### User creation fails
- Ensure email addresses are valid
- Password must be at least 6 characters (Supabase requirement)
- If a user already exists, the script reuses the account and resets the password you entered (requires `SUPABASE_SERVICE_ROLE_KEY`; otherwise you'll be prompted to update manually)
- If using RLS, ensure `SUPABASE_SERVICE_ROLE_KEY` is set in `.env` for seeding

### RLS Policy Issues
- RLS policies are automatically created during migration
- Policies allow authenticated users to access their own data and organization data
- Service role key bypasses RLS (use for admin operations like seeding)
- If you encounter permission errors, check that users are properly authenticated

## Notes

- Cloud storage connection is left for manual setup after seeding
- Users can connect their cloud storage through the application interface
- The seed script creates real users in Supabase Auth, so they can log in immediately
