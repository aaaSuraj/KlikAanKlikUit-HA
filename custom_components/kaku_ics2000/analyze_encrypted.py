#!/usr/bin/env python3
"""
Simple analysis of the encrypted data to understand its structure
"""

import base64
import json

def analyze_data():
    """Analyze the encrypted data structure."""
    
    # Your encrypted data
    encrypted_status_b64 = "rO1UhRri1NsdqgRGLOMd6Xnt08JKaGyalJHfxivRlHIgBb+BBvico1g+61eBj8KT72Yt/bpUR0NC6j4Or9VyTA=="
    encrypted_data_b64 = "5OO/DACQWmrMdUtvSe7E8W7wFwzmoyNbdbevK/YWvTHAxSNf/Jdp1/1qjapiAVDagBZ1XyXXwaL/iwUUjllzB3oStLeKxsBW8mrmW04ynXDBdmz0+p4gsiLNarxbW79Al9IEobQPkW7g7+00Uu39SnuLXNH9AWzwwQbMKSv/OuM8Mf7KzH4PL9pGrpn0v5iSBfir4fkA4RfSZJAvDuM9IVkTpFVHXZcK7cmXW7pT7HuSAMkiXrNyIBktK5Kj+dhM/mcETjOlhp3nxh0B+9/t6ygRhPtBcchmnR5dvT+nso0="
    
    print("=== Encrypted Data Analysis ===\n")
    
    # Decode base64
    status_bytes = base64.b64decode(encrypted_status_b64)
    data_bytes = base64.b64decode(encrypted_data_b64)
    
    print("Status field:")
    print(f"  Base64 chars: {len(encrypted_status_b64)}")
    print(f"  Binary bytes: {len(status_bytes)}")
    print(f"  Hex (first 32): {status_bytes[:32].hex()}")
    print(f"  Hex (last 32): {status_bytes[-32:].hex()}")
    
    print("\nData field:")
    print(f"  Base64 chars: {len(encrypted_data_b64)}")
    print(f"  Binary bytes: {len(data_bytes)}")
    print(f"  Hex (first 32): {data_bytes[:32].hex()}")
    print(f"  Hex (last 32): {data_bytes[-32:].hex()}")
    
    # Check for patterns
    print("\n=== Pattern Analysis ===")
    
    # Check if it starts with common JSON characters after some offset
    for offset in range(16):
        if status_bytes[offset:offset+1] in [b'{', b'[', b'"']:
            print(f"Possible JSON at offset {offset} in status: {status_bytes[offset:offset+20]}")
    
    for offset in range(16):
        if data_bytes[offset:offset+1] in [b'{', b'[', b'"']:
            print(f"Possible JSON at offset {offset} in data: {data_bytes[offset:offset+20]}")
    
    # Try to find text patterns
    print("\n=== Text Pattern Search ===")
    
    # Common words that might appear
    patterns = [b'entity', b'Entity', b'name', b'Name', b'device', b'Device', 
                b'status', b'Status', b'dimmer', b'switch', b'light']
    
    for pattern in patterns:
        if pattern in status_bytes:
            pos = status_bytes.index(pattern)
            print(f"Found '{pattern.decode()}' at position {pos} in status")
            print(f"  Context: {status_bytes[max(0,pos-10):pos+20]}")
        
        if pattern in data_bytes:
            pos = data_bytes.index(pattern)
            print(f"Found '{pattern.decode()}' at position {pos} in data")
            print(f"  Context: {data_bytes[max(0,pos-10):pos+20]}")
    
    # Check if it might be compressed
    print("\n=== Compression Check ===")
    
    # Check for gzip header
    if data_bytes[:2] == b'\x1f\x8b':
        print("Data might be gzipped")
    
    # Check for zlib header
    if data_bytes[0] == 0x78:
        print("Data might be zlib compressed")
    
    # Try different key derivations
    print("\n=== Key Derivation Possibilities ===")
    
    aes_key_hex = "f27089bd7728f1899d8aabeacacf8d13"
    mac = "0012A30263F5"
    
    import hashlib
    
    # Different ways the key might be derived
    print(f"Original key: {aes_key_hex}")
    
    # MD5 of hex string
    md5_hex = hashlib.md5(aes_key_hex.encode()).hexdigest()
    print(f"MD5 of hex string: {md5_hex}")
    
    # MD5 of MAC
    md5_mac = hashlib.md5(mac.encode()).hexdigest()
    print(f"MD5 of MAC: {md5_mac}")
    
    # MD5 of MAC bytes
    mac_bytes = bytes.fromhex(mac)
    md5_mac_bytes = hashlib.md5(mac_bytes).hexdigest()
    print(f"MD5 of MAC bytes: {md5_mac_bytes}")
    
    # SHA256 variants
    sha256_hex = hashlib.sha256(aes_key_hex.encode()).hexdigest()[:32]
    print(f"SHA256 of hex (truncated): {sha256_hex}")

if __name__ == "__main__":
    analyze_data()
