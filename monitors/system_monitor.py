import psutil
import subprocess
import os
from typing import Dict, List, Any


class SystemMonitor:
    """Monitors Linux system resources and services"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.cpu_threshold = config.get('cpu_threshold', 80)
        self.memory_threshold = config.get('memory_threshold', 85)
        self.disk_threshold = config.get('disk_threshold', 90)
        self.services_to_check = config.get('check_services', [])
        self.mounts_to_check = config.get('check_mounts', [])

    def check_cpu(self) -> Dict[str, Any]:
        """Check CPU usage"""
        cpu_percent = psutil.cpu_percent(interval=1)
        return {
            'metric': 'cpu_usage',
            'value': cpu_percent,
            'threshold': self.cpu_threshold,
            'healthy': cpu_percent < self.cpu_threshold,
            'message': f'CPU usage at {cpu_percent}%'
        }

    def check_memory(self) -> Dict[str, Any]:
        """Check memory usage"""
        memory = psutil.virtual_memory()
        return {
            'metric': 'memory_usage',
            'value': memory.percent,
            'threshold': self.memory_threshold,
            'healthy': memory.percent < self.memory_threshold,
            'message': f'Memory usage at {memory.percent}% ({memory.used // (1024**3)}GB / {memory.total // (1024**3)}GB)'
        }

    def check_disk(self) -> List[Dict[str, Any]]:
        """Check disk usage for all partitions"""
        issues = []
        for partition in psutil.disk_partitions():
            # Skip snap partitions (read-only squashfs, always 100%)
            if partition.mountpoint.startswith('/snap/'):
                continue

            try:
                usage = psutil.disk_usage(partition.mountpoint)
                is_healthy = usage.percent < self.disk_threshold
                if not is_healthy or partition.mountpoint == '/':  # Always report root
                    issues.append({
                        'metric': 'disk_usage',
                        'partition': partition.mountpoint,
                        'value': usage.percent,
                        'threshold': self.disk_threshold,
                        'healthy': is_healthy,
                        'message': f'Disk {partition.mountpoint} at {usage.percent}% ({usage.used // (1024**3)}GB / {usage.total // (1024**3)}GB)'
                    })
            except PermissionError:
                continue
        return issues

    def check_service(self, service_name: str) -> Dict[str, Any]:
        """Check if a systemd service is running"""
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', service_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            is_active = result.stdout.strip() == 'active'
            return {
                'metric': 'service_status',
                'service': service_name,
                'healthy': is_active,
                'status': result.stdout.strip(),
                'message': f'Service {service_name} is {result.stdout.strip()}'
            }
        except Exception as e:
            return {
                'metric': 'service_status',
                'service': service_name,
                'healthy': False,
                'error': str(e),
                'message': f'Failed to check service {service_name}: {e}'
            }

    def check_processes(self) -> Dict[str, Any]:
        """Check for problematic processes"""
        issues = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                if proc.info['cpu_percent'] > 90:
                    issues.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cpu': proc.info['cpu_percent'],
                        'issue': 'high_cpu'
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return {
            'metric': 'processes',
            'healthy': len(issues) == 0,
            'issues': issues,
            'message': f'Found {len(issues)} problematic processes'
        }

    def check_mount(self, mount_config: Dict[str, Any]) -> Dict[str, Any]:
        """Check if a mount point is accessible"""
        mount_point = mount_config.get('path')
        mount_type = mount_config.get('type', 'unknown')

        if not mount_point:
            return {
                'metric': 'mount_status',
                'healthy': False,
                'error': 'No mount path specified',
                'message': 'Invalid mount configuration'
            }

        try:
            # Check if mount point exists
            if not os.path.exists(mount_point):
                return {
                    'metric': 'mount_status',
                    'mount': mount_point,
                    'type': mount_type,
                    'healthy': False,
                    'issue': 'mount_point_missing',
                    'message': f'Mount point {mount_point} does not exist',
                    'config': mount_config
                }

            # Check if it's actually mounted
            result = subprocess.run(
                ['mountpoint', '-q', mount_point],
                capture_output=True,
                timeout=5
            )

            is_mounted = result.returncode == 0

            if not is_mounted:
                return {
                    'metric': 'mount_status',
                    'mount': mount_point,
                    'type': mount_type,
                    'healthy': False,
                    'issue': 'not_mounted',
                    'message': f'Mount {mount_point} ({mount_type}) is not mounted',
                    'config': mount_config
                }

            # Check if mount is accessible (can read)
            try:
                os.listdir(mount_point)
                return {
                    'metric': 'mount_status',
                    'mount': mount_point,
                    'type': mount_type,
                    'healthy': True,
                    'message': f'Mount {mount_point} is accessible'
                }
            except PermissionError:
                return {
                    'metric': 'mount_status',
                    'mount': mount_point,
                    'type': mount_type,
                    'healthy': False,
                    'issue': 'permission_denied',
                    'message': f'Mount {mount_point} exists but is not accessible (permission denied)',
                    'config': mount_config
                }
            except OSError as e:
                return {
                    'metric': 'mount_status',
                    'mount': mount_point,
                    'type': mount_type,
                    'healthy': False,
                    'issue': 'stale_mount',
                    'message': f'Mount {mount_point} appears stale or disconnected: {str(e)}',
                    'config': mount_config
                }

        except subprocess.TimeoutExpired:
            return {
                'metric': 'mount_status',
                'mount': mount_point,
                'type': mount_type,
                'healthy': False,
                'issue': 'timeout',
                'message': f'Timeout checking mount {mount_point} (may be hung)',
                'config': mount_config
            }
        except Exception as e:
            return {
                'metric': 'mount_status',
                'mount': mount_point,
                'type': mount_type,
                'healthy': False,
                'error': str(e),
                'message': f'Error checking mount {mount_point}: {str(e)}',
                'config': mount_config
            }

    def run_checks(self) -> List[Dict[str, Any]]:
        """Run all system checks"""
        results = []

        # CPU check
        results.append(self.check_cpu())

        # Memory check
        results.append(self.check_memory())

        # Disk checks
        results.extend(self.check_disk())

        # Service checks
        for service in self.services_to_check:
            results.append(self.check_service(service))

        # Mount checks
        for mount in self.mounts_to_check:
            results.append(self.check_mount(mount))

        # Process check
        results.append(self.check_processes())

        return results
