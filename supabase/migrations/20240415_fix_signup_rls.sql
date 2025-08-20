-- Fix signup table RLS policies
-- This migration ensures the signup table has proper RLS policies for service role access

-- Enable RLS on signup table if not already enabled
alter table public.signup enable row level security;

-- Drop existing policies if they exist
drop policy if exists "Service role can manage signup" on public.signup;
drop policy if exists "Anyone can read signup" on public.signup;
drop policy if exists "Anyone can insert signup" on public.signup;

-- Create comprehensive policies for signup table
create policy "Service role can manage signup"
    on public.signup for all
    using (auth.role() = 'service_role');

-- Allow service role to read, insert, update, delete
create policy "Service role can read signup"
    on public.signup for select
    using (auth.role() = 'service_role');

create policy "Service role can insert signup"
    on public.signup for insert
    with check (auth.role() = 'service_role');

create policy "Service role can update signup"
    on public.signup for update
    using (auth.role() = 'service_role');

create policy "Service role can delete signup"
    on public.signup for delete
    using (auth.role() = 'service_role');

-- Also allow authenticated users to read their own signup data
create policy "Users can read own signup data"
    on public.signup for select
    using (auth.uid()::text = id::text);

-- Grant necessary permissions
grant usage on schema public to service_role;
grant all on public.signup to service_role;
grant all on public.users to service_role;

-- Ensure the signup table exists with proper structure
create table if not exists public.signup (
    id uuid default gen_random_uuid() primary key,
    email text unique not null,
    password text not null,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Add index for email lookups
create index if not exists signup_email_idx on public.signup(email);

-- Verify the table structure
comment on table public.signup is 'User signup information for authentication'; 