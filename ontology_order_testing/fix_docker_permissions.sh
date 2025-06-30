#!/bin/bash
# Fix Docker permission issues for ontology testing

set -e

echo "🔧 Docker Permission Fix Tool"
echo "============================"

# Get current user info
USER_ID=$(id -u)
GROUP_ID=$(id -g)
echo "📋 Current user: $(whoami) (UID=$USER_ID, GID=$GROUP_ID)"

# Function to fix permissions using Docker
fix_with_docker() {
    local dir="$1"
    echo "  🔧 Fixing $dir/..."
    docker run --rm \
        -v "$PWD:/workspace" \
        -w /workspace \
        --user root \
        alpine:latest \
        sh -c "chown -R $USER_ID:$GROUP_ID $dir 2>/dev/null || true"
}

# Check which directories need fixing
DIRS_TO_FIX=()
for dir in results data logs; do
    if [ -d "$dir" ] && [ ! -w "$dir" ]; then
        DIRS_TO_FIX+=("$dir")
        echo "❌ Found non-writable directory: $dir/"
    elif [ -d "$dir" ]; then
        echo "✅ Directory OK: $dir/"
    fi
done

# Fix permissions if needed
if [ ${#DIRS_TO_FIX[@]} -gt 0 ]; then
    echo ""
    echo "🚀 Fixing permissions..."
    
    for dir in "${DIRS_TO_FIX[@]}"; do
        fix_with_docker "$dir"
    done
    
    echo ""
    echo "✅ Permissions fixed!"
else
    echo ""
    echo "✅ All directories have correct permissions!"
fi

# Check for root-owned files
echo ""
echo "📊 Checking for root-owned files..."
ROOT_FILES=$(find . -maxdepth 3 -user root 2>/dev/null | head -10 || true)

if [ -n "$ROOT_FILES" ]; then
    echo "⚠️  Found some root-owned files:"
    echo "$ROOT_FILES"
    if [ $(echo "$ROOT_FILES" | wc -l) -ge 10 ]; then
        echo "... and more"
    fi
    echo ""
    echo "Run './fix_docker_permissions.sh --all' to fix all files"
else
    echo "✅ No root-owned files found!"
fi

# Handle --all flag
if [ "$1" = "--all" ]; then
    echo ""
    echo "🔧 Fixing ALL files (this may take a moment)..."
    docker run --rm \
        -v "$PWD:/workspace" \
        -w /workspace \
        --user root \
        alpine:latest \
        sh -c "chown -R $USER_ID:$GROUP_ID . 2>/dev/null || true"
    echo "✅ All files fixed!"
fi