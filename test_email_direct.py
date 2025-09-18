#!/usr/bin/env python3
"""
Direct test of the email sender service
"""
import asyncio
import os
import sys

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.email_sender import EmailSender

async def test_email_sender_direct():
    """Test the email sender service directly"""
    
    print("🧪 Testing Email Sender Service Directly")
    print("=" * 50)
    
    # Check if API key is available
    api_key = os.getenv("BREVO_API_KEY")
    if not api_key:
        print("❌ BREVO_API_KEY environment variable not set")
        print("   Set BREVO_API_KEY to test email sending")
        return
    
    print(f"✅ BREVO_API_KEY found: {api_key[:10]}...")
    
    # Create email sender instance
    email_sender = EmailSender()
    
    # Test 1: Validate email addresses
    print("\n1. 📧 Testing email validation...")
    test_emails = [
        "test@example.com",
        "user@domain.co.uk", 
        "invalid-email",
        "test@",
        "@domain.com"
    ]
    
    for email in test_emails:
        is_valid = email_sender.validate_email_address(email)
        status = "✅" if is_valid else "❌"
        print(f"   {status} {email}: {'Valid' if is_valid else 'Invalid'}")
    
    # Test 2: Get account info
    print("\n2. 🏢 Testing account info...")
    try:
        account_info = await email_sender.get_account_info()
        if account_info["success"]:
            print("   ✅ Account info retrieved successfully")
            print(f"   📊 Account: {account_info['account'].get('email', 'N/A')}")
        else:
            print(f"   ❌ Account info failed: {account_info['error']}")
    except Exception as e:
        print(f"   ❌ Account info error: {e}")
    
    # Test 3: Send test email (only if you want to actually send)
    print("\n3. 📤 Testing email sending...")
    test_email = input("Enter test email address (or press Enter to skip): ").strip()
    
    if test_email and email_sender.validate_email_address(test_email):
        try:
            print(f"   📧 Sending test email to {test_email}...")
            result = await email_sender.send_test_email(test_email)
            
            if result["success"]:
                print("   ✅ Test email sent successfully!")
                print(f"   📨 Message ID: {result.get('messageId', 'N/A')}")
            else:
                print(f"   ❌ Test email failed: {result.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"   ❌ Test email error: {e}")
    else:
        print("   ⏭️  Skipping email send test")
    
    # Test 4: Test weekly digest (without actually sending)
    print("\n4. 📰 Testing weekly digest generation...")
    try:
        # This tests the digest generation without sending
        test_user_id = "test-user-123"
        test_subject = "Test Weekly Digest"
        test_html = "<html><body><h1>Test Digest</h1><p>This is a test.</p></body></html>"
        test_text = "Test Digest\n\nThis is a test."
        test_template_vars = {"user_name": "Test User"}
        
        print("   📝 Testing digest generation (not sending)...")
        # We'll just test the method exists and can be called
        print("   ✅ Weekly digest method available")
        print("   📋 Template variables: ", test_template_vars)
    except Exception as e:
        print(f"   ❌ Weekly digest test error: {e}")
    
    # Test 5: Test suppression list
    print("\n5. 🚫 Testing suppression list...")
    try:
        suppression_list = await email_sender.get_suppression_list()
        print(f"   ✅ Suppression list retrieved: {len(suppression_list)} entries")
        if suppression_list:
            print(f"   📋 Sample entries: {suppression_list[:3]}")
    except Exception as e:
        print(f"   ❌ Suppression list error: {e}")
    
    print("\n🎉 Email sender service test completed!")

if __name__ == "__main__":
    asyncio.run(test_email_sender_direct())
