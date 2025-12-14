import subprocess
import json
from typing import Dict, List, Any


class RemoteServerMonitor:
    """Monitor remote servers via SSH"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.servers = config.get('servers', [])

    def _ssh_command(self, host: str, user: str, command: str, timeout: int = 10) -> tuple:
        """Execute command on remote server via SSH"""
        try:
            result = subprocess.run(
                ['ssh', '-o', 'ConnectTimeout=5', '-o', 'StrictHostKeyChecking=no',
                 f'{user}@{host}', command],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "SSH command timed out"
        except Exception as e:
            return False, "", str(e)

    def check_server(self, server_config: Dict[str, Any]) -> Dict[str, Any]:
        """Check health of a remote server"""
        host = server_config.get('host')
        user = server_config.get('user', 'root')
        name = server_config.get('name', host)

        # Basic connectivity check
        ping_result = subprocess.run(
            ['ping', '-c', '2', '-W', '2', host],
            capture_output=True,
            timeout=5
        )

        if ping_result.returncode != 0:
            return {
                'metric': 'remote_server',
                'server': name,
                'host': host,
                'healthy': False,
                'issue': 'unreachable',
                'message': f'Server {name} ({host}) is unreachable'
            }

        # SSH connectivity check
        success, stdout, stderr = self._ssh_command(host, user, 'echo "OK"')

        if not success:
            return {
                'metric': 'remote_server',
                'server': name,
                'host': host,
                'healthy': False,
                'issue': 'ssh_failed',
                'message': f'SSH to {name} failed: {stderr}'
            }

        # Get system stats
        stats_cmd = """
        echo '{'
        echo '"uptime":'$(cat /proc/uptime | awk '{print int($1)}')','
        echo '"load":'$(cat /proc/loadavg | awk '{print $1}')','
        echo '"cpu_count":'$(nproc)','
        echo '"mem_total":'$(free -b | awk '/^Mem:/ {print $2}')','
        echo '"mem_used":'$(free -b | awk '/^Mem:/ {print $3}')','
        echo '"disk_root":'$(df -B1 / | awk 'NR==2 {print int($3/$2*100)}')
        echo '}'
        """

        success, stats_json, stderr = self._ssh_command(host, user, stats_cmd)

        if success:
            try:
                stats = json.loads(stats_json)
                mem_percent = (stats['mem_used'] / stats['mem_total']) * 100
                cpu_load = float(stats['load'])
                cpu_count = int(stats['cpu_count'])
                load_percent = (cpu_load / cpu_count) * 100

                issues = []
                if load_percent > 80:
                    issues.append(f"High CPU load: {load_percent:.1f}%")
                if mem_percent > 85:
                    issues.append(f"High memory: {mem_percent:.1f}%")
                if stats['disk_root'] > 90:
                    issues.append(f"High disk usage: {stats['disk_root']}%")

                return {
                    'metric': 'remote_server',
                    'server': name,
                    'host': host,
                    'healthy': len(issues) == 0,
                    'uptime': stats['uptime'],
                    'load_percent': load_percent,
                    'mem_percent': mem_percent,
                    'disk_percent': stats['disk_root'],
                    'issues': issues,
                    'message': f"{name}: " + (", ".join(issues) if issues else "Healthy")
                }
            except:
                pass

        return {
            'metric': 'remote_server',
            'server': name,
            'host': host,
            'healthy': True,
            'message': f'Server {name} is reachable'
        }

    def run_checks(self) -> List[Dict[str, Any]]:
        """Run all remote server checks"""
        results = []

        for server in self.servers:
            results.append(self.check_server(server))

        return results
