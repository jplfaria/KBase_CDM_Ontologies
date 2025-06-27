#!/bin/bash
# Cleanup script for Docker-created files
# Uses Docker to remove files created with root permissions

set -e

TESTING_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$TESTING_DIR")"

echo "🧹 Order Testing Cleanup"
echo "📁 Testing directory: $TESTING_DIR"

# Function to clean specific directories
clean_directory() {
    local dir_name="$1"
    local dir_path="$TESTING_DIR/$dir_name"
    
    if [ -d "$dir_path" ]; then
        echo "🗑️  Cleaning $dir_name/..."
        
        # Use Docker to remove files as root
        docker run --rm \
            -v "$TESTING_DIR:/workspace" \
            -w /workspace \
            --user root \
            alpine:latest \
            rm -rf "$dir_name/*"
        
        echo "✅ $dir_name/ cleaned"
    else
        echo "⏭️  $dir_name/ doesn't exist, skipping"
    fi
}

# Parse command line arguments
TARGET="${1:-all}"

case "$TARGET" in
    "results")
        clean_directory "results"
        ;;
    
    "logs")
        clean_directory "logs"
        ;;
    
    "data")
        echo "⚠️  Are you sure you want to delete downloaded ontologies? (y/N)"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            clean_directory "data"
        else
            echo "❌ Data cleanup cancelled"
        fi
        ;;
    
    "all")
        echo "🧹 Cleaning all test outputs..."
        clean_directory "results"
        clean_directory "logs"
        echo ""
        echo "💡 To also clean downloaded data, run: $0 data"
        ;;
    
    *)
        echo "Usage: $0 [results|logs|data|all]"
        echo ""
        echo "Targets:"
        echo "  results  - Clean test results only"
        echo "  logs     - Clean log files only"
        echo "  data     - Clean downloaded ontologies (requires confirmation)"
        echo "  all      - Clean results and logs (default)"
        exit 1
        ;;
esac

echo ""
echo "🎉 Cleanup complete!"