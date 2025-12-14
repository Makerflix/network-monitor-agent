# Network Monitor Agent - Setup Guide

## Quick Start

1. **Install dependencies**:
   ```bash
   ./setup.sh
   ```

2. **Activate virtual environment**:
   ```bash
   source venv/bin/activate
   ```

3. **Configure SSH access** (for remote monitoring):
   ```bash
   # Generate SSH key if you don't have one
   ssh-keygen -t ed25519 -C "network-monitor-agent"

   # Copy SSH key to remote servers
   ssh-copy-id root@192.168.1.98   # prx-mdastck-svr
   ssh-copy-id root@192.168.1.163  # prx-jelfrig-srv
   ssh-copy-id root@192.168.1.234  # SideNas-Unraid
   ```

4. **Set environment variables** (optional, for Proxmox API):
   ```bash
   export PROXMOX_PASSWORD="your-proxmox-password"
   ```

5. **Test the agent**:
   ```bash
   python3 main.py --test
   ```

6. **Run continuously**:
   ```bash
   python3 main.py
   ```

## Configuration

Edit `config.yaml` to customize:

- **Monitoring Intervals**: How often to check systems
- **Thresholds**: CPU, memory, disk usage alerts
- **Services**: Which services to monitor
- **Remote Servers**: Add/remove servers to monitor
- **Auto-Remediation**: Enable/disable automatic fixes
- **Notifications**: Configure Discord, Slack, or file logging

## Remote Monitoring

The agent monitors your entire homelab infrastructure:

### Local Monitoring
- System resources (CPU, memory, disk)
- Network interfaces and connectivity
- Local Docker containers
- NFS mounts

### Remote Monitoring (requires SSH keys)
- **prx-mdastck-svr** (192.168.1.98): System stats, Proxmox VMs/LXCs
- **prx-jelfrig-srv** (192.168.1.163): System stats, Proxmox VMs/LXCs
- **SideNas-Unraid** (192.168.1.234): System stats, Docker containers

### Web Service Monitoring
- Open WebUI, Ollama, Paperless, SearXNG (local)
- Home Assistant (Primary & Secondary)
- Jellyfin, Frigate NVR
- Proxmox Web UIs
- Unraid WebUI

## Auto-Remediation

The agent can automatically fix common issues:

- `restart_service`: Restart failed services
- `restart_container`: Restart Docker containers
- `kill_hung_process`: Terminate unresponsive processes
- `clear_cache`: Clear system caches
- `clear_disk_space`: Remove temporary files
- `remount`: Fix stale NFS mounts
- `unmount_remount`: Full remount for failed mounts

Configure in `config.yaml` under `remediation.allowed_actions`.

## Running as a Service

Create a systemd service to run the agent automatically:

```bash
sudo nano /etc/systemd/system/network-monitor-agent.service
```

```ini
[Unit]
Description=Network Monitor Agent
After=network.target

[Service]
Type=simple
User=aa-ai
WorkingDirectory=/home/aa-ai/network-monitor-agent
ExecStart=/home/aa-ai/network-monitor-agent/venv/bin/python3 main.py
Restart=always
RestartSec=10
Environment="PROXMOX_PASSWORD=your-password"

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable network-monitor-agent
sudo systemctl start network-monitor-agent
sudo systemctl status network-monitor-agent
```

View logs:
```bash
sudo journalctl -u network-monitor-agent -f
```

## Troubleshooting

### SSH Authentication Failures
If you see "Permission denied" errors:
1. Ensure SSH keys are copied to remote servers: `ssh-copy-id root@<host>`
2. Test SSH connection manually: `ssh root@<host>`
3. Check SSH key permissions: `chmod 600 ~/.ssh/id_ed25519`

### Proxmox API Authentication
Set the `PROXMOX_PASSWORD` environment variable or edit config.yaml.

### SSL Certificate Errors
The agent automatically trusts self-signed certificates for Proxmox web UIs.

### Services Not Found
If the agent tries to restart a service that doesn't exist, it means the service is running on a different server. Update `config.yaml` to disable monitoring for that endpoint or configure remote remediation.
