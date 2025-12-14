import json
from typing import Dict, List, Any, Optional
import os


class DecisionEngine:
    """AI-powered decision engine for analyzing issues and recommending fixes"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.provider = config.get('provider', 'anthropic')
        self.model = config.get('model', 'claude-sonnet-4-5-20250929')
        self.api_key = os.getenv('ANTHROPIC_API_KEY') or config.get('api_key')

        # Initialize AI client based on provider
        if self.provider == 'anthropic':
            try:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("Please install anthropic: pip install anthropic")
        elif self.provider == 'openai':
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("Please install openai: pip install openai")
        elif self.provider == 'ollama':
            try:
                import ollama
                self.client = ollama
            except ImportError:
                raise ImportError("Please install ollama: pip install ollama")
        else:
            raise ValueError(f"Unsupported AI provider: {self.provider}")

    def analyze_issues(self, monitoring_results: List[Dict[str, Any]], allowed_actions: List[str]) -> List[Dict[str, Any]]:
        """Analyze monitoring results and recommend actions"""

        # Filter for unhealthy results
        issues = [r for r in monitoring_results if not r.get('healthy', True)]

        if not issues:
            return []

        # Create prompt for AI
        prompt = self._create_analysis_prompt(issues, allowed_actions)

        # Get AI response
        try:
            if self.provider == 'anthropic':
                response = self._call_anthropic(prompt)
            elif self.provider == 'openai':
                response = self._call_openai(prompt)
            elif self.provider == 'ollama':
                response = self._call_ollama(prompt)
            else:
                return []

            # Parse AI response
            actions = self._parse_ai_response(response)
            return actions

        except Exception as e:
            print(f"AI analysis failed: {e}")
            # Fallback to rule-based decisions
            return self._fallback_analysis(issues, allowed_actions)

    def _create_analysis_prompt(self, issues: List[Dict[str, Any]], allowed_actions: List[str]) -> str:
        """Create the prompt for AI analysis"""
        prompt = f"""You are a system administrator AI agent analyzing server and network issues.

MONITORING ISSUES DETECTED:
{json.dumps(issues, indent=2)}

ALLOWED REMEDIATION ACTIONS:
{json.dumps(allowed_actions, indent=2)}

Your task:
1. Analyze each issue and determine its severity (critical, high, medium, low)
2. Identify the root cause if possible
3. Recommend specific remediation actions from the allowed actions list
4. If the issue requires human intervention, set action to "alert_only"

Respond with a JSON array of action objects. Each action should have:
{{
  "issue": "description of the issue",
  "severity": "critical|high|medium|low",
  "root_cause": "identified or suspected root cause",
  "action": "action to take from allowed list or alert_only",
  "action_params": {{}},  // parameters for the action
  "reasoning": "why this action is recommended"
}}

Examples of actions:
- restart_service: {{"service": "nginx"}}
- kill_hung_process: {{"pid": 1234}}
- clear_disk_space: {{"path": "/var/log", "threshold_mb": 1000}}
- restart_container: {{"container": "app"}}
- clear_cache: {{"type": "system"}}
- remount: {{"mount_config": {{...}}}}
- unmount_remount: {{"mount_config": {{...}}}}

Respond ONLY with the JSON array, no other text."""

        return prompt

    def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic Claude API"""
        message = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text

    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000
        )
        return response.choices[0].message.content

    def _call_ollama(self, prompt: str) -> str:
        """Call Ollama local model"""
        response = self.client.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response['message']['content']

    def _parse_ai_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse AI response into action objects"""
        try:
            # Extract JSON from response (handle markdown code blocks)
            response = response.strip()
            if response.startswith('```'):
                # Remove markdown code block
                lines = response.split('\n')
                response = '\n'.join(lines[1:-1])

            actions = json.loads(response)

            # Validate structure
            if not isinstance(actions, list):
                actions = [actions]

            return actions

        except json.JSONDecodeError as e:
            print(f"Failed to parse AI response as JSON: {e}")
            print(f"Response: {response}")
            return []

    def _fallback_analysis(self, issues: List[Dict[str, Any]], allowed_actions: List[str]) -> List[Dict[str, Any]]:
        """Fallback rule-based analysis when AI fails"""
        actions = []

        for issue in issues:
            metric = issue.get('metric')

            # Service down - restart it
            if metric == 'service_status' and 'restart_service' in allowed_actions:
                actions.append({
                    'issue': issue.get('message'),
                    'severity': 'high',
                    'root_cause': 'Service is not running',
                    'action': 'restart_service',
                    'action_params': {'service': issue.get('service')},
                    'reasoning': 'Service is inactive, attempting restart'
                })

            # High disk usage - clear space
            elif metric == 'disk_usage' and issue.get('value', 0) > 90 and 'clear_disk_space' in allowed_actions:
                actions.append({
                    'issue': issue.get('message'),
                    'severity': 'high',
                    'root_cause': 'Disk space critically low',
                    'action': 'clear_disk_space',
                    'action_params': {'partition': issue.get('partition')},
                    'reasoning': 'Clear temporary files and logs to free disk space'
                })

            # Network issues - just alert
            elif metric == 'network_ping':
                actions.append({
                    'issue': issue.get('message'),
                    'severity': 'medium',
                    'root_cause': 'Network connectivity issue',
                    'action': 'alert_only',
                    'action_params': {},
                    'reasoning': 'Network issues require investigation'
                })

            # Web endpoint down - might need service restart
            elif metric == 'web_endpoint':
                actions.append({
                    'issue': issue.get('message'),
                    'severity': 'high',
                    'root_cause': 'Web service not responding',
                    'action': 'alert_only',
                    'action_params': {},
                    'reasoning': 'Endpoint check required before automated action'
                })

            # Mount issues
            elif metric == 'mount_status':
                mount_issue = issue.get('issue')
                if mount_issue == 'stale_mount' and 'remount' in allowed_actions:
                    actions.append({
                        'issue': issue.get('message'),
                        'severity': 'high',
                        'root_cause': 'Stale or hung mount (common with NFS)',
                        'action': 'remount',
                        'action_params': {'mount_config': issue.get('config')},
                        'reasoning': 'Remount to recover stale NFS/network mount'
                    })
                elif mount_issue == 'not_mounted' and 'unmount_remount' in allowed_actions:
                    actions.append({
                        'issue': issue.get('message'),
                        'severity': 'high',
                        'root_cause': 'Mount not active',
                        'action': 'unmount_remount',
                        'action_params': {'mount_config': issue.get('config')},
                        'reasoning': 'Unmount and remount to restore mount'
                    })
                else:
                    actions.append({
                        'issue': issue.get('message'),
                        'severity': 'high',
                        'root_cause': 'Mount issue',
                        'action': 'alert_only',
                        'action_params': {},
                        'reasoning': 'Mount requires investigation'
                    })

        return actions
