-- Add avatar_url column to users table
alter table public.users 
add column if not exists avatar_url text;

-- Add bio column to users table for future use
alter table public.users 
add column if not exists bio text;

-- Add index for avatar_url for better performance
create index if not exists users_avatar_url_idx on public.users(avatar_url);

-- Update RLS policies to allow avatar_url updates
drop policy if exists "Users can update their own profile" on public.users;

create policy "Users can update their own profile"
    on public.users for update
    using (auth.uid() = id)
    with check (auth.uid() = id);

-- Allow service role to update user profiles
create policy "Service role can update user profiles"
    on public.users for update
    using (auth.role() = 'service_role')
    with check (auth.role() = 'service_role'); 