#!/bin/bash
# Quick status checker for background order testing processes

TESTING_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$TESTING_DIR/logs"

echo "🔍 Order Testing Status Checker"
echo "📁 Testing directory: $TESTING_DIR"
echo ""

# Check if any Docker processes are running
echo "🐳 Docker Processes:"
DOCKER_PROCS=$(ps aux | grep -E "(docker.*ontology|cdm-ontologies)" | grep -v grep)
if [ -n "$DOCKER_PROCS" ]; then
    echo "$DOCKER_PROCS"
else
    echo "  No Docker processes found"
fi
echo ""

# Check for recent log files
echo "📋 Recent Log Files:"
if [ -d "$LOG_DIR" ]; then
    LOG_FILES=$(find "$LOG_DIR" -name "*.log" -mtime -1 2>/dev/null | sort)
    if [ -n "$LOG_FILES" ]; then
        for log_file in $LOG_FILES; do
            size=$(du -h "$log_file" | cut -f1)
            modified=$(stat -c "%y" "$log_file" 2>/dev/null || stat -f "%Sm" "$log_file")
            echo "  📄 $(basename "$log_file") - $size - $modified"
        done
        
        echo ""
        echo "📊 Latest Log Activity:"
        LATEST_LOG=$(find "$LOG_DIR" -name "*.log" -mtime -1 2>/dev/null | head -1)
        if [ -n "$LATEST_LOG" ]; then
            echo "  🔗 $LATEST_LOG"
            echo ""
            tail -10 "$LATEST_LOG" | sed 's/^/    /'
            echo ""
            echo "Commands to monitor:"
            echo "  tail -f $LATEST_LOG"
            echo "  grep -E '(✅|❌|🧪|📊)' $LATEST_LOG"
        fi
    else
        echo "  No recent log files found"
    fi
else
    echo "  No logs directory found"
fi

echo ""
echo "🎯 Current Memory Usage:"
free -h | head -2

echo ""
echo "📈 Java Processes:"
JAVA_PROCS=$(ps aux | grep java | grep -v grep)
if [ -n "$JAVA_PROCS" ]; then
    echo "$JAVA_PROCS" | while read line; do
        pid=$(echo "$line" | awk '{print $2}')
        mem=$(echo "$line" | awk '{print $6}')
        mem_gb=$((mem / 1024 / 1024))
        echo "  PID $pid: ${mem_gb}GB"
    done
else
    echo "  No Java processes found"
fi