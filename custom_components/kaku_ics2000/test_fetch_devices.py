#!/usr/bin/env python3
"""
Test script to fetch and decrypt your ICS-2000 devices
Shows what devices are actually configured in your system
"""

import json
import base64
import ssl
import urllib.request
import urllib.parse

def main():
    print("=== ICS-2000 Device Fetcher ===\n")
    print("This will fetch and show your actual devices\n")
    
    # Get credentials
    email = input("Enter your email: ").strip()
    password = input("Enter your password: ").strip()
    
    # Create SSL context
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    print("\n1. Authenticating...")
    
    # Step 1: Authenticate
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
                print("❌ No homes found in account")
                return
            
            home = auth_data['homes'][0]
            home_id = home['home_id']
            gateway_mac = home['mac']
            aes_key_hex = home['aes_key']
            
            print(f"✅ Authenticated successfully")
            print(f"   Home ID: {home_id}")
            print(f"   Gateway MAC: {gateway_mac}")
            print(f"   AES Key: {aes_key_hex}")
            
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return
    
    print("\n2. Fetching device data...")
    
    # Step 2: Fetch encrypted device data
    sync_data = {
        'email': email,
        'mac': gateway_mac,
        'action': 'sync',
        'password_hash': password,
        'home_id': home_id,
    }
    
    try:
        data = urllib.parse.urlencode(sync_data).encode('utf-8')
        req = urllib.request.Request(
            "https://trustsmartcloud2.com/ics2000_api/gateway.php",
            data=data,
            method='POST'
        )
        
        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            sync_text = response.read().decode('utf-8')
            sync_data = json.loads(sync_text)
            
            if not sync_data:
                print("❌ No data returned from gateway")
                return
            
            gateway_data = sync_data[0] if isinstance(sync_data, list) else sync_data
            
            print(f"✅ Got encrypted data")
            
            # Get encrypted fields
            encrypted_status = gateway_data.get('status', '')
            encrypted_data = gateway_data.get('data', '')
            
            print(f"\n3. Encrypted data received:")
            print(f"   Status length: {len(encrypted_status)} chars")
            print(f"   Data length: {len(encrypted_data)} chars")
            
    except Exception as e:
        print(f"❌ Device fetch failed: {e}")
        return
    
    print("\n4. To decrypt this data:")
    print("   You need to install: pip install cryptography")
    print("   Then run: python3 decrypt_devices.py")
    print("\n   Or replace your hub.py with hub_fixed.py")
    
    # Save the encrypted data for later decryption
    save_data = {
        'aes_key': aes_key_hex,
        'encrypted_status': encrypted_status,
        'encrypted_data': encrypted_data,
        'home_id': home_id,
        'gateway_mac': gateway_mac,
    }
    
    with open('encrypted_devices.json', 'w') as f:
        json.dump(save_data, f, indent=2)
    
    print(f"\n✅ Saved encrypted data to: encrypted_devices.json")
    print("   You can decrypt this offline with the AES key")

if __name__ == "__main__":
    main()
