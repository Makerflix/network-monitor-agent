import subprocess
import re
from typing import Dict, List, Any


class NetworkMonitor:
    """Monitors network connectivity and performance"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.hosts = config.get('hosts_to_ping', ['8.8.8.8'])
        self.packet_loss_threshold = config.get('packet_loss_threshold', 10)
        self.latency_threshold = config.get('latency_threshold', 200)
        self.ignore_interfaces = config.get('ignore_interfaces', [])

    def ping_host(self, host: str, count: int = 4) -> Dict[str, Any]:
        """Ping a host and return statistics"""
        try:
            result = subprocess.run(
                ['ping', '-c', str(count), '-W', '2', host],
                capture_output=True,
                text=True,
                timeout=10
            )

            # Parse ping output
            output = result.stdout

            # Extract packet loss
            packet_loss_match = re.search(r'(\d+)% packet loss', output)
            packet_loss = int(packet_loss_match.group(1)) if packet_loss_match else 100

            # Extract average latency
            latency_match = re.search(r'rtt min/avg/max/mdev = [\d.]+/([\d.]+)/', output)
            avg_latency = float(latency_match.group(1)) if latency_match else None

            is_healthy = (
                packet_loss < self.packet_loss_threshold and
                (avg_latency is None or avg_latency < self.latency_threshold)
            )

            return {
                'metric': 'network_ping',
                'host': host,
                'packet_loss': packet_loss,
                'avg_latency': avg_latency,
                'healthy': is_healthy,
                'message': f'Ping to {host}: {packet_loss}% loss, {avg_latency}ms avg' if avg_latency else f'Ping to {host}: {packet_loss}% loss'
            }

        except subprocess.TimeoutExpired:
            return {
                'metric': 'network_ping',
                'host': host,
                'healthy': False,
                'error': 'timeout',
                'message': f'Ping to {host} timed out'
            }
        except Exception as e:
            return {
                'metric': 'network_ping',
                'host': host,
                'healthy': False,
                'error': str(e),
                'message': f'Failed to ping {host}: {e}'
            }

    def check_interface_status(self) -> List[Dict[str, Any]]:
        """Check network interface status"""
        results = []
        try:
            result = subprocess.run(
                ['ip', 'link', 'show'],
                capture_output=True,
                text=True,
                timeout=5
            )

            # Parse interface status
            interfaces = re.findall(r'\d+: ([^:]+):.*state (\w+)', result.stdout)

            for interface, state in interfaces:
                # Skip loopback and ignored interfaces
                if interface.startswith('lo') or interface in self.ignore_interfaces:
                    continue

                is_up = state == 'UP'
                results.append({
                    'metric': 'interface_status',
                    'interface': interface,
                    'state': state,
                    'healthy': is_up,
                    'message': f'Interface {interface} is {state}'
                })

        except Exception as e:
            results.append({
                'metric': 'interface_status',
                'healthy': False,
                'error': str(e),
                'message': f'Failed to check interfaces: {e}'
            })

        return results

    def run_checks(self) -> List[Dict[str, Any]]:
        """Run all network checks"""
        results = []

        # Ping checks
        for host in self.hosts:
            results.append(self.ping_host(host))

        # Interface checks
        results.extend(self.check_interface_status())

        return results
