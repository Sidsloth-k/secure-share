# Scalability Guide

## Overview

This guide provides detailed scalability analysis for the authentication system, covering scenarios from 100 users to 1 million concurrent logins.

## Performance Characteristics

### Development Mode (File Storage)

- **Session Load**: < 10ms (file read)
- **Session Save**: < 5ms (file write)
- **Token Refresh**: ~100-200ms (network call)
- **Session Validation**: ~50-100ms (Supabase API call)
- **Memory Footprint**: ~1KB per session
- **Storage**: ~1KB per session (JSON file)

### Production Mode (Database Storage)

- **Session Load**: ~10-30ms (indexed database query)
- **Session Save**: ~20-50ms (database upsert)
- **Token Refresh**: ~100-200ms (network call)
- **Session Validation**: ~50-100ms (Supabase API call)
- **Memory Footprint**: ~1KB per session (cached)
- **Database Storage**: ~2-5KB per session (JSONB + metadata)

---

## Scenario 1: 100 Users

### Characteristics

- **Concurrent Logins**: ~1-5 per minute
- **Database Load**: Minimal
- **API Calls**: ~100-500 per hour
- **Session Storage**: 100 files (~100KB total) or 100 database rows

### Performance

```
Login Request:
- Auth API: ~50-100ms
- Database Query: ~5-10ms
- Total: ~55-110ms per login

Token Refresh:
- Auth API: ~50-100ms
- No database query
- Total: ~50-100ms per refresh

Database Queries:
- Users table: < 1ms (indexed lookup)
- No connection pool needed
- Single connection sufficient
```

### Configuration

**Development Mode (Recommended)**:
```env
ENVIRONMENT=development
ENABLE_SESSION_ENCRYPTION=false
ENABLE_REFRESH_METRICS=false
```

**Storage**: File-based (`~/.secure_share/session.json`)

### Handling

- ✅ **Current implementation handles this easily**
- ✅ No optimization needed
- ✅ File-based sessions work perfectly
- ✅ Single Supabase project sufficient

---

## Scenario 2: 1 Million Users

### Characteristics

- **Concurrent Logins**: ~100-1000 per minute
- **Database Load**: Moderate to High
- **API Calls**: ~1M-10M per hour
- **Session Storage**: 1M database rows (~5GB total)

### Performance Challenges

```
Login Request:
- Auth API: ~50-200ms (under load)
- Database Query: ~10-50ms (with connection pooling)
- Total: ~60-250ms per login

Token Refresh:
- Auth API: ~50-200ms
- No database query
- Total: ~50-200ms per refresh

Database Queries:
- Users table: ~5-20ms (indexed, but large table)
- Connection pool: 20-100 connections needed
- Query optimization critical
```

### Required Configuration

**Production Mode (Required)**:
```env
ENVIRONMENT=production
ENABLE_SESSION_ENCRYPTION=true
ENABLE_REFRESH_METRICS=true
USE_DATABASE_STORAGE=true  # Auto-enabled in production
```

### Required Changes

#### 1. Database Setup

```sql
-- Run migration
-- database/migrate/002_user_sessions.sql

-- Required indexes
CREATE INDEX idx_user_sessions_expires_at 
    ON user_sessions(expires_at);
CREATE INDEX idx_user_sessions_updated_at 
    ON user_sessions(updated_at);
CREATE INDEX idx_user_sessions_data_gin 
    ON user_sessions USING GIN (session_data);
```

#### 2. Connection Pooling

```python
from supabase import create_client, ClientOptions

options = ClientOptions(
    db_pool_size=50,
    db_max_overflow=100
)
client = create_client(SUPABASE_URL, SUPABASE_KEY, options)
```

#### 3. Caching Layer (Optional but Recommended)

```python
# Add Redis cache for user profiles
import redis

redis_client = redis.Redis(host='localhost', port=6379)

def get_user_profile(user_id):
    cached = redis_client.get(f"user:{user_id}")
    if cached:
        return json.loads(cached)
    # Fetch from database and cache
    profile = fetch_from_db(user_id)
    redis_client.setex(f"user:{user_id}", 3600, json.dumps(profile))
    return profile
```

### Handling

- ✅ **Database storage required** - Use `ENVIRONMENT=production`
- ✅ **Connection pooling essential** - Configure in Supabase client
- ✅ **Indexing critical** - Create indexes as shown above
- ✅ **Caching recommended** - Add Redis for >100K users
- ✅ Supabase can handle this with proper configuration

### Monitoring

- Track session load/save times
- Monitor database connection pool usage
- Alert on query times > 100ms
- Track refresh success rates

---

## Scenario 3: 1 Million Concurrent Logins

### Characteristics

- **Concurrent Logins**: 1,000,000 simultaneous
- **Database Load**: Extreme
- **API Calls**: Burst of 1M requests
- **Session Creation**: 1M sessions in seconds

### Performance Challenges

```
Login Request (under extreme load):
- Auth API: ~200-2000ms (rate limited)
- Database Query: ~50-500ms (connection pool exhausted)
- Total: ~250-2500ms per login
- Many requests will timeout or fail

Token Refresh:
- Auth API: ~200-1000ms
- No database query
- Total: ~200-1000ms per refresh

Database Queries:
- Users table: ~50-500ms (connection pool saturated)
- Connection pool: 1000+ connections needed
- Database may become bottleneck
```

### Required Architecture

#### 1. Load Balancing

```
┌─────────────┐
│ Load Balancer│
└──────┬───────┘
       │
┌──────┼──────┐
│      │     │
▼      ▼     ▼
┌──┐ ┌──┐ ┌──┐
│S1│ │S2│ │S3│  (Multiple Supabase instances)
└──┘ └──┘ └──┘
```

#### 2. Database Sharding

```sql
-- Shard users by user_id hash
-- Shard 0: user_id % 10 = 0
-- Shard 1: user_id % 10 = 1
-- ... (10 shards)

CREATE TABLE user_sessions_0 (
    CHECK (user_id::text::int % 10 = 0)
) INHERITS (user_sessions);

CREATE TABLE user_sessions_1 (
    CHECK (user_id::text::int % 10 = 1)
) INHERITS (user_sessions);
```

#### 3. Rate Limiting

```python
from flask_limiter import Limiter

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["1000 per hour", "100 per minute"]
)
```

#### 4. Queue System

```python
# Use message queue for login requests
import celery

@celery.task
def process_login(email, password):
    # Process login asynchronously
    return auth.login(email, password)
```

#### 5. Multi-Layer Caching

```python
# L1: In-memory (local)
# L2: Redis (distributed)
# L3: Database (persistent)

def get_session(user_id):
    # Try L1 cache
    if cached := local_cache.get(user_id):
        return cached
    
    # Try L2 cache
    if cached := redis.get(f"session:{user_id}"):
        local_cache.set(user_id, cached)
        return cached
    
    # Fetch from L3 (database)
    session = db.load_session(user_id)
    redis.setex(f"session:{user_id}", 300, session)
    local_cache.set(user_id, session)
    return session
```

### Handling

- ❌ **Current implementation cannot handle this alone**
- ❌ Requires complete architecture redesign
- ✅ Supabase Enterprise can handle with proper setup
- ✅ Requires horizontal scaling
- ✅ Database sharding essential
- ✅ CDN and caching critical

### Required Infrastructure

1. **Multiple Supabase Instances**
   - Load balanced
   - Geographic distribution

2. **Database Cluster**
   - Primary + read replicas
   - Sharding by user_id

3. **Caching Layer**
   - Redis cluster
   - In-memory cache

4. **Message Queue**
   - Celery/RabbitMQ
   - Async processing

5. **CDN**
   - Static assets
   - API caching

---

## Scalability Recommendations by User Count

### < 100 Users
- ✅ File storage (development mode)
- ✅ No special configuration
- ✅ Single Supabase instance

### 100 - 10K Users
- ✅ Database storage (production mode)
- ✅ Basic indexing
- ✅ Connection pooling (10-20 connections)

### 10K - 100K Users
- ✅ Database storage
- ✅ Comprehensive indexing
- ✅ Connection pooling (20-50 connections)
- ✅ Consider Redis caching

### 100K - 1M Users
- ✅ Database storage
- ✅ Optimized indexes
- ✅ Connection pooling (50-100 connections)
- ✅ Redis caching
- ✅ Read replicas

### > 1M Users
- ✅ Database sharding
- ✅ Horizontal scaling
- ✅ Load balancing
- ✅ CDN
- ✅ Message queues

---

## Database Optimization

### Indexes

```sql
-- Essential indexes for user_sessions
CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_expires_at ON user_sessions(expires_at);
CREATE INDEX idx_user_sessions_updated_at ON user_sessions(updated_at);

-- GIN index for JSONB queries
CREATE INDEX idx_user_sessions_data_gin 
    ON user_sessions USING GIN (session_data);
```

### Connection Pooling

```python
# Recommended pool sizes
# < 1K users: 10-20 connections
# 1K-10K users: 20-50 connections
# 10K-100K users: 50-100 connections
# > 100K users: 100+ connections + read replicas
```

### Query Optimization

```sql
-- Use EXPLAIN ANALYZE to optimize queries
EXPLAIN ANALYZE 
SELECT * FROM user_sessions 
WHERE user_id = 'uuid-here';

-- Ensure index usage
-- Add covering indexes if needed
```

---

## Monitoring & Alerting

### Key Metrics

1. **Session Operations**
   - Load time (p50, p95, p99)
   - Save time (p50, p95, p99)
   - Error rate

2. **Token Refresh**
   - Success rate
   - Average duration
   - Failure types

3. **Database**
   - Connection pool usage
   - Query times
   - Lock contention

### Alert Thresholds

- Session load time > 100ms (p95)
- Session save time > 200ms (p95)
- Token refresh failure rate > 5%
- Database connection pool > 80% utilization
- Query time > 500ms (p95)

---

## Migration Path

### From File to Database

1. **Run Migration**
   ```bash
   psql -f database/migrate/002_user_sessions.sql
   ```

2. **Update Environment**
   ```env
   ENVIRONMENT=production
   ```

3. **Test**
   ```bash
   ENVIRONMENT=production python tests/test_auth_session.py
   ```

4. **Monitor**
   - Check session persistence
   - Verify performance
   - Monitor errors

### Scaling Up

1. **Add Indexes** (if not already present)
2. **Configure Connection Pooling**
3. **Add Caching Layer** (Redis)
4. **Set Up Read Replicas** (if needed)
5. **Implement Sharding** (for >1M users)

---

## Conclusion

The authentication system scales from single-user CLI applications to enterprise-level deployments:

- ✅ **100 users**: File storage, no optimization needed
- ✅ **1M users**: Database storage, indexing, connection pooling
- ⚠️ **1M concurrent**: Requires horizontal scaling, sharding, caching

Choose the appropriate configuration based on your user count and requirements.

