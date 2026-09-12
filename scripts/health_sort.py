#!/usr/bin/env python3
"""
Health check and sort script for VPN servers.
Parses servers.txt, checks TCP connectivity, sorts by latency, and generates report.
Deletes dead servers and adds country information with flags.
"""

import socket
import time
import re
import urllib.request
import json
from datetime import datetime
from typing import List, Tuple, Dict, Optional

SERVERS_FILE = "servers.txt"
REPORT_FILE = "health-report.md"
TCP_TIMEOUT = 4
GEOLOCATION_API = "http://ip-api.com/json"

# Country code to flag emoji mapping
COUNTRY_FLAGS = {
    'US': '🇺🇸', 'GB': '🇬🇧', 'CA': '🇨🇦', 'AU': '🇦🇺', 'DE': '🇩🇪', 'FR': '🇫🇷', 
    'JP': '🇯🇵', 'CN': '🇨🇳', 'IN': '🇮🇳', 'BR': '🇧🇷', 'RU': '🇷🇺', 'NL': '🇳🇱',
    'SG': '🇸🇬', 'HK': '🇭🇰', 'KR': '🇰🇷', 'MX': '🇲🇽', 'IT': '🇮🇹', 'ES': '🇪🇸',
    'SE': '🇸🇪', 'CH': '🇨🇭', 'NO': '🇳🇴', 'FI': '🇫🇮', 'PL': '🇵🇱', 'TR': '🇹🇷',
    'IR': '🇮🇷', 'AE': '🇦🇪', 'SA': '🇸🇦', 'IL': '🇮🇱', 'EG': '🇪🇬', 'ZA': '🇿🇦',
    'TH': '🇹🇭', 'MY': '🇲🇾', 'ID': '🇮🇩', 'PH': '🇵🇭', 'VN': '🇻🇳', 'TW': '🇹🇼',
    'NZ': '🇳🇿', 'PK': '🇵🇰', 'BD': '🇧🇩', 'LK': '🇱🇰', 'NG': '🇳🇬', 'KE': '🇰🇪',
    'CZ': '🇨🇿', 'HU': '🇭🇺', 'RO': '🇷🇴', 'UA': '🇺🇦', 'GR': '🇬🇷', 'PT': '🇵🇹',
    'BE': '🇧🇪', 'AT': '🇦🇹', 'DK': '🇩🇰', 'CL': '🇨🇱', 'AR': '🇦🇷', 'CO': '🇨🇴',
    'PE': '🇵🇪', 'EC': '🇪🇨', 'VE': '🇻🇪', 'UY': '🇺🇾', 'CR': '🇨🇷', 'PA': '🇵🇦',
}

def extract_host_port(line: str) -> Tuple[str, int, str]:
    if not line.strip():
        return None, None, line

    if line.startswith("ss://"):
        match = re.search(r"@([^/#?:]+):(\d+)", line)
        if match:
            return match.group(1), int(match.group(2)), line
    elif line.startswith("vmess://"):
        match = re.search(r"vmess://[^@]*@([^/:?]+)", line)
        if match:
            host = match.group(1)
            port_match = re.search(r":(\d+)(?:[/?]|$)", line)
            port = int(port_match.group(1)) if port_match else 443
            return host, port, line
    elif line.startswith("vless://"):
        match = re.search(r"vless://[^@]*@([^/:?]+):(\d+)", line)
        if match:
            return match.group(1), int(match.group(2)), line
    elif line.startswith("trojan://"):
        match = re.search(r"trojan://[^@]*@([^/:?]+):(\d+)", line)
        if match:
            return match.group(1), int(match.group(2)), line

    return None, None, line

def check_tcp_connectivity(host: str, port: int, timeout: float = TCP_TIMEOUT) -> Tuple[bool, float]:
    try:
        start_time = time.time()
        socket.create_connection((host, port), timeout=timeout)
        latency = (time.time() - start_time) * 1000
        return True, latency
    except (socket.timeout, socket.error, OSError):
        return False, float('inf')

def get_country_info(host: str) -> Optional[Dict]:
    """Get country information for IP address using urllib"""
    try:
        url = f"{GEOLOCATION_API}/{host}?fields=country,countryCode,city"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=2) as response:
            data = json.loads(response.read().decode())
            if data.get("status") == "success":
                return {
                    "country": data.get("country", "Unknown"),
                    "country_code": data.get("countryCode", ""),
                    "city": data.get("city", "")
                }
    except Exception as e:
        pass  # Silently fail
    return None

def get_flag(country_code: str) -> str:
    """Get flag emoji for country code"""
    return COUNTRY_FLAGS.get(country_code, "🌍")

def process_servers(servers_file: str) -> Tuple[List[Dict], List[Dict]]:
    live_servers = []
    dead_servers = []

    try:
        with open(servers_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: {servers_file} not found")
        return [], []

    print(f"Processing {len(lines)} server lines...\n")

    for idx, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue

        host, port, original = extract_host_port(line)

        if host is None or port is None:
            dead_servers.append({
                "line": original, 
                "latency": float('inf'), 
                "error": "Parse error",
                "country": "Unknown",
                "country_code": "",
                "city": ""
            })
            continue

        print(f"  [{idx:2d}] Checking {host:30s}...", end=" ", flush=True)
        is_alive, latency = check_tcp_connectivity(host, port)

        # Get geolocation info
        geo_info = get_country_info(host)
        country = geo_info["country"] if geo_info else "Unknown"
        country_code = geo_info["country_code"] if geo_info else ""
        city = geo_info["city"] if geo_info else ""
        flag = get_flag(country_code)

        if is_alive:
            location_name = f"{flag} {country}"
            if city and city != country:
                location_name += f" ({city})"
            
            live_servers.append({
                "line": original, 
                "latency": latency, 
                "host": host, 
                "port": port,
                "country": country,
                "country_code": country_code,
                "city": city,
                "flag": flag,
                "location_name": location_name
            })
            print(f"✓ {location_name:45s} {latency:7.1f}ms")
        else:
            location_name = f"{flag} {country}" if geo_info else "Unknown"
            if geo_info and city and city != country:
                location_name += f" ({city})"
                
            dead_servers.append({
                "line": original, 
                "latency": float('inf'), 
                "host": host, 
                "port": port,
                "error": "Connection Timeout",
                "country": country,
                "country_code": country_code,
                "city": city,
                "flag": flag,
                "location_name": location_name
            })
            print(f"✗ {location_name:45s} Timeout")

    live_servers.sort(key=lambda x: x["latency"])
    return live_servers, dead_servers

def write_output(servers_file: str, report_file: str, live: List[Dict], dead: List[Dict]) -> None:
    # Write only live servers to servers.txt with location prefix in comment
    with open(servers_file, 'w', encoding='utf-8') as f:
        for server in live:
            comment = f" # {server['location_name']} [{server['latency']:.0f}ms]"
            f.write(server["line"] + comment + "\n")

    # Generate health report
    report_content = f"""# VPN Server Health Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary
- **Live Servers**: {len(live)}
- **Dead Servers Removed**: {len(dead)}
- **Total Checked**: {len(live) + len(dead)}

## Live Servers (sorted by latency - fastest first)

| Flag | Country | City | Host | Port | Latency (ms) |
|------|---------|------|------|------|--------------|
"""

    for server in live:
        host = server.get("host", "N/A")
        port = server.get("port", "N/A")
        country = server.get("country", "Unknown")
        city = server.get("city", "")
        flag = server.get("flag", "🌍")
        latency = f"{server['latency']:.1f}" if server['latency'] != float('inf') else "N/A"
        report_content += f"| {flag} | {country} | {city} | {host} | {port} | {latency} |\n"

    report_content += f"""
## Removed Dead Servers

Total removed: **{len(dead)}**

| Flag | Country | City | Host | Port | Reason |
|------|---------|------|------|------|--------|
"""

    for server in dead:
        host = server.get("host", "N/A")
        port = server.get("port", "N/A")
        country = server.get("country", "Unknown")
        city = server.get("city", "")
        flag = server.get("flag", "🌍")
        error = server.get("error", "Unknown")
        report_content += f"| {flag} | {country} | {city} | {host} | {port} | {error} |\n"

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_content)

    print(f"\n✓ Updated {servers_file} (removed {len(dead)} dead servers)")
    print(f"✓ Generated {report_file}")

def main():
    print("=" * 80)
    print("VPN Server Health Check & Sort with Geolocation")
    print("=" * 80 + "\n")

    live_servers, dead_servers = process_servers(SERVERS_FILE)

    print(f"\n" + "=" * 80)
    print(f"Results:")
    print(f"  Live servers: {len(live_servers)}")
    print(f"  Dead servers (will be removed): {len(dead_servers)}\n")

    write_output(SERVERS_FILE, REPORT_FILE, live_servers, dead_servers)

    print("\n" + "=" * 80)
    print("Health check complete!")
    print("=" * 80)

if __name__ == "__main__":
    main()
