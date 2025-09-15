#!/usr/bin/env python3
"""
Check if the 'status' field in gateway.php response contains device state
"""

import json
import base64
import ssl
import urllib.request
import urllib.parse

def decrypt_field(encrypted_b64: str, aes_key_hex: str, field_name: str):
    """Decrypt a field and show what's in it."""
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend
        
        aes_key = bytes.fromhex(aes_key_hex)
        encrypted = base64.b64decode(encrypted_b64)
        
        print(f"\n  {field_name} field:")
        print(f"    Encrypted length: {len(encrypted)} bytes")
        
        iv = b'\x00' * 16
        cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted = decryptor.update(encrypted) + decryptor.finalize()
        
        # Find JSON start
        json_start = -1
        for i in range(len(decrypted)):
            if decrypted[i:i+1] in [b'{', b'[']:
                json_start = i
                break
        
        if json_start >= 0:
            json_bytes = decrypted[json_start:]
            
            # Remove padding
            if len(json_bytes) > 0:
                pad_len = json_bytes[-1]
                if isinstance(pad_len, int) and pad_len < 16:
                    if all(b == pad_len for b in json_bytes[-pad_len:]):
                        json_bytes = json_bytes[:-pad_len]
            
            json_text = json_bytes.decode('utf-8', errors='ignore')
            
            # Find JSON end
            depth = 0
            for i, char in enumerate(json_text):
                if char == '{':
                    depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 0:
                        json_text = json_text[:i+1]
                        break
            
            data = json.loads(json_text)
            print(f"    ✅ Decrypted successfully!")
            print(f"    Content: {json.dumps(data, indent=6)}")
            
            # Check for status-related fields
            status_fields = ['status', 'state', 'on', 'off', 'value', 'level', 'brightness', 'position']
            found_status = []
            
            def check_dict(d, path=""):
                for key, value in d.items():
                    current_path = f"{path}.{key}" if path else key
                    if any(sf in key.lower() for sf in status_fields):
                        found_status.append(f"{current_path} = {value}")
                    if isinstance(value, dict):
                        check_dict(value, current_path)
            
            if isinstance(data, dict):
                check_dict(data)
            
            if found_status:
                print(f"    🔍 Possible status fields found:")
                for sf in found_status:
                    print(f"       - {sf}")
            
            return data
            
    except Exception as e:
        print(f"    ❌ Decryption failed: {str(e)[:100]}")
        return None

def main():
    print("=== ICS-2000 Status Field Analysis ===\n")
    print("Checking if the 'status' field contains device state information...\n")
    
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
    
    # Fetch modules
    print("\nFetching modules...")
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
            
            if isinstance(sync_response, list):
                print(f"✅ Got {len(sync_response)} modules\n")
                
                # Analyze a few modules
                modules_to_check = min(5, len(sync_response))
                
                print(f"Analyzing first {modules_to_check} modules...")
                print("="*60)
                
                status_has_state = False
                data_has_state = False
                
                for i in range(modules_to_check):
                    module_data = sync_response[i]
                    module_id = module_data.get('id')
                    
                    print(f"\nModule {i+1} (ID: {module_id}):")
                    print(f"  Version status: {module_data.get('version_status')}")
                    print(f"  Version data: {module_data.get('version_data')}")
                    print(f"  Time added: {module_data.get('time_added')}")
                    
                    # Decrypt status field
                    if 'status' in module_data and module_data['status']:
                        status_result = decrypt_field(module_data['status'], aes_key_hex, "STATUS")
                        if status_result:
                            # Check what's in status
                            if 'module' in status_result:
                                module = status_result['module']
                                if any(key in module for key in ['state', 'status', 'on', 'value']):
                                    status_has_state = True
                    
                    # Decrypt data field for comparison
                    if 'data' in module_data and module_data['data']:
                        data_result = decrypt_field(module_data['data'], aes_key_hex, "DATA")
                        if data_result:
                            # Check what's in data
                            if 'module' in data_result:
                                module = data_result['module']
                                if any(key in module for key in ['state', 'status', 'on', 'value']):
                                    data_has_state = True
                
                print("\n" + "="*60)
                print("ANALYSIS RESULTS")
                print("="*60)
                
                print("\n📊 Summary:")
                
                if status_has_state:
                    print("✅ The 'status' field DOES contain device state information!")
                else:
                    print("❌ The 'status' field does NOT contain device state")
                    print("   It appears to contain configuration/capability data")
                
                if data_has_state:
                    print("✅ The 'data' field contains state information")
                else:
                    print("❌ The 'data' field does NOT contain device state")
                    print("   It contains device configuration (name, type, etc.)")
                
                print("\n💡 Conclusions:")
                
                if not status_has_state and not data_has_state:
                    print("• Device state is NOT included in the gateway.php response")
                    print("• The system likely uses one of these methods:")
                    print("  1. Local polling - devices must be queried directly")
                    print("  2. Event-based - state changes are pushed via WebSocket/MQTT")
                    print("  3. Stateless - the ICS-2000 doesn't track state, only sends commands")
                    print("  4. Different endpoint - another API call gets current state")
                elif status_has_state:
                    print("• Device state IS available in the 'status' field!")
                    print("• The hub should decrypt and use the 'status' field for current state")
                
                # Try to send a command and see if state changes
                print("\n" + "="*60)
                print("TESTING STATE CHANGES")
                print("="*60)
                
                print("\nWould you like to test if state changes after sending a command?")
                print("This will turn a device on/off to see if the cloud state updates.")
                test = input("Test state change? (y/n): ").strip().lower()
                
                if test == 'y':
                    device_id = input("Enter device/module ID to test: ").strip()
                    
                    # We would need to implement the command sending here
                    # For now, just suggest manual testing
                    print("\nTo test state changes:")
                    print("1. Turn the device on/off using the official app")
                    print("2. Run this script again to see if the 'status' field changed")
                    print("3. If it changes, we know the cloud tracks state")
                    print("4. If not, state is only tracked locally or not at all")
                
            else:
                print("❌ Unexpected response format")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
