#!/usr/bin/env python3
"""
Test script to verify AI summary integration in the insights API
"""

import asyncio
import os
import sys
from app.core.database import get_supabase
from app.services.insights_service import InsightsService
from uuid import UUID

async def test_summary_integration():
    """Test if summary data is being returned correctly from the API"""
    
    print("🧪 Testing AI Summary Integration...")
    
    # Get a test user ID (you may need to adjust this)
    test_user_id = "be91dade-1872-444d-b0e7-185ff7e0545a"  # Replace with actual user ID
    
    try:
        # Initialize the insights service
        insights_service = InsightsService()
        
        print(f"📊 Testing insights retrieval for user: {test_user_id}")
        
        # Test get_insights
        print("\n1️⃣ Testing get_insights...")
        result = await insights_service.get_insights(
            user_id=UUID(test_user_id),
            page=1,
            limit=5,
            include_tags=True
        )
        
        if result.get("success"):
            insights = result.get("data", {}).get("insights", [])
            print(f"✅ Retrieved {len(insights)} insights")
            
            for i, insight in enumerate(insights):
                print(f"\n🔍 Insight {i+1}: {insight.get('title', 'No title')}")
                print(f"   ID: {insight.get('id')}")
                
                # Check insight_contents
                insight_contents = insight.get('insight_contents', [])
                print(f"   Has insight_contents: {len(insight_contents) > 0}")
                
                if insight_contents:
                    content = insight_contents[0]
                    summary = content.get('summary')
                    thought = content.get('thought')
                    
                    print(f"   Summary exists: {summary is not None}")
                    if summary:
                        print(f"   Summary length: {len(summary)}")
                        print(f"   Summary preview: {summary[:100]}...")
                    else:
                        print("   ❌ No summary found")
                    
                    print(f"   Thought exists: {thought is not None}")
                    if thought:
                        print(f"   Thought length: {len(thought)}")
                    else:
                        print("   ❌ No thought found")
                else:
                    print("   ❌ No insight_contents found")
        else:
            print(f"❌ Failed to get insights: {result.get('message')}")
            
        # Test direct database query
        print("\n2️⃣ Testing direct database query...")
        supabase = get_supabase()
        
        # Query insights with insight_contents
        response = supabase.table('insights').select(
            'id, title, insight_contents(summary, thought)'
        ).eq('user_id', test_user_id).limit(3).execute()
        
        if response.data:
            print(f"✅ Direct query returned {len(response.data)} insights")
            for insight in response.data:
                print(f"\n🔍 Direct query insight: {insight.get('title')}")
                contents = insight.get('insight_contents', [])
                if contents:
                    content = contents[0]
                    print(f"   Summary: {content.get('summary', 'None')[:50]}...")
                    print(f"   Thought: {content.get('thought', 'None')[:50]}...")
                else:
                    print("   ❌ No contents in direct query")
        else:
            print("❌ Direct query returned no data")
            
        # Check if there are any summaries in the database
        print("\n3️⃣ Checking database for existing summaries...")
        summary_response = supabase.table('insight_contents').select(
            'insight_id, summary, thought'
        ).not_.is_('summary', 'null').limit(5).execute()
        
        if summary_response.data:
            print(f"✅ Found {len(summary_response.data)} records with summaries")
            for record in summary_response.data:
                print(f"   Insight ID: {record.get('insight_id')}")
                print(f"   Summary: {record.get('summary', '')[:100]}...")
        else:
            print("❌ No summaries found in insight_contents table")
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_summary_integration())
