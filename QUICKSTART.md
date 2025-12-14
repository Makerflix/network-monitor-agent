# Quick Start Guide

Get your Network Monitor Agent up and running in 5 minutes!

## Step 1: Install Dependencies

```bash
cd /home/aa-ai/network-monitor-agent
./setup.sh
```

Or manually:
```bash
pip3 install -r requirements.txt
```

## Step 2: Configure API Key

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

To make it permanent, add to your `~/.bashrc`:
```bash
echo 'export ANTHROPIC_API_KEY="your-key"' >> ~/.bashrc
source ~/.bashrc
```

## Step 3: Customize Configuration (Optional)

Edit `config.yaml` to:
- Add your web services/APIs to monitor
- Adjust monitoring thresholds
- Configure Slack/Discord webhooks
- Enable/disable specific monitors

## Step 4: Run a Test

```bash
python3 main.py --test
```

This runs a single monitoring cycle to verify everything works.

## Step 5: Run Continuously

```bash
# Foreground (see output)
python3 main.py

# Background
nohup python3 main.py >> agent.log 2>&1 &

# As systemd service (recommended for production)
sudo cp network-monitor-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable network-monitor-agent
sudo systemctl start network-monitor-agent
sudo systemctl status network-monitor-agent
```

## What Happens Next?

The agent will:
1. Monitor your system every 60 seconds (configurable)
2. Check CPU, memory, disk, services, network, and web endpoints
3. Use AI to analyze any issues it finds
4. Automatically fix common problems
5. Send notifications to Slack/Discord and log files

## View Logs

```bash
# Live logs
tail -f ~/network-monitor-agent.log

# Or if using systemd
sudo journalctl -u network-monitor-agent -f
```

## Common Issues

**Can't write to /var/log**
- The agent will automatically fallback to `~/network-monitor-agent.log`

**Permission denied on sudo commands**
- Some actions require sudo. See README.md for setup

**API key not found**
- Make sure to export ANTHROPIC_API_KEY before running

## Next Steps

- Customize monitoring thresholds in `config.yaml`
- Add your web services to monitor
- Set up Slack/Discord notifications
- Configure as a systemd service for auto-start
- Review logs regularly

For detailed documentation, see README.md
