import docker
import subprocess
from typing import Dict, List, Any


class DockerRemoteMonitor:
    """Monitor Docker containers on local and remote hosts"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.hosts = config.get('hosts', [])

    def _ssh_docker_command(self, host: str, user: str, command: str) -> tuple:
        """Execute docker command on remote server via SSH"""
        try:
            full_cmd = f'ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no {user}@{host} "docker {command}"'
            result = subprocess.run(
                full_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=15
            )
            return result.returncode == 0, result.stdout, result.stderr
        except Exception as e:
            return False, "", str(e)

    def check_local_docker(self) -> List[Dict[str, Any]]:
        """Check local Docker containers"""
        results = []

        try:
            client = docker.from_env()
            containers = client.containers.list(all=True)

            for container in containers:
                name = container.name
                status = container.status
                health = None

                # Check health if available
                if container.attrs.get('State', {}).get('Health'):
                    health = container.attrs['State']['Health']['Status']

                is_healthy = status == 'running'
                if health:
                    is_healthy = is_healthy and health == 'healthy'

                results.append({
                    'metric': 'docker_container',
                    'host': 'local',
                    'container': name,
                    'status': status,
                    'health': health,
                    'healthy': is_healthy,
                    'message': f'{name}: {status}' + (f' ({health})' if health else '')
                })

        except Exception as e:
            results.append({
                'metric': 'docker_container',
                'host': 'local',
                'healthy': False,
                'error': str(e),
                'message': f'Failed to check local Docker: {str(e)}'
            })

        return results

    def check_remote_docker(self, host_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check Docker containers on a remote host"""
        results = []
        host = host_config.get('host')
        user = host_config.get('user', 'root')
        name = host_config.get('name', host)

        # Get container list
        success, stdout, stderr = self._ssh_docker_command(
            host, user,
            "ps -a --format '{{.Names}}|{{.Status}}|{{.State}}'"
        )

        if not success:
            results.append({
                'metric': 'docker_remote',
                'host': name,
                'healthy': False,
                'error': stderr,
                'message': f'Failed to check Docker on {name}: {stderr}'
            })
            return results

        # Parse container info
        for line in stdout.strip().split('\n'):
            if not line:
                continue

            parts = line.split('|')
            if len(parts) >= 3:
                container_name = parts[0]
                status_text = parts[1]
                state = parts[2]

                is_healthy = state == 'running'

                results.append({
                    'metric': 'docker_container',
                    'host': name,
                    'container': container_name,
                    'status': state,
                    'status_text': status_text,
                    'healthy': is_healthy,
                    'message': f'{name}/{container_name}: {state}'
                })

        return results

    def run_checks(self) -> List[Dict[str, Any]]:
        """Run all Docker checks"""
        results = []

        # Check local Docker
        results.extend(self.check_local_docker())

        # Check remote Docker hosts
        for host_config in self.hosts:
            results.extend(self.check_remote_docker(host_config))

        return results
