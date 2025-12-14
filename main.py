#!/usr/bin/env python3
"""
Network Monitor Agent - AI-powered system monitoring and remediation
"""

import yaml
import time
import signal
import sys
from typing import Dict, Any
import os

from monitors import (
    SystemMonitor, NetworkMonitor, WebMonitor,
    RemoteServerMonitor, ProxmoxMonitor, DockerRemoteMonitor
)
from ai import DecisionEngine
from remediation import RemediationActions
from notifications import Notifier


class NetworkMonitorAgent:
    """Main agent orchestrator"""

    def __init__(self, config_path: str = 'config.yaml'):
        # Load configuration
        self.config = self._load_config(config_path)

        # Initialize components
        self.notifier = Notifier(self.config.get('notifications', {}))
        self.notifier.notify_startup()

        # Initialize monitors
        monitoring_config = self.config.get('monitoring', {})
        self.monitors = []

        if monitoring_config.get('system', {}).get('enabled', True):
            self.monitors.append(SystemMonitor(monitoring_config.get('system', {})))

        if monitoring_config.get('network', {}).get('enabled', True):
            self.monitors.append(NetworkMonitor(monitoring_config.get('network', {})))

        if monitoring_config.get('web_services', {}).get('enabled', True):
            self.monitors.append(WebMonitor(monitoring_config.get('web_services', {})))

        if monitoring_config.get('remote_servers', {}).get('enabled', False):
            self.monitors.append(RemoteServerMonitor(monitoring_config.get('remote_servers', {})))

        if monitoring_config.get('proxmox', {}).get('enabled', False):
            self.monitors.append(ProxmoxMonitor(monitoring_config.get('proxmox', {})))

        if monitoring_config.get('docker_remote', {}).get('enabled', False):
            self.monitors.append(DockerRemoteMonitor(monitoring_config.get('docker_remote', {})))

        # Log enabled monitors
        monitor_names = [m.__class__.__name__ for m in self.monitors]
        self.notifier.log_info(f"Enabled monitors: {', '.join(monitor_names)}")

        # Initialize AI decision engine
        self.decision_engine = DecisionEngine(self.config.get('ai', {}))

        # Initialize remediation
        remediation_config = self.config.get('remediation', {})
        self.remediation = RemediationActions(remediation_config)
        self.auto_fix = remediation_config.get('auto_fix', True)
        self.allowed_actions = remediation_config.get('allowed_actions', [])

        # Monitoring interval
        self.interval = monitoring_config.get('interval', 60)

        # Running flag
        self.running = False

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

            # Expand environment variables
            config = self._expand_env_vars(config)
            return config

        except FileNotFoundError:
            print(f"Error: Config file {config_path} not found")
            sys.exit(1)
        except yaml.YAMLError as e:
            print(f"Error parsing config file: {e}")
            sys.exit(1)

    def _expand_env_vars(self, obj):
        """Recursively expand environment variables in config"""
        if isinstance(obj, dict):
            return {k: self._expand_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._expand_env_vars(item) for item in obj]
        elif isinstance(obj, str) and obj.startswith('${') and obj.endswith('}'):
            env_var = obj[2:-1]
            return os.getenv(env_var, obj)
        else:
            return obj

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.notifier.log_info(f"Received signal {signum}, shutting down...")
        self.running = False

    def run_monitoring_cycle(self):
        """Run one complete monitoring cycle"""
        self.notifier.log_info("=" * 60)
        self.notifier.log_info("Starting monitoring cycle")

        # Collect all monitoring results
        all_results = []

        for monitor in self.monitors:
            try:
                results = monitor.run_checks()
                all_results.extend(results)
            except Exception as e:
                self.notifier.log_error(f"Monitor {monitor.__class__.__name__} failed: {e}")

        # Filter unhealthy results
        issues = [r for r in all_results if not r.get('healthy', True)]

        if not issues:
            self.notifier.notify_system_healthy()
            return

        # Report issues
        self.notifier.notify_issue_detected(issues)

        # Analyze with AI and get recommended actions
        try:
            actions = self.decision_engine.analyze_issues(all_results, self.allowed_actions)

            if not actions:
                self.notifier.log_warning("No actions recommended by AI")
                return

            # Execute actions
            for action in actions:
                severity = action.get('severity', 'unknown')
                action_type = action.get('action', 'unknown')

                self.notifier.log_info(f"AI Recommendation: {action_type} (severity: {severity})")
                self.notifier.log_info(f"  Reasoning: {action.get('reasoning', 'N/A')}")

                # Check if we should execute automatically
                if action_type == 'alert_only' or not self.auto_fix:
                    self.notifier.notify_critical_issue(action)
                    continue

                # Execute the action
                success, result_message = self.remediation.execute_action(action)
                self.notifier.notify_action_taken(action, success, result_message)

        except Exception as e:
            self.notifier.log_error(f"AI analysis failed: {e}")
            # Continue without AI - issues have been logged

    def run(self):
        """Main agent loop"""
        self.running = True
        self.notifier.log_info(f"Network Monitor Agent running (interval: {self.interval}s)")

        try:
            while self.running:
                try:
                    self.run_monitoring_cycle()
                except Exception as e:
                    self.notifier.log_error(f"Error in monitoring cycle: {e}")

                # Wait for next cycle
                if self.running:
                    time.sleep(self.interval)

        except KeyboardInterrupt:
            pass
        finally:
            self.notifier.notify_shutdown()
            self.notifier.log_info("Agent stopped")


def main():
    """Entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Network Monitor Agent')
    parser.add_argument(
        '-c', '--config',
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Run a single monitoring cycle and exit'
    )

    args = parser.parse_args()

    # Create agent
    agent = NetworkMonitorAgent(args.config)

    if args.test:
        # Test mode - run once
        agent.run_monitoring_cycle()
    else:
        # Normal mode - run continuously
        agent.run()


if __name__ == '__main__':
    main()
