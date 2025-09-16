#!/usr/bin/env python3
"""
Test different command formats for large device IDs
"""

import socket
import struct
import time

def test_command_formats(ip, mac, device_id):
    """Test different packet formats for large device IDs."""
    
    mac_clean = mac.replace(":", "").upper()
    mac_bytes = bytes.fromhex(mac_clean)
    
    print(f"Testing device {device_id} at {ip}")
    print(f"Device ID in hex: {device_id:08X}")
    print(f"Device ID bytes: {device_id.to_bytes(4, 'big').hex()}")
    print("="*60)
    
    formats = []
    
    # Format 1: Original (only last byte)
    packet1 = bytearray()
    packet1.extend(b'\xAA\xAA')
    packet1.extend(mac_bytes)
    packet1.append(device_id & 0xFF)  # Only last byte
    packet1.append(0x01)  # ON
    packet1.append(0x00)
    checksum = sum(packet1) & 0xFF
    packet1.append(checksum)
    formats.append(("Original (last byte only)", bytes(packet1)))
    
    # Format 2: 2-byte device ID
    packet2 = bytearray()
    packet2.extend(b'\xAA\xAA')
    packet2.extend(mac_bytes)
    packet2.extend(struct.pack('>H', device_id & 0xFFFF))  # 2 bytes, big-endian
    packet2.append(0x01)  # ON
    packet2.append(0x00)
    checksum = sum(packet2) & 0xFF
    packet2.append(checksum)
    formats.append(("2-byte device ID (big-endian)", bytes(packet2)))
    
    # Format 3: 4-byte device ID
    packet3 = bytearray()
    packet3.extend(b'\xAA\xAA')
    packet3.extend(mac_bytes)
    packet3.extend(struct.pack('>I', device_id))  # 4 bytes, big-endian
    packet3.append(0x01)  # ON
    packet3.append(0x00)
    checksum = sum(packet3) & 0xFF
    packet3.append(checksum)
    formats.append(("4-byte device ID (big-endian)", bytes(packet3)))
    
    # Format 4: Little-endian 4-byte
    packet4 = bytearray()
    packet4.extend(b'\xAA\xAA')
    packet4.extend(mac_bytes)
    packet4.extend(struct.pack('<I', device_id))  # 4 bytes, little-endian
    packet4.append(0x01)  # ON
    packet4.append(0x00)
    checksum = sum(packet4) & 0xFF
    packet4.append(checksum)
    formats.append(("4-byte device ID (little-endian)", bytes(packet4)))
    
    # Format 5: Different header
    packet5 = bytearray()
    packet5.extend(b'\x5A\x5A')  # Different header
    packet5.extend(mac_bytes)
    packet5.extend(struct.pack('>I', device_id))
    packet5.append(0x01)  # ON
    packet5.append(0x00)
    checksum = sum(packet5) & 0xFF
    packet5.append(checksum)
    formats.append(("Different header (5A5A)", bytes(packet5)))
    
    # Format 6: JSON command
    import json
    json_cmd = json.dumps({
        'mac': mac,
        'device': device_id,
        'command': 'on'
    })
    formats.append(("JSON format", json_cmd.encode()))
    
    # Test each format
    for description, packet in formats:
        print(f"\nTesting: {description}")
        print(f"Packet: {packet.hex() if isinstance(packet, bytes) else packet[:50]}")
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1.0)
            
            # Send 3 times
            for _ in range(3):
                sock.sendto(packet, (ip, 9760))
                time.sleep(0.1)
            
            sock.close()
            print("✓ Sent successfully")
            
            # Wait to see if light turns on
            input("Check if the light turned on, then press Enter to continue...")
            
        except Exception as e:
            print(f"✗ Error: {e}")

def main():
    print("=== Testing Command Formats for Large Device IDs ===\n")
    
    ip = input("Enter ICS-2000 IP (default: 192.168.0.39): ").strip() or "192.168.0.39"
    mac = input("Enter MAC address: ").strip()
    
    # Test Office Right
    device_id = 26087308
    
    print(f"\nTesting Office Right (ID: {device_id})")
    test_command_formats(ip, mac, device_id)
    
    print("\n" + "="*60)
    print("If none worked, the large IDs might:")
    print("1. Use a completely different protocol")
    print("2. Not be controllable via local commands")
    print("3. Be virtual/cloud-only devices")

if __name__ == "__main__":
    main()
