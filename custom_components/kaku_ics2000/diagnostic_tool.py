#!/usr/bin/env python3
"""
Diagnostic script to test KlikAanKlikUit ICS-2000 cloud authentication and device fetching.
Run this to debug authentication and device discovery issues.
Uses only standard library modules.
"""

import json
import socket
import ssl
import urllib.request
import urllib.parse
import urllib.error
from typing import Dict, List, Optional, Tuple

def test_authentication(email: str, password: str, mac: str) -> Tuple[bool, Optional[Dict]]:
    """Test cloud authentication using Homebridge format."""
    
    mac_clean = mac.upper().replace(":", "").replace("-", "").replace(" ", "")
    
    print("\n=== Testing Authentication ===")
    print(f"Email: {email}")
    print(f"MAC (original): {mac}")
    print(f"MAC (cleaned): {mac_clean}")
    print(f"Password: {'*' * len(password)}")
    
    mac_formats = [
        ("", "Empty string"),
        (mac_clean, "Uppercase without colons"),
        (mac_clean.lower(), "Lowercase without colons"),
        (":".join([mac_clean[i:i+2] for i in range(0, 12, 2)]), "Uppercase with colons"),
        (":".join([mac_clean[i:i+2] for i in range(0, 12, 2)]).lower(), "Lowercase with colons"),
    ]
    
    endpoints = [
        "https://trustsmartcloud2.com/ics2000_api/account.php",
        "https://trustsmartcloud.com/ics2000_api/account.php",
        "https://www.trustsmartcloud2.com/ics2000_api/account.php",
    ]
    
    # Create SSL context that doesn't verify certificates (for testing)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    for endpoint in endpoints:
        print(f"\n--- Testing endpoint: {endpoint} ---")
        
        for mac_format, mac_desc in mac_formats:
            login_data = {
                'action': 'login',
                'email': email,
                'password_hash': password,
                'device_unique_id': 'android',
                'platform': '',
                'mac': mac_format,
            }
            
            print(f"\nTrying: MAC={mac_desc}")
            
            try:
                data = urllib.parse.urlencode(login_data).encode('utf-8')
                req = urllib.request.Request(endpoint, data=data, method='POST')
                
                with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
                    text = response.read().decode('utf-8')
                    print(f"  Status: {response.status}")
                    print(f"  Response preview: {text[:200]}")
                    
                    if response.status == 200:
                        if any(word in text.lower() for word in ['aes_key', 'homes', 'home_id']):
                            print("\n✅ SUCCESS! Working configuration:")
                            print(f"  Endpoint: {endpoint}")
                            print(f"  MAC format: {mac_desc} ({mac_format})")
                            
                            try:
                                auth_data = json.loads(text)
                                return True, auth_data
                            except:
                                return True, None
                                
            except urllib.error.HTTPError as e:
                print(f"  HTTP Error {e.code}: {e.reason}")
            except Exception as e:
                print(f"  Error: {str(e)[:100]}")
    
    print("\n❌ No working authentication method found")
    return False, None


def test_device_sync(email: str, password: str, mac: str, auth_data: Optional[Dict]) -> bool:
    """Test device sync using various endpoints."""
    
    print("\n=== Testing Device Sync ===")
    
    mac_clean = mac.upper().replace(":", "").replace("-", "").replace(" ", "")
    
    # Extract home_id and gateway_id from auth if available
    home_id = ""
    gateway_id = mac_clean
    
    if auth_data and 'homes' in auth_data:
        if auth_data['homes']:
            home = auth_data['homes'][0]
            home_id = home.get('home_id', '')
            gateway_id = home.get('mac', mac_clean)
    
    print(f"Using home_id: {home_id or 'none'}")
    print(f"Using gateway_id: {gateway_id}")
    
    # Endpoints to test for device sync
    sync_endpoints = [
        ("https://trustsmartcloud2.com/ics2000_api/gateway.php", "gateway.php"),
        ("https://trustsmartcloud2.com/ics2000_api/devices.php", "devices.php"),
        ("https://trustsmartcloud2.com/ics2000_api/entities.php", "entities.php"),
        ("https://trustsmartcloud.com/ics2000_api/gateway.php", "gateway.php"),
        ("https://www.trustsmartcloud2.com/ics2000_api/gateway.php", "gateway.php"),
    ]
    
    # Different sync data formats to try
    sync_formats = [
        {
            'email': email,
            'mac': gateway_id,
            'action': 'sync',
            'password_hash': password,
            'home_id': home_id,
        },
        {
            'action': 'sync',
            'email': email,
            'password_hash': password,
            'mac': gateway_id,
        },
        {
            'email': email,
            'password': password,
            'action': 'sync',
            'mac': gateway_id,
        },
        {
            'action': 'get_devices',
            'email': email,
            'password_hash': password,
            'mac': gateway_id,
        },
    ]
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    for endpoint, endpoint_name in sync_endpoints:
        print(f"\n--- Testing {endpoint_name} ---")
        
        for i, sync_data in enumerate(sync_formats):
            print(f"\nFormat {i+1}: {list(sync_data.keys())}")
            
            try:
                data = urllib.parse.urlencode(sync_data).encode('utf-8')
                req = urllib.request.Request(endpoint, data=data, method='POST')
                
                with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
                    text = response.read().decode('utf-8')
                    
                    if response.status == 200:
                        # Check if response contains device data
                        device_keywords = ['entity', 'entities', 'device', 'devices', 'scene', 
                                         'dimmer', 'switch', 'dimLevel', 'status', 'entityId']
                        
                        if any(word in text.lower() for word in device_keywords):
                            print(f"✅ SUCCESS! Found devices at {endpoint_name}")
                            print(f"Response preview: {text[:500]}")
                            
                            # Try to parse and show structure
                            try:
                                data = json.loads(text)
                                if isinstance(data, dict):
                                    print(f"JSON structure keys: {list(data.keys())}")
                                    
                                    # Count devices/entities
                                    if 'entities' in data:
                                        print(f"Found {len(data['entities'])} entities")
                                    if 'devices' in data:
                                        print(f"Found {len(data['devices'])} devices")
                                    if 'scenes' in data:
                                        print(f"Found {len(data['scenes'])} scenes")
                                        
                                    # Show sample entity
                                    if 'entities' in data and data['entities']:
                                        print("\nSample entity structure:")
                                        print(json.dumps(data['entities'][0], indent=2))
                                        
                            except json.JSONDecodeError:
                                print("(Response is not JSON)")
                            
                            print(f"\n💡 Working sync configuration:")
                            print(f"Endpoint: {endpoint}")
                            print(f"Sync data format: {sync_data}")
                            return True
                        else:
                            print(f"  Response doesn't contain device data")
                            
            except urllib.error.HTTPError as e:
                print(f"  HTTP Error {e.code}: {e.reason}")
            except Exception as e:
                print(f"  Error: {str(e)[:100]}")
    
    print("\n❌ No working device sync method found")
    return False


def test_local_discovery(mac: str, ip_address: Optional[str] = None) -> Optional[str]:
    """Test local network discovery and direct IP communication."""
    
    print(f"\n=== Testing Local Discovery ===")
    
    mac_clean = mac.upper().replace(":", "").replace("-", "").replace(" ", "")
    discovered_ip = None
    
    # First try broadcast discovery
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(5)
        
        print("Sending discovery broadcast...")
        sock.sendto(b"D", ("255.255.255.255", 2012))
        
        try:
            data, addr = sock.recvfrom(1024)
            print(f"✅ Response from {addr[0]}")
            print(f"Data: {data.hex()}")
            
            if mac_clean in data.hex().upper():
                print(f"✅ MAC address confirmed in response")
                discovered_ip = addr[0]
            else:
                print(f"⚠️ Response doesn't contain expected MAC")
                discovered_ip = addr[0]
                
        except socket.timeout:
            print("❌ No broadcast response - ICS-2000 may not be on network")
            
    except Exception as e:
        print(f"❌ Discovery error: {e}")
    finally:
        sock.close()
    
    # Test provided IP address if given
    if ip_address:
        print(f"\n--- Testing provided IP: {ip_address} ---")
        if test_direct_connection(ip_address, mac_clean):
            return ip_address
    
    # Test discovered IP if different from provided
    if discovered_ip and discovered_ip != ip_address:
        print(f"\n--- Testing discovered IP: {discovered_ip} ---")
        if test_direct_connection(discovered_ip, mac_clean):
            return discovered_ip
    
    return discovered_ip or ip_address


def test_direct_connection(ip: str, mac: str) -> bool:
    """Test direct connection to ICS-2000 at given IP."""
    
    print(f"Testing direct connection to {ip}")
    
    # Test different ports
    ports = [
        (2012, "Discovery port"),
        (9760, "Control port"),
        (9761, "Alternative control port"),
        (80, "HTTP port"),
    ]
    
    success = False
    
    for port, port_name in ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2)
            
            # Try different discovery messages
            messages = [b"D", b"ICSINF", b"ICS2000", b"STATUS"]
            
            for msg in messages:
                try:
                    sock.sendto(msg, (ip, port))
                    data, addr = sock.recvfrom(1024)
                    print(f"  ✅ Response on {port_name} ({port}) with message '{msg.decode()}': {data.hex()[:50]}...")
                    
                    if mac in data.hex().upper():
                        print(f"  ✅ MAC confirmed in response!")
                    
                    success = True
                    break
                except socket.timeout:
                    continue
                except Exception as e:
                    continue
            
            sock.close()
            
        except Exception as e:
            continue
    
    # Also test TCP connection
    print(f"\nTesting TCP connection to {ip}...")
    for port in [80, 8080, 9760]:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((ip, port))
            if result == 0:
                print(f"  ✅ TCP port {port} is open")
                success = True
            sock.close()
        except:
            pass
    
    if success:
        print(f"✅ ICS-2000 appears to be at {ip}")
    else:
        print(f"❌ No response from {ip}")
    
    return success


def test_local_commands(ip: str, mac: str) -> None:
    """Test sending local commands to ICS-2000."""
    
    print(f"\n=== Testing Local Commands ===")
    print(f"Target IP: {ip}")
    
    mac_bytes = bytes.fromhex(mac)
    
    # Build a test command packet (turn on device 1)
    packet = bytearray()
    packet.extend(b'\xAA\xAA')  # Header
    packet.extend(mac_bytes)  # MAC
    packet.append(0x01)  # Device ID 1
    packet.append(0x01)  # Command: ON
    packet.append(0x00)  # Value
    
    # Calculate checksum
    checksum = sum(packet) & 0xFF
    packet.append(checksum)
    
    print(f"Sending test command packet: {packet.hex()}")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2)
        
        # Try different ports
        for port in [9760, 9761, 2012]:
            try:
                sock.sendto(bytes(packet), (ip, port))
                print(f"  Sent to port {port}")
                
                # Try to receive response
                try:
                    data, addr = sock.recvfrom(1024)
                    print(f"  ✅ Response from port {port}: {data.hex()}")
                except socket.timeout:
                    print(f"  No response from port {port}")
                    
            except Exception as e:
                print(f"  Error on port {port}: {e}")
        
        sock.close()
        
    except Exception as e:
        print(f"❌ Command test error: {e}")


def main():
    """Main diagnostic function."""
    print("=== KlikAanKlikUit ICS-2000 Diagnostic Tool ===")
    print("Testing authentication and device sync methods\n")
    
    # Get credentials
    email = input("Enter your email: ").strip()
    password = input("Enter your password: ").strip()
    mac = input("Enter MAC address (any format): ").strip()
    ip_input = input("Enter IP address (optional, press Enter to skip): ").strip()
    
    ip_address = ip_input if ip_input else None
    
    # Test authentication
    auth_success, auth_data = test_authentication(email, password, mac)
    
    # Test device sync if auth succeeded
    sync_success = False
    if auth_success:
        sync_success = test_device_sync(email, password, mac, auth_data)
    
    # Test local discovery and connection
    mac_clean = mac.upper().replace(":", "").replace("-", "").replace(" ", "")
    local_ip = test_local_discovery(mac_clean, ip_address)
    
    # Test local commands if we have an IP
    if local_ip:
        test_local_commands(local_ip, mac_clean)
    elif ip_address:
        print("\n--- Testing commands with provided IP ---")
        test_local_commands(ip_address, mac_clean)
    
    # Summary
    print(f"\n{'='*50}")
    print("=== SUMMARY ===")
    print(f"{'='*50}")
    print(f"Cloud Authentication: {'✅ Working' if auth_success else '❌ Failed'}")
    print(f"Device Sync: {'✅ Working' if sync_success else '❌ Failed'}")
    print(f"Local Discovery: {'✅ Found at ' + local_ip if local_ip else '❌ Not found'}")
    if ip_address:
        print(f"Provided IP: {ip_address}")
    
    if not auth_success:
        print("\n💡 Authentication troubleshooting:")
        print("1. Try logging in at https://trustsmartcloud2.com with your credentials")
        print("2. Check if your ICS-2000 is registered to your account")
        print("3. Ensure the MAC address is correct (check the device label)")
        print("4. Try resetting your password on the website")
    
    if auth_success and not sync_success:
        print("\n💡 Device sync troubleshooting:")
        print("1. Check if devices are configured in the KlikAanKlikUit app")
        print("2. Try adding a device through the official app first")
        print("3. Ensure your ICS-2000 firmware is up to date")
    
    if not local_ip and not ip_address:
        print("\n💡 Local discovery troubleshooting:")
        print("1. Ensure ICS-2000 is on the same network")
        print("2. Check if firewall is blocking UDP port 2012")
        print("3. Try providing the IP address directly")
        print("4. Check the ICS-2000 is powered on and connected to network")


if __name__ == "__main__":
    main()
