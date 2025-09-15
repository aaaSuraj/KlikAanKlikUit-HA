#!/usr/bin/env python3
"""
Explore local communication with ICS-2000 to get device status
"""

import socket
import struct
import time
import hashlib
import json

def test_udp_port(ip, port, message, description):
    """Test UDP communication on a specific port."""
    print(f"\n{'='*50}")
    print(f"Testing: {description}")
    print(f"Port: {port}, Message: {message}")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2)
        
        # Send message
        if isinstance(message, str):
            message = message.encode()
        
        sock.sendto(message, (ip, port))
        print(f"Sent {len(message)} bytes")
        
        # Try to receive response
        try:
            data, addr = sock.recvfrom(1024)
            print(f"✅ Got response from {addr[0]}:{addr[1]}")
            print(f"Response (hex): {data.hex()}")
            print(f"Response (ascii): {data.decode('ascii', errors='ignore')}")
            
            # Try to interpret response
            if len(data) >= 4:
                print(f"First 4 bytes as int: {struct.unpack('>I', data[:4])[0]}")
            
            return data
            
        except socket.timeout:
            print("No response (timeout)")
            return None
            
    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        sock.close()

def test_tcp_port(ip, port, message, description):
    """Test TCP communication on a specific port."""
    print(f"\n{'='*50}")
    print(f"Testing TCP: {description}")
    print(f"Port: {port}")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        
        # Try to connect
        sock.connect((ip, port))
        print(f"✅ Connected to {ip}:{port}")
        
        # Send message if provided
        if message:
            if isinstance(message, str):
                message = message.encode()
            sock.send(message)
            print(f"Sent {len(message)} bytes")
        
        # Try to receive
        try:
            data = sock.recv(1024)
            if data:
                print(f"Response (hex): {data.hex()}")
                print(f"Response (ascii): {data.decode('ascii', errors='ignore')}")
                return data
            else:
                print("Connected but no data received")
                return None
        except socket.timeout:
            print("Connected but no response")
            return None
            
    except socket.timeout:
        print(f"Connection timeout - port might be closed")
        return None
    except ConnectionRefused:
        print(f"Connection refused - port is closed")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        try:
            sock.close()
        except:
            pass

def build_status_packet(mac, device_id=0):
    """Build a status request packet."""
    mac_clean = mac.replace(":", "").upper()
    mac_bytes = bytes.fromhex(mac_clean)
    
    # Try different packet formats
    packets = []
    
    # Format 1: Simple status request
    packet1 = bytearray()
    packet1.extend(b'\xAA\xAA')  # Header
    packet1.extend(mac_bytes)     # MAC
    packet1.append(0xFF)           # Status command
    packet1.append(device_id)      # Device ID (0 for all)
    checksum = sum(packet1) & 0xFF
    packet1.append(checksum)
    packets.append(("Status request format 1", bytes(packet1)))
    
    # Format 2: GET command
    packet2 = bytearray()
    packet2.extend(b'GET')
    packet2.extend(mac_bytes)
    packet2.append(device_id)
    packets.append(("GET command", bytes(packet2)))
    
    # Format 3: JSON request
    json_req = json.dumps({
        'action': 'status',
        'mac': mac,
        'device': device_id
    })
    packets.append(("JSON request", json_req.encode()))
    
    return packets

def main():
    print("=== ICS-2000 Local Status Explorer ===\n")
    
    # Get ICS-2000 info
    ip = input("Enter ICS-2000 IP address (default: 192.168.0.39): ").strip()
    if not ip:
        ip = "192.168.0.39"
    
    mac = input("Enter MAC address: ").strip()
    
    print(f"\nExploring ICS-2000 at {ip}")
    print(f"MAC: {mac}")
    
    # Common IoT device ports
    udp_ports = [
        (2012, "Discovery port"),
        (9760, "Control port"),
        (8899, "Common IoT port"),
        (5577, "LED controller port"),
        (1234, "Simple protocol port"),
        (6668, "Alternative control"),
        (9999, "Debug port"),
        (30000, "High port range"),
        (49999, "Alternative high port"),
    ]
    
    print("\n" + "="*60)
    print("TESTING UDP PORTS")
    print("="*60)
    
    # Test each UDP port with different messages
    for port, description in udp_ports:
        # Test with discovery message
        test_udp_port(ip, port, b"D", f"{description} - Discovery")
        
        # Test with status request
        test_udp_port(ip, port, b"STATUS", f"{description} - STATUS")
        
        # Test with custom packet
        packets = build_status_packet(mac)
        for pkt_desc, packet in packets:
            result = test_udp_port(ip, port, packet, f"{description} - {pkt_desc}")
            if result:
                print(f"💡 Got response on port {port}!")
                break
    
    print("\n" + "="*60)
    print("TESTING TCP PORTS")
    print("="*60)
    
    tcp_ports = [
        (80, "HTTP"),
        (443, "HTTPS"),
        (8080, "Alt HTTP"),
        (9760, "Control port"),
        (23, "Telnet"),
        (22, "SSH"),
        (1883, "MQTT"),
        (8883, "MQTT SSL"),
        (502, "Modbus"),
        (6668, "Alternative"),
    ]
    
    for port, description in tcp_ports:
        test_tcp_port(ip, port, None, description)
    
    print("\n" + "="*60)
    print("TESTING HTTP/API ENDPOINTS")
    print("="*60)
    
    # Test HTTP endpoints
    import urllib.request
    import ssl
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    http_endpoints = [
        f"http://{ip}/",
        f"http://{ip}/status",
        f"http://{ip}/api/status",
        f"http://{ip}/api/devices",
        f"http://{ip}/cgi-bin/status.cgi",
        f"http://{ip}:8080/",
        f"https://{ip}/",
    ]
    
    for endpoint in http_endpoints:
        print(f"\nTrying: {endpoint}")
        try:
            req = urllib.request.Request(endpoint)
            with urllib.request.urlopen(req, timeout=2, context=ctx) as response:
                print(f"✅ HTTP {response.status} - Found web interface!")
                content = response.read().decode('utf-8', errors='ignore')
                if 'status' in content.lower() or 'device' in content.lower():
                    print(f"Contains status/device keywords!")
                    print(f"Preview: {content[:200]}")
        except Exception as e:
            print(f"Failed: {str(e)[:50]}")
    
    print("\n" + "="*60)
    print("TESTING BROADCAST STATUS REQUEST")
    print("="*60)
    
    # Try broadcast for status
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(3)
        
        # Send status request broadcast
        messages = [b"STATUS", b"STATE", b"GET", b"INFO", b"LIST"]
        
        for msg in messages:
            print(f"\nBroadcasting: {msg.decode()}")
            sock.sendto(msg, ("255.255.255.255", 2012))
            
            try:
                data, addr = sock.recvfrom(1024)
                if addr[0] == ip:
                    print(f"✅ Got response from ICS-2000!")
                    print(f"Response: {data.hex()}")
                    print(f"ASCII: {data.decode('ascii', errors='ignore')}")
            except socket.timeout:
                print("No response")
        
        sock.close()
        
    except Exception as e:
        print(f"Broadcast error: {e}")
    
    print("\n" + "="*60)
    print("ANALYSIS")
    print("="*60)
    print("\nBased on the responses:")
    print("1. If UDP port 9760 responds - that's likely the control/status port")
    print("2. If HTTP is available - check for API endpoints")
    print("3. If only discovery works - device might not support status queries")
    print("4. The 'status' field in gateway.php might be the only status source")

if __name__ == "__main__":
    main()
