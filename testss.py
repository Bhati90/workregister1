import requests
import json

META_ACCESS_TOKEN = "EAAhMBt21QaMBPCyLtJj6gwjDy6Gai4fZApb3MXuZBZCCm0iSEd8ZCZCJdkRt4cOtvhyeFLZCNUwitFaLZA3ZCwv7enN6FBFgDMAOKl7LMx0J2kCjy6Qd6AqnbnhB2bo2tgsdGmn9ZCN5MD6yCgE3shuP62t1spfSB6ZALy1QkNLvIaeWZBcvPH00HHpyW6US4kil2ENZADL4ZCvDLVWV9seSbZCxXYzVCezIenCjhSYtoKTIlJ"
WABA_ID = "1477047197063313"

def test_minimal_publishable_flow():
    """Test with the most minimal publishable flow structure"""
    
    # Ultra-minimal flow that should definitely be publishable
    flow_json = {
        "version": "5.0",
        "screens": [
            {
                "id": "WELCOME_SCREEN",
                "title": "Welcome",
                "layout": {
                    "type": "SingleColumnLayout",
                    "children": [
                        {
                            "type": "TextHeading",
                            "text": "Hello World"
                        },
                        {
                            "type": "Footer",
                            "label": "Complete",
                            "on-click-action": {
                                "name": "complete",
                                "payload": {}
                            }
                        }
                    ]
                },
                "terminal": True,
                "success": True
            }
        ]
    }
    
    payload = {
        "name": "minimal_test_flow",
        "flow_json": json.dumps(flow_json),
        "categories": ["OTHER"]
    }
    
    headers = {
        "Authorization": f"Bearer {META_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    url = f"https://graph.facebook.com/v19.0/{WABA_ID}/flows"
    
    print("=== Creating Minimal Flow ===")
    response = requests.post(url, headers=headers, json=payload)
    result = response.json()
    
    if response.status_code == 200:
        flow_id = result.get('id')
        print(f"✅ Flow created successfully! Flow ID: {flow_id}")
        
        # Try to publish
        print("=== Attempting to Publish ===")
        publish_url = f"https://graph.facebook.com/v19.0/{flow_id}/publish"
        publish_response = requests.post(publish_url, headers=headers, json={})
        publish_result = publish_response.json()
        
        print(f"Publish Response Status: {publish_response.status_code}")
        print(f"Publish Response: {json.dumps(publish_result, indent=2)}")
        
        if publish_response.status_code == 200:
            print("✅ Flow published successfully!")
            return flow_id
        else:
            print("❌ Failed to publish")
            
            # Let's check the flow details to see what might be wrong
            print("\n=== Checking Flow Details ===")
            flow_details_url = f"https://graph.facebook.com/v19.0/{flow_id}"
            details_response = requests.get(flow_details_url, headers=headers)
            print(f"Flow Details: {json.dumps(details_response.json(), indent=2)}")
            
    else:
        print(f"❌ Failed to create flow: {result}")
    
    return None

def check_account_permissions():
    """Check if the account has proper permissions"""
    headers = {
        "Authorization": f"Bearer {META_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    print("\n=== Checking Account Permissions ===")
    
    # Check WABA details
    waba_url = f"https://graph.facebook.com/v19.0/{WABA_ID}"
    waba_response = requests.get(waba_url, headers=headers)
    print(f"WABA Details: {json.dumps(waba_response.json(), indent=2)}")
    
    # Check if we can list existing flows
    flows_url = f"https://graph.facebook.com/v19.0/{WABA_ID}/flows"
    flows_response = requests.get(flows_url, headers=headers)
    print(f"Existing Flows: {json.dumps(flows_response.json(), indent=2)}")

if __name__ == "__main__":
    check_account_permissions()
    test_minimal_publishable_flow()
    
    print("\n=== Troubleshooting Tips ===")
    print("1. Check if your WABA is verified and approved for Flows")
    print("2. Verify your access token has 'whatsapp_business_management' permissions")
    print("3. Check if there are any pending reviews or restrictions on your account")
    print("4. Try publishing manually in Meta Business Manager first")
    print("5. Contact Meta support if the issue persists")