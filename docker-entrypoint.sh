#!/bin/bash
# Docker entrypoint that fixes permissions on exit

# Store the command to run
CMD="$@"

# Function to fix permissions
fix_permissions() {
    if [ -n "$HOST_UID" ] && [ -n "$HOST_GID" ]; then
        # Only fix files we created (not the entire filesystem)
        find /home/ontology/workspace -type f -user root -newer /tmp/start_marker 2>/dev/null | \
            xargs -r chown $HOST_UID:$HOST_GID 2>/dev/null || true
        find /home/ontology/workspace -type d -user root -newer /tmp/start_marker 2>/dev/null | \
            xargs -r chown $HOST_UID:$HOST_GID 2>/dev/null || true
    fi
}

# Create a marker to know which files are new
touch /tmp/start_marker

# Set up trap to fix permissions on exit
trap fix_permissions EXIT

# Run the actual command
exec $CMD