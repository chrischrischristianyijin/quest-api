-- Create tables for Quest application

-- Users table (linked to Supabase auth.users)
create table if not exists public.users (
    id uuid references auth.users on delete cascade primary key,
    email text unique not null,
    nickname text not null,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Insights table
create table if not exists public.insights (
    id uuid default gen_random_uuid() primary key,
    user_id uuid references public.users(id) on delete cascade,
    link text not null,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Metadata table
create table if not exists public.metadata (
    id uuid default gen_random_uuid() primary key,
    insight_id uuid references public.insights(id) on delete cascade,
    title text,
    description text,
    image_url text,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Shared media table
create table if not exists public.shared_media (
    id uuid default gen_random_uuid() primary key,
    name text not null,
    email text not null,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Add indexes
create index if not exists users_email_idx on public.users(email);
create index if not exists insights_user_id_idx on public.insights(user_id);
create index if not exists metadata_insight_id_idx on public.metadata(insight_id);
create index if not exists shared_media_email_idx on public.shared_media(email);

-- Add RLS (Row Level Security) policies
alter table public.users enable row level security;
alter table public.insights enable row level security;
alter table public.metadata enable row level security;
alter table public.shared_media enable row level security;

-- Users policies
create policy "Users can read their own data"
    on public.users for select
    using (auth.uid() = id);

create policy "Service role can create users"
    on public.users for insert
    with check (auth.role() = 'service_role');

create policy "Users can update their own profile"
    on public.users for update
    using (auth.uid() = id);

-- Insights policies
create policy "Service role can manage insights"
    on public.insights for all
    using (auth.role() = 'service_role');

create policy "Users can read their own insights"
    on public.insights for select
    using (auth.uid() = user_id);

-- Metadata policies
create policy "Service role can manage metadata"
    on public.metadata for all
    using (auth.role() = 'service_role');

create policy "Users can read metadata of their insights"
    on public.metadata for select
    using (
        exists (
            select 1
            from public.insights
            where insights.id = metadata.insight_id
            and insights.user_id = auth.uid()
        )
    );

-- Shared media policies
create policy "Anyone can read shared media"
    on public.shared_media for select
    using (true);

create policy "Authenticated users can insert shared media"
    on public.shared_media for insert
    with check (auth.role() = 'authenticated'); 