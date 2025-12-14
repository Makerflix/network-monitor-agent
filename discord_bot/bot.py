"""
Discord Bot - Interactive interface for Network Monitor Agent
"""
import discord
from discord.ext import commands
import asyncio
from typing import Optional


class HomelabBot(commands.Bot):
    """Discord bot for interacting with the homelab monitoring agent"""

    def __init__(self, agent_controller, command_prefix: str = '!'):
        # Set up intents
        intents = discord.Intents.default()
        intents.message_content = True

        # Initialize bot
        super().__init__(command_prefix=command_prefix, intents=intents)

        # Store controller
        self.controller = agent_controller

        # Add commands
        self.add_commands()

    def add_commands(self):
        """Register all bot commands"""

        @self.command(name='status', help='Check homelab health status')
        async def status(ctx):
            """Get current homelab health status"""
            await ctx.send("🔍 Checking homelab status...")

            try:
                status_data = await self.controller.get_status()

                # Create embed
                embed = discord.Embed(
                    title="🏠 Homelab Health Status",
                    description=status_data['summary'],
                    color=discord.Color.green() if status_data['healthy'] else discord.Color.red()
                )

                # Add timestamp
                embed.timestamp = discord.utils.utcnow()

                await ctx.send(embed=embed)

            except Exception as e:
                await ctx.send(f"❌ Error getting status: {str(e)}")

        @self.command(name='check', help='Run manual monitoring check')
        async def check(ctx):
            """Trigger immediate monitoring cycle"""
            await ctx.send("🔄 Running manual check... this may take a moment")

            try:
                result = await self.controller.run_manual_check()

                if result['success']:
                    # Create embed
                    embed = discord.Embed(
                        title="✅ Manual Check Complete",
                        description=result['message'],
                        color=discord.Color.blue()
                    )

                    # Add issues if any
                    if result['issues']:
                        issues_text = "\n".join([
                            f"• {issue.get('metric', 'Unknown')}: {issue.get('message', 'No details')}"
                            for issue in result['issues'][:5]  # Limit to 5 issues
                        ])
                        embed.add_field(
                            name="Issues Found",
                            value=issues_text,
                            inline=False
                        )

                    # Add actions if any
                    if result['actions']:
                        actions_text = "\n".join([
                            f"• {action.get('action', 'Unknown')}"
                            for action in result['actions'][:5]
                        ])
                        embed.add_field(
                            name="Actions Taken",
                            value=actions_text,
                            inline=False
                        )

                    embed.timestamp = discord.utils.utcnow()
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(f"❌ {result['message']}")

            except Exception as e:
                await ctx.send(f"❌ Error running check: {str(e)}")

        @self.command(name='issues', help='View recent issues (usage: !issues [limit])')
        async def issues(ctx, limit: int = 5):
            """Get recent issues from history"""
            # Validate limit
            if limit < 1 or limit > 20:
                await ctx.send("⚠️ Limit must be between 1 and 20")
                return

            try:
                history = await self.controller.get_recent_issues(limit)

                if not history:
                    await ctx.send("✅ No recent issues found!")
                    return

                # Create embed
                embed = discord.Embed(
                    title=f"📋 Recent Issues (Last {len(history)})",
                    color=discord.Color.orange()
                )

                for idx, entry in enumerate(reversed(history), 1):
                    timestamp = entry['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                    issues = entry.get('issues', [])
                    actions = entry.get('actions', [])

                    # Format issues
                    issues_text = "\n".join([
                        f"  - {issue.get('metric', 'Unknown')}: {issue.get('message', 'No details')}"
                        for issue in issues[:3]  # Limit per entry
                    ])

                    if len(issues) > 3:
                        issues_text += f"\n  ... and {len(issues) - 3} more"

                    # Format actions
                    actions_text = f"\n**Actions**: {len(actions)} taken" if actions else ""

                    value = f"**Time**: {timestamp}\n{issues_text}{actions_text}"

                    embed.add_field(
                        name=f"Entry #{idx}",
                        value=value[:1024],  # Discord field value limit
                        inline=False
                    )

                embed.timestamp = discord.utils.utcnow()
                await ctx.send(embed=embed)

            except Exception as e:
                await ctx.send(f"❌ Error getting issues: {str(e)}")

        @self.command(name='autofix', help='Control auto-fix mode (usage: !autofix on/off)')
        async def autofix(ctx, mode: Optional[str] = None):
            """Enable or disable automatic remediation"""
            if mode is None:
                # Show current status
                try:
                    is_enabled = await self.controller.get_autofix_status()
                    status_text = "enabled ✅" if is_enabled else "disabled ❌"
                    await ctx.send(f"Auto-fix is currently **{status_text}**")
                except Exception as e:
                    await ctx.send(f"❌ Error getting auto-fix status: {str(e)}")
                return

            mode = mode.lower()

            if mode not in ['on', 'off', 'enable', 'disable', 'enabled', 'disabled']:
                await ctx.send("⚠️ Usage: `!autofix on` or `!autofix off`")
                return

            try:
                if mode in ['on', 'enable', 'enabled']:
                    await self.controller.enable_autofix()
                    await ctx.send("✅ Auto-fix **enabled**. Agent will automatically remediate issues.")
                else:
                    await self.controller.disable_autofix()
                    await ctx.send("⚠️ Auto-fix **disabled**. Agent will only alert on issues.")

            except Exception as e:
                await ctx.send(f"❌ Error changing auto-fix mode: {str(e)}")

    async def on_ready(self):
        """Called when bot is ready"""
        import logging
        logging.info(f"✅ Discord bot logged in as {self.user.name} (ID: {self.user.id})")
        logging.info(f"✅ Connected to {len(self.guilds)} server(s)")
        print(f"✅ Discord bot logged in as {self.user.name} (ID: {self.user.id})")
        print(f"✅ Connected to {len(self.guilds)} server(s)")

    async def on_command_error(self, ctx, error):
        """Handle command errors"""
        if isinstance(error, commands.CommandNotFound):
            await ctx.send("❓ Unknown command. Use `!help` to see available commands.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"⚠️ Missing argument: {error.param.name}. Use `!help` for usage info.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"⚠️ Invalid argument. Use `!help` for usage info.")
        else:
            await ctx.send(f"❌ Error: {str(error)}")
            print(f"Command error: {error}")
