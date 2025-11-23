-- Migration: Create user_sessions table for production session storage
-- This table stores user sessions in the database for scalability
-- Run this migration when ENVIRONMENT=production

-- Create user_sessions table
CREATE TABLE IF NOT EXISTS user_sessions (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    session_data JSONB NOT NULL,
    expires_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    encrypted BOOLEAN DEFAULT false
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at 
    ON user_sessions(expires_at);

CREATE INDEX IF NOT EXISTS idx_user_sessions_updated_at 
    ON user_sessions(updated_at);

-- Create index on session_data for faster lookups (if needed)
CREATE INDEX IF NOT EXISTS idx_user_sessions_data_gin 
    ON user_sessions USING GIN (session_data);

-- Enable Row Level Security
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;

-- Create policy: Users can only access their own sessions
CREATE POLICY "Users can manage their own sessions"
    ON user_sessions
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_user_sessions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to update updated_at on row update
CREATE TRIGGER update_user_sessions_timestamp
    BEFORE UPDATE ON user_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_user_sessions_updated_at();

-- Create function to cleanup expired sessions (can be called periodically)
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM user_sessions
    WHERE expires_at < NOW();
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Grant necessary permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON user_sessions TO authenticated;
GRANT EXECUTE ON FUNCTION cleanup_expired_sessions() TO authenticated;

-- Comments for documentation
COMMENT ON TABLE user_sessions IS 'Stores user authentication sessions for production scalability';
COMMENT ON COLUMN user_sessions.user_id IS 'References auth.users.id, primary key';
COMMENT ON COLUMN user_sessions.session_data IS 'JSONB containing session tokens and metadata';
COMMENT ON COLUMN user_sessions.expires_at IS 'Timestamp when session expires';
COMMENT ON COLUMN user_sessions.encrypted IS 'Whether session_data is encrypted';
COMMENT ON FUNCTION cleanup_expired_sessions() IS 'Removes expired sessions, returns count of deleted rows';

