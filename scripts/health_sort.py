#!/usr/bin/env python3
"""
Health check and sort script for VPN servers.
Parses servers.txt, checks TCP connectivity, sorts by latency, and generates report.
Deletes dead servers (only keeps live ones).
"""

import socket
import time
import re
from datetime import datetime
from typing import List, Tuple, Dict

SERVERS_FILE = "servers.txt"
REPORT_FILE = "health-report.md"
TCP_TIMEOUT = 4

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

def process_servers(servers_file: str) -> Tuple[List[Dict], List[Dict]]:
    live_servers = []
    dead_servers = []

    try:
        with open(servers_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: {servers_file} not found")
        return [], []

    print(f"Processing {len(lines)} server lines...")

    for idx, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue

        host, port, original = extract_host_port(line)

        if host is None or port is None:
            dead_servers.append({"line": original, "latency": float('inf'), "error": "Parse error"})
            continue

        print(f"  [{idx}] Checking {host}:{port}...", end=" ")
        is_alive, latency = check_tcp_connectivity(host, port)

        if is_alive:
            live_servers.append({"line": original, "latency": latency, "host": host, "port": port})
            print(f"✓ ({latency:.1f}ms)")
        else:
            dead_servers.append({"line": original, "latency": float('inf'), "host": host, "port": port})
            print(f"✗ (timeout)")

    live_servers.sort(key=lambda x: x["latency"])
    return live_servers, dead_servers

def write_output(servers_file: str, report_file: str, live: List[Dict], dead: List[Dict]) -> None:
    # Write only live servers to servers.txt (dead servers are deleted)
    with open(servers_file, 'w', encoding='utf-8') as f:
        for server in live:
            f.write(server["line"] + "\n")

    # Generate health report
    report_content = f"""# VPN Server Health Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary
- **Live Servers**: {len(live)}
- **Dead Servers Removed**: {len(dead)}
- **Total Checked**: {len(live) + len(dead)}

## Live Servers (sorted by latency - fastest first)

| Host | Port | Latency (ms) |
|------|------|--------------|
"""

    for server in live:
        host = server.get("host", "N/A")
        port = server.get("port", "N/A")
        latency = f"{server['latency']:.1f}" if server['latency'] != float('inf') else "N/A"
        report_content += f"| {host} | {port} | {latency} |\n"

    report_content += f"""
## Removed Dead Servers

Total removed: **{len(dead)}**

| Host | Port | Reason |
|------|------|--------|
"""

    for server in dead:
        host = server.get("host", "Parse Error")
        port = server.get("port", "N/A")
        error = server.get("error", "Connection Timeout")
        report_content += f"| {host} | {port} | {error} |\n"

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_content)

    print(f"\n✓ Updated {servers_file} (removed {len(dead)} dead servers)")
    print(f"✓ Generated {report_file}")

def main():
    print("=" * 60)
    print("VPN Server Health Check & Sort")
    print("=" * 60 + "\n")

    live_servers, dead_servers = process_servers(SERVERS_FILE)

    print(f"\nResults:")
    print(f"  Live servers: {len(live_servers)}")
    print(f"  Dead servers (will be removed): {len(dead_servers)}\n")

    write_output(SERVERS_FILE, REPORT_FILE, live_servers, dead_servers)

    print("\n" + "=" * 60)
    print("Health check complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
