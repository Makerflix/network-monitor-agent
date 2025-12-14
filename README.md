# Network Monitor Agent

An AI-powered agent that monitors your network and servers for issues and automatically fixes them. The agent uses Claude AI to intelligently analyze problems and determine the best course of action.

## Features

- **System Monitoring**: CPU, memory, disk usage, service status, process monitoring
- **Network Monitoring**: Connectivity checks, latency monitoring, interface status
- **Web Service Monitoring**: HTTP endpoint health checks, API monitoring
- **AI-Powered Analysis**: Uses Claude AI to analyze issues and recommend fixes
- **Automatic Remediation**: Can automatically fix common issues
- **Smart Notifications**: Alerts via Slack/Discord and detailed logging
- **Configurable**: Easy YAML configuration for all settings

## Architecture

```
network-monitor-agent/
├── main.py              # Main orchestration loop
├── config.yaml          # Configuration file
├── monitors/            # Monitoring modules
│   ├── system_monitor.py
│   ├── network_monitor.py
│   └── web_monitor.py
├── ai/                  # AI decision engine
│   └── decision_engine.py
├── remediation/         # Auto-fix actions
│   └── actions.py
└── notifications/       # Alert system
    └── notifier.py
```

## Installation

### 1. Clone or download this directory

```bash
cd /home/aa-ai/network-monitor-agent
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure the agent

Edit `config.yaml` to customize:

- **AI Provider**: Set your API key and model
- **Monitoring**: Configure what to monitor and thresholds
- **Remediation**: Enable/disable auto-fix and set allowed actions
- **Notifications**: Setup Slack/Discord webhooks

### 4. Set environment variables

```bash
# For Anthropic Claude (recommended)
export ANTHROPIC_API_KEY="your-api-key-here"

# Optional: For Slack notifications
export SLACK_WEBHOOK_URL="your-slack-webhook-url"

# Optional: For Discord notifications
export DISCORD_WEBHOOK_URL="your-discord-webhook-url"
```

## Usage

### Run continuously (production mode)

```bash
python3 main.py
```

### Run a single test cycle

```bash
python3 main.py --test
```

### Run with custom config file

```bash
python3 main.py --config /path/to/config.yaml
```

### Run as a background service

```bash
nohup python3 main.py >> agent.log 2>&1 &
```

## Configuration Guide

### Monitoring Settings

```yaml
monitoring:
  interval: 60  # Check every 60 seconds

  system:
    enabled: true
    cpu_threshold: 80      # Alert if CPU > 80%
    memory_threshold: 85   # Alert if memory > 85%
    disk_threshold: 90     # Alert if disk > 90%
    check_services:
      - docker
      - nginx
      - ssh
```

### Remediation Actions

The agent can automatically perform these actions:

- `restart_service`: Restart systemd services
- `clear_cache`: Clear system caches
- `kill_hung_process`: Terminate unresponsive processes
- `restart_container`: Restart Docker containers
- `clear_disk_space`: Clean temporary files and logs

### Safety Features

- **Cooldown Period**: Prevents repeated attempts (default: 5 minutes)
- **Max Attempts**: Limits retry attempts (default: 3)
- **Allowed Actions List**: Only executes whitelisted actions
- **AI Oversight**: AI must approve each action before execution

## Example Scenarios

### 1. Service Down
**Detection**: systemctl shows nginx is inactive
**AI Analysis**: Identifies service failure
**Action**: Restarts nginx service
**Result**: Service restored, notification sent

### 2. High Disk Usage
**Detection**: /var partition at 95%
**AI Analysis**: Identifies disk space issue
**Action**: Cleans old logs and temporary files
**Result**: Disk usage reduced to 75%

### 3. Network Issue
**Detection**: High packet loss to 8.8.8.8
**AI Analysis**: Network connectivity problem
**Action**: Alert only (requires human intervention)
**Result**: Critical notification sent to Slack/Discord

## Notifications

### Log Files
All events are logged to:
- `/var/log/network-monitor-agent.log` (if writable)
- `~/network-monitor-agent.log` (fallback)

### Slack Integration
1. Create a Slack webhook: https://api.slack.com/messaging/webhooks
2. Set `SLACK_WEBHOOK_URL` environment variable or in config
3. Enable in config: `notifications.slack.enabled: true`

### Discord Integration
1. Create a Discord webhook in your server settings
2. Set `DISCORD_WEBHOOK_URL` environment variable or in config
3. Enable in config: `notifications.discord.enabled: true`

## Permissions

Some actions require sudo privileges:

- Restarting services
- Clearing system caches
- Cleaning system directories

### Setup passwordless sudo for specific commands:

```bash
sudo visudo
```

Add:
```
your-username ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart *
your-username ALL=(ALL) NOPASSWD: /usr/bin/journalctl --vacuum-time=*
your-username ALL=(ALL) NOPASSWD: /usr/bin/apt-get clean
```

## Running as a Systemd Service

Create `/etc/systemd/system/network-monitor-agent.service`:

```ini
[Unit]
Description=Network Monitor Agent
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/home/aa-ai/network-monitor-agent
Environment="ANTHROPIC_API_KEY=your-key-here"
ExecStart=/usr/bin/python3 /home/aa-ai/network-monitor-agent/main.py
Restart=always
RestartSec=10

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

## AI Providers

### Anthropic Claude (Recommended)
```yaml
ai:
  provider: "anthropic"
  model: "claude-sonnet-4-5-20250929"
  api_key: "${ANTHROPIC_API_KEY}"
```

### OpenAI
```yaml
ai:
  provider: "openai"
  model: "gpt-4"
  api_key: "${OPENAI_API_KEY}"
```

### Ollama (Local)
```yaml
ai:
  provider: "ollama"
  model: "llama2"
```

## Troubleshooting

### Agent not starting
- Check config file syntax: `python3 -c "import yaml; yaml.safe_load(open('config.yaml'))"`
- Verify API key is set: `echo $ANTHROPIC_API_KEY`
- Check logs for errors

### Actions not executing
- Verify `auto_fix: true` in config
- Check that actions are in `allowed_actions` list
- Review cooldown settings
- Check sudo permissions

### No notifications
- Verify webhook URLs are correct
- Check `enabled: true` for notification channels
- Test webhooks manually with curl

## Security Considerations

1. **Limit allowed actions**: Only enable actions you're comfortable automating
2. **Use sudo restrictions**: Limit which commands can run via sudo
3. **Monitor the agent**: Review logs regularly
4. **API key security**: Store API keys in environment variables, not in config files
5. **Network security**: Run on trusted networks only

## Customization

### Adding Custom Monitors

Create a new monitor in `monitors/` directory:

```python
class CustomMonitor:
    def __init__(self, config):
        self.config = config

    def run_checks(self):
        return [
            {
                'metric': 'custom_check',
                'healthy': True,
                'message': 'All good'
            }
        ]
```

### Adding Custom Actions

Add to `remediation/actions.py`:

```python
def custom_action(self, params) -> Tuple[bool, str]:
    # Your custom remediation logic
    return True, "Action completed"
```

## Contributing

Feel free to customize and extend this agent for your specific needs!

## License

MIT License - feel free to use and modify as needed.
