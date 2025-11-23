# Authentication Module Documentation

## Overview

The authentication module (`auth.py`) provides secure, scalable session management for the SecureShare application. It supports both development (file-based) and production (database) storage modes with automatic selection based on environment configuration.

## Quick Start

### Development Mode

```python
from supabase import create_client
from auth import Auth

client = create_client(SUPABASE_URL, SUPABASE_KEY)
auth = Auth(client)  # Automatically uses file storage

# Login
auth.login(email, password)

# Check authentication
if auth.is_authenticated():
    print("User is authenticated")
```

### Production Mode

```python
# Set ENVIRONMENT=production in .env
from supabase import create_client
from auth import Auth

client = create_client(SUPABASE_URL, SUPABASE_KEY)
auth = Auth(client)  # Automatically uses database storage

# Login (saves to database)
auth.login(email, password)
```

## Features

- ✅ **Dual Storage Modes**: File (dev) or Database (prod)
- ✅ **Session Encryption**: Optional encryption at rest
- ✅ **Token Refresh**: Automatic proactive refresh
- ✅ **Async Support**: High-concurrency ready
- ✅ **Metrics**: Token refresh monitoring
- ✅ **Thread-Safe**: Concurrent access support

## Configuration

See [Configuration Guide](CONFIGURATION.md) for detailed environment variables and setup.

## Documentation

- [How It Works](HOW_IT_WORKS.md) - Detailed explanation of session management
- [Recommendations](RECOMMENDATIONS.md) - Best practices and recommendations
- [Scalability](SCALABILITY.md) - **Scaling from 100 to 1M+ users** (detailed analysis)

## Architecture

```
┌─────────────────────────────────────┐
│         Auth Module                 │
│  ┌───────────────────────────────┐  │
│  │  Session Storage              │  │
│  │  (File or Database)           │  │
│  └───────────────┬───────────────┘  │
│                  │                   │
│  ┌───────────────▼───────────────┐  │
│  │  Token Manager                │  │
│  │  (Refresh, Validation)        │  │
│  └───────────────┬───────────────┘  │
│                  │                   │
│  ┌───────────────▼───────────────┐  │
│  │  Client Manager               │  │
│  │  (Supabase Session)            │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

## Storage Modes

### Development (File Storage)
- Location: `~/.secure_share/session.json`
- Use Case: Local development, testing
- Scalability: Single user

### Production (Database Storage)
- Location: `user_sessions` table in PostgreSQL
- Use Case: Production deployments, multi-user
- Scalability: Millions of users

## Getting Help

- Check [How It Works](HOW_IT_WORKS.md) for detailed explanations
- See [Recommendations](RECOMMENDATIONS.md) for best practices
- Review [Scalability](SCALABILITY.md) for production deployment

