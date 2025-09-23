#!/usr/bin/env python3
"""
Debug AI Summary Service
Test the AI summary service directly to identify issues
"""

import os
import sys
import asyncio
import logging

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_ai_summary():
    """Debug the AI summary service step by step"""
    
    print("🔍 Debugging AI Summary Service")
    print("=" * 50)
    
    # Check environment variables
    print("\n1️⃣ Checking Environment Variables:")
    openai_key = os.getenv('OPENAI_API_KEY')
    openai_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
    chat_model = os.getenv('CHAT_MODEL', 'gpt-4o-mini')
    
    print(f"   OPENAI_API_KEY: {'✅ Set' if openai_key else '❌ Not set'}")
    print(f"   OPENAI_BASE_URL: {openai_url}")
    print(f"   CHAT_MODEL: {chat_model}")
    
    if not openai_key:
        print("❌ OPENAI_API_KEY not set - AI summary will use fallback")
        return
    
    # Test AI summary service
    print("\n2️⃣ Testing AI Summary Service:")
    
    try:
        from app.services.ai_summary_service import AISummaryService
        
        service = AISummaryService()
        print("✅ AI Summary Service initialized")
        
        # Test with a sample user ID
        test_user_id = "test-user-123"
        print(f"   Testing with user ID: {test_user_id}")
        
        # Test insights retrieval
        print("\n3️⃣ Testing Insights Retrieval:")
        insights = await service._get_weekly_insights(test_user_id)
        print(f"   Found {len(insights)} insights from the past week")
        
        if insights:
            print("   Sample insight structure:")
            sample = insights[0]
            print(f"     Title: {sample.get('title', 'N/A')}")
            print(f"     Created: {sample.get('created_at', 'N/A')}")
            
            # Check insight_contents structure
            insight_contents = sample.get('insight_contents', [])
            if insight_contents and len(insight_contents) > 0:
                print(f"     Summary: {insight_contents[0].get('summary', 'N/A')[:100]}...")
            else:
                print("     No insight_contents data")
        
        # Test AI summary generation
        print("\n4️⃣ Testing AI Summary Generation:")
        
        if insights:
            # Test formatting
            formatted_text = service._format_insights_for_ai(insights)
            print(f"   Formatted text length: {len(formatted_text)}")
            print(f"   Formatted text preview: {formatted_text[:200]}...")
            
            # Test prompt creation
            prompt = service._create_summary_prompt(formatted_text, len(insights))
            print(f"   Prompt length: {len(prompt)}")
            print(f"   Prompt preview: {prompt[:300]}...")
            
            # Test ChatGPT API call
            print("\n5️⃣ Testing ChatGPT API Call:")
            try:
                summary = await service._call_chatgpt_api(prompt)
                if summary:
                    print("✅ ChatGPT API call successful!")
                    print(f"   Summary: {summary}")
                else:
                    print("❌ ChatGPT API returned empty response")
            except Exception as e:
                print(f"❌ ChatGPT API call failed: {e}")
                import traceback
                print(f"   Traceback: {traceback.format_exc()}")
        else:
            print("   No insights available for testing")
        
        # Test full generation
        print("\n6️⃣ Testing Full AI Summary Generation:")
        try:
            full_summary = await service.generate_weekly_insights_summary(test_user_id)
            print(f"✅ Full generation result: {full_summary}")
        except Exception as e:
            print(f"❌ Full generation failed: {e}")
            import traceback
            print(f"   Traceback: {traceback.format_exc()}")
            
    except Exception as e:
        print(f"❌ Error initializing AI summary service: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(debug_ai_summary())
