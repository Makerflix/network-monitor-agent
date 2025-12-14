# Mount Monitoring Feature

Your agent now monitors all your NFS mounts and can automatically fix mount issues!

## Monitored Mounts

The agent is now checking these 5 NFS mounts every 60 seconds:

1. **PersonalOS**: `/mnt/PersonalOS` → `192.168.1.234:/mnt/user/PersonalOS`
2. **AI Server**: `/mnt/nas-ai` → `192.168.1.234:/mnt/user/AIserver`
3. **Scans**: `/mnt/nas/Scans` → `192.168.1.234:/mnt/user/Scans`
4. **STLs**: `/mnt/unraid/STLs` → `192.168.1.234:/mnt/user/STLs`
5. **Movies**: `/mnt/nas/Movies` → `192.168.1.234:/mnt/user/Movies`

## What the Agent Detects

The agent checks for several mount issues:

### 1. Stale Mounts
**Problem**: NFS mount becomes unresponsive (common with network hiccups)
**Symptoms**: Commands hang when accessing the mount
**Detection**: Timeout when trying to read directory
**Auto-Fix**: `remount` - Remounts the filesystem without unmounting

### 2. Unmounted Filesystems
**Problem**: Mount point exists but nothing is mounted
**Symptoms**: Directory is empty or shows local filesystem
**Detection**: `mountpoint` command returns not mounted
**Auto-Fix**: `unmount_remount` - Full unmount and remount cycle

### 3. Permission Issues
**Problem**: Mount exists but not accessible
**Symptoms**: Permission denied errors
**Detection**: Cannot list directory contents
**Auto-Fix**: Alert only (requires investigation)

### 4. Missing Mount Points
**Problem**: Mount directory doesn't exist
**Symptoms**: Path not found
**Detection**: Directory check fails
**Auto-Fix**: Alert only (directory needs to be created)

## How Auto-Fix Works

When a mount issue is detected:

1. **AI Analysis**: The linuxexpert model analyzes the issue
2. **Severity Assessment**: Determines criticality
3. **Action Selection**:
   - **Stale mount** → Remount in place
   - **Not mounted** → Full unmount/remount
   - **Other issues** → Alert for human review
4. **Execution**: Runs the fix with sudo
5. **Verification**: Confirms mount is accessible after fix
6. **Cooldown**: Waits 5 minutes before retrying

## Example Scenario

**Scenario**: Network glitch causes NFS mount to go stale

```
01:30:00 - Detecting stale mount on /mnt/nas-ai
01:30:01 - AI Analysis: "Stale NFS mount, likely network interruption"
01:30:01 - Action: remount /mnt/nas-ai
01:30:03 - Success: Mount restored and accessible
01:30:03 - Notification: "✅ Successfully remounted /mnt/nas-ai"
```

**Without this agent**: You'd notice hours/days later when apps fail or commands hang

**With this agent**: Fixed automatically in 3 seconds!

## Safety Features

- **Cooldown Period**: Won't retry same mount for 5 minutes
- **Max Attempts**: Stops after 3 failed attempts
- **Verification**: Always confirms mount works after fix
- **Soft Remount First**: Tries remount before unmount
- **AI Oversight**: AI evaluates each situation

## Configuration

Mounts are configured in `config.yaml`:

```yaml
check_mounts:
  - path: /mnt/nas-ai
    source: "192.168.1.234:/mnt/user/AIserver"
    type: nfs4
    options: "defaults,_netdev"
```

Add new mounts here and restart the agent.

## Logs

Watch for mount issues:
```bash
tail -f ~/network-monitor-agent.log | grep -i mount
```

## Common Issues

### Sudo Password Required
If you see "password required" errors, configure passwordless sudo:

```bash
sudo visudo
```

Add:
```
your-username ALL=(ALL) NOPASSWD: /usr/bin/mount
your-username ALL=(ALL) NOPASSWD: /usr/bin/umount
```

### Mount Options
The agent uses the mount options from your config when remounting.
Ensure they match your `/etc/fstab` or current mount options.

## Benefits

✅ **No More Stale Mounts**: Automatically detects and fixes
✅ **Faster Recovery**: Fixes in seconds vs manual intervention
✅ **Prevents Cascading Failures**: Apps don't hang waiting for mounts
✅ **Peace of Mind**: Your NAS mounts stay healthy 24/7

---

**Your NFS mounts are now protected!** 🛡️
