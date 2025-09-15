#!/usr/bin/env python3
"""
Robust decryptor for KlikAanKlikUit ICS-2000 device data
Handles different padding methods and encryption modes
"""

import json
import base64
import hashlib

def try_decrypt_methods(encrypted_data: bytes, key: bytes):
    """Try different decryption methods."""
    results = []
    
    # Try cryptography library if available
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import padding
        
        # Method 1: AES ECB with PKCS7 padding
        try:
            cipher = Cipher(algorithms.AES(key), modes.ECB(), backend=default_backend())
            decryptor = cipher.decryptor()
            decrypted = decryptor.update(encrypted_data) + decryptor.finalize()
            
            # Try to remove PKCS7 padding
            try:
                unpadder = padding.PKCS7(128).unpadder()
                unpadded = unpadder.update(decrypted) + unpadder.finalize()
                results.append(("AES ECB + PKCS7", unpadded))
            except:
                pass
            
            # Try without padding removal
            results.append(("AES ECB raw", decrypted))
            
            # Try manual padding removal
            if len(decrypted) > 0:
                pad_len = decrypted[-1]
                if pad_len < 16:
                    try:
                        unpadded = decrypted[:-pad_len]
                        results.append(("AES ECB + manual unpad", unpadded))
                    except:
                        pass
        except Exception as e:
            print(f"Cryptography ECB error: {e}")
        
        # Method 2: AES CBC with zero IV
        try:
            iv = b'\x00' * 16
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            decrypted = decryptor.update(encrypted_data) + decryptor.finalize()
            
            # Try different padding removals
            try:
                unpadder = padding.PKCS7(128).unpadder()
                unpadded = unpadder.update(decrypted) + unpadder.finalize()
                results.append(("AES CBC + PKCS7", unpadded))
            except:
                results.append(("AES CBC raw", decrypted))
        except:
            pass
            
    except ImportError:
        print("cryptography library not available, trying pycrypto/pycryptodome")
    
    # Try with pycrypto/pycryptodome if available
    try:
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import unpad
        
        # ECB mode
        try:
            cipher = AES.new(key, AES.MODE_ECB)
            decrypted = cipher.decrypt(encrypted_data)
            
            # Try different unpadding
            try:
                unpadded = unpad(decrypted, AES.block_size)
                results.append(("PyCrypto ECB + unpad", unpadded))
            except:
                results.append(("PyCrypto ECB raw", decrypted))
        except Exception as e:
            print(f"PyCrypto ECB error: {e}")
        
        # CBC mode with zero IV
        try:
            iv = b'\x00' * 16
            cipher = AES.new(key, AES.MODE_CBC, iv)
            decrypted = cipher.decrypt(encrypted_data)
            try:
                unpadded = unpad(decrypted, AES.block_size)
                results.append(("PyCrypto CBC + unpad", unpadded))
            except:
                results.append(("PyCrypto CBC raw", decrypted))
        except:
            pass
    except ImportError:
        pass
    
    return results

def load_encrypted_data():
    """Load encrypted data from file or use hardcoded values."""
    try:
        with open('encrypted_devices.json', 'r') as f:
            data = json.load(f)
            return data
    except:
        # Use your hardcoded values
        return {
            'aes_key': 'f27089bd7728f1899d8aabeacacf8d13',
            'encrypted_status': 'rO1UhRri1NsdqgRGLOMd6Xnt08JKaGyalJHfxivRlHIgBb+BBvico1g+61eBj8KT72Yt/bpUR0NC6j4Or9VyTA==',
            'encrypted_data': '5OO/DACQWmrMdUtvSe7E8W7wFwzmoyNbdbevK/YWvTHAxSNf/Jdp1/1qjapiAVDagBZ1XyXXwaL/iwUUjllzB3oStLeKxsBW8mrmW04ynXDBdmz0+p4gsiLNarxbW79Al9IEobQPkW7g7+00Uu39SnuLXNH9AWzwwQbMKSv/OuM8Mf7KzH4PL9pGrpn0v5iSBfir4fkA4RfSZJAvDuM9IVkTpFVHXZcK7cmXW7pT7HuSAMkiXrNyIBktK5Kj+dhM/mcETjOlhp3nxh0B+9/t6ygRhPtBcchmnR5dvT+nso0='
        }

def analyze_encrypted_data(encrypted_b64: str):
    """Analyze encrypted data structure."""
    encrypted = base64.b64decode(encrypted_b64)
    print(f"  Base64 length: {len(encrypted_b64)}")
    print(f"  Binary length: {len(encrypted)} bytes")
    print(f"  Blocks (16-byte): {len(encrypted) / 16}")
    print(f"  First 16 bytes (hex): {encrypted[:16].hex()}")
    print(f"  Last 16 bytes (hex): {encrypted[-16:].hex()}")
    
    # Check if it's multiple of 16 (AES block size)
    if len(encrypted) % 16 == 0:
        print("  ✓ Length is multiple of 16 (good for AES)")
    else:
        print(f"  ⚠ Length is not multiple of 16 (padding issue?)")
    
    return encrypted

def main():
    print("=== ICS-2000 Robust Device Data Decryptor ===\n")
    
    # Load data
    data = load_encrypted_data()
    aes_key_hex = data['aes_key']
    encrypted_status_b64 = data['encrypted_status']
    encrypted_data_b64 = data['encrypted_data']
    
    print(f"AES Key: {aes_key_hex}")
    aes_key = bytes.fromhex(aes_key_hex)
    
    # Also try MD5 of key as the actual key (some implementations do this)
    aes_key_md5 = hashlib.md5(aes_key_hex.encode()).digest()
    
    print("\n=== Analyzing Status Field ===")
    encrypted_status = analyze_encrypted_data(encrypted_status_b64)
    
    print("\n=== Analyzing Data Field ===")
    encrypted_data = analyze_encrypted_data(encrypted_data_b64)
    
    print("\n=== Trying Decryption Methods on Status ===")
    
    # Try with original key
    print("\nWith original key:")
    results = try_decrypt_methods(encrypted_status, aes_key)
    
    for method, decrypted in results:
        print(f"\n{method}:")
        try:
            # Try to decode as UTF-8
            text = decrypted.decode('utf-8', errors='ignore')
            print(f"  UTF-8: {text[:100]}")
            
            # Try to parse as JSON
            if '{' in text or '[' in text:
                # Find JSON start
                json_start = max(text.find('{'), text.find('['))
                if json_start >= 0:
                    json_text = text[json_start:]
                    try:
                        parsed = json.loads(json_text)
                        print(f"  ✅ Valid JSON found!")
                        print(json.dumps(parsed, indent=2))
                    except:
                        print(f"  JSON-like but not valid")
        except:
            print(f"  Binary (hex): {decrypted[:32].hex()}")
    
    # Try with MD5 of key
    print("\nWith MD5 of key:")
    results = try_decrypt_methods(encrypted_status, aes_key_md5)
    for method, decrypted in results:
        try:
            text = decrypted.decode('utf-8', errors='ignore')
            if '{' in text or '[' in text:
                print(f"\n{method}: {text[:100]}")
        except:
            pass
    
    print("\n=== Trying Decryption Methods on Data ===")
    
    # Try with original key
    print("\nWith original key:")
    results = try_decrypt_methods(encrypted_data, aes_key)
    
    for method, decrypted in results:
        print(f"\n{method}:")
        try:
            # Try to decode as UTF-8
            text = decrypted.decode('utf-8', errors='ignore')
            print(f"  UTF-8: {text[:200]}")
            
            # Try to parse as JSON
            if '{' in text or '[' in text:
                # Find JSON start
                json_start = max(text.find('{'), text.find('['))
                if json_start >= 0:
                    json_text = text[json_start:]
                    try:
                        parsed = json.loads(json_text)
                        print(f"  ✅ Valid JSON found!")
                        print(json.dumps(parsed, indent=2)[:500])
                        
                        # Show device info if found
                        if 'entities' in parsed:
                            print(f"\n  Found {len(parsed['entities'])} entities")
                            for entity in parsed['entities'][:3]:
                                print(f"    - {entity.get('name', 'Unknown')}")
                    except:
                        print(f"  JSON-like but not valid")
        except:
            print(f"  Binary (hex): {decrypted[:32].hex()}")
    
    print("\n=== Testing XOR Encryption ===")
    # Some systems use simple XOR
    for i in range(256):
        xor_key = bytes([i]) * 16
        decrypted = bytes(a ^ b for a, b in zip(encrypted_status[:16], xor_key))
        if b'{' in decrypted or b'entity' in decrypted.lower():
            print(f"Possible XOR key: {i:02x}")
            print(f"Result: {decrypted}")

if __name__ == "__main__":
    main()
