#!/usr/bin/env python3
"""
Diagnostic script to test KlikAanKlikUit device name extraction
Run this to verify that device names can be properly extracted from your account
"""

import json
import base64
import urllib.request
import urllib.parse
import ssl
import hashlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

def decrypt_kaku_data(encrypted_b64, aes_key_hex):
    """Decrypt KlikAanKlikUit data."""
    try:
        aes_key = bytes.fromhex(aes_key_hex)
        encrypted = base64.b64decode(encrypted_b64)
        
        # Use CBC mode with zero IV
        iv = b'\x00' * 16
        cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted = decryptor.update(encrypted) + decryptor.finalize()
        
        # Find JSON start
        for i in range(len(decrypted)):
            if decrypted[i:i+1] in [b'{', b'[']:
                json_bytes = decrypted[i:]
                
                # Remove padding if present
                if len(json_bytes) > 0:
                    pad_len = json_bytes[-1]
                    if isinstance(pad_len, int) and 0 < pad_len <= 16:
                        if all(b == pad_len for b in json_bytes[-pad_len:]):
                            json_bytes = json_bytes[:-pad_len]
                
                # Decode and extract valid JSON
                json_str = json_bytes.decode('utf-8', errors='ignore')
                
                # Find end of JSON
                depth = 0
                end_pos = 0
                for j, char in enumerate(json_str):
                    if char in '{[':
                        depth += 1
                    elif char in '}]':
                        depth -= 1
                        if depth == 0:
                            end_pos = j + 1
                            break
                
                if end_pos > 0:
                    json_str = json_str[:end_pos]
                    return json.loads(json_str)
                break
    except Exception as e:
        print(f"Decryption error: {e}")
    return None

def extract_device_name(module_data, aes_key_hex):
    """Extract device name from module data."""
    # Try the 'data' field first (this usually contains the name)
    if 'data' in module_data and module_data['data']:
        decrypted = decrypt_kaku_data(module_data['data'], aes_key_hex)
        
        if decrypted and 'module' in decrypted:
            module = decrypted['module']
            
            # Try module name
            if 'name' in module and module['name']:
                return module['name']
            
            # Try entities
            if 'entities' in module and module['entities']:
                for entity in module['entities']:
                    if 'name' in entity and entity['name']:
                        return entity['name']
            
            # Try device field
            if 'device' in module and module['device']:
                return module['device']
    
    # Fallback to status field
    if 'status' in module_data and module_data['status']:
        decrypted = decrypt_kaku_data(module_data['status'], aes_key_hex)
        
        if decrypted and 'module' in decrypted:
            module = decrypted['module']
            if 'name' in module and module['name']:
                return module['name']
            if 'device' in module and module['device']:
                return module['device']
    
    return None

def main():
    print("=" * 60)
    print("KlikAanKlikUit Device Name Extraction Test")
    print("=" * 60)
    print()
    
    # Get credentials
    print("Please enter your KlikAanKlikUit credentials:")
    email = input("Email: ").strip()
    password = input("Password: ").strip()
    gateway_mac = input("Gateway MAC (format: XX:XX:XX:XX:XX:XX): ").strip()
    
    # Format MAC
    gateway_mac = gateway_mac.upper().replace(":", "")
    
    print("\n🔐 Authenticating...")
    
    # Step 1: Authenticate
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    auth_data = {
        'email': email,
        'mac': gateway_mac,
        'password_hash': hashlib.md5(password.encode()).hexdigest(),
        'action': 'check',
    }
    
    try:
        data = urllib.parse.urlencode(auth_data).encode('utf-8')
        req = urllib.request.Request(
            "https://ics2000.trustsmartcloud.com/gateway.php",
            data=data,
            method='POST'
        )
        
        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            auth_result = json.loads(response.read().decode('utf-8'))
            
            if auth_result.get('status') != 'ok':
                print(f"❌ Authentication failed: {auth_result}")
                return
            
            home_id = auth_result.get('home_id', '')
            aes_key_hex = auth_result.get('aes_key', '')
            
            print(f"✅ Authenticated! Home ID: {home_id}")
            print(f"   AES Key: {aes_key_hex[:8]}...")
    
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return
    
    print("\n📡 Fetching devices...")
    
    # Step 2: Get devices
    sync_data = {
        'email': email,
        'mac': gateway_mac,
        'action': 'sync',
        'password_hash': hashlib.md5(password.encode()).hexdigest(),
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
            sync_response = json.loads(response.read().decode('utf-8'))
            
            if isinstance(sync_response, list):
                print(f"✅ Found {len(sync_response)} devices/modules\n")
                
                print("=" * 60)
                print("DEVICE NAME EXTRACTION RESULTS:")
                print("=" * 60)
                print()
                
                success_count = 0
                failed_count = 0
                
                for idx, module_data in enumerate(sync_response):
                    module_id = module_data.get('id', 'unknown')
                    
                    # Try to extract the device name
                    device_name = extract_device_name(module_data, aes_key_hex)
                    
                    if device_name and device_name != f"Device {module_id}":
                        print(f"✅ Module {module_id}: '{device_name}'")
                        success_count += 1
                    else:
                        print(f"❌ Module {module_id}: No name found (will show as 'Device {module_id}')")
                        failed_count += 1
                        
                        # Show what data is available for debugging
                        if 'data' in module_data:
                            print(f"   - Has 'data' field: {len(module_data['data'])} chars")
                        if 'status' in module_data:
                            print(f"   - Has 'status' field: {len(module_data['status'])} chars")
                
                print()
                print("=" * 60)
                print("SUMMARY:")
                print("=" * 60)
                print(f"✅ Successfully extracted names: {success_count}/{len(sync_response)}")
                print(f"❌ Failed to extract names: {failed_count}/{len(sync_response)}")
                print()
                
                if success_count == 0:
                    print("⚠️  WARNING: No device names could be extracted!")
                    print("   This might indicate:")
                    print("   1. Devices haven't been named in the KlikAanKlikUit app")
                    print("   2. The encryption format has changed")
                    print("   3. An issue with your credentials or gateway")
                elif failed_count > 0:
                    print("💡 TIP: Some devices don't have names set.")
                    print("   You can set device names in the KlikAanKlikUit app.")
                else:
                    print("🎉 All device names extracted successfully!")
                    print("   The fix should work perfectly for your setup!")
                
    except Exception as e:
        print(f"❌ Error fetching devices: {e}")

if __name__ == "__main__":
    main()
