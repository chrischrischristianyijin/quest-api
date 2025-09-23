#!/usr/bin/env python3
"""
Test script for Email Digest with AI Summary integration
Tests the complete email digest generation with the new AI summary feature
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.api.v1.email import _generate_digest_params
from app.core.database import get_supabase_service

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_email_digest_with_ai_summary():
    """Test email digest generation with AI summary"""
    
    print("📧 Testing Email Digest with AI Summary")
    print("=" * 50)
    
    # Check if OpenAI API key is configured
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key to test the AI summary feature")
        return False
    
    # Check if Supabase is configured
    if not os.getenv('SUPABASE_URL'):
        print("❌ Error: SUPABASE_URL environment variable not set")
        print("Please configure Supabase to test the email digest feature")
        return False
    
    try:
        # Test with a sample user
        test_user = {
            "id": "test-user-123",
            "email": "test@example.com",
            "name": "Test User"
        }
        
        print(f"👤 Testing with user: {test_user['email']}")
        
        # Generate digest parameters
        print("\n🔄 Generating digest parameters...")
        
        try:
            params = await _generate_digest_params(test_user)
            
            print("✅ Digest parameters generated successfully!")
            print(f"📊 Tags: {len(params.get('tags', []))}")
            print(f"🤖 AI Summary: {params.get('ai_summary', 'N/A')[:100]}...")
            print(f"🏷️  Recommended Tag: {params.get('recommended_tag', 'N/A')}")
            print(f"📚 Recommended Articles: {params.get('recommended_articles', 'N/A')}")
            
            # Check if AI summary looks good
            ai_summary = params.get('ai_summary', '')
            if ai_summary and len(ai_summary.strip()) > 0:
                print("\n✅ AI Summary generated successfully!")
                
                # Check for bullet points
                if "•" in ai_summary or "-" in ai_summary:
                    print("✅ AI Summary appears to be formatted as bullet points")
                else:
                    print("⚠️  AI Summary may not be in bullet point format")
                
                # Show the full AI summary
                print(f"\n📝 Full AI Summary:")
                print("-" * 40)
                print(ai_summary)
                print("-" * 40)
                
            else:
                print("⚠️  AI Summary is empty - this might be expected if there are no insights")
            
            return True
            
        except Exception as e:
            print(f"❌ Error generating digest parameters: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False

async def test_ai_summary_service_directly():
    """Test the AI summary service directly"""
    
    print("\n🧠 Testing AI Summary Service Directly")
    print("=" * 50)
    
    try:
        from app.services.ai_summary_service import AISummaryService
        
        service = AISummaryService()
        test_user_id = "test-user-123"
        
        print(f"🔄 Generating AI summary for user: {test_user_id}")
        
        summary = await service.generate_weekly_insights_summary(test_user_id)
        
        if summary:
            print("✅ AI Summary generated successfully!")
            print(f"\n📝 Summary: {summary}")
        else:
            print("ℹ️  No summary generated (likely no insights found)")
            
        return True
        
    except Exception as e:
        print(f"❌ Error testing AI summary service: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Starting Email Digest AI Summary Integration Tests")
    print("=" * 60)
    
    # Check environment
    required_vars = ['OPENAI_API_KEY', 'SUPABASE_URL']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("\nTo run this test, set the following environment variables:")
        for var in missing_vars:
            print(f"  export {var}=your_value_here")
        return False
    
    # Run tests
    try:
        success1 = asyncio.run(test_email_digest_with_ai_summary())
        success2 = asyncio.run(test_ai_summary_service_directly())
        
        if success1 and success2:
            print("\n✅ All tests passed! Email Digest with AI Summary is working correctly.")
            return True
        else:
            print("\n❌ Some tests failed. Please check the errors above.")
            return False
            
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error during testing: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
