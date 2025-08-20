-- Drop the old insights and metadata tables
drop table if exists public.metadata;
drop table if exists public.insights;

-- Create new insights table
create table if not exists public.insights (
    id uuid default gen_random_uuid() primary key,
    user_id uuid references public.users(id) on delete cascade,
    url text not null,
    title text,
    description text,
    image_url text,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Add indexes
create index if not exists insights_user_id_idx on public.insights(user_id);

-- Add RLS (Row Level Security) policies
alter table public.insights enable row level security;

-- Service role can do everything (separate policies for each operation)
create policy "Service role can read insights"
    on public.insights for select
    using (true);

create policy "Service role can insert insights"
    on public.insights for insert
    with check (true);

create policy "Service role can update insights"
    on public.insights for update
    using (true);

create policy "Service role can delete insights"
    on public.insights for delete
    using (true);

-- Users can read their own insights
create policy "Users can read their own insights"
    on public.insights for select
    using (auth.uid() = user_id);

-- Users can insert their own insights
create policy "Users can insert their own insights"
    on public.insights for insert
    with check (auth.uid() = user_id);

-- Users can update their own insights
create policy "Users can update their own insights"
    on public.insights for update
    using (auth.uid() = user_id);

-- Users can delete their own insights
create policy "Users can delete their own insights"
    on public.insights for delete
    using (auth.uid() = user_id); 