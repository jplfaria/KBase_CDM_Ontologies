#!/bin/bash
# Self-contained Docker execution for order testing
# All operations contained within ontology_order_testing/ folder

set -e

# Get the absolute path to the testing directory
TESTING_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$TESTING_DIR")"

echo "🔧 Order Testing Docker Runner"
echo "📁 Testing directory: $TESTING_DIR"
echo "📁 Repository directory: $REPO_DIR"

# Check if we have the required files
if [ ! -f "$TESTING_DIR/local_env/.env.local" ]; then
    echo "❌ Missing: $TESTING_DIR/local_env/.env.local"
    exit 1
fi

if [ ! -f "$TESTING_DIR/ontologies_source_full.txt" ]; then
    echo "❌ Missing: $TESTING_DIR/ontologies_source_full.txt"
    exit 1
fi

# Function to run Docker with proper mounts
run_docker() {
    local script_path="$1"
    local description="$2"
    
    echo ""
    echo "🚀 Running: $description"
    echo "📋 Script: $script_path"
    
    # Export host user ID for Docker (UID might be readonly, so check first)
    if [ -z "$UID" ] || [ "$UID" = "" ]; then
        export UID=$(id -u)
    fi
    export GID=$(id -g)
    
    # Load environment variables from local env file  
    source "$TESTING_DIR/local_env/.env.local"
    
    docker compose -f "$REPO_DIR/docker-compose.yml" -f "$TESTING_DIR/docker-compose.override.yml" run --rm \
        -v "$TESTING_DIR:/home/ontology/workspace/testing" \
        -w "/home/ontology/workspace/testing" \
        cdm-ontologies \
        python "$script_path"
}

# Function to run with custom working directory
run_docker_custom() {
    local command="$1"
    local description="$2"
    
    echo ""
    echo "🚀 Running: $description"
    echo "📋 Command: $command"
    
    # Export host user ID for Docker (UID might be readonly, so check first)
    if [ -z "$UID" ] || [ "$UID" = "" ]; then
        export UID=$(id -u)
    fi
    export GID=$(id -g)
    
    # Load environment variables from local env file  
    source "$TESTING_DIR/local_env/.env.local"
    
    docker compose -f "$REPO_DIR/docker-compose.yml" -f "$TESTING_DIR/docker-compose.override.yml" run --rm \
        -v "$TESTING_DIR:/home/ontology/workspace/testing" \
        -w "/home/ontology/workspace/testing" \
        cdm-ontologies \
        $command
}

# Main execution
case "${1:-all}" in
    "download")
        echo "📥 Downloading all ontologies..."
        run_docker "scripts/download_ontologies.py" "Download all ontologies"
        ;;
    
    "pseudo-base")
        echo "🔧 Creating pseudo-base versions..."
        run_docker "scripts/create_pseudo_base_local.py" "Create pseudo-base versions"
        ;;
    
    "test-orders")
        echo "🧪 Testing merge orders..."
        run_docker "test_merge_orders.py" "Test different merge orders"
        ;;
    
    "compare")
        echo "🔍 Comparing merge results..."
        run_docker "compare_merges.py" "Compare merge results"
        ;;
    
    "analyze")
        echo "📊 Analyzing annotations..."
        run_docker "analyze_annotations.py" "Analyze term annotations"
        ;;
    
    "shell")
        echo "🐚 Opening interactive shell..."
        run_docker_custom "bash" "Interactive shell"
        ;;
    
    "all")
        echo "🎯 Running complete testing workflow..."
        
        # Step 1: Download ontologies
        echo ""
        echo "=" * 60
        echo "STEP 1: Download ontologies"
        echo "=" * 60
        run_docker "scripts/download_ontologies.py" "Download all ontologies"
        
        # Step 2: Create pseudo-base versions
        echo ""
        echo "=" * 60
        echo "STEP 2: Create pseudo-base versions"
        echo "=" * 60
        run_docker "scripts/create_pseudo_base_local.py" "Create pseudo-base versions"
        
        # Step 3: Test merge orders
        echo ""
        echo "=" * 60
        echo "STEP 3: Test merge orders"
        echo "=" * 60
        run_docker "test_merge_orders.py" "Test different merge orders"
        
        # Step 4: Compare results
        echo ""
        echo "=" * 60
        echo "STEP 4: Compare merge results"
        echo "=" * 60
        run_docker "compare_merges.py" "Compare merge results"
        
        # Step 5: Analyze annotations
        echo ""
        echo "=" * 60
        echo "STEP 5: Analyze annotations"
        echo "=" * 60
        run_docker "analyze_annotations.py" "Analyze term annotations"
        
        echo ""
        echo "🎉 Complete testing workflow finished!"
        echo "📋 Check results/ directory for outputs"
        ;;
    
    *)
        echo "Usage: $0 [download|pseudo-base|test-orders|compare|analyze|shell|all]"
        echo ""
        echo "Commands:"
        echo "  download     - Download all 23 ontologies"
        echo "  pseudo-base  - Create pseudo-base versions of non-base ontologies"
        echo "  test-orders  - Test different merge orders"
        echo "  compare      - Compare merge results"
        echo "  analyze      - Analyze term annotations"
        echo "  shell        - Open interactive shell"
        echo "  all          - Run complete workflow (default)"
        exit 1
        ;;
esac

echo ""
echo "✅ Task completed successfully!"