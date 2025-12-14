import requests
import urllib3
from typing import Dict, List, Any

# Disable SSL warnings for self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ProxmoxMonitor:
    """Monitor Proxmox VMs and LXC containers"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.hosts = config.get('hosts', [])
        self.tickets = {}  # Cache authentication tickets

    def _get_ticket(self, host: str, username: str, password: str) -> tuple:
        """Get authentication ticket from Proxmox"""
        cache_key = f"{host}:{username}"

        if cache_key in self.tickets:
            return True, self.tickets[cache_key]

        try:
            url = f"https://{host}:8006/api2/json/access/ticket"
            data = {
                'username': username,
                'password': password
            }

            response = requests.post(url, data=data, verify=False, timeout=10)

            if response.status_code == 200:
                result = response.json()
                ticket = result['data']['ticket']
                csrf_token = result['data']['CSRFPreventionToken']
                self.tickets[cache_key] = (ticket, csrf_token)
                return True, (ticket, csrf_token)
            else:
                return False, None

        except Exception as e:
            return False, None

    def _api_get(self, host: str, ticket_info: tuple, endpoint: str) -> tuple:
        """Make GET request to Proxmox API"""
        try:
            ticket, csrf = ticket_info
            url = f"https://{host}:8006/api2/json/{endpoint}"
            headers = {
                'Cookie': f'PVEAuthCookie={ticket}'
            }

            response = requests.get(url, headers=headers, verify=False, timeout=10)

            if response.status_code == 200:
                return True, response.json()['data']
            else:
                return False, None

        except Exception as e:
            return False, None

    def check_proxmox_host(self, host_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check Proxmox host and all VMs/LXCs"""
        results = []
        host = host_config.get('host')
        name = host_config.get('name', host)
        username = host_config.get('username', 'root@pam')
        password = host_config.get('password', '')
        node = host_config.get('node', 'pve')

        # Try to authenticate
        success, ticket_info = self._get_ticket(host, username, password)

        if not success:
            results.append({
                'metric': 'proxmox_host',
                'host': name,
                'healthy': False,
                'issue': 'auth_failed',
                'message': f'Failed to authenticate to Proxmox {name}'
            })
            return results

        # Get all VMs
        success, vms = self._api_get(host, ticket_info, f'nodes/{node}/qemu')

        if success and vms:
            for vm in vms:
                vmid = vm.get('vmid')
                vm_name = vm.get('name', f'VM-{vmid}')
                status = vm.get('status')
                cpu = vm.get('cpu', 0)
                mem = vm.get('mem', 0)
                maxmem = vm.get('maxmem', 1)

                mem_percent = (mem / maxmem * 100) if maxmem > 0 else 0
                cpu_percent = cpu * 100

                is_healthy = status == 'running' and cpu_percent < 90 and mem_percent < 90

                results.append({
                    'metric': 'proxmox_vm',
                    'host': name,
                    'vmid': vmid,
                    'name': vm_name,
                    'status': status,
                    'healthy': is_healthy,
                    'cpu_percent': cpu_percent,
                    'mem_percent': mem_percent,
                    'message': f'{vm_name} (VM {vmid}): {status}'
                })

        # Get all LXC containers
        success, lxcs = self._api_get(host, ticket_info, f'nodes/{node}/lxc')

        if success and lxcs:
            for lxc in lxcs:
                vmid = lxc.get('vmid')
                lxc_name = lxc.get('name', f'LXC-{vmid}')
                status = lxc.get('status')
                cpu = lxc.get('cpu', 0)
                mem = lxc.get('mem', 0)
                maxmem = lxc.get('maxmem', 1)

                mem_percent = (mem / maxmem * 100) if maxmem > 0 else 0
                cpu_percent = cpu * 100

                is_healthy = status == 'running' and cpu_percent < 90 and mem_percent < 90

                results.append({
                    'metric': 'proxmox_lxc',
                    'host': name,
                    'vmid': vmid,
                    'name': lxc_name,
                    'status': status,
                    'healthy': is_healthy,
                    'cpu_percent': cpu_percent,
                    'mem_percent': mem_percent,
                    'message': f'{lxc_name} (LXC {vmid}): {status}'
                })

        return results

    def run_checks(self) -> List[Dict[str, Any]]:
        """Run all Proxmox checks"""
        results = []

        for host_config in self.hosts:
            results.extend(self.check_proxmox_host(host_config))

        return results
