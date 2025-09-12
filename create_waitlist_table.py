#!/usr/bin/env python3
"""
Script to create the waitlist table in Supabase
Run this script to set up the waitlist table in your database
"""

import asyncio
import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

async def create_waitlist_table():
    """Create the waitlist table in Supabase"""
    
    # Get Supabase credentials
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Missing Supabase credentials. Please check your .env file.")
        return False
    
    try:
        # Create Supabase client
        supabase = create_client(supabase_url, supabase_key)
        print("✅ Connected to Supabase")
        
        # SQL to create the waitlist table
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS waitlist (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email VARCHAR(255) UNIQUE NOT NULL,
            status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'unsubscribed', 'notified')),
            source VARCHAR(50) DEFAULT 'website',
            ip_address INET,
            user_agent TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """
        
        # Execute the SQL
        result = supabase.rpc('exec_sql', {'sql': create_table_sql}).execute()
        print("✅ Waitlist table created successfully")
        
        # Create indexes
        indexes_sql = [
            "CREATE INDEX IF NOT EXISTS idx_waitlist_email ON waitlist(email);",
            "CREATE INDEX IF NOT EXISTS idx_waitlist_status ON waitlist(status);",
            "CREATE INDEX IF NOT EXISTS idx_waitlist_created_at ON waitlist(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_waitlist_source ON waitlist(source);"
        ]
        
        for index_sql in indexes_sql:
            try:
                supabase.rpc('exec_sql', {'sql': index_sql}).execute()
                print(f"✅ Created index: {index_sql.split()[5]}")
            except Exception as e:
                print(f"⚠️  Index creation warning: {e}")
        
        print("\n🎉 Waitlist table setup completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error creating waitlist table: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Creating waitlist table in Supabase...")
    success = asyncio.run(create_waitlist_table())
    
    if success:
        print("\n✅ Waitlist table is ready to use!")
    else:
        print("\n❌ Failed to create waitlist table")
        exit(1)
