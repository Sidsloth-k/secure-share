# Auth Session Management Test Suite

## Overview

Comprehensive test suite for authentication and session management. Tests follow a structured flow: **Login → Session Security → Token Refresh → Session Management → Cleanup**.

## Quick Start

### Testing with Fake Tokens (Development Mode)

```bash
# Use development mode for fake token tests
ENVIRONMENT=development python tests/test_auth_session.py
# Select option 2 (Fake Tokens) when prompted
```

**Why Development Mode?**
- Uses file-based storage (faster for testing)
- No database setup required
- Tests logic without real authentication

### Testing with Real Tokens (Production Mode)

```bash
# Use production mode for real token tests
ENVIRONMENT=production python tests/test_auth_session.py
# Select option 1 (Real Tokens) when prompted
# Enter your Supabase credentials
```

**Why Production Mode?**
- Tests database storage (production scenario)
- Validates encryption and metrics
- End-to-end testing with real Supabase

**Prerequisites for Production Mode:**
- Database migration run: `database/migrate/002_user_sessions.sql`
- Valid Supabase credentials

## Test Flow

1. **Login & Registration** - Real or fake token authentication
2. **Session Security** - Persistence, integrity, encryption, validation
3. **Token Refresh** - Proactive refresh, expired handling, error recovery
4. **Session Management** - Helper methods, metrics, persistence
5. **Cleanup & Logout** - Session cleanup and logout

## Test Modes

### Fake Tokens (Development Mode)
- **Environment**: `ENVIRONMENT=development`
- **Storage**: File-based (`~/.secure_share/session.json`)
- **Use Case**: Testing logic, faster iteration
- **No Credentials Required**: Uses mock data

### Real Tokens (Production Mode)
- **Environment**: `ENVIRONMENT=production`
- **Storage**: Database (`user_sessions` table)
- **Use Case**: End-to-end testing, production validation
- **Credentials Required**: Interactive login prompt

## Expected Results

All 5 phases should pass:
- ✅ Login & Registration
- ✅ Session Security  
- ✅ Token Refresh
- ✅ Session Management
- ✅ Cleanup & Logout

## Documentation

For detailed documentation, see:

- **[Test Documentation](../../docs/tests/README.md)** - Complete test guide
- **[Auth Documentation](../../docs/auth/README.md)** - Authentication module docs
- **[How It Works](../../docs/auth/HOW_IT_WORKS.md)** - Detailed session management flow
- **[Recommendations](../../docs/auth/RECOMMENDATIONS.md)** - Best practices

## Troubleshooting

### "Session file not found" (Production mode)
- Expected: Production uses database, not files
- Test automatically detects storage mode

### Real login fails
- Verify credentials
- Check network connectivity
- Ensure Supabase is accessible

## Features Tested

- ✅ File-based storage (development)
- ✅ Database storage (production)
- ✅ Session encryption
- ✅ Token refresh
- ✅ Error handling
- ✅ Session persistence
- ✅ Metrics tracking

## See Also

- [Auth Module](../../auth.py) - Source code
- [Database Migration](../../database/migrate/002_user_sessions.sql) - Production setup
