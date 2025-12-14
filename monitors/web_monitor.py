import requests
from typing import Dict, List, Any
import time


class WebMonitor:
    """Monitors web services and APIs"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.endpoints = config.get('endpoints', [])

    def check_endpoint(self, endpoint: Dict[str, Any]) -> Dict[str, Any]:
        """Check if a web endpoint is responding correctly"""
        url = endpoint['url']
        name = endpoint.get('name', url)
        timeout = endpoint.get('timeout', 5)
        expected_status = endpoint.get('expected_status', 200)

        try:
            start_time = time.time()
            response = requests.get(url, timeout=timeout, allow_redirects=True)
            response_time = (time.time() - start_time) * 1000  # Convert to ms

            is_healthy = response.status_code == expected_status

            return {
                'metric': 'web_endpoint',
                'name': name,
                'url': url,
                'status_code': response.status_code,
                'response_time': round(response_time, 2),
                'expected_status': expected_status,
                'healthy': is_healthy,
                'message': f'{name}: {response.status_code} ({response_time:.0f}ms)'
            }

        except requests.exceptions.Timeout:
            return {
                'metric': 'web_endpoint',
                'name': name,
                'url': url,
                'healthy': False,
                'error': 'timeout',
                'message': f'{name}: Request timed out after {timeout}s'
            }
        except requests.exceptions.ConnectionError as e:
            return {
                'metric': 'web_endpoint',
                'name': name,
                'url': url,
                'healthy': False,
                'error': 'connection_error',
                'message': f'{name}: Connection failed - {str(e)}'
            }
        except Exception as e:
            return {
                'metric': 'web_endpoint',
                'name': name,
                'url': url,
                'healthy': False,
                'error': str(e),
                'message': f'{name}: Check failed - {str(e)}'
            }

    def run_checks(self) -> List[Dict[str, Any]]:
        """Run all web service checks"""
        results = []

        for endpoint in self.endpoints:
            results.append(self.check_endpoint(endpoint))

        return results
