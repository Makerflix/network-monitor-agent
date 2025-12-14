import subprocess
import os
import shutil
import requests
from typing import Dict, Any, Tuple
import time


class RemediationActions:
    """Execute remediation actions to fix issues"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_attempts = config.get('max_attempts', 3)
        self.cooldown = config.get('cooldown', 300)
        self.attempt_history = {}  # Track attempts per action

    def execute_action(self, action: Dict[str, Any]) -> Tuple[bool, str]:
        """Execute a remediation action"""
        action_type = action.get('action')
        params = action.get('action_params', {})

        # Check cooldown
        if not self._check_cooldown(action_type, params):
            return False, f"Action {action_type} in cooldown period"

        # Record attempt
        self._record_attempt(action_type, params)

        # Execute the appropriate action
        if action_type == 'restart_service':
            return self.restart_service(params.get('service'))

        elif action_type == 'clear_cache':
            return self.clear_cache(params.get('type', 'system'))

        elif action_type == 'kill_hung_process':
            return self.kill_process(params.get('pid'))

        elif action_type == 'restart_container':
            return self.restart_container(params.get('container'))

        elif action_type == 'clear_disk_space':
            return self.clear_disk_space(params.get('partition'))

        elif action_type == 'remount':
            return self.remount(params.get('mount_config'))

        elif action_type == 'unmount_remount':
            return self.unmount_remount(params.get('mount_config'))

        elif action_type == 'enable_automation':
            return self.enable_automation(params)

        elif action_type == 'reload_integration':
            return self.reload_integration(params)

        elif action_type == 'alert_only':
            return True, "Alert only - no action taken"

        else:
            return False, f"Unknown action type: {action_type}"

    def restart_service(self, service_name: str) -> Tuple[bool, str]:
        """Restart a systemd service"""
        if not service_name:
            return False, "No service name provided"

        try:
            # Check if service exists
            check_result = subprocess.run(
                ['systemctl', 'list-unit-files', f'{service_name}.service'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if service_name not in check_result.stdout:
                return False, f"Service {service_name} not found"

            # Restart the service
            result = subprocess.run(
                ['sudo', 'systemctl', 'restart', service_name],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                # Verify it's running
                time.sleep(2)
                verify = subprocess.run(
                    ['systemctl', 'is-active', service_name],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if verify.stdout.strip() == 'active':
                    return True, f"Successfully restarted {service_name}"
                else:
                    return False, f"Service {service_name} restarted but not active"
            else:
                return False, f"Failed to restart {service_name}: {result.stderr}"

        except subprocess.TimeoutExpired:
            return False, f"Timeout while restarting {service_name}"
        except Exception as e:
            return False, f"Error restarting {service_name}: {str(e)}"

    def clear_cache(self, cache_type: str = 'system') -> Tuple[bool, str]:
        """Clear system caches"""
        try:
            if cache_type == 'system':
                # Clear PageCache, dentries and inodes
                result = subprocess.run(
                    ['sudo', 'sh', '-c', 'sync; echo 3 > /proc/sys/vm/drop_caches'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode == 0:
                    return True, "System cache cleared successfully"
                else:
                    return False, f"Failed to clear cache: {result.stderr}"

            else:
                return False, f"Unknown cache type: {cache_type}"

        except Exception as e:
            return False, f"Error clearing cache: {str(e)}"

    def kill_process(self, pid: int) -> Tuple[bool, str]:
        """Kill a hung process"""
        if not pid:
            return False, "No PID provided"

        try:
            # Check if process exists
            check_result = subprocess.run(
                ['ps', '-p', str(pid)],
                capture_output=True,
                text=True,
                timeout=5
            )

            if check_result.returncode != 0:
                return False, f"Process {pid} not found"

            # Try graceful termination first
            result = subprocess.run(
                ['kill', str(pid)],
                capture_output=True,
                text=True,
                timeout=5
            )

            time.sleep(2)

            # Check if process is still running
            check_again = subprocess.run(
                ['ps', '-p', str(pid)],
                capture_output=True,
                text=True,
                timeout=5
            )

            if check_again.returncode != 0:
                return True, f"Successfully terminated process {pid}"

            # Force kill if still running
            force_result = subprocess.run(
                ['kill', '-9', str(pid)],
                capture_output=True,
                text=True,
                timeout=5
            )

            if force_result.returncode == 0:
                return True, f"Force killed process {pid}"
            else:
                return False, f"Failed to kill process {pid}"

        except Exception as e:
            return False, f"Error killing process {pid}: {str(e)}"

    def restart_container(self, container_name: str) -> Tuple[bool, str]:
        """Restart a Docker container"""
        if not container_name:
            return False, "No container name provided"

        try:
            # Check if Docker is available
            docker_check = subprocess.run(
                ['which', 'docker'],
                capture_output=True,
                timeout=5
            )

            if docker_check.returncode != 0:
                return False, "Docker not found on system"

            # Restart the container
            result = subprocess.run(
                ['docker', 'restart', container_name],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                return True, f"Successfully restarted container {container_name}"
            else:
                return False, f"Failed to restart container: {result.stderr}"

        except subprocess.TimeoutExpired:
            return False, f"Timeout while restarting container {container_name}"
        except Exception as e:
            return False, f"Error restarting container: {str(e)}"

    def clear_disk_space(self, partition: str = '/') -> Tuple[bool, str]:
        """Clear disk space by removing temporary files and old logs"""
        if not partition:
            partition = '/'

        try:
            freed_space = 0

            # Clear /tmp if it's on the same partition
            if partition == '/' or partition.startswith('/tmp'):
                tmp_files = ['/tmp/*', '/var/tmp/*']
                for pattern in tmp_files:
                    try:
                        result = subprocess.run(
                            ['sudo', 'find', pattern.split('/*')[0], '-type', 'f', '-atime', '+7', '-delete'],
                            capture_output=True,
                            text=True,
                            timeout=30
                        )
                    except:
                        pass

            # Clean old journal logs
            if partition == '/' or partition.startswith('/var'):
                try:
                    result = subprocess.run(
                        ['sudo', 'journalctl', '--vacuum-time=7d'],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                except:
                    pass

            # Clean apt cache on Debian/Ubuntu systems
            if partition == '/' or partition.startswith('/var'):
                if os.path.exists('/usr/bin/apt-get'):
                    try:
                        subprocess.run(
                            ['sudo', 'apt-get', 'clean'],
                            capture_output=True,
                            timeout=30
                        )
                    except:
                        pass

            # Clean old log files
            if partition == '/' or partition.startswith('/var'):
                try:
                    subprocess.run(
                        ['sudo', 'find', '/var/log', '-type', 'f', '-name', '*.log.*', '-mtime', '+30', '-delete'],
                        capture_output=True,
                        timeout=60
                    )
                except:
                    pass

            return True, f"Disk cleanup completed for {partition}"

        except Exception as e:
            return False, f"Error clearing disk space: {str(e)}"

    def _check_cooldown(self, action_type: str, params: Dict[str, Any]) -> bool:
        """Check if action is in cooldown period"""
        key = f"{action_type}_{str(params)}"

        if key in self.attempt_history:
            last_attempt, count = self.attempt_history[key]
            time_since = time.time() - last_attempt

            if count >= self.max_attempts and time_since < self.cooldown:
                return False

        return True

    def remount(self, mount_config: Dict[str, Any]) -> Tuple[bool, str]:
        """Remount a filesystem (for stale NFS mounts, etc.)"""
        if not mount_config:
            return False, "No mount configuration provided"

        mount_point = mount_config.get('path')
        if not mount_point:
            return False, "No mount path specified"

        try:
            # Try remounting
            result = subprocess.run(
                ['sudo', 'mount', '-o', 'remount', mount_point],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                # Verify mount is accessible
                time.sleep(2)
                try:
                    os.listdir(mount_point)
                    return True, f"Successfully remounted {mount_point}"
                except:
                    return False, f"Remount command succeeded but {mount_point} still not accessible"
            else:
                return False, f"Failed to remount {mount_point}: {result.stderr}"

        except subprocess.TimeoutExpired:
            return False, f"Timeout while remounting {mount_point}"
        except Exception as e:
            return False, f"Error remounting {mount_point}: {str(e)}"

    def unmount_remount(self, mount_config: Dict[str, Any]) -> Tuple[bool, str]:
        """Unmount and remount a filesystem (for failed mounts)"""
        if not mount_config:
            return False, "No mount configuration provided"

        mount_point = mount_config.get('path')
        mount_source = mount_config.get('source')
        mount_type = mount_config.get('type', 'auto')
        mount_options = mount_config.get('options', 'defaults')

        if not mount_point or not mount_source:
            return False, "Mount configuration missing path or source"

        try:
            # First, try to unmount (force if needed)
            unmount_result = subprocess.run(
                ['sudo', 'umount', '-f', mount_point],
                capture_output=True,
                text=True,
                timeout=30
            )

            time.sleep(2)

            # Now mount it again
            mount_cmd = ['sudo', 'mount']
            if mount_type != 'auto':
                mount_cmd.extend(['-t', mount_type])
            if mount_options != 'defaults':
                mount_cmd.extend(['-o', mount_options])
            mount_cmd.extend([mount_source, mount_point])

            mount_result = subprocess.run(
                mount_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if mount_result.returncode == 0:
                # Verify mount is accessible
                time.sleep(2)
                try:
                    os.listdir(mount_point)
                    return True, f"Successfully unmounted and remounted {mount_point}"
                except:
                    return False, f"Mount command succeeded but {mount_point} still not accessible"
            else:
                return False, f"Failed to mount {mount_point}: {mount_result.stderr}"

        except subprocess.TimeoutExpired:
            return False, f"Timeout while unmounting/remounting {mount_point}"
        except Exception as e:
            return False, f"Error unmounting/remounting {mount_point}: {str(e)}"

    def _record_attempt(self, action_type: str, params: Dict[str, Any]):
        """Record an action attempt"""
        key = f"{action_type}_{str(params)}"
        current_time = time.time()

        if key in self.attempt_history:
            last_attempt, count = self.attempt_history[key]
            time_since = current_time - last_attempt

            if time_since < self.cooldown:
                self.attempt_history[key] = (current_time, count + 1)
            else:
                # Reset counter if outside cooldown
                self.attempt_history[key] = (current_time, 1)
        else:
            self.attempt_history[key] = (current_time, 1)

    def enable_automation(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        """Re-enable a disabled Home Assistant automation"""
        entity_id = params.get('entity_id')
        url = params.get('url')
        token = params.get('token')
        friendly_name = params.get('friendly_name', entity_id)

        if not all([entity_id, url, token]):
            return False, "Missing required parameters (entity_id, url, token)"

        try:
            # Call Home Assistant service to turn on automation
            service_url = f"{url}/api/services/automation/turn_on"
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            data = {'entity_id': entity_id}

            response = requests.post(service_url, headers=headers, json=data, verify=False, timeout=10)

            if response.status_code == 200:
                return True, f"Successfully enabled automation '{friendly_name}'"
            else:
                return False, f"Failed to enable automation: HTTP {response.status_code}"

        except Exception as e:
            return False, f"Failed to enable automation: {str(e)}"

    def reload_integration(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        """Reload a failed Home Assistant integration"""
        integration_id = params.get('integration_id')
        url = params.get('url')
        token = params.get('token')
        title = params.get('title', integration_id)

        if not all([integration_id, url, token]):
            return False, "Missing required parameters (integration_id, url, token)"

        try:
            # Call Home Assistant service to reload config entry
            service_url = f"{url}/api/config/config_entries/entry/{integration_id}/reload"
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }

            response = requests.post(service_url, headers=headers, verify=False, timeout=10)

            if response.status_code in [200, 204]:
                return True, f"Successfully reloaded integration '{title}'"
            else:
                return False, f"Failed to reload integration: HTTP {response.status_code}"

        except Exception as e:
            return False, f"Failed to reload integration: {str(e)}"
