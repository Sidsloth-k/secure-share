# How Authentication Works

## Session Management Flow

### 1. Application Startup

```
┌─────────────────────────────────────┐
│      Application Starts              │
└──────────────┬──────────────────────┘
               │
               ▼
    ┌──────────────────────┐
    │  Auth.__init__()     │
    │  - Check ENVIRONMENT  │
    │  - Select storage    │
    │  - Load session      │
    └──────────┬───────────┘
               │
    ┌──────────┴──────────┐
    │                     │
    ▼                     ▼
Development          Production
(File Storage)      (Database Storage)
```

### 2. Login Process

```
User Login Request
    │
    ▼
┌─────────────────────────────┐
│  auth.login(email, pwd)    │
└──────────┬─────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  Supabase Auth API          │
│  - Validate credentials     │
│  - Generate JWT tokens      │
└──────────┬─────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  Store Session              │
│  - Save tokens              │
│  - Set expiration           │
│  - Store in file/DB         │
└──────────┬─────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  Configure Client           │
│  - Set session on client    │
│  - Ready for API calls      │
└─────────────────────────────┘
```

### 3. Token Refresh Flow

```
API Call or is_authenticated()
    │
    ▼
┌─────────────────────────────┐
│  _ensure_valid_session()    │
└──────────┬─────────────────┘
           │
    ┌──────┴──────┐
    │             │
    ▼             ▼
Expired?    Past 80%?
    │             │
    └──────┬──────┘
           │
           ▼
┌─────────────────────────────┐
│  _refresh_token()           │
│  - Use refresh_token         │
│  - Get new tokens            │
│  - Update session            │
│  - Save to storage           │
└─────────────────────────────┘
```

## API Interactions with Database

### Login Flow

1. **Client Request**
   ```
   POST /auth/v1/token?grant_type=password
   { email, password }
   ```

2. **Supabase Auth API**
   - Validates credentials
   - Queries `auth.users` table
   - Verifies password hash
   - Generates JWT tokens
   - Returns session

3. **Client Processing**
   - Saves session to file/database
   - Sets session on Supabase client
   - Fetches user profile

4. **Database Query** (if production)
   ```
   INSERT INTO user_sessions
   VALUES (user_id, session_data, expires_at)
   ```

### Token Refresh Flow

1. **No Database Query Required**
   - Uses refresh_token (JWT)
   - Pure token validation
   - No database lookup

2. **Supabase Auth API**
   ```
   POST /auth/v1/token?grant_type=refresh_token
   { refresh_token }
   ```

3. **Update Session**
   - Update stored session
   - Save to file/database
   - Update client session

## Storage Mechanisms

### File Storage (Development)

**Location**: `~/.secure_share/session.json`

**Structure**:
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "access_token": "jwt_token",
  "refresh_token": "jwt_token",
  "expires_at": 1234567890.0,
  "original_lifetime": 3600
}
```

**Operations**:
- Load: Read JSON file
- Save: Write JSON file
- Clear: Delete file

### Database Storage (Production)

**Table**: `user_sessions`

**Schema**:
```sql
CREATE TABLE user_sessions (
    user_id UUID PRIMARY KEY,
    session_data JSONB NOT NULL,
    expires_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    encrypted BOOLEAN DEFAULT false
);
```

**Operations**:
- Load: `SELECT * FROM user_sessions WHERE user_id = $1`
- Save: `UPSERT INTO user_sessions ...`
- Clear: `DELETE FROM user_sessions WHERE user_id = $1`

## Security Features

### Session Encryption

**When Enabled**: Production mode with `ENABLE_SESSION_ENCRYPTION=true`

**Method**: Fernet (symmetric encryption)

**Key Storage**:
1. Environment variable (`SESSION_ENCRYPTION_KEY`)
2. OS keyring (if available)
3. Machine-specific key (fallback)

**Process**:
```
Session Data
    │
    ▼
JSON Serialization
    │
    ▼
Fernet Encryption
    │
    ▼
Base64 Encoding
    │
    ▼
Storage (File/DB)
```

### Token Security

- Tokens never logged
- Secure storage (encrypted if enabled)
- Automatic token rotation on refresh
- Expiration handling

## Error Handling

### Authentication Errors

```
API Call Fails
    │
    ▼
handle_auth_error()
    │
    ▼
Is Auth Error?
(401, 403, expired, etc.)
    │
    ├─ Yes ──► Attempt Token Refresh
    │         │
    │         ├─ Success ──► Retry API Call
    │         │
    │         └─ Failure ──► Clear Session, Force Re-login
    │
    └─ No ──► Return Error (Don't handle)
```

### Retry Logic

- **Max Retries**: 3 attempts
- **Backoff**: Exponential (1s, 2s, 4s)
- **Non-retryable**: Invalid/expired tokens
- **Retryable**: Network errors, timeouts

## Thread Safety

### Refresh Lock

```python
# TokenManager uses threading.Lock()
with self._refresh_lock:
    # Only one refresh at a time
    refresh_token()
```

**Benefits**:
- Prevents concurrent refreshes
- Avoids race conditions
- Ensures consistent state

## Performance Characteristics

### Development Mode (File)
- Session Load: < 10ms
- Session Save: < 5ms
- Token Refresh: ~100-200ms
- Memory: ~1KB per session

### Production Mode (Database)
- Session Load: ~10-30ms (indexed query)
- Session Save: ~20-50ms (upsert)
- Token Refresh: ~100-200ms
- Memory: ~1KB per session (cached)
- Database: ~2-5KB per session (JSONB)

## Scalability

### 100 Users
- ✅ File storage sufficient
- ✅ No optimization needed

### 1 Million Users
- ✅ Database storage required
- ✅ Indexing essential
- ✅ Connection pooling needed

### 1 Million Concurrent Logins
- ⚠️ Requires horizontal scaling
- ⚠️ Database sharding
- ⚠️ Load balancing
- ⚠️ Caching layer

See [Scalability Guide](SCALABILITY.md) for detailed analysis.

