"""
Check the payload of the digest that was sent
"""
import asyncio
from dotenv import load_dotenv
from app.services.digest_repo import DigestRepo
import json

load_dotenv()

async def check_digest_payload(digest_id: str):
    """Check what was in the digest payload"""
    repo = DigestRepo()
    
    print(f"\n{'='*60}")
    print(f"Checking Digest: {digest_id}")
    print('='*60 + '\n')
    
    # Get digest record
    result = repo.supabase_service.table("email_digests").select("*").eq("id", digest_id).execute()
    
    if not result.data:
        print("❌ Digest not found")
        return
    
    digest = result.data[0]
    
    print(f"Status: {digest.get('status')}")
    print(f"User ID: {digest.get('user_id')}")
    print(f"Week Start: {digest.get('week_start')}")
    print(f"Sent At: {digest.get('sent_at')}\n")
    
    payload = digest.get('payload', {})
    print(f"Payload Keys: {list(payload.keys())}\n")
    
    if 'ai_summary' in payload:
        ai_summary = payload['ai_summary']
        print(f"✅ AI Summary Found ({len(ai_summary)} chars):")
        print(f"   {ai_summary[:300]}..." if len(ai_summary) > 300 else f"   {ai_summary}")
    else:
        print("❌ No ai_summary in payload")
        print(f"\nFull payload structure:")
        print(json.dumps(payload, indent=2)[:1000])
    
    print(f"\n{'='*60}")

if __name__ == "__main__":
    # Check the digest for stao042906@gmail.com
    digest_id = "b2744056-73c4-4d09-ac64-b4e5c61412c3"
    asyncio.run(check_digest_payload(digest_id))
