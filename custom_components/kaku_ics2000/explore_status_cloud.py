#!/usr/bin/env python3
"""
Explore ways to get device status from KlikAanKlikUit cloud
"""

import json
import base64
import ssl
import urllib.request
import urllib.parse
import time

def try_endpoint(session_data, endpoint, params, description):
    """Try an endpoint with given parameters."""
    print(f"\n{'='*50}")
    print(f"Testing: {description}")
    print(f"Endpoint: {endpoint}")
    print(f"Params: {params}")
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    try:
        data = urllib.parse.urlencode(params).encode('utf-8')
        req = urllib.request.Request(endpoint, data=data, method='POST')
        
        with urllib.request.urlopen(req, context=ctx, timeout=5) as response:
            if response.status == 200:
                text = response.read().decode('utf-8')
                
                # Check if it contains status-like data
                if any(word in text.lower() for word in ['status', 'state', 'on', 'off', 'brightness', 'level']):
                    print(f"✅ FOUND STATUS DATA!")
                    
                    # Try to parse as JSON
                    try:
                        result = json.loads(text)
                        print(f"Response preview: {json.dumps(result, indent=2)[:500]}")
                        return result
                    except:
                        print(f"Response (not JSON): {text[:200]}")
                        return text
                else:
                    print(f"Response doesn't contain status keywords")
                    return None
            else:
                print(f"Status code: {response.status}")
                return None
                
    except Exception as e:
        print(f"Error: {str(e)[:100]}")
        return None

def main():
    print("=== ICS-2000 Device Status Explorer ===\n")
    
    email = input("Enter email: ").strip()
    password = input("Enter password: ").strip()
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    # Authenticate
    print("\nAuthenticating...")
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
            
            home = auth_data['homes'][0]
            home_id = home['home_id']
            gateway_mac = home['mac']
            aes_key_hex = home['aes_key']
            
            print(f"✅ Authenticated (Home: {home_id}, MAC: {gateway_mac})")
            
            session_data = {
                'email': email,
                'password': password,
                'home_id': home_id,
                'mac': gateway_mac,
                'aes_key': aes_key_hex
            }
            
    except Exception as e:
        print(f"❌ Auth failed: {e}")
        return
    
    print("\n" + "="*60)
    print("EXPLORING CLOUD STATUS ENDPOINTS")
    print("="*60)
    
    # Try different actions on gateway.php
    gateway_actions = [
        'status', 'get_status', 'device_status', 'state', 
        'get_state', 'get_devices', 'list_devices', 'refresh'
    ]
    
    for action in gateway_actions:
        params = {
            'email': email,
            'mac': gateway_mac,
            'action': action,
            'password_hash': password,
            'home_id': home_id,
        }
        
        result = try_endpoint(
            session_data,
            "https://trustsmartcloud2.com/ics2000_api/gateway.php",
            params,
            f"gateway.php with action='{action}'"
        )
        
        if result:
            print(f"\n💡 Action '{action}' returned data!")
    
    # Try different PHP endpoints
    endpoints = [
        "status.php", "device_status.php", "get_status.php",
        "state.php", "devices.php", "control.php", "command.php"
    ]
    
    for endpoint in endpoints:
        url = f"https://trustsmartcloud2.com/ics2000_api/{endpoint}"
        
        params = {
            'email': email,
            'mac': gateway_mac,
            'password_hash': password,
            'home_id': home_id,
        }
        
        result = try_endpoint(
            session_data,
            url,
            params,
            f"Endpoint: {endpoint}"
        )
    
    # Try to get status for a specific device
    print("\n" + "="*60)
    print("TRYING TO GET STATUS FOR SPECIFIC DEVICE")
    print("="*60)
    
    # Use Guest Toilet as test (ID: 17147303)
    test_device_id = "17147303"
    
    # Try different parameter combinations
    param_variations = [
        {'device_id': test_device_id},
        {'entity_id': test_device_id},
        {'id': test_device_id},
        {'module_id': test_device_id},
        {'device': test_device_id},
    ]
    
    for extra_params in param_variations:
        params = {
            'email': email,
            'mac': gateway_mac,
            'password_hash': password,
            'home_id': home_id,
            'action': 'status',
            **extra_params
        }
        
        result = try_endpoint(
            session_data,
            "https://trustsmartcloud2.com/ics2000_api/gateway.php",
            params,
            f"Device status with {list(extra_params.keys())[0]}={test_device_id}"
        )
    
    # Try WebSocket-style long polling
    print("\n" + "="*60)
    print("CHECKING FOR REAL-TIME STATUS UPDATES")
    print("="*60)
    
    params = {
        'email': email,
        'mac': gateway_mac,
        'password_hash': password,
        'home_id': home_id,
        'action': 'sync',
        'timestamp': str(int(time.time())),
        'wait': '1',  # Wait for updates
    }
    
    result = try_endpoint(
        session_data,
        "https://trustsmartcloud2.com/ics2000_api/gateway.php",
        params,
        "Sync with timestamp (checking for updates)"
    )
    
    print("\n" + "="*60)
    print("ANALYSIS COMPLETE")
    print("="*60)
    print("\nIf no status endpoints were found, the system might:")
    print("1. Only store configuration, not state")
    print("2. Require local communication for real-time status")
    print("3. Use a different protocol (WebSocket, MQTT, etc.)")
    print("4. Store state in the encrypted 'status' field we already have")

if __name__ == "__main__":
    main()
