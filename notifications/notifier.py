import logging
import requests
from typing import Dict, Any, List
import os
from datetime import datetime
import json


class Notifier:
    """Handle notifications via logging, Slack, and Discord"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Setup logging
        log_file = config.get('log_file', '/var/log/network-monitor-agent.log')
        log_level = config.get('log_level', 'INFO')

        # Create logger
        self.logger = logging.getLogger('NetworkMonitorAgent')
        self.logger.setLevel(getattr(logging, log_level))

        # File handler
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            )
            self.logger.addHandler(file_handler)
        except PermissionError:
            # Fallback to local log file
            fallback_log = os.path.expanduser('~/network-monitor-agent.log')
            file_handler = logging.FileHandler(fallback_log)
            file_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            )
            self.logger.addHandler(file_handler)
            print(f"Warning: Could not write to {log_file}, using {fallback_log}")

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        self.logger.addHandler(console_handler)

        # Slack config
        self.slack_enabled = config.get('slack', {}).get('enabled', False)
        self.slack_webhook = os.getenv('SLACK_WEBHOOK_URL') or config.get('slack', {}).get('webhook_url')

        # Discord config
        self.discord_config = config.get('discord', {})
        self.discord_enabled = self.discord_config.get('enabled', False)
        self.discord_webhook = os.getenv('DISCORD_WEBHOOK_URL') or self.discord_config.get('webhook_url')
        self.discord_notify_on = self.discord_config.get('notify_on', [])

    def log_info(self, message: str):
        """Log info message"""
        self.logger.info(message)

    def log_warning(self, message: str):
        """Log warning message"""
        self.logger.warning(message)

    def log_error(self, message: str):
        """Log error message"""
        self.logger.error(message)

    def _should_notify_discord(self, event_type: str, severity: str = None) -> bool:
        """Check if event should trigger Discord notification"""
        if not self.discord_enabled:
            return False

        if event_type == 'actions_taken' and 'actions_taken' in self.discord_notify_on:
            return True
        if event_type == 'critical_issues' and 'critical_issues' in self.discord_notify_on:
            return severity in ['critical', 'high']
        if event_type == 'daily_summary' and 'daily_summary' in self.discord_notify_on:
            return True

        return False

    def notify_issue_detected(self, issues: List[Dict[str, Any]]):
        """Notify about detected issues"""
        if not issues:
            return

        message = f"🚨 Detected {len(issues)} issue(s):\n"
        for issue in issues:
            message += f"  • {issue.get('message', 'Unknown issue')}\n"

        self.log_warning(message)

        # Send to Slack
        if len(issues) > 0:
            self._send_slack(message, color='warning')

        # Send to Discord only if we have critical/high severity issues
        critical_issues = [i for i in issues if i.get('severity') in ['critical', 'high']]
        if critical_issues and self._should_notify_discord('critical_issues', 'critical'):
            critical_message = f"🚨 Detected {len(critical_issues)} critical issue(s):\n"
            for issue in critical_issues:
                critical_message += f"  • {issue.get('message', 'Unknown issue')}\n"
            self._send_discord(critical_message, color='red')

    def notify_action_taken(self, action: Dict[str, Any], success: bool, result_message: str):
        """Notify about remediation action"""
        action_type = action.get('action', 'unknown')
        issue = action.get('issue', 'Unknown issue')
        severity = action.get('severity', 'unknown')

        if success:
            message = f"✅ Successfully executed {action_type}\n"
            message += f"  Issue: {issue}\n"
            message += f"  Result: {result_message}"
            self.log_info(message)
            self._send_slack(message, color='good')
            # Only send to Discord if actions_taken notifications are enabled
            if self._should_notify_discord('actions_taken'):
                self._send_discord(message, color='green')
        else:
            message = f"❌ Failed to execute {action_type}\n"
            message += f"  Issue: {issue}\n"
            message += f"  Severity: {severity}\n"
            message += f"  Error: {result_message}"
            self.log_error(message)
            self._send_slack(message, color='danger')
            self._send_discord(message, color='red')

    def notify_critical_issue(self, issue: Dict[str, Any]):
        """Notify about critical issue requiring human intervention"""
        message = f"🔴 CRITICAL ISSUE - Human intervention required\n"
        message += f"  Issue: {issue.get('issue', 'Unknown')}\n"
        message += f"  Root cause: {issue.get('root_cause', 'Unknown')}\n"
        message += f"  Reasoning: {issue.get('reasoning', 'N/A')}"

        self.log_error(message)
        self._send_slack(message, color='danger')
        self._send_discord(message, color='red')

    def notify_system_healthy(self):
        """Notify that all systems are healthy"""
        message = "✨ All systems healthy"
        self.log_info(message)

    def _send_slack(self, message: str, color: str = 'good'):
        """Send notification to Slack"""
        if not self.slack_enabled or not self.slack_webhook:
            return

        try:
            payload = {
                'attachments': [{
                    'color': color,
                    'text': message,
                    'footer': 'Network Monitor Agent',
                    'ts': int(datetime.now().timestamp())
                }]
            }

            response = requests.post(
                self.slack_webhook,
                json=payload,
                timeout=10
            )

            if response.status_code != 200:
                self.logger.error(f"Failed to send Slack notification: {response.status_code}")

        except Exception as e:
            self.logger.error(f"Error sending Slack notification: {e}")

    def _send_discord(self, message: str, color: str = 'green'):
        """Send notification to Discord"""
        if not self.discord_enabled or not self.discord_webhook:
            return

        try:
            # Discord color codes
            color_map = {
                'green': 0x00FF00,
                'orange': 0xFFA500,
                'red': 0xFF0000,
                'good': 0x00FF00,
                'warning': 0xFFA500,
                'danger': 0xFF0000
            }

            payload = {
                'embeds': [{
                    'description': message,
                    'color': color_map.get(color, 0x00FF00),
                    'footer': {
                        'text': 'Network Monitor Agent'
                    },
                    'timestamp': datetime.utcnow().isoformat()
                }]
            }

            response = requests.post(
                self.discord_webhook,
                json=payload,
                timeout=10
            )

            if response.status_code not in [200, 204]:
                self.logger.error(f"Failed to send Discord notification: {response.status_code}")

        except Exception as e:
            self.logger.error(f"Error sending Discord notification: {e}")

    def notify_startup(self):
        """Notify that the agent has started"""
        message = "🤖 Network Monitor Agent started"
        self.log_info(message)
        self._send_slack(message, color='good')
        self._send_discord(message, color='green')

    def notify_shutdown(self):
        """Notify that the agent is shutting down"""
        message = "🛑 Network Monitor Agent shutting down"
        self.log_info(message)
        self._send_slack(message, color='warning')
        self._send_discord(message, color='orange')

    def notify_daily_summary(self, summary_data: Dict[str, Any]):
        """Send daily health summary"""
        if not self._should_notify_discord('daily_summary'):
            return

        total_checks = summary_data.get('total_checks', 0)
        issues_found = summary_data.get('issues_found', 0)
        actions_taken = summary_data.get('actions_taken', 0)
        systems_healthy = summary_data.get('systems_healthy', 0)
        systems_total = summary_data.get('systems_total', 0)

        message = "📊 **Daily Homelab Health Summary**\n\n"
        message += f"**Monitoring Cycles**: {total_checks}\n"
        message += f"**Issues Detected**: {issues_found}\n"
        message += f"**Actions Taken**: {actions_taken}\n"
        message += f"**System Health**: {systems_healthy}/{systems_total} healthy\n\n"

        if issues_found == 0:
            message += "✅ No issues detected today!"
            color = 'green'
        elif actions_taken > 0:
            message += f"🔧 {actions_taken} issue(s) automatically resolved"
            color = 'green'
        else:
            message += "⚠️ Some issues require attention"
            color = 'orange'

        self.log_info("Sending daily summary")
        self._send_discord(message, color=color)
