-- SecureShare Database Migration
-- This migration creates all necessary tables, indexes, and storage buckets
--
-- IMPORTANT NOTES:
-- 1. After running this migration, create the storage bucket 'encrypted-files' 
--    either via the migrate.py script or manually in Supabase Dashboard
-- 2. Configure S3 access keys in Supabase Dashboard > Settings > Storage > S3 Access Keys
-- 3. Add S3 credentials to your .env file (see env.example)
--
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    cloud_connected BOOLEAN DEFAULT FALSE,
    cloud_provider TEXT CHECK (cloud_provider IN ('google_drive', 'dropbox', 'onedrive')),
    cloud_credentials JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Organizations table
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    invite_code TEXT UNIQUE,
    invite_code_expires_at TIMESTAMPTZ,
    invite_enabled BOOLEAN DEFAULT TRUE,
    admin_id UUID REFERENCES users(id) ON DELETE CASCADE,
    member_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Organization members table
CREATE TABLE IF NOT EXISTS organization_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('admin', 'member')),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(organization_id, user_id)
);

-- Files table
CREATE TABLE IF NOT EXISTS files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    size BIGINT NOT NULL,
    type TEXT,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    uploader_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    uploaded_at TIMESTAMPTZ DEFAULT NOW(),
    encrypted_at TIMESTAMPTZ,
    storage_path TEXT NOT NULL,
    threshold INTEGER NOT NULL CHECK (threshold >= 3),
    total_shares INTEGER NOT NULL,
    nonce TEXT NOT NULL,
    salt TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'available' CHECK (status IN ('available', 'pending_decryption', 'decrypted', 'deleted'))
);

-- Key shares table
CREATE TABLE IF NOT EXISTS key_shares (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_id UUID NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    share_index INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'retrieved')),
    cloud_path TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(file_id, user_id)
);

-- Decryption requests table
CREATE TABLE IF NOT EXISTS decryption_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_id UUID NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    requester_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    requested_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'ready', 'expired', 'completed')),
    current_shares INTEGER DEFAULT 0,
    threshold INTEGER NOT NULL,
    message TEXT
);

-- Audit logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    file_id UUID REFERENCES files(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    details JSONB
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_organization_members_org_id ON organization_members(organization_id);
CREATE INDEX IF NOT EXISTS idx_organization_members_user_id ON organization_members(user_id);
CREATE INDEX IF NOT EXISTS idx_files_org_id ON files(organization_id);
CREATE INDEX IF NOT EXISTS idx_files_uploader_id ON files(uploader_id);
CREATE INDEX IF NOT EXISTS idx_key_shares_file_id ON key_shares(file_id);
CREATE INDEX IF NOT EXISTS idx_key_shares_user_id ON key_shares(user_id);
CREATE INDEX IF NOT EXISTS idx_decryption_requests_file_id ON decryption_requests(file_id);
CREATE INDEX IF NOT EXISTS idx_decryption_requests_status ON decryption_requests(status);
CREATE INDEX IF NOT EXISTS idx_audit_logs_org_id ON audit_logs(organization_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_file_id ON audit_logs(file_id);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at (drop if exists first)
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_organizations_updated_at ON organizations;
CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

-- Drop existing policies if they exist (for idempotent migrations)
DROP POLICY IF EXISTS "Users can read own profile" ON users;
DROP POLICY IF EXISTS "Users can update own profile" ON users;
DROP POLICY IF EXISTS "Users can read org member profiles" ON users;
DROP POLICY IF EXISTS "Users can insert own profile" ON users;
DROP POLICY IF EXISTS "Users can read own organizations" ON organizations;
DROP POLICY IF EXISTS "Users can create organizations" ON organizations;
DROP POLICY IF EXISTS "Admins can update own organizations" ON organizations;
DROP POLICY IF EXISTS "Users can read org members" ON organization_members;
DROP POLICY IF EXISTS "Admins can add members" ON organization_members;
DROP POLICY IF EXISTS "Admins can update members" ON organization_members;
DROP POLICY IF EXISTS "Admins can remove members" ON organization_members;
DROP POLICY IF EXISTS "Users can join organizations" ON organization_members;
DROP POLICY IF EXISTS "Users can read org files" ON files;
DROP POLICY IF EXISTS "Users can upload files" ON files;
DROP POLICY IF EXISTS "Users can update own files" ON files;
DROP POLICY IF EXISTS "Admins can delete files" ON files;
DROP POLICY IF EXISTS "Users can read own key shares" ON key_shares;
DROP POLICY IF EXISTS "System can insert key shares" ON key_shares;
DROP POLICY IF EXISTS "Users can update own key shares" ON key_shares;
DROP POLICY IF EXISTS "Users can read org decryption requests" ON decryption_requests;
DROP POLICY IF EXISTS "Users can create decryption requests" ON decryption_requests;
DROP POLICY IF EXISTS "Users can update decryption requests" ON decryption_requests;
DROP POLICY IF EXISTS "Users can read org audit logs" ON audit_logs;
DROP POLICY IF EXISTS "System can insert audit logs" ON audit_logs;

-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE organization_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE files ENABLE ROW LEVEL SECURITY;
ALTER TABLE key_shares ENABLE ROW LEVEL SECURITY;
ALTER TABLE decryption_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Helper function to check if user is member of organization
-- Note: auth.uid() is provided by Supabase, no need to create it
-- Drop existing function if it exists (in case of parameter changes)
DROP FUNCTION IF EXISTS is_org_member(UUID);
CREATE OR REPLACE FUNCTION is_org_member(org_id UUID) RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM organization_members 
        WHERE organization_id = is_org_member.org_id 
        AND user_id = auth.uid()
        AND status = 'active'
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Helper function to check if user is admin of organization
-- Drop existing function if it exists (in case of parameter changes)
DROP FUNCTION IF EXISTS is_org_admin(UUID);
CREATE OR REPLACE FUNCTION is_org_admin(org_id UUID) RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM organization_members 
        WHERE organization_id = is_org_admin.org_id 
        AND user_id = auth.uid()
        AND role = 'admin' 
        AND status = 'active'
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- USERS TABLE POLICIES
-- ============================================================================

-- Users can read their own profile
CREATE POLICY "Users can read own profile" ON users
    FOR SELECT USING (auth.uid() = id);

-- Users can update their own profile
CREATE POLICY "Users can update own profile" ON users
    FOR UPDATE USING (auth.uid() = id);

-- Users can read profiles of members in their organizations
CREATE POLICY "Users can read org member profiles" ON users
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM organization_members om1
            JOIN organization_members om2 ON om1.organization_id = om2.organization_id
            WHERE om1.user_id = auth.uid() 
            AND om2.user_id = users.id
            AND om1.status = 'active'
            AND om2.status = 'active'
        )
    );

-- Allow users to insert their own profile (during registration)
-- The id must match the authenticated user's ID from auth.users
-- Also allow when id is a valid auth user (for service role operations)
CREATE POLICY "Users can insert own profile" ON users
    FOR INSERT WITH CHECK (
        auth.uid() = id 
        OR EXISTS (SELECT 1 FROM auth.users WHERE id = users.id)
    );

-- ============================================================================
-- ORGANIZATIONS TABLE POLICIES
-- ============================================================================

-- Users can read organizations they are members of
CREATE POLICY "Users can read own organizations" ON organizations
    FOR SELECT USING (is_org_member(id));

-- Users can create organizations (they become admin)
-- Also allow when admin_id is set to a valid user (for service role operations)
CREATE POLICY "Users can create organizations" ON organizations
    FOR INSERT WITH CHECK (
        auth.uid() = admin_id 
        OR EXISTS (SELECT 1 FROM users WHERE id = admin_id)
    );

-- Admins can update their organizations
CREATE POLICY "Admins can update own organizations" ON organizations
    FOR UPDATE USING (is_org_admin(id));

-- ============================================================================
-- ORGANIZATION_MEMBERS TABLE POLICIES
-- ============================================================================

-- Users can read members of organizations they belong to
CREATE POLICY "Users can read org members" ON organization_members
    FOR SELECT USING (is_org_member(organization_id));

-- Admins can insert new members
CREATE POLICY "Admins can add members" ON organization_members
    FOR INSERT WITH CHECK (is_org_admin(organization_id));

-- Admins can update members (change roles, etc.)
CREATE POLICY "Admins can update members" ON organization_members
    FOR UPDATE USING (is_org_admin(organization_id));

-- Admins can remove members (except themselves)
CREATE POLICY "Admins can remove members" ON organization_members
    FOR DELETE USING (
        is_org_admin(organization_id) 
        AND user_id != auth.uid()
    );

-- Users can join organizations via invite code (handled by application logic)
CREATE POLICY "Users can join organizations" ON organization_members
    FOR INSERT WITH CHECK (user_id = auth.uid());

-- ============================================================================
-- FILES TABLE POLICIES
-- ============================================================================

-- Users can read files from organizations they are members of
CREATE POLICY "Users can read org files" ON files
    FOR SELECT USING (is_org_member(organization_id));

-- Users can upload files to organizations they are members of
CREATE POLICY "Users can upload files" ON files
    FOR INSERT WITH CHECK (
        is_org_member(organization_id) 
        AND uploader_id = auth.uid()
    );

-- Uploaders and admins can update files
CREATE POLICY "Users can update own files" ON files
    FOR UPDATE USING (
        uploader_id = auth.uid() 
        OR is_org_admin(organization_id)
    );

-- Admins can delete files
CREATE POLICY "Admins can delete files" ON files
    FOR DELETE USING (is_org_admin(organization_id));

-- ============================================================================
-- KEY_SHARES TABLE POLICIES
-- ============================================================================

-- Users can read their own key shares
CREATE POLICY "Users can read own key shares" ON key_shares
    FOR SELECT USING (user_id = auth.uid());

-- System can insert key shares (when file is uploaded)
CREATE POLICY "System can insert key shares" ON key_shares
    FOR INSERT WITH CHECK (true);

-- Users can update their own key shares (when retrieving)
CREATE POLICY "Users can update own key shares" ON key_shares
    FOR UPDATE USING (user_id = auth.uid());

-- ============================================================================
-- DECRYPTION_REQUESTS TABLE POLICIES
-- ============================================================================

-- Users can read decryption requests for files in their organizations
CREATE POLICY "Users can read org decryption requests" ON decryption_requests
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM files f
            WHERE f.id = decryption_requests.file_id
            AND is_org_member(f.organization_id)
        )
    );

-- Users can create decryption requests for files in their organizations
CREATE POLICY "Users can create decryption requests" ON decryption_requests
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM files f
            WHERE f.id = decryption_requests.file_id
            AND is_org_member(f.organization_id)
        )
        AND requester_id = auth.uid()
    );

-- Users can update decryption requests (submit shares, etc.)
CREATE POLICY "Users can update decryption requests" ON decryption_requests
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM files f
            WHERE f.id = decryption_requests.file_id
            AND is_org_member(f.organization_id)
        )
    );

-- ============================================================================
-- AUDIT_LOGS TABLE POLICIES
-- ============================================================================

-- Users can read audit logs for organizations they are members of
CREATE POLICY "Users can read org audit logs" ON audit_logs
    FOR SELECT USING (
        organization_id IS NULL 
        OR is_org_member(organization_id)
    );

-- System can insert audit logs
CREATE POLICY "System can insert audit logs" ON audit_logs
    FOR INSERT WITH CHECK (true);

-- Note: S3 bucket creation will be handled by the migration runner script
-- The bucket 'encrypted-files' will be created programmatically using boto3
