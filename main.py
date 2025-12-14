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
import asyncio

from monitors import (
    SystemMonitor, NetworkMonitor, WebMonitor,
    RemoteServerMonitor, ProxmoxMonitor, DockerRemoteMonitor,
    HomeAssistantMonitor
)
from ai import DecisionEngine
from remediation import RemediationActions
from notifications import Notifier
from discord_bot import HomelabBot, AgentController


def load_env_file(env_path: str = '.env'):
    """Load environment variables from .env file"""
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()


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

        if monitoring_config.get('home_assistant', {}).get('enabled', False):
            self.monitors.append(HomeAssistantMonitor(monitoring_config.get('home_assistant', {})))

        # Log enabled monitors
        monitor_names = [m.__class__.__name__ for m in self.monitors]
        self.notifier.log_info(f"Enabled monitors: {', '.join(monitor_names)}")

        # Initialize AI decision engine
        self.decision_engine = DecisionEngine(self.config.get('ai', {}))

        # Initialize remediation
        remediation_config = self.config.get('remediation', {})
        self.remediation = RemediationActions(remediation_config)

        # Daily summary tracking
        from datetime import datetime
        self.last_summary = datetime.now()
        self.daily_stats = {
            'total_checks': 0,
            'issues_found': 0,
            'actions_taken': 0,
            'systems_healthy': 0,
            'systems_total': 0
        }
        self.auto_fix = remediation_config.get('auto_fix', True)
        self.allowed_actions = remediation_config.get('allowed_actions', [])

        # Monitoring interval
        self.interval = monitoring_config.get('interval', 60)

        # Running flag
        self.running = False

        # Initialize Discord bot if enabled
        bot_config = self.config.get('discord_bot', {})
        self.bot_enabled = bot_config.get('enabled', False)
        self.discord_bot = None

        if self.bot_enabled:
            bot_token = os.getenv('DISCORD_BOT_TOKEN')
            if bot_token:
                self.agent_controller = AgentController(self)
                self.discord_bot = HomelabBot(
                    self.agent_controller,
                    command_prefix=bot_config.get('prefix', '!')
                )
                self.notifier.log_info("Discord bot initialized")
            else:
                self.notifier.log_warning("Discord bot enabled but DISCORD_BOT_TOKEN not found")
                self.bot_enabled = False

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

        # Track daily stats
        self.daily_stats['total_checks'] += 1

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

        # Track systems health
        self.daily_stats['systems_total'] = len(all_results)
        self.daily_stats['systems_healthy'] = len([r for r in all_results if r.get('healthy', True)])

        if not issues:
            self.notifier.notify_system_healthy()
            return

        # Track issues found
        self.daily_stats['issues_found'] += len(issues)

        # Report issues
        self.notifier.notify_issue_detected(issues)

        # Analyze with AI and get recommended actions
        try:
            actions = self.decision_engine.analyze_issues(all_results, self.allowed_actions)

            if not actions:
                self.notifier.log_warning("No actions recommended by AI")
                # Add to bot history even with no actions
                if self.bot_enabled and hasattr(self, 'agent_controller'):
                    self.agent_controller.add_to_history(issues, [])
                return

            # Execute actions
            executed_actions = []
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

                # Track successful actions
                if success:
                    self.daily_stats['actions_taken'] += 1
                    executed_actions.append(action)

            # Add to bot history
            if self.bot_enabled and hasattr(self, 'agent_controller'):
                self.agent_controller.add_to_history(issues, executed_actions)

        except Exception as e:
            self.notifier.log_error(f"AI analysis failed: {e}")
            # Add to bot history even on error
            if self.bot_enabled and hasattr(self, 'agent_controller'):
                self.agent_controller.add_to_history(issues, [])
            # Continue without AI - issues have been logged

    async def _monitoring_loop(self):
        """Async monitoring loop that runs monitoring cycles"""
        from datetime import datetime
        self.notifier.log_info(f"Network Monitor Agent running (interval: {self.interval}s)")

        try:
            while self.running:
                try:
                    # Run monitoring cycle in thread pool to avoid blocking
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, self.run_monitoring_cycle)
                except Exception as e:
                    self.notifier.log_error(f"Error in monitoring cycle: {e}")

                # Check if 24 hours passed for daily summary
                time_since_summary = (datetime.now() - self.last_summary).total_seconds()
                if time_since_summary >= 86400:  # 24 hours
                    self.notifier.notify_daily_summary(self.daily_stats)
                    self.last_summary = datetime.now()
                    # Reset daily stats
                    self.daily_stats = {
                        'total_checks': 0,
                        'issues_found': 0,
                        'actions_taken': 0,
                        'systems_healthy': 0,
                        'systems_total': 0
                    }

                # Wait for next cycle
                if self.running:
                    await asyncio.sleep(self.interval)

        except asyncio.CancelledError:
            pass

    async def _start_discord_bot(self):
        """Start Discord bot with error handling"""
        try:
            bot_token = os.getenv('DISCORD_BOT_TOKEN')
            self.notifier.log_info("Starting Discord bot connection...")
            await self.discord_bot.start(bot_token)
        except Exception as e:
            self.notifier.log_error(f"Discord bot failed to start: {e}")
            import traceback
            self.notifier.log_error(traceback.format_exc())

    async def run_async(self):
        """Main async agent loop with Discord bot support"""
        self.running = True

        try:
            tasks = []

            # Start monitoring loop
            tasks.append(asyncio.create_task(self._monitoring_loop()))

            # Start Discord bot if enabled
            if self.bot_enabled and self.discord_bot:
                tasks.append(asyncio.create_task(self._start_discord_bot()))

            # Wait for all tasks
            await asyncio.gather(*tasks, return_exceptions=True)

        except KeyboardInterrupt:
            pass
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.notifier.log_error(f"Error in async loop: {e}")
        finally:
            # Clean shutdown
            self.running = False

            # Stop Discord bot
            if self.bot_enabled and self.discord_bot:
                try:
                    await self.discord_bot.close()
                except:
                    pass

            self.notifier.notify_shutdown()
            self.notifier.log_info("Agent stopped")

    def run(self):
        """Main agent loop (sync wrapper for async)"""
        if self.bot_enabled:
            # Run async event loop for bot support
            try:
                asyncio.run(self.run_async())
            except KeyboardInterrupt:
                pass
        else:
            # Run synchronous mode if no bot
            from datetime import datetime
            self.running = True
            self.notifier.log_info(f"Network Monitor Agent running (interval: {self.interval}s)")

            try:
                while self.running:
                    try:
                        self.run_monitoring_cycle()
                    except Exception as e:
                        self.notifier.log_error(f"Error in monitoring cycle: {e}")

                    # Check if 24 hours passed for daily summary
                    time_since_summary = (datetime.now() - self.last_summary).total_seconds()
                    if time_since_summary >= 86400:  # 24 hours
                        self.notifier.notify_daily_summary(self.daily_stats)
                        self.last_summary = datetime.now()
                        # Reset daily stats
                        self.daily_stats = {
                            'total_checks': 0,
                            'issues_found': 0,
                            'actions_taken': 0,
                            'systems_healthy': 0,
                            'systems_total': 0
                        }

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

    # Load environment variables from .env file
    load_env_file()

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
