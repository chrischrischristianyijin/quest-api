#!/usr/bin/env python3
"""
Test webhook configuration after setting up in Brevo
"""
import asyncio
import httpx
import json
from datetime import datetime, timezone

# Your webhook endpoint
WEBHOOK_URL = "https://quest-api-edz1.onrender.com/api/v1/email/webhooks/brevo"

async def test_webhook_configuration():
    """Test the webhook configuration"""
    
    print("🔗 Testing Brevo Webhook Configuration")
    print("=" * 50)
    
    # Test webhook events
    test_events = [
        {
            "event": "delivered",
            "message-id": "test-delivered-001",
            "email": "test@example.com",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": "test-delivery"
        },
        {
            "event": "opened",
            "message-id": "test-opened-002", 
            "email": "test@example.com",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": "test-open"
        },
        {
            "event": "clicked",
            "message-id": "test-clicked-003",
            "email": "test@example.com", 
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": "test-click",
            "url": "https://myquestspace.com/my-space"
        },
        {
            "event": "bounced",
            "message-id": "test-bounced-004",
            "email": "invalid@example.com",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": "test-bounce"
        },
        {
            "event": "spam",
            "message-id": "test-spam-005",
            "email": "spam@example.com",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": "test-spam"
        }
    ]
    
    async with httpx.AsyncClient() as client:
        print(f"📡 Testing webhook endpoint: {WEBHOOK_URL}")
        print()
        
        for i, event in enumerate(test_events, 1):
            print(f"{i}. Testing {event['event']} event...")
            
            try:
                response = await client.post(
                    WEBHOOK_URL,
                    json=event,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    print(f"   ✅ {event['event']}: Success")
                    print(f"   📨 Response: {response.text}")
                else:
                    print(f"   ❌ {event['event']}: Failed - {response.status_code}")
                    print(f"   📨 Response: {response.text}")
                    
            except Exception as e:
                print(f"   ❌ {event['event']}: Error - {e}")
            
            print()
        
        print("🎉 Webhook configuration test completed!")
        print()
        print("📋 Next Steps:")
        print("1. Set BREVO_API_KEY in Render dashboard")
        print("2. Configure webhook in Brevo dashboard")
        print("3. Test with real email sending")
        print("4. Monitor webhook events in Brevo dashboard")

if __name__ == "__main__":
    asyncio.run(test_webhook_configuration())
