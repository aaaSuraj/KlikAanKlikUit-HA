#!/usr/bin/env python3
"""
Working decryptor for KlikAanKlikUit ICS-2000
The data uses AES CBC with zero IV, but the JSON starts after the first block
"""

import json
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

def decrypt_kaku_data(encrypted_b64: str, aes_key_hex: str):
    """Decrypt KlikAanKlikUit data."""
    
    # Convert inputs
    aes_key = bytes.fromhex(aes_key_hex)
    encrypted = base64.b64decode(encrypted_b64)
    
    # Decrypt using AES CBC with zero IV
    iv = b'\x00' * 16
    cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    decrypted = decryptor.update(encrypted) + decryptor.finalize()
    
    # Find where JSON starts (usually after first block at position 16)
    json_start = -1
    for i in range(len(decrypted)):
        if decrypted[i:i+1] in [b'{', b'[']:
            json_start = i
            break
    
    if json_start < 0:
        print("No JSON found in decrypted data")
        return None
    
    # Extract JSON part
    json_bytes = decrypted[json_start:]
    
    # Remove padding if present
    if len(json_bytes) > 0:
        # Check last byte for PKCS7 padding
        pad_len = json_bytes[-1]
        if pad_len < 16:
            # Verify it's valid padding
            if all(b == pad_len for b in json_bytes[-pad_len:]):
                json_bytes = json_bytes[:-pad_len]
    
    # Decode and parse
    json_text = json_bytes.decode('utf-8', errors='ignore')
    
    # Find the end of JSON (remove any trailing garbage)
    depth = 0
    json_end = 0
    for i, char in enumerate(json_text):
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                json_end = i + 1
                break
    
    if json_end > 0:
        json_text = json_text[:json_end]
    
    return json.loads(json_text)

def main():
    print("=== KlikAanKlikUit Device Decryptor ===\n")
    
    # Your data
    aes_key_hex = "f27089bd7728f1899d8aabeacacf8d13"
    
    encrypted_status = "rO1UhRri1NsdqgRGLOMd6Xnt08JKaGyalJHfxivRlHIgBb+BBvico1g+61eBj8KT72Yt/bpUR0NC6j4Or9VyTA=="
    encrypted_data = "5OO/DACQWmrMdUtvSe7E8W7wFwzmoyNbdbevK/YWvTHAxSNf/Jdp1/1qjapiAVDagBZ1XyXXwaL/iwUUjllzB3oStLeKxsBW8mrmW04ynXDBdmz0+p4gsiLNarxbW79Al9IEobQPkW7g7+00Uu39SnuLXNH9AWzwwQbMKSv/OuM8Mf7KzH4PL9pGrpn0v5iSBfir4fkA4RfSZJAvDuM9IVkTpFVHXZcK7cmXW7pT7HuSAMkiXrNyIBktK5Kj+dhM/mcETjOlhp3nxh0B+9/t6ygRhPtBcchmnR5dvT+nso0="
    
    print("Decrypting Status...")
    status = decrypt_kaku_data(encrypted_status, aes_key_hex)
    if status:
        print("✅ Status decrypted successfully!")
        print(json.dumps(status, indent=2))
    
    print("\n" + "="*50 + "\n")
    
    print("Decrypting Data...")
    data = decrypt_kaku_data(encrypted_data, aes_key_hex)
    if data:
        print("✅ Data decrypted successfully!")
        print(json.dumps(data, indent=2))
        
        # Extract module info
        if 'module' in data:
            module = data['module']
            print(f"\n📦 Module Info:")
            print(f"  ID: {module.get('id')}")
            print(f"  Name: {module.get('name')}")
            print(f"  Version: {module.get('version')}")
            
            # Check for entities
            if 'entities' in module:
                entities = module['entities']
                print(f"\n✅ Found {len(entities)} entities:")
                
                for entity in entities:
                    entity_id = entity.get('entityId')
                    name = entity.get('name', 'Unknown')
                    device_type = entity.get('deviceType')
                    status = entity.get('status', False)
                    
                    type_names = {
                        1: "Switch",
                        2: "Dimmer",
                        3: "Light",
                        4: "Cover",
                        5: "Sensor"
                    }
                    type_name = type_names.get(device_type, f"Type {device_type}")
                    
                    print(f"\n  Entity {entity_id}:")
                    print(f"    Name: {name}")
                    print(f"    Type: {type_name}")
                    print(f"    Status: {'ON' if status else 'OFF'}")
                    
                    if 'dimLevel' in entity:
                        print(f"    Dim Level: {entity['dimLevel']}%")
                    if 'isGroup' in entity:
                        print(f"    Is Group: {entity['isGroup']}")
            
            # Check for scenes
            if 'scenes' in module:
                scenes = module['scenes']
                print(f"\n✅ Found {len(scenes)} scenes:")
                
                for scene in scenes:
                    scene_id = scene.get('entityId')
                    name = scene.get('name', 'Unknown')
                    print(f"  Scene {scene_id}: {name}")
        
        # Save decrypted data
        with open('decrypted_devices.json', 'w') as f:
            json.dump(data, f, indent=2)
        print("\n💾 Saved full decrypted data to: decrypted_devices.json")

if __name__ == "__main__":
    main()
