# ifix-vpn-subs

Automatic VPN server health-check and subscription management system.

## Overview

This repository contains a collection of VPN proxy servers (ss, vmess, vless, trojan) with an automated health-check system that validates server connectivity and sorts them by latency.

## Features

- **Automated Health Checks**: GitHub Actions workflow runs every 3 hours
- **TCP Connectivity Testing**: Tests each server's availability with ~4s timeout
- **Latency Sorting**: Orders live servers by response time (lowest first)
- **Dead Server Handling**: Keeps dead servers at the bottom (not deleted)
- **Health Reports**: Generates detailed markdown reports with status and latency metrics
- **Manual Execution**: Supports `workflow_dispatch` for on-demand health checks

## File Structure

```
ifix-vpn-subs/
├── servers.txt                      # VPN proxy list (auto-sorted by health)
├── scripts/
│   └── health_sort.py              # Health check and sort script
├── .github/
│   └── workflows/
│       └── health-check.yml        # GitHub Actions workflow
├── health-report.md                 # Generated health check report
└── README.md                        # This file
```

## How the Health Check Works

1. **Parse**: Reads `servers.txt` and extracts host:port from each proxy URL
2. **Test**: Performs TCP connectivity test with 4-second timeout
3. **Sort**: Arranges live servers by latency (fastest first)
4. **Report**: Generates `health-report.md` with detailed results
5. **Commit**: Auto-commits changes if servers were reordered

## Supported Proxy Protocols

- `ss://` (Shadowsocks)
- `vmess://` (VMess)
- `vless://` (VLESS)
- `trojan://` (Trojan)

## Running the Health Check

### Automatic (Scheduled)
The workflow runs automatically every **3 hours**.

### Manual Execution
Go to:
```
Actions → Health Check servers.txt → Run workflow → Run workflow
```

### Local Execution
```bash
python scripts/health_sort.py
```

This will:
- Check all servers in `servers.txt`
- Reorder them by latency
- Create/update `health-report.md`

## Output

### servers.txt
Live servers are placed at the top, sorted by latency (fastest first). Dead servers remain at the bottom.

### health-report.md
Contains:
- **Summary**: Live/dead server counts
- **Live Servers Table**: Host, port, latency (ms)
- **Dead Servers Table**: Host, port, error reason

## Workflow Configuration

- **Trigger**: Scheduled every 3 hours + manual dispatch
- **Environment**: Ubuntu latest
- **Python**: 3.11
- **Permissions**: Write access to repository contents

## Troubleshooting

### Actions Disabled?
If the workflow doesn't run, enable it:
```
Settings → Actions → General → Allow all actions
```

### Script Errors?
Check the workflow logs:
```
Actions → Health Check servers.txt → [Latest run] → health-check job
```

### No Changes Committed?
The workflow only commits if servers were reordered. If all servers remain in the same order, no commit is made.

## Notes

- Dead servers are **never deleted**, only moved to the bottom
- TCP timeout is set to ~4 seconds per server
- Each check output shows latency in milliseconds
- Reports are regenerated on every run
