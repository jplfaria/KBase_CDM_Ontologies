#!/bin/bash
set -e

# Handle dynamic UID/GID adjustment for GitHub Actions and other environments
if [ -n "$HOST_UID" ] && [ -n "$HOST_GID" ]; then
    # Check if we're running as root (needed to change UID/GID)
    if [ "$(id -u)" = "0" ]; then
        echo "Adjusting ontology user to UID=$HOST_UID GID=$HOST_GID"
        
        # Modify the ontology user's UID and GID
        usermod -u "$HOST_UID" ontology 2>/dev/null || true
        groupmod -g "$HOST_GID" ontology 2>/dev/null || true
        
        # Fix home directory ownership
        chown -R ontology:ontology /home/ontology || true
        
        # Ensure workspace permissions if it exists
        if [ -d "/home/ontology/workspace" ]; then
            # Only fix ownership of files we create, not the mounted volume itself
            find /home/ontology/workspace -user 1000 -exec chown ontology:ontology {} \; 2>/dev/null || true
        fi
        
        # Drop privileges and run as ontology user
        exec gosu ontology "$@"
    else
        echo "Warning: Cannot adjust UID/GID when not running as root"
        exec "$@"
    fi
else
    # No UID/GID adjustment needed
    exec "$@"
fi