#!/usr/bin/env python3
"""
Simple test script to debug AI summary service
Run this from the quest-api directory
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

async def test_ai_health():
    """Test the AI summary service health check"""
    try:
        from app.services.ai_summary_service import get_ai_summary_service
        
        print("🔍 Testing AI Summary Service...")
        print("=" * 50)
        
        service = get_ai_summary_service()
        
        # Check basic availability
        print(f"✅ Client available: {service.is_available()}")
        print(f"✅ API Key set: {bool(service.openai_api_key)}")
        print(f"✅ Model: {service.chat_model}")
        print(f"✅ Base URL: {service.openai_base_url}")
        print()
        
        # Test health check
        print("🏥 Running health check...")
        is_healthy, health_msg = await service._health_check()
        print(f"✅ Health check: {is_healthy}")
        print(f"✅ Health message: {health_msg}")
        print()
        
        if is_healthy:
            print("🎉 AI Summary Service is working!")
        else:
            print("❌ AI Summary Service has issues:")
            print(f"   - {health_msg}")
            
    except Exception as e:
        print(f"❌ Error testing AI service: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    print("Starting AI Summary Service Debug Test...")
    asyncio.run(test_ai_health())
