# Background Execution with Nohup

This guide explains how to run the comprehensive order testing in the background to survive SSH connection timeouts.

## Quick Start

```bash
# Run complete workflow in background
./docker-run.sh all --nohup

# Check status after reconnecting
./check_status.sh
```

## Usage

### Starting Background Tests

```bash
# Complete workflow (recommended)
./docker-run.sh all --nohup

# Individual components
./docker-run.sh enhanced --nohup      # 24-ontology analysis
./docker-run.sh permutations --nohup  # 4-ontology permutation tests
```

### Monitoring Progress

After starting a background test, you'll see output like:
```
🚀 Running with nohup support...
📋 Log file: /path/to/logs/docker_run_20250627_151500.log
✅ Background process started with PID: 12345

Commands to monitor:
  tail -f /path/to/logs/docker_run_20250627_151500.log    # Follow log output
  grep -E '(✅|❌|🧪|📊)' /path/to/logs/docker_run_20250627_151500.log    # Show status updates
  ps aux | grep docker                                    # Check if still running
```

### After SSH Reconnection

When you reconnect to the machine:

```bash
# Quick status overview
./check_status.sh

# Follow the latest log
tail -f logs/docker_run_*.log

# Check specific progress
grep -E '(✅|❌|🧪|📊)' logs/docker_run_*.log
```

## Expected Timeline

- **Enhanced Analysis (6 tests):** ~1-3 hours
- **Permutation Tests (48 tests):** ~2-4 hours  
- **Complete Workflow:** ~3-7 hours

## Log Files

- Stored in `logs/docker_run_TIMESTAMP.log`
- Contain all output including memory monitoring
- Timestamped for easy identification
- Can be filtered for status updates using grep

## Memory Monitoring

The tests will show memory usage like:
```
2025-06-27 14:51:24,718 - INFO - Memory: 535.46GB used, 2472.87GB available, Java: 6.11GB
```

This helps track progress and ensure memory allocation is working correctly.

## Troubleshooting

### Check if still running
```bash
ps aux | grep docker
./check_status.sh
```

### Find memory usage
```bash
free -h
./check_status.sh
```

### If tests fail
Check the log files for specific error messages:
```bash
grep -A5 -B5 "❌\|Failed\|Error" logs/docker_run_*.log
```