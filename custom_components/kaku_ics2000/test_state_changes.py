#!/usr/bin/env python3
"""
Test if cloud data changes when device state changes
"""

import json
import base64
import ssl
import urllib.request
import urllib.parse
import time
import hashlib

def get_module_data(email, password, home_id, gateway_mac, module_id):
    """Get current data for a specific module."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
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
            sync_response = json.loads(sync_text)
            
            # Find the specific module
            for module in sync_response:
                if module.get('id') == str(module_id):
                    return module
            
            return None
            
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def decrypt_field(encrypted_b64, aes_key_hex):
    """Decrypt a field."""
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend
        
        aes_key = bytes.fromhex(aes_key_hex)
        encrypted = base64.b64decode(encrypted_b64)
        
        iv = b'\x00' * 16
        cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted = decryptor.update(encrypted) + decryptor.finalize()
        
        # Find JSON
        for i in range(len(decrypted)):
            if decrypted[i:i+1] in [b'{', b'[']:
                json_bytes = decrypted[i:]
                
                # Remove padding
                if len(json_bytes) > 0:
                    pad_len = json_bytes[-1]
                    if isinstance(pad_len, int) and pad_len < 16:
                        if all(b == pad_len for b in json_bytes[-pad_len:]):
                            json_bytes = json_bytes[:-pad_len]
                
                json_text = json_bytes.decode('utf-8', errors='ignore')
                
                # Find end
                depth = 0
                for j, char in enumerate(json_text):
                    if char == '{':
                        depth += 1
                    elif char == '}':
                        depth -= 1
                        if depth == 0:
                            return json.loads(json_text[:j+1])
        
    except:
        pass
    return None

def main():
    print("=== ICS-2000 State Change Detector ===\n")
    print("This will monitor a device to see if cloud data changes when state changes.\n")
    
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
            
            print(f"✅ Authenticated")
            
    except Exception as e:
        print(f"❌ Auth failed: {e}")
        return
    
    # List available devices
    print("\nFetching devices...")
    sync_data = {
        'email': email,
        'mac': gateway_mac,
        'action': 'sync',
        'password_hash': password,
        'home_id': home_id,
    }
    
    devices = []
    
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
            
            # Get device names
            for module_data in sync_response[:20]:  # First 20 devices
                module_id = module_data.get('id')
                
                # Try to get name
                name = f"Device {module_id}"
                encrypted_data = module_data.get('data')
                if encrypted_data:
                    decrypted = decrypt_field(encrypted_data, aes_key_hex)
                    if decrypted and 'module' in decrypted:
                        name = decrypted['module'].get('name', name)
                
                devices.append((module_id, name))
            
            print(f"\nAvailable devices (first 20):")
            for i, (dev_id, name) in enumerate(devices):
                print(f"  {i+1}. {name} (ID: {dev_id})")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # Select device to monitor
    choice = input("\nSelect device number to monitor: ").strip()
    try:
        idx = int(choice) - 1
        module_id, device_name = devices[idx]
    except:
        print("Invalid selection")
        return
    
    print(f"\n📍 Monitoring: {device_name} (ID: {module_id})")
    print("="*60)
    
    # Get initial state
    print("\n1. Getting initial state...")
    before = get_module_data(email, password, home_id, gateway_mac, module_id)
    
    if not before:
        print("❌ Couldn't get device data")
        return
    
    print("Initial data captured:")
    print(f"  version_status: {before.get('version_status')}")
    print(f"  version_data: {before.get('version_data')}")
    print(f"  status hash: {hashlib.md5(before.get('status', '').encode()).hexdigest()[:8]}")
    print(f"  data hash: {hashlib.md5(before.get('data', '').encode()).hexdigest()[:8]}")
    
    # Decrypt to show current content
    if before.get('status'):
        status_decrypted = decrypt_field(before['status'], aes_key_hex)
        if status_decrypted:
            print(f"  status content: {json.dumps(status_decrypted, separators=(',', ':'))[:100]}")
    
    print("\n" + "="*60)
    print("ACTION REQUIRED:")
    print("="*60)
    print("\n📱 Now please:")
    print("1. Open the KlikAanKlikUit app")
    print("2. Turn the device ON or OFF")
    print("3. Wait a few seconds")
    print("4. Press Enter here to check for changes")
    
    input("\nPress Enter after changing device state...")
    
    # Check for changes
    print("\n2. Checking for changes...")
    
    # Try multiple times with delays
    changes_found = False
    
    for attempt in range(3):
        print(f"\nAttempt {attempt + 1}/3...")
        time.sleep(2)  # Wait 2 seconds between attempts
        
        after = get_module_data(email, password, home_id, gateway_mac, module_id)
        
        if not after:
            print("❌ Couldn't get device data")
            continue
        
        # Compare versions
        version_changed = False
        if before.get('version_status') != after.get('version_status'):
            print(f"✅ version_status changed: {before.get('version_status')} → {after.get('version_status')}")
            version_changed = True
            changes_found = True
        
        if before.get('version_data') != after.get('version_data'):
            print(f"✅ version_data changed: {before.get('version_data')} → {after.get('version_data')}")
            version_changed = True
            changes_found = True
        
        # Compare encrypted data
        if before.get('status') != after.get('status'):
            print(f"✅ 'status' field changed!")
            
            # Decrypt both to see what changed
            before_decrypted = decrypt_field(before['status'], aes_key_hex)
            after_decrypted = decrypt_field(after['status'], aes_key_hex)
            
            if before_decrypted and after_decrypted:
                print(f"  Before: {json.dumps(before_decrypted, separators=(',', ':'))}")
                print(f"  After:  {json.dumps(after_decrypted, separators=(',', ':'))}")
            
            changes_found = True
        
        if before.get('data') != after.get('data'):
            print(f"✅ 'data' field changed!")
            
            # Decrypt both to see what changed
            before_decrypted = decrypt_field(before['data'], aes_key_hex)
            after_decrypted = decrypt_field(after['data'], aes_key_hex)
            
            if before_decrypted and after_decrypted:
                print(f"  Before: {json.dumps(before_decrypted, separators=(',', ':'))[:200]}")
                print(f"  After:  {json.dumps(after_decrypted, separators=(',', ':'))[:200]}")
            
            changes_found = True
        
        if changes_found:
            break
        else:
            print("  No changes detected yet...")
    
    print("\n" + "="*60)
    print("RESULTS:")
    print("="*60)
    
    if changes_found:
        print("\n✅ CHANGES DETECTED!")
        print("The cloud DOES track some state information.")
        print("The version numbers or encrypted fields changed when device state changed.")
    else:
        print("\n❌ NO CHANGES DETECTED")
        print("The cloud does NOT track device state.")
        print("This confirms that KlikAanKlikUit uses stateless operation.")
        print("\nThis is normal for 433MHz devices:")
        print("• Commands are sent one-way")
        print("• No feedback from devices")
        print("• State must be assumed")
    
    print("\n💡 Try running this test with different devices.")
    print("Zigbee devices might show state changes, while 433MHz won't.")

if __name__ == "__main__":
    main()
