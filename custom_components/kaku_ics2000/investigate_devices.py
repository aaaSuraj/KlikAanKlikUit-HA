#!/usr/bin/env python3
"""
Check what's actually configured in your ICS-2000 system
"""

import json
import base64
import ssl
import urllib.request
import urllib.parse

def main():
    print("=== ICS-2000 Device Investigation ===\n")
    print("This will help us find where your devices are hiding!\n")
    
    email = input("Enter email: ").strip()
    password = input("Enter password: ").strip()
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    # Authenticate
    print("\n1. Checking your account...")
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
            
            print(f"✅ Logged in as: {auth_data.get('person_name', 'Unknown')}")
            
            homes = auth_data.get('homes', [])
            print(f"\n📊 Account Overview:")
            print(f"  Homes: {len(homes)}")
            
            if 'cameras' in auth_data:
                print(f"  Cameras: {len(auth_data['cameras'])}")
            
            # For each home
            for home in homes:
                home_id = home['home_id']
                home_name = home.get('home_name', 'Unknown')
                gateway_mac = home['mac']
                aes_key_hex = home['aes_key']
                
                print(f"\n🏠 Home: {home_name}")
                print(f"  ID: {home_id}")
                print(f"  Gateway MAC: {gateway_mac}")
                
                # Try different MAC formats in sync
                mac_formats = [
                    gateway_mac,  # As returned
                    gateway_mac.upper().replace(":", ""),  # No colons
                    "",  # Empty
                ]
                
                for mac_test in mac_formats:
                    print(f"\n  Testing with MAC format: '{mac_test}'")
                    
                    sync_data = {
                        'email': email,
                        'mac': mac_test,
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
                            sync_response = json.loads(sync_text)
                            
                            if isinstance(sync_response, list):
                                print(f"    → Got {len(sync_response)} module(s)")
                                
                                # If we get more than 1, this is the right format!
                                if len(sync_response) > 1:
                                    print(f"    ✅ FOUND {len(sync_response)} MODULES with this MAC format!")
                                    
                                    # Decrypt each module
                                    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
                                    from cryptography.hazmat.backends import default_backend
                                    
                                    aes_key = bytes.fromhex(aes_key_hex)
                                    
                                    for idx, module_data in enumerate(sync_response):
                                        module_id = module_data.get('id')
                                        print(f"\n    Module {idx + 1} (ID: {module_id}):")
                                        
                                        encrypted_data = module_data.get('data')
                                        if encrypted_data:
                                            try:
                                                encrypted = base64.b64decode(encrypted_data)
                                                
                                                iv = b'\x00' * 16
                                                cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
                                                decryptor = cipher.decryptor()
                                                decrypted = decryptor.update(encrypted) + decryptor.finalize()
                                                
                                                # Find JSON
                                                for i in range(len(decrypted)):
                                                    if decrypted[i:i+1] == b'{':
                                                        json_text = decrypted[i:].decode('utf-8', errors='ignore')
                                                        # Find end
                                                        depth = 0
                                                        for j, char in enumerate(json_text):
                                                            if char == '{':
                                                                depth += 1
                                                            elif char == '}':
                                                                depth -= 1
                                                                if depth == 0:
                                                                    json_text = json_text[:j+1]
                                                                    break
                                                        
                                                        data = json.loads(json_text)
                                                        if 'module' in data:
                                                            module = data['module']
                                                            print(f"      Name: {module.get('name', 'Unknown')}")
                                                            print(f"      Type/Device: {module.get('device', 'Unknown')}")
                                                        break
                                            except:
                                                print(f"      (Couldn't decrypt)")
                                    
                                    # Save all raw modules
                                    with open('all_raw_modules.json', 'w') as f:
                                        json.dump(sync_response, f, indent=2)
                                    print(f"\n    💾 Saved all raw modules to: all_raw_modules.json")
                                    
                                    return  # Found them!
                                    
                    except Exception as e:
                        print(f"    Error: {e}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    print("\n\n❓ Questions to help debug:")
    print("1. How many devices do you have paired in the KlikAanKlikUit app?")
    print("2. Are they all in the 'Guest Toilet' room/module?")
    print("3. Or are they in different rooms/modules?")
    print("4. Can you see all devices in the official app?")

if __name__ == "__main__":
    main()
