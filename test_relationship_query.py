#!/usr/bin/env python3
"""
Test the relationship query syntax to see if it's working
"""

import os
import sys
from supabase import create_client, Client

def test_relationship_queries():
    """Test different relationship query syntaxes"""
    
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
        
        # Test 1: Basic insights query
        print("\n🧪 Test 1: Basic insights query...")
        try:
            result = supabase.table('insights').select('id, title').limit(3).execute()
            print(f"📊 Found {len(result.data)} insights")
            if result.data:
                print("📋 Sample insights:", [{"id": i["id"], "title": i["title"]} for i in result.data[:2]])
        except Exception as e:
            print(f"❌ Error querying insights: {e}")
        
        # Test 2: Basic insight_contents query
        print("\n🧪 Test 2: Basic insight_contents query...")
        try:
            result = supabase.table('insight_contents').select('id, insight_id, summary').limit(3).execute()
            print(f"📊 Found {len(result.data)} insight_contents")
            if result.data:
                print("📋 Sample insight_contents:", [{"id": i["id"], "insight_id": i["insight_id"], "summary": i["summary"][:50] + "..." if i["summary"] else "NULL"} for i in result.data[:2]])
        except Exception as e:
            print(f"❌ Error querying insight_contents: {e}")
        
        # Test 3: Relationship query with different syntaxes
        print("\n🧪 Test 3: Testing relationship query syntaxes...")
        
        # Syntax 1: insight_contents(summary, thought)
        try:
            print("🔍 Testing syntax: insight_contents(summary, thought)")
            result = supabase.table('insights').select(
                'id, title, insight_contents(summary, thought)'
            ).limit(2).execute()
            
            print(f"📊 Relationship query returned {len(result.data)} insights")
            if result.data:
                for i, insight in enumerate(result.data):
                    print(f"🔍 Insight {i+1}: {insight.get('title', 'No title')}")
                    print(f"   - insight_contents: {insight.get('insight_contents', 'None')}")
            else:
                print("❌ No insights returned from relationship query")
                
        except Exception as e:
            print(f"❌ Error with relationship query: {e}")
        
        # Test 4: Check if there are matching insight_ids
        print("\n🧪 Test 4: Checking for matching insight_ids...")
        try:
            # Get some insight IDs
            insights_result = supabase.table('insights').select('id').limit(5).execute()
            insight_ids = [i['id'] for i in insights_result.data] if insights_result.data else []
            
            if insight_ids:
                print(f"📊 Checking {len(insight_ids)} insights for content...")
                print(f"📋 Insight IDs: {insight_ids}")
                
                # Check if any of these insights have content
                content_result = supabase.table('insight_contents').select('insight_id, summary').in_('insight_id', insight_ids).execute()
                
                print(f"📊 Found {len(content_result.data)} insight_contents records for these insights")
                
                if content_result.data:
                    print("✅ Found matching insight_contents records!")
                    for content in content_result.data:
                        print(f"   - Insight {content['insight_id']}: summary={bool(content.get('summary'))}")
                else:
                    print("❌ No insight_contents records found for any of these insights")
                    print("🔍 This suggests the insight_ids don't match between tables")
            else:
                print("❌ No insights found to check")
                
        except Exception as e:
            print(f"❌ Error checking matching insight_ids: {e}")
            
    except Exception as e:
        print(f"❌ Error creating Supabase client: {e}")

if __name__ == "__main__":
    test_relationship_queries()
