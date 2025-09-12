#!/usr/bin/env python3
"""
Test script for stacks endpoints
"""
import requests
import json
from uuid import uuid4

# Test configuration
BASE_URL = "https://quest-api-edz1.onrender.com"
# BASE_URL = "http://localhost:8000"  # For local testing

def test_stacks_endpoints():
    """Test all stacks endpoints"""
    print("🧪 Testing Stacks API Endpoints")
    print("=" * 50)
    
    # Test 1: Check if stacks endpoints are available
    print("\n1. Checking if stacks endpoints are available...")
    try:
        response = requests.get(f"{BASE_URL}/openapi.json")
        if response.status_code == 200:
            openapi_spec = response.json()
            stack_paths = [path for path in openapi_spec.get('paths', {}).keys() if 'stacks' in path]
            if stack_paths:
                print(f"✅ Found stacks endpoints: {stack_paths}")
            else:
                print("❌ No stacks endpoints found in API spec")
                return False
        else:
            print(f"❌ Failed to get OpenAPI spec: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error checking API spec: {e}")
        return False
    
    # Test 2: Test stack creation (without auth - should fail)
    print("\n2. Testing stack creation without auth...")
    try:
        stack_data = {
            "name": "Test Stack",
            "description": "A test stack"
        }
        response = requests.post(f"{BASE_URL}/api/v1/stacks", json=stack_data)
        print(f"   Status: {response.status_code}")
        if response.status_code == 401:
            print("✅ Correctly requires authentication")
        else:
            print(f"❌ Unexpected response: {response.text}")
    except Exception as e:
        print(f"❌ Error testing stack creation: {e}")
    
    # Test 3: Test stack listing (without auth - should fail)
    print("\n3. Testing stack listing without auth...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/stacks")
        print(f"   Status: {response.status_code}")
        if response.status_code == 401:
            print("✅ Correctly requires authentication")
        else:
            print(f"❌ Unexpected response: {response.text}")
    except Exception as e:
        print(f"❌ Error testing stack listing: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Basic endpoint tests completed!")
    print("Note: Full functionality requires authentication and database setup")

if __name__ == "__main__":
    test_stacks_endpoints()


