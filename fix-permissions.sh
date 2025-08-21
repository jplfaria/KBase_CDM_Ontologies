#!/bin/bash
# Universal permission fix script for Docker containers
# This runs inside the container to fix any permission issues

# Get the host UID/GID from environment or use defaults
HOST_UID="${HOST_UID:-1000}"
HOST_GID="${HOST_GID:-1000}"

echo "Fixing permissions for UID:GID = $HOST_UID:$HOST_GID"

# Function to create and fix permissions for a directory
ensure_dir_with_permissions() {
    local dir="$1"
    # Create directory if it doesn't exist
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        echo "Created directory: $dir"
    fi
    # Fix permissions
    chown -R $HOST_UID:$HOST_GID "$dir" 2>/dev/null || true
}

# Main directories to ensure exist and have correct permissions
DIRS_TO_FIX=(
    "/home/ontology/workspace/outputs"
    "/home/ontology/workspace/outputs/tsv_tables"
    "/home/ontology/workspace/outputs_test"
    "/home/ontology/workspace/outputs_test/tsv_tables"
    "/home/ontology/workspace/ontology_data_owl"
    "/home/ontology/workspace/ontology_data_owl/non-base-ontologies"
    "/home/ontology/workspace/ontology_data_owl_test"
    "/home/ontology/workspace/ontology_data_owl_test/non-base-ontologies"
    "/home/ontology/workspace/ontology_versions"
    "/home/ontology/workspace/ontology_versions_test"
    "/home/ontology/workspace/logs"
    "/home/ontology/workspace/results"
    "/home/ontology/workspace/data"
)

# Create and fix permissions for all directories
for dir in "${DIRS_TO_FIX[@]}"; do
    ensure_dir_with_permissions "$dir"
done

# Also fix any files in the workspace root created by root
find /home/ontology/workspace -maxdepth 1 -user 0 -exec chown $HOST_UID:$HOST_GID {} + 2>/dev/null || true

echo "Permission fixes completed"