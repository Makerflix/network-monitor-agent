# Git Repository Information

This project is pushed to both GitHub and Gitea.

## Repository URLs

### GitHub (Public)
- **URL**: https://github.com/Makerflix/network-monitor-agent
- **Clone**: `git clone https://github.com/Makerflix/network-monitor-agent.git`

### Gitea (Private Server)
- **URL**: http://192.168.1.234:3000/aa-git/network-monitor-agent
- **Clone**: `git clone http://192.168.1.234:3000/aa-git/network-monitor-agent.git`

## Git Remotes

This repository has two remotes configured:

```bash
origin  → GitHub
gitea   → Gitea (192.168.1.234)
```

## Pushing Updates

To push to both repositories:

```bash
# Push to GitHub
git push origin main

# Push to Gitea
git push gitea main

# Push to both at once
git push origin main && git push gitea main
```

## Branch Setup

- **Main Branch**: `main`
- **Tracking**: Both origin and gitea

## Initial Commit

The initial commit includes:
- Complete AI monitoring agent
- System, network, and mount monitoring
- Automatic remediation actions
- AI decision engine (Ollama integration)
- Full documentation

---

Repository created and synced on: 2025-12-14
