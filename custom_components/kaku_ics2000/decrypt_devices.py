#!/usr/bin/env python3
"""
Decrypt KlikAanKlikUit ICS-2000 device data from gateway.php
"""

import json
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding

def decrypt_aes_ecb(encrypted_data: bytes, key: bytes) -> str:
    """Decrypt AES ECB encrypted data."""
    try:
        # Create cipher
        cipher = Cipher(
            algorithms.AES(key),
            modes.ECB(),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        # Decrypt
        decrypted = decryptor.update(encrypted_data) + decryptor.finalize()
        
        # Remove PKCS7 padding
        unpadder = padding.PKCS7(128).unpadder()
        unpadded = unpadder.update(decrypted) + unpadder.finalize()
        
        # Decode to string
        return unpadded.decode('utf-8')
    except Exception as e:
        print(f"Decryption error: {e}")
        return None

def main():
    print("=== ICS-2000 Device Data Decryptor ===\n")
    
    # Your AES key from authentication
    aes_key_hex = "f27089bd7728f1899d8aabeacacf8d13"
    aes_key = bytes.fromhex(aes_key_hex)
    print(f"Using AES key: {aes_key_hex}\n")
    
    # The encrypted data from gateway.php
    encrypted_status_b64 = "rO1UhRri1NsdqgRGLOMd6Xnt08JKaGyalJHfxivRlHIgBb+BBvico1g+61eBj8KT72Yt/bpUR0NC6j4Or9VyTA=="
    encrypted_data_b64 = "5OO/DACQWmrMdUtvSe7E8W7wFwzmoyNbdbevK/YWvTHAxSNf/Jdp1/1qjapiAVDagBZ1XyXXwaL/iwUUjllzB3oStLeKxsBW8mrmW04ynXDBdmz0+p4gsiLNarxbW79Al9IEobQPkW7g7+00Uu39SnuLXNH9AWzwwQbMKSv/OuM8Mf7KzH4PL9pGrpn0v5iSBfir4fkA4RfSZJAvDuM9IVkTpFVHXZcK7cmXW7pT7HuSAMkiXrNyIBktK5Kj+dhM/mcETjOlhp3nxh0B+9/t6ygRhPtBcchmnR5dvT+nso0="
    
    # Decode from base64
    encrypted_status = base64.b64decode(encrypted_status_b64)
    encrypted_data = base64.b64decode(encrypted_data_b64)
    
    print("Decrypting status field...")
    status_json = decrypt_aes_ecb(encrypted_status, aes_key)
    if status_json:
        print("Status decrypted successfully!")
        try:
            status = json.loads(status_json)
            print(json.dumps(status, indent=2))
        except:
            print(f"Raw status: {status_json}")
    
    print("\n" + "="*50 + "\n")
    
    print("Decrypting data field...")
    data_json = decrypt_aes_ecb(encrypted_data, aes_key)
    if data_json:
        print("Data decrypted successfully!")
        try:
            data = json.loads(data_json)
            print(json.dumps(data, indent=2))
            
            # Parse devices
            if 'entities' in data:
                print(f"\n✅ Found {len(data['entities'])} entities:")
                for entity in data['entities']:
                    entity_id = entity.get('entityId', 'unknown')
                    name = entity.get('name', 'Unknown')
                    device_type = entity.get('deviceType', 'unknown')
                    print(f"  - ID: {entity_id}, Name: {name}, Type: {device_type}")
            
            if 'scenes' in data:
                print(f"\n✅ Found {len(data['scenes'])} scenes:")
                for scene in data['scenes']:
                    scene_id = scene.get('entityId', 'unknown')
                    name = scene.get('name', 'Unknown')
                    print(f"  - ID: {scene_id}, Name: {name}")
                    
        except Exception as e:
            print(f"Parse error: {e}")
            print(f"Raw data: {data_json[:500]}")

if __name__ == "__main__":
    main()
