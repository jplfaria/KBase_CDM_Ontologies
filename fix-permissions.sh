#!/bin/bash
# Universal permission fix script for Docker containers
# This runs inside the container to fix any permission issues

# Function to fix permissions for a directory
fix_dir_permissions() {
    local dir="$1"
    if [ -d "$dir" ] && [ -n "$HOST_UID" ] && [ -n "$HOST_GID" ]; then
        # Find files created by root (UID 0) and fix them
        find "$dir" -user 0 -exec chown $HOST_UID:$HOST_GID {} + 2>/dev/null || true
    fi
}

# Main directories to fix
DIRS_TO_FIX=(
    "/home/ontology/workspace/outputs"
    "/home/ontology/workspace/outputs_test"
    "/home/ontology/workspace/ontology_data_owl"
    "/home/ontology/workspace/ontology_data_owl_test"
    "/home/ontology/workspace/logs"
    "/home/ontology/workspace/results"
    "/home/ontology/workspace/data"
)

# Fix permissions for all directories
for dir in "${DIRS_TO_FIX[@]}"; do
    fix_dir_permissions "$dir"
done

# Also fix any files in the workspace root created by root
if [ -n "$HOST_UID" ] && [ -n "$HOST_GID" ]; then
    find /home/ontology/workspace -maxdepth 1 -user 0 -exec chown $HOST_UID:$HOST_GID {} + 2>/dev/null || true
fi