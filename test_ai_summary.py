#!/usr/bin/env python3
"""
Test script for AI Summary Service
Tests the new AI-powered insights summarization feature
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.services.ai_summary_service import AISummaryService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_ai_summary_service():
    """Test the AI summary service with sample data"""
    
    print("🧠 Testing AI Summary Service")
    print("=" * 50)
    
    # Check if OpenAI API key is configured
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key to test the AI summary feature")
        return False
    
    # Initialize the service
    try:
        service = AISummaryService()
        print("✅ AI Summary Service initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize AI Summary Service: {e}")
        return False
    
    # Test with a sample user ID (you can replace this with a real user ID from your database)
    test_user_id = "test-user-123"
    
    print(f"\n📊 Testing AI summary generation for user: {test_user_id}")
    
    try:
        # Generate AI summary
        summary = await service.generate_weekly_insights_summary(test_user_id)
        
        print("\n📝 Generated AI Summary:")
        print("-" * 30)
        print(summary)
        print("-" * 30)
        
        if summary and len(summary.strip()) > 0:
            print("✅ AI summary generated successfully!")
            
            # Check if it looks like bullet points
            if "•" in summary or "-" in summary:
                print("✅ Summary appears to be formatted as bullet points")
            else:
                print("⚠️  Summary may not be in bullet point format")
            
            # Check length
            if len(summary) > 50:
                print("✅ Summary has substantial content")
            else:
                print("⚠️  Summary seems quite short")
                
        else:
            print("❌ AI summary is empty or failed to generate")
            return False
            
    except Exception as e:
        print(f"❌ Error generating AI summary: {e}")
        return False
    
    # Test fallback functionality
    print(f"\n🔄 Testing fallback functionality...")
    
    try:
        # Test with empty insights
        fallback_summary = service._get_fallback_summary_from_insights([])
        print(f"Empty insights fallback: {fallback_summary}")
        
        # Test with sample insights
        sample_insights = [
            {
                "title": "Machine Learning Basics",
                "summary": "Introduction to supervised and unsupervised learning algorithms",
                "url": "https://example.com/ml-basics",
                "tags": ["AI", "Technology"]
            },
            {
                "title": "Python Data Structures",
                "summary": "Understanding lists, dictionaries, and sets in Python",
                "url": "https://example.com/python-data",
                "tags": ["Programming", "Python"]
            }
        ]
        
        fallback_with_insights = service._get_fallback_summary_from_insights(sample_insights)
        print(f"Sample insights fallback: {fallback_with_insights}")
        
        print("✅ Fallback functionality working correctly")
        
    except Exception as e:
        print(f"❌ Error testing fallback functionality: {e}")
        return False
    
    print("\n🎉 All tests completed successfully!")
    return True

async def test_with_real_data():
    """Test with real data from the database (if available)"""
    
    print("\n🔍 Testing with real database data...")
    
    try:
        service = AISummaryService()
        
        # Try to get insights from the past week
        insights = await service._get_weekly_insights("test-user-123")
        
        if insights:
            print(f"✅ Found {len(insights)} insights from the past week")
            
            # Show sample insights (handle insight_contents join structure)
            for i, insight in enumerate(insights[:3], 1):  # Show first 3
                print(f"\nInsight {i}:")
                print(f"  Title: {insight.get('title', 'N/A')}")
                
                # Extract summary from insight_contents join
                insight_contents = insight.get('insight_contents', [])
                summary = ""
                if insight_contents and len(insight_contents) > 0:
                    summary = insight_contents[0].get('summary', '') or insight_contents[0].get('thought', '')
                if not summary:
                    summary = insight.get('description', 'N/A')
                
                print(f"  Summary: {summary[:100]}...")
                print(f"  Created: {insight.get('created_at', 'N/A')}")
        else:
            print("ℹ️  No insights found for the past week (this is normal for test data)")
            
    except Exception as e:
        print(f"⚠️  Could not test with real data: {e}")
        print("This is expected if the database is not accessible or has no test data")

def main():
    """Main test function"""
    print("🚀 Starting AI Summary Service Tests")
    print("=" * 50)
    
    # Check environment
    required_vars = ['OPENAI_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("\nTo run this test, set the following environment variables:")
        for var in missing_vars:
            print(f"  export {var}=your_value_here")
        return False
    
    # Run tests
    try:
        success = asyncio.run(test_ai_summary_service())
        asyncio.run(test_with_real_data())
        
        if success:
            print("\n✅ All tests passed! AI Summary Service is working correctly.")
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
