#!/usr/bin/env python3
"""
Test script to debug email API authentication issues
"""
import requests
import json

# Test token from the frontend logs
TOKEN = "eyJhbGciOiJIUzI1NiIsImtpZCI6IjJTWkh3clV5YWRXQm5EaWwiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3dscGl0c3Rnam9teW56Zm5xa3llLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiJiZTkxZGFkZS0xODcyLTQ0NGQtYjBlNy0xODVmZjdlMDU0NWEiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzU4MjY5NjM0LCJpYXQiOjE3NTgxODMyMzQsImVtYWlsIjoic3RhbzA0MjkwNkBnbWFpbC5jb20iLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7ImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJuaWNrbmFtZSI6IkdhcnkiLCJ1c2VybmFtZSI6InN0YW8wNDI5MDZfMmI4NzllNzYifSwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhYWwiOiJhYWwxIiwiYW1yIjpbeyJtZXRob2QiOiJwYXNzd29yZCIsInRpbWVzdGFtcCI6MTc1ODE4MzIzNH1dLCJzZXNzaW9uX2lkIjoiNzlmZDBlMGItOWE5OS00NzRjLWI0YzQtMGRkMTk5MTlhMDYwIiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.-7u2Y_WcJcxM7X8WDQ92repoTgqQ_1OLf5Rkxs9z5Dc"

BASE_URL = "https://quest-api-edz1.onrender.com"

def test_email_preferences():
    """Test the email preferences endpoint"""
    url = f"{BASE_URL}/api/v1/email/preferences"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    
    print(f"Testing GET {url}")
    print(f"Token (first 50 chars): {TOKEN[:50]}...")
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 401:
            print("\n❌ Authentication failed!")
            try:
                error_data = response.json()
                print(f"Error details: {json.dumps(error_data, indent=2)}")
            except:
                print("Could not parse error response as JSON")
        elif response.status_code == 200:
            print("\n✅ Authentication successful!")
            try:
                data = response.json()
                print(f"Response data: {json.dumps(data, indent=2)}")
            except:
                print("Could not parse response as JSON")
        else:
            print(f"\n⚠️ Unexpected status code: {response.status_code}")
            
    except Exception as e:
        print(f"Request failed: {e}")

def decode_token():
    """Decode the token to see its contents"""
    import jwt
    
    print("Decoding token without verification:")
    try:
        payload = jwt.decode(TOKEN, options={"verify_signature": False})
        print(f"Token payload: {json.dumps(payload, indent=2)}")
        
        # Check token expiration
        import time
        current_time = int(time.time())
        exp_time = payload.get('exp', 0)
        
        print(f"\nToken timing:")
        print(f"Current time: {current_time}")
        print(f"Expiration time: {exp_time}")
        print(f"Time until expiration: {exp_time - current_time} seconds")
        
        if exp_time < current_time:
            print("❌ TOKEN IS EXPIRED!")
        else:
            print("✅ Token is still valid")
            
    except Exception as e:
        print(f"Failed to decode token: {e}")

if __name__ == "__main__":
    print("=== Email API Authentication Test ===\n")
    
    decode_token()
    print("\n" + "="*50 + "\n")
    test_email_preferences()
