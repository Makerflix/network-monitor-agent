import requests
import urllib3
from typing import Dict, List, Any
from datetime import datetime, timedelta

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class HomeAssistantMonitor:
    """Monitor Home Assistant automations, devices, and integrations"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.instances = config.get('instances', [])

    def _api_get(self, url: str, token: str, endpoint: str) -> tuple:
        """Make GET request to Home Assistant API"""
        try:
            full_url = f"{url}/api/{endpoint}"
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }

            response = requests.get(full_url, headers=headers, verify=False, timeout=10)

            if response.status_code == 200:
                return True, response.json()
            else:
                return False, None

        except Exception as e:
            return False, None

    def check_automations(self, instance_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check Home Assistant automations for issues"""
        results = []
        url = instance_config.get('url')
        token = instance_config.get('token')
        name = instance_config.get('name', url)

        if not instance_config.get('check_automations', True):
            return results

        # Get all automation states
        success, states = self._api_get(url, token, 'states')

        if not success:
            return results

        # Filter to just automations
        automations = [s for s in states if s.get('entity_id', '').startswith('automation.')]

        for automation in automations:
            entity_id = automation.get('entity_id')
            state = automation.get('state')
            attributes = automation.get('attributes', {})
            friendly_name = attributes.get('friendly_name', entity_id)

            # Check if automation is disabled
            if state == 'off':
                results.append({
                    'metric': 'ha_automation',
                    'instance': name,
                    'entity_id': entity_id,
                    'friendly_name': friendly_name,
                    'state': state,
                    'healthy': False,
                    'issue': 'disabled',
                    'message': f'Automation "{friendly_name}" is disabled',
                    'url': url,
                    'token': token
                })

        return results

    def check_entities(self, instance_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check Home Assistant entities for unavailable/unknown states"""
        results = []
        url = instance_config.get('url')
        token = instance_config.get('token')
        name = instance_config.get('name', url)
        entity_domains = instance_config.get('entity_domains', [
            'light', 'switch', 'climate', 'binary_sensor', 'sensor', 'lock', 'cover'
        ])

        if not instance_config.get('check_entities', True):
            return results

        # Get all entity states
        success, states = self._api_get(url, token, 'states')

        if not success:
            return results

        # Filter to monitored domains
        monitored_entities = [
            s for s in states
            if any(s.get('entity_id', '').startswith(f'{domain}.') for domain in entity_domains)
        ]

        for entity in monitored_entities:
            entity_id = entity.get('entity_id')
            state = entity.get('state')
            attributes = entity.get('attributes', {})
            friendly_name = attributes.get('friendly_name', entity_id)
            domain = entity_id.split('.')[0] if '.' in entity_id else 'unknown'

            # Check for problematic states
            if state in ['unavailable', 'unknown']:
                results.append({
                    'metric': 'ha_entity',
                    'instance': name,
                    'entity_id': entity_id,
                    'friendly_name': friendly_name,
                    'domain': domain,
                    'state': state,
                    'healthy': False,
                    'issue': f'{state}_state',
                    'message': f'{domain.capitalize()} "{friendly_name}" is {state}',
                    'url': url,
                    'token': token
                })

        return results

    def check_integrations(self, instance_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check Home Assistant integrations for failures"""
        results = []
        url = instance_config.get('url')
        token = instance_config.get('token')
        name = instance_config.get('name', url)

        if not instance_config.get('check_integrations', True):
            return results

        # Get all config entries (integrations)
        success, entries = self._api_get(url, token, 'config/config_entries/entry')

        if not success:
            # Config entries endpoint might not be available or require different permissions
            # This is optional, so we just skip if it fails
            return results

        if isinstance(entries, list):
            for entry in entries:
                entry_id = entry.get('entry_id', '')
                domain = entry.get('domain', 'unknown')
                title = entry.get('title', domain)
                state = entry.get('state', 'unknown')

                # Check for non-loaded states
                if state not in ['loaded', 'not_loaded']:
                    results.append({
                        'metric': 'ha_integration',
                        'instance': name,
                        'integration_id': entry_id,
                        'domain': domain,
                        'title': title,
                        'state': state,
                        'healthy': False,
                        'issue': 'integration_failed',
                        'message': f'Integration "{title}" ({domain}) is in state: {state}',
                        'url': url,
                        'token': token
                    })

        return results

    def check_instance(self, instance_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check one Home Assistant instance"""
        results = []
        url = instance_config.get('url')
        token = instance_config.get('token')
        name = instance_config.get('name', url)

        # Test basic connectivity first
        try:
            response = requests.get(f"{url}/api/", headers={'Authorization': f'Bearer {token}'}, verify=False, timeout=5)
            if response.status_code != 200:
                results.append({
                    'metric': 'ha_connection',
                    'instance': name,
                    'healthy': False,
                    'error': f'HTTP {response.status_code}',
                    'message': f'Failed to connect to Home Assistant at {name}'
                })
                return results
        except Exception as e:
            results.append({
                'metric': 'ha_connection',
                'instance': name,
                'healthy': False,
                'error': str(e),
                'message': f'Failed to connect to Home Assistant at {name}: {str(e)}'
            })
            return results

        # Run all checks
        results.extend(self.check_automations(instance_config))
        results.extend(self.check_entities(instance_config))
        results.extend(self.check_integrations(instance_config))

        return results

    def run_checks(self) -> List[Dict[str, Any]]:
        """Run all Home Assistant checks"""
        results = []

        for instance in self.instances:
            results.extend(self.check_instance(instance))

        return results
