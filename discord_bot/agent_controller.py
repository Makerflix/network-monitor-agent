"""
Agent Controller - Interface between Discord bot and monitoring agent
"""
from typing import Dict, List, Any
from datetime import datetime
import asyncio


class AgentController:
    """Interface for Discord bot to control and query the monitoring agent"""

    def __init__(self, agent_instance):
        self.agent = agent_instance
        self.issues_history = []
        self.max_history = 100

    def add_to_history(self, issues: List[Dict], actions: List[Dict]):
        """Add issues and actions to history"""
        if issues:
            self.issues_history.append({
                'timestamp': datetime.now(),
                'issues': issues,
                'actions': actions
            })

            # Limit history size
            self.issues_history = self.issues_history[-self.max_history:]

    async def get_status(self) -> Dict[str, Any]:
        """Get current homelab health status"""
        try:
            # Get current stats
            stats = self.agent.daily_stats

            total_systems = stats.get('systems_total', 0)
            healthy_systems = stats.get('systems_healthy', 0)
            issues_found = stats.get('issues_found', 0)
            actions_taken = stats.get('actions_taken', 0)

            is_healthy = total_systems > 0 and healthy_systems == total_systems

            summary = f"**Homelab Health Status**\n\n"
            summary += f"**Systems**: {healthy_systems}/{total_systems} healthy\n"
            summary += f"**Today's Issues**: {issues_found}\n"
            summary += f"**Auto-fixes**: {actions_taken}\n"
            summary += f"**Monitoring Cycles**: {stats.get('total_checks', 0)}\n"

            if is_healthy:
                summary += "\n✅ **All systems operational**"
            else:
                summary += f"\n⚠️ **{total_systems - healthy_systems} system(s) need attention**"

            return {
                'healthy': is_healthy,
                'summary': summary,
                'stats': stats
            }
        except Exception as e:
            return {
                'healthy': False,
                'summary': f"Error getting status: {str(e)}",
                'stats': {}
            }

    async def run_manual_check(self) -> Dict[str, Any]:
        """Trigger immediate monitoring cycle"""
        try:
            # Run monitoring cycle in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.agent.run_monitoring_cycle)

            # Get recent issues
            recent = self.issues_history[-1] if self.issues_history else None

            if recent:
                issues = recent.get('issues', [])
                actions = recent.get('actions', [])

                return {
                    'success': True,
                    'issues': issues,
                    'actions': actions,
                    'message': f"Check complete. Found {len(issues)} issue(s), took {len(actions)} action(s)."
                }
            else:
                return {
                    'success': True,
                    'issues': [],
                    'actions': [],
                    'message': "Check complete. No issues found."
                }
        except Exception as e:
            return {
                'success': False,
                'issues': [],
                'actions': [],
                'message': f"Check failed: {str(e)}"
            }

    async def get_recent_issues(self, limit: int = 10) -> List[Dict]:
        """Get recent issues from history"""
        return self.issues_history[-limit:]

    async def enable_autofix(self):
        """Enable automatic remediation"""
        self.agent.auto_fix = True

    async def disable_autofix(self):
        """Disable automatic remediation"""
        self.agent.auto_fix = False

    async def get_autofix_status(self) -> bool:
        """Get current auto-fix status"""
        return self.agent.auto_fix
