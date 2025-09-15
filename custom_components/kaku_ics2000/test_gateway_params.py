#!/usr/bin/env python3
"""
Test different parameters with gateway.php to see if we can get unencrypted device data
"""

import json
import ssl
import urllib.request
import urllib.parse

def test_gateway_parameters():
    """Test different parameter combinations with gateway.php."""
    
    print("=== Testing Gateway.php Parameters ===\n")
    
    # Get credentials
    email = input("Enter email: ").strip()
    password = input("Enter password: ").strip()
    
    # First authenticate to get details
    print("\n1. Authenticating...")
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    login_data = {
        'action': 'login',
        'email': email,
        'password_hash': password,
        'device_unique_id': 'android',
        'platform': '',
        'mac': '',
    }
    
    try:
        data = urllib.parse.urlencode(login_data).encode('utf-8')
        req = urllib.request.Request(
            "https://trustsmartcloud2.com/ics2000_api/account.php",
            data=data,
            method='POST'
        )
        
        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            auth_text = response.read().decode('utf-8')
            auth_data = json.loads(auth_text)
            
            if 'homes' not in auth_data or not auth_data['homes']:
                print("❌ No homes found")
                return
            
            home = auth_data['homes'][0]
            home_id = home['home_id']
            gateway_mac = home['mac']
            aes_key = home['aes_key']
            
            print(f"✅ Authenticated")
            print(f"   Home ID: {home_id}")
            print(f"   Gateway MAC: {gateway_mac}")
            
    except Exception as e:
        print(f"❌ Auth failed: {e}")
        return
    
    print("\n2. Testing different gateway.php parameters...")
    
    # Different parameter combinations to try
    test_params = [
        # Original working params
        {
            'email': email,
            'mac': gateway_mac,
            'action': 'sync',
            'password_hash': password,
            'home_id': home_id,
        },
        # Try with format parameter
        {
            'email': email,
            'mac': gateway_mac,
            'action': 'sync',
            'password_hash': password,
            'home_id': home_id,
            'format': 'json',
        },
        # Try with decrypt flag
        {
            'email': email,
            'mac': gateway_mac,
            'action': 'sync',
            'password_hash': password,
            'home_id': home_id,
            'decrypt': '1',
        },
        # Try with raw flag
        {
            'email': email,
            'mac': gateway_mac,
            'action': 'sync',
            'password_hash': password,
            'home_id': home_id,
            'raw': '1',
        },
        # Try get_devices action
        {
            'email': email,
            'mac': gateway_mac,
            'action': 'get_devices',
            'password_hash': password,
            'home_id': home_id,
        },
        # Try list action
        {
            'email': email,
            'mac': gateway_mac,
            'action': 'list',
            'password_hash': password,
            'home_id': home_id,
        },
        # Try with AES key included
        {
            'email': email,
            'mac': gateway_mac,
            'action': 'sync',
            'password_hash': password,
            'home_id': home_id,
            'aes_key': aes_key,
        },
        # Try with version parameter
        {
            'email': email,
            'mac': gateway_mac,
            'action': 'sync',
            'password_hash': password,
            'home_id': home_id,
            'version': '2',
        },
        # Try plain password field
        {
            'email': email,
            'mac': gateway_mac,
            'action': 'sync',
            'password': password,
            'home_id': home_id,
        },
    ]
    
    for i, params in enumerate(test_params):
        print(f"\n--- Test {i+1}: {list(params.keys())} ---")
        
        try:
            data = urllib.parse.urlencode(params).encode('utf-8')
            req = urllib.request.Request(
                "https://trustsmartcloud2.com/ics2000_api/gateway.php",
                data=data,
                method='POST'
            )
            
            with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
                text = response.read().decode('utf-8')
                
                # Check response format
                if text.startswith('['):
                    print("  Response format: JSON array")
                elif text.startswith('{'):
                    print("  Response format: JSON object")
                else:
                    print(f"  Response format: Other ({text[:20]}...)")
                
                # Try to parse
                try:
                    data = json.loads(text)
                    
                    # Check structure
                    if isinstance(data, list) and data:
                        item = data[0]
                        print(f"  First item keys: {list(item.keys())}")
                        
                        # Check if we have unencrypted entities
                        if 'entities' in item:
                            print("  ✅ Found 'entities' key directly!")
                            entities = item['entities']
                            if entities:
                                print(f"  → {len(entities)} entities")
                                print(f"  → First entity: {entities[0]}")
                            return
                        
                        # Check data field
                        if 'data' in item:
                            data_field = item['data']
                            # Check if data is already JSON
                            if isinstance(data_field, dict):
                                print("  ✅ 'data' field is already a dict!")
                                if 'entities' in data_field:
                                    print(f"  → Found {len(data_field['entities'])} entities")
                                return
                            elif isinstance(data_field, str):
                                # Check if it's JSON string
                                if data_field.startswith('{') or data_field.startswith('['):
                                    try:
                                        parsed = json.loads(data_field)
                                        print("  ✅ 'data' field is JSON string!")
                                        if 'entities' in parsed:
                                            print(f"  → Found {len(parsed['entities'])} entities")
                                        return
                                    except:
                                        pass
                                
                                # Check length to see if encrypted
                                if len(data_field) > 100:
                                    print(f"  'data' is long string ({len(data_field)} chars) - likely encrypted")
                                else:
                                    print(f"  'data' is short string: {data_field}")
                    
                    elif isinstance(data, dict):
                        print(f"  Response keys: {list(data.keys())}")
                        
                        if 'entities' in data:
                            print("  ✅ Found 'entities' key directly!")
                            print(f"  → {len(data['entities'])} entities")
                            if data['entities']:
                                print(f"  → First entity: {data['entities'][0]}")
                            return
                    
                except json.JSONDecodeError:
                    print("  Not valid JSON")
                    # Check if response contains readable text
                    if 'entity' in text.lower() or 'device' in text.lower():
                        print("  But contains device-related keywords!")
                        print(f"  Preview: {text[:200]}")
                
        except Exception as e:
            print(f"  Error: {e}")
    
    print("\n3. Testing other endpoints...")
    
    other_endpoints = [
        "https://trustsmartcloud2.com/ics2000_api/devices.php",
        "https://trustsmartcloud2.com/ics2000_api/entities.php",
        "https://trustsmartcloud2.com/ics2000_api/get_devices.php",
        "https://trustsmartcloud.com/api/gateway.php",
    ]
    
    base_params = {
        'email': email,
        'mac': gateway_mac,
        'password_hash': password,
        'home_id': home_id,
    }
    
    for endpoint in other_endpoints:
        print(f"\n--- Testing {endpoint.split('/')[-1]} ---")
        
        for action in ['sync', 'get', 'list', '']:
            params = base_params.copy()
            if action:
                params['action'] = action
            
            try:
                data = urllib.parse.urlencode(params).encode('utf-8')
                req = urllib.request.Request(endpoint, data=data, method='POST')
                
                with urllib.request.urlopen(req, context=ctx, timeout=5) as response:
                    text = response.read().decode('utf-8')
                    
                    if 'entity' in text.lower() or 'device' in text.lower():
                        print(f"  ✅ Action '{action}' returned device data!")
                        print(f"  Preview: {text[:200]}")
                        
                        try:
                            parsed = json.loads(text)
                            if 'entities' in parsed:
                                print(f"  → Found {len(parsed['entities'])} entities!")
                                return
                        except:
                            pass
                        
            except:
                pass

if __name__ == "__main__":
    test_gateway_parameters()
