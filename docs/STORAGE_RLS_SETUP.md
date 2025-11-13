# Supabase Storage RLS Setup Guide

## Problem
When uploading files to Supabase Storage, you may encounter the error:
```
new row violates row-level security policy
```

This occurs because Supabase Storage has its own Row-Level Security (RLS) policies that are separate from database RLS.

## Solution: Configure Storage Bucket Policies

Even with the service role key, Supabase Storage RLS policies must be configured in the Supabase Dashboard. The service role key may not bypass Storage RLS in all cases.

### Step 1: Access Storage Policies

1. Go to your Supabase Dashboard: https://supabase.com/dashboard
2. Select your project
3. Navigate to **Storage** in the left sidebar
4. Click on the **`encrypted-files`** bucket
5. Click on the **Policies** tab

### Step 2: Create Upload Policy

Create a policy that allows authenticated users (who are organization members) to upload files.

**If you are using the Supabase Dashboard UI:**

1. Click **New policy**.
2. Set **Operation** to `INSERT` and **Roles** to `authenticated`.
3. **Important:** the UI already wraps the condition in a `WITH CHECK (...)` block, so paste **only the boolean expression** below into the condition field (do **not** include `CREATE POLICY ...`).
4. Save the policy.

Boolean expression to paste in the UI:

```
bucket_id = 'encrypted-files'
AND EXISTS (
  SELECT 1
  FROM public.organization_members om
  WHERE om.user_id = auth.uid()
    AND om.status = 'active'
)
```

**If you prefer running SQL in the Supabase SQL Editor**, run the full statement:

**Policy Name:** `Allow authenticated org members to upload`

**Policy Definition:**
```sql
CREATE POLICY "Allow authenticated org members to upload"
ON storage.objects
FOR INSERT
TO authenticated
WITH CHECK (
  bucket_id = 'encrypted-files'
  AND (
    -- Allow if user is a member of an organization
    EXISTS (
      SELECT 1
      FROM organization_members om
      WHERE om.user_id = auth.uid()
      AND om.status = 'active'
    )
  )
);
```

### Step 3: Create Read Policy

Create a policy that allows organization members to read files.

**Supabase Dashboard UI instructions:**

1. Click **New policy**.
2. Set **Operation** to `SELECT` and **Roles** to `authenticated`.
3. Paste only the expression below into the condition field.
4. Save the policy.

Boolean expression to paste in the UI:

```
bucket_id = 'encrypted-files'
AND (
  owner = auth.uid()
  OR EXISTS (
    SELECT 1
    FROM public.files f
    JOIN public.organization_members om
      ON f.organization_id = om.organization_id
    WHERE f.storage_path = storage.objects.name
      AND om.user_id = auth.uid()
      AND om.status = 'active'
  )
)
```

**SQL Editor version:**

**Policy Name:** `Allow org members to read encrypted files`

**Policy Definition:**
```sql
CREATE POLICY "Allow org members to read encrypted files"
ON storage.objects
FOR SELECT
TO authenticated
USING (
  bucket_id = 'encrypted-files'
  AND (
    -- Allow if user owns the file or is in the same org
    owner = auth.uid()
    OR EXISTS (
      SELECT 1
      FROM files f
      JOIN organization_members om ON f.organization_id = om.organization_id
      WHERE f.storage_path = storage.objects.name
      AND om.user_id = auth.uid()
      AND om.status = 'active'
    )
  )
);
```

### Step 4: Create Delete Policy (Optional)

If you need to allow file deletion, follow the same pattern in the UI (use `DELETE` and the expression below) or run the SQL statement directly.

**Policy Name:** `Allow org admins to delete files`

**Policy Definition:**
```sql
CREATE POLICY "Allow org admins to delete files"
ON storage.objects
FOR DELETE
TO authenticated
USING (
  bucket_id = 'encrypted-files'
  AND EXISTS (
    SELECT 1
    FROM files f
    JOIN organization_members om ON f.organization_id = om.organization_id
    WHERE f.storage_path = storage.objects.name
    AND om.user_id = auth.uid()
    AND om.role = 'admin'
    AND om.status = 'active'
  )
);
```

## Alternative: Disable RLS (Not Recommended)

If you want to disable RLS on the storage bucket entirely (not recommended for production):

1. Go to **Storage** > **`encrypted-files`** bucket
2. Click **Settings**
3. Toggle off **"Public bucket"** if it's on
4. Go to **Policies** tab
5. You may need to disable RLS at the database level (requires superuser access)

**Warning:** Disabling RLS removes all security controls. Only do this for development/testing.

## Verification

After creating the policies:

1. Try uploading a file through the application
2. Check the logs to confirm the upload succeeds
3. Verify the file appears in the Storage bucket

## Troubleshooting

### Policy Not Working

- Ensure the policy is saved and active
- Check that the user is authenticated (`auth.uid()` is not null)
- Verify the user is an active organization member
- Check the policy conditions match your database schema

### Still Getting RLS Errors

- Verify the bucket name is exactly `encrypted-files`
- Check that RLS is enabled on `storage.objects` table
- Ensure your user is logged in (has a valid session)
- Try using the service role key for testing (but configure policies for production)

## Notes

- Storage policies are separate from database RLS policies
- The service role key may not bypass Storage RLS in all Supabase configurations
- Always test policies in a development environment first
- Keep policies as restrictive as possible for security

