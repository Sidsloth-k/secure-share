# Test Suite Documentation

## Overview

The test suite (`tests/test_auth_session.py`) validates all session management functionality in a structured flow: Login → Session Security → Token Refresh → Session Management → Cleanup.

## Quick Start

### Run Tests

```bash
# Development mode
ENVIRONMENT=development python tests/test_auth_session.py

# Production mode
ENVIRONMENT=production python tests/test_auth_session.py
```

### Test Modes

1. **Real Tokens**: Requires actual Supabase credentials
2. **Fake Tokens**: Tests logic without real authentication

## Test Flow

```
┌─────────────────────────────────────┐
│  Phase 1: Login & Registration      │
│  - Real or fake tokens              │
│  - Session creation                 │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Phase 2: Session Security          │
│  - Persistence                      │
│  - Data integrity                   │
│  - Encryption                       │
│  - Validation                       │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Phase 3: Token Refresh             │
│  - Proactive refresh                │
│  - Expired token handling           │
│  - Error handling                   │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Phase 4: Session Management        │
│  - Helper methods                   │
│  - Time remaining                   │
│  - Metrics                          │
│  - Persistence across restarts      │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Phase 5: Cleanup & Logout          │
│  - Logout functionality             │
│  - Session cleanup                  │
└─────────────────────────────────────┘
```

## Test Phases

### Phase 1: Login & Registration

**Tests**:
- Real login with Supabase
- Fake token creation
- Session storage (file/database)

**Expected Results**:
- ✅ Login successful
- ✅ Session created
- ✅ Session stored correctly

### Phase 2: Session Security

**Tests**:
- Session persistence (file or database)
- Data integrity
- Session loading
- Encryption (if enabled)
- Session validation

**Expected Results**:
- ✅ Session persisted
- ✅ All fields present
- ✅ Session loads correctly
- ✅ Encryption working (if enabled)

### Phase 3: Token Refresh

**Tests**:
- Proactive refresh detection
- Session validation
- Expired token handling
- Error handling

**Expected Results**:
- ✅ Refresh logic works
- ✅ Expired tokens detected
- ✅ Errors handled correctly

### Phase 4: Session Management

**Tests**:
- Helper methods (`get_user_id`, `get_access_token`)
- Session time remaining
- Refresh metrics (if enabled)
- Persistence across restarts

**Expected Results**:
- ✅ Helper methods work
- ✅ Time remaining calculated
- ✅ Metrics available (if enabled)
- ✅ Session persists

### Phase 5: Cleanup & Logout

**Tests**:
- Logout functionality
- Session cleanup (file/database)
- Memory cleanup

**Expected Results**:
- ✅ Logout successful
- ✅ Session cleared
- ✅ Memory cleared

## Running Tests

### Prerequisites

1. **Environment Setup**
   ```bash
   cp env.example .env
   # Set SUPABASE_URL and SUPABASE_KEY
   ```

2. **Database Setup** (Production mode)
   ```bash
   # Run migration
   psql -f database/migrate/002_user_sessions.sql
   ```

### Basic Usage

```bash
python tests/test_auth_session.py
```

### With Real Login

1. Run test
2. Select option 1 (Real Tokens)
3. Enter email when prompted
4. Enter password when prompted (hidden input)
5. Test will reuse session if available

### With Fake Tokens

1. Run test
2. Select option 2 (Fake Tokens)
3. Tests run with mock data

## Expected Output

```
======================================================================
Auth Session Management Test Suite
======================================================================

Environment: PRODUCTION
Encryption: Enabled
Metrics: Enabled

Test Mode Selection
1. Use Real Tokens (requires login)
2. Use Fake Tokens (for testing logic)

Enter choice (1 or 2): 1

======================================================================
TEST: PHASE 1: Login & Registration
======================================================================
✓ Real login successful

======================================================================
TEST: PHASE 2: Session Security
======================================================================
✓ Session persisted in database
✓ All required session fields present
✓ Session loaded correctly from database
✓ Session encryption enabled (database mode)
✓ Session validation passed

======================================================================
TEST: PHASE 3: Token Refresh
======================================================================
✓ Session valid for 3595 more seconds
✓ Session validation/refresh logic executed
✓ Expired token refresh logic executed
✓ Error handling tested: 2 auth errors detected

======================================================================
TEST: PHASE 4: Session Management
======================================================================
✓ get_user_id() returned: 84d9f07f...
✓ get_access_token() returned token (length: 865)
✓ Session persisted across Auth instance recreation

======================================================================
TEST: PHASE 5: Cleanup & Logout
======================================================================
✓ Session cleared from database after logout
✓ Session cleared from memory

======================================================================
Test Summary
======================================================================

✓ Login & Registration
✓ Session Security
✓ Token Refresh
✓ Session Management
✓ Cleanup & Logout

Total: 5/5 phases passed
All tests passed!
```

## Troubleshooting

### Test Fails: "Session file not found"

**Cause**: Running in production mode but checking for file

**Solution**: Test automatically detects storage mode. Ensure database is set up for production mode.

### Test Fails: "No session available"

**Cause**: Session was cleared during test

**Solution**: Test should restore session. Check logs for errors.

### Real Login Fails

**Cause**: Invalid credentials or network issue

**Solution**: 
- Verify credentials
- Check network connectivity
- Check Supabase API status

## Test Coverage

- ✅ Login/Registration
- ✅ Session persistence (file & database)
- ✅ Session security
- ✅ Token refresh
- ✅ Error handling
- ✅ Session management
- ✅ Cleanup/logout

## Continuous Integration

### GitHub Actions Example

```yaml
name: Auth Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - run: pip install -r requirements.txt
      - run: python tests/test_auth_session.py
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
          ENVIRONMENT: development
```

## See Also

- [Auth Documentation](../auth/README.md)
- [How It Works](../auth/HOW_IT_WORKS.md)
- [Recommendations](../auth/RECOMMENDATIONS.md)

