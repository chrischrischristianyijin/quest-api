#!/usr/bin/env python3
"""
Test the deployed API directly to check if insight_contents data is being returned
"""

import requests
import json

def test_api_response():
    """Test the API response to see if insight_contents is included"""
    
    # Test the API endpoint
    url = "https://quest-api-edz1.onrender.com/api/v1/insights/"
    params = {
        'page': 1,
        'limit': 5,
        'user_id': 'be91dade-1872-444d-b0e7-185ff7e0545a',
        'include_tags': 'true'
    }
    
    print("🧪 Testing API endpoint:", url)
    print("📋 Parameters:", params)
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"📡 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API Response received")
            print(f"📊 Response keys: {list(data.keys())}")
            
            if 'data' in data and 'items' in data['data']:
                items = data['data']['items']
                print(f"📦 Found {len(items)} insights")
                
                if items:
                    first_item = items[0]
                    print(f"🔍 First insight keys: {list(first_item.keys())}")
                    
                    if 'insight_contents' in first_item:
                        print("✅ insight_contents field found!")
                        print(f"📋 insight_contents: {first_item['insight_contents']}")
                    else:
                        print("❌ insight_contents field NOT found")
                        print("🔍 Available fields:", list(first_item.keys()))
                else:
                    print("❌ No insights found in response")
            else:
                print("❌ Unexpected response structure")
                print("📋 Full response:", json.dumps(data, indent=2)[:500] + "...")
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"📋 Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing API: {e}")

if __name__ == "__main__":
    test_api_response()
