#!/usr/bin/env python3
"""
Test if there are any insight_contents records in the database
"""

import os
import sys
from supabase import create_client, Client

def test_insight_contents():
    """Test if insight_contents table has any data"""
    
    # Get Supabase credentials from environment
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    
    if not url or not key:
        print("❌ Supabase credentials not found in environment")
        print("🔍 Please set SUPABASE_URL and SUPABASE_ANON_KEY")
        return
    
    try:
        # Create Supabase client
        supabase: Client = create_client(url, key)
        print("✅ Supabase client created")
        
        # Test 1: Check if insight_contents table exists and has data
        print("\n🧪 Test 1: Checking insight_contents table...")
        try:
            result = supabase.table('insight_contents').select('*').limit(5).execute()
            print(f"📊 Found {len(result.data)} insight_contents records")
            
            if result.data:
                print("✅ insight_contents table has data!")
                print("📋 Sample record:", result.data[0])
            else:
                print("❌ insight_contents table is empty")
        except Exception as e:
            print(f"❌ Error querying insight_contents: {e}")
        
        # Test 2: Check insights table
        print("\n🧪 Test 2: Checking insights table...")
        try:
            result = supabase.table('insights').select('id, title, created_at').limit(5).execute()
            print(f"📊 Found {len(result.data)} insights records")
            
            if result.data:
                print("✅ insights table has data!")
                print("📋 Sample insight:", result.data[0])
            else:
                print("❌ insights table is empty")
        except Exception as e:
            print(f"❌ Error querying insights: {e}")
        
        # Test 3: Try the relationship query
        print("\n🧪 Test 3: Testing relationship query...")
        try:
            result = supabase.table('insights').select(
                'id, title, insight_contents!left(summary, thought)'
            ).limit(3).execute()
            
            print(f"📊 Relationship query returned {len(result.data)} insights")
            
            if result.data:
                for i, insight in enumerate(result.data):
                    print(f"🔍 Insight {i+1}: {insight.get('title', 'No title')}")
                    print(f"   - insight_contents: {insight.get('insight_contents', 'None')}")
            else:
                print("❌ No insights returned from relationship query")
                
        except Exception as e:
            print(f"❌ Error with relationship query: {e}")
        
        # Test 4: Check if there are any insights with insight_contents
        print("\n🧪 Test 4: Checking for insights with content...")
        try:
            # First get all insight IDs
            insights_result = supabase.table('insights').select('id').limit(10).execute()
            insight_ids = [i['id'] for i in insights_result.data] if insights_result.data else []
            
            if insight_ids:
                print(f"📊 Checking {len(insight_ids)} insights for content...")
                
                # Check if any of these insights have content
                content_result = supabase.table('insight_contents').select('insight_id, summary, thought').in_('insight_id', insight_ids).execute()
                
                print(f"📊 Found {len(content_result.data)} insight_contents records for these insights")
                
                if content_result.data:
                    print("✅ Found insight_contents records!")
                    for content in content_result.data:
                        print(f"   - Insight {content['insight_id']}: summary={bool(content.get('summary'))}, thought={bool(content.get('thought'))}")
                else:
                    print("❌ No insight_contents records found for any insights")
            else:
                print("❌ No insights found to check")
                
        except Exception as e:
            print(f"❌ Error checking insights with content: {e}")
            
    except Exception as e:
        print(f"❌ Error creating Supabase client: {e}")

if __name__ == "__main__":
    test_insight_contents()
