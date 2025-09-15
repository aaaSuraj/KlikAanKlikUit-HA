#!/usr/bin/env python3
"""
Find the correct IV for AES CBC decryption of KlikAanKlikUit data
"""

import json
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
import hashlib

def try_decrypt_with_iv(encrypted_data: bytes, key: bytes, iv: bytes):
    """Try to decrypt with specific IV."""
    try:
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted = decryptor.update(encrypted_data) + decryptor.finalize()
        
        # Try to unpad
        try:
            unpadder = padding.PKCS7(128).unpadder()
            unpadded = unpadder.update(decrypted) + unpadder.finalize()
            return unpadded
        except:
            # Manual unpad
            if len(decrypted) > 0:
                pad_len = decrypted[-1]
                if pad_len < 16:
                    return decrypted[:-pad_len]
            return decrypted
    except:
        return None

def find_json_start(data: bytes):
    """Find where JSON actually starts in the data."""
    for i in range(len(data)):
        if data[i:i+1] in [b'{', b'[']:
            return i
    return -1

def main():
    print("=== Finding Correct IV for Decryption ===\n")
    
    # Your data
    aes_key_hex = "f27089bd7728f1899d8aabeacacf8d13"
    aes_key = bytes.fromhex(aes_key_hex)
    
    encrypted_status_b64 = "rO1UhRri1NsdqgRGLOMd6Xnt08JKaGyalJHfxivRlHIgBb+BBvico1g+61eBj8KT72Yt/bpUR0NC6j4Or9VyTA=="
    encrypted_data_b64 = "5OO/DACQWmrMdUtvSe7E8W7wFwzmoyNbdbevK/YWvTHAxSNf/Jdp1/1qjapiAVDagBZ1XyXXwaL/iwUUjllzB3oStLeKxsBW8mrmW04ynXDBdmz0+p4gsiLNarxbW79Al9IEobQPkW7g7+00Uu39SnuLXNH9AWzwwQbMKSv/OuM8Mf7KzH4PL9pGrpn0v5iSBfir4fkA4RfSZJAvDuM9IVkTpFVHXZcK7cmXW7pT7HuSAMkiXrNyIBktK5Kj+dhM/mcETjOlhp3nxh0B+9/t6ygRhPtBcchmnR5dvT+nso0="
    
    encrypted_status = base64.b64decode(encrypted_status_b64)
    encrypted_data = base64.b64decode(encrypted_data_b64)
    
    # Common IV patterns
    mac = "0012A30263F5"
    mac_bytes = bytes.fromhex(mac)
    
    test_ivs = [
        (b'\x00' * 16, "Zero IV"),
        (mac_bytes + b'\x00' * 10, "MAC padded with zeros"),
        (b'\x00' * 10 + mac_bytes, "MAC at end"),
        (mac_bytes * 3)[:16], "MAC repeated"),
        (hashlib.md5(mac_bytes).digest(), "MD5 of MAC"),
        (hashlib.md5(mac.encode()).digest(), "MD5 of MAC string"),
        (aes_key, "Same as key"),
        (bytes.fromhex(aes_key_hex[:32]), "First 16 bytes of key"),
        (encrypted_status[:16], "First block of ciphertext (CTR mode)"),
    ]
    
    # Try to find correct IV by looking for clean JSON
    print("Testing Status field decryption:\n")
    
    for iv, description in test_ivs:
        result = try_decrypt_with_iv(encrypted_status, aes_key, iv)
        if result:
            try:
                text = result.decode('utf-8', errors='ignore')
                json_start = find_json_start(result)
                
                if json_start >= 0:
                    json_text = result[json_start:].decode('utf-8', errors='ignore')
                    try:
                        parsed = json.loads(json_text)
                        print(f"✅ FOUND with {description}!")
                        print(f"   IV (hex): {iv.hex()}")
                        print(f"   JSON starts at byte {json_start}")
                        print(f"   Decoded: {json.dumps(parsed, indent=2)}")
                        
                        # Use this IV for data field
                        print("\n\nDecrypting Data field with same IV:")
                        data_result = try_decrypt_with_iv(encrypted_data, aes_key, iv)
                        if data_result:
                            data_json_start = find_json_start(data_result)
                            if data_json_start >= 0:
                                data_json_text = data_result[data_json_start:].decode('utf-8', errors='ignore')
                                data_parsed = json.loads(data_json_text)
                                print(json.dumps(data_parsed, indent=2))
                                
                                # Show entities
                                if 'entities' in data_parsed:
                                    print(f"\n✅ Found {len(data_parsed['entities'])} entities!")
                                    for entity in data_parsed['entities']:
                                        entity_id = entity.get('entityId', 'unknown')
                                        name = entity.get('name', 'Unknown')
                                        device_type = entity.get('deviceType', 'unknown')
                                        print(f"  - ID: {entity_id}, Name: {name}, Type: {device_type}")
                                
                                if 'scenes' in data_parsed:
                                    print(f"\n✅ Found {len(data_parsed['scenes'])} scenes!")
                                    for scene in data_parsed['scenes']:
                                        scene_id = scene.get('entityId', 'unknown')
                                        name = scene.get('name', 'Unknown')
                                        print(f"  - ID: {scene_id}, Name: {name}")
                        
                        return
                        
                    except json.JSONDecodeError:
                        if '{' in json_text[:50]:
                            print(f"Partial match with {description}: {json_text[:100]}")
            except:
                pass
    
    # If standard IVs don't work, try to figure it out from the pattern
    print("\n\nAnalyzing decryption pattern...")
    
    # Decrypt with zero IV to see the pattern
    zero_iv_result = try_decrypt_with_iv(encrypted_status, aes_key, b'\x00' * 16)
    if zero_iv_result:
        print("Decrypted with zero IV (hex):", zero_iv_result[:16].hex())
        print("Decrypted with zero IV (text):", zero_iv_result.decode('utf-8', errors='ignore')[:50])
        
        # The first block is XORed with the IV in CBC mode
        # So: plaintext_block_1 = decrypt(ciphertext_block_1) XOR IV
        # If we know what plaintext should be, we can find IV
        
        # The plaintext should probably start with '{"module"' or similar
        expected_start = b'{"module":{"id":'
        
        # Calculate what IV would give us this start
        first_block_decrypted = zero_iv_result[:16]
        calculated_iv = bytes(a ^ b for a, b in zip(first_block_decrypted, expected_start))
        
        print(f"\nCalculated IV based on expected JSON start: {calculated_iv.hex()}")
        
        # Try with calculated IV
        result = try_decrypt_with_iv(encrypted_status, aes_key, calculated_iv)
        if result:
            try:
                text = result.decode('utf-8', errors='ignore')
                print(f"Result with calculated IV: {text}")
                parsed = json.loads(text)
                print("✅ Successfully decrypted with calculated IV!")
                print(json.dumps(parsed, indent=2))
            except:
                print("Calculated IV didn't work perfectly")

if __name__ == "__main__":
    main()
