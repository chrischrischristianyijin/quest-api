-- Add tags support to insights table
ALTER TABLE public.insights 
ADD COLUMN IF NOT EXISTS tags text[] DEFAULT '{}';

-- Add index for tags for better performance
CREATE INDEX IF NOT EXISTS insights_tags_idx ON public.insights USING GIN (tags);

-- Update insights table to include title, description, and image_url directly
ALTER TABLE public.insights 
ADD COLUMN IF NOT EXISTS title text,
ADD COLUMN IF NOT EXISTS description text,
ADD COLUMN IF NOT EXISTS image_url text;

-- Rename link column to url for consistency
ALTER TABLE public.insights 
RENAME COLUMN link TO url;

-- Add index for url
CREATE INDEX IF NOT EXISTS insights_url_idx ON public.insights(url);

-- Update RLS policies to allow tags updates
CREATE POLICY "Users can update their own insights"
    ON public.insights FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id); 