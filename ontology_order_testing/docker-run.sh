#!/bin/bash
# Self-contained Docker execution for order testing
# All operations contained within ontology_order_testing/ folder

set -e

# Auto-export UID/GID - no manual setup needed
export UID=$(id -u) 2>/dev/null || export UID=$(id -u)
export GID=$(id -g) 2>/dev/null || export GID=$(id -g)

# Parse arguments for nohup support
USE_NOHUP=false
ORIGINAL_ARGS=("$@")
FILTERED_ARGS=()

for arg in "$@"; do
    if [[ "$arg" == "--nohup" ]]; then
        USE_NOHUP=true
    else
        FILTERED_ARGS+=("$arg")
    fi
done

# Get the absolute path to the testing directory
TESTING_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$TESTING_DIR")"

echo "🔧 Order Testing Docker Runner"
echo "📁 Testing directory: $TESTING_DIR"
echo "📁 Repository directory: $REPO_DIR"

# Handle nohup execution
if [ "$USE_NOHUP" = true ]; then
    LOG_DIR="$TESTING_DIR/logs"
    # Ensure directory exists
    mkdir -p "$LOG_DIR" 2>/dev/null || {
        echo "❌ Failed to create logs directory: $LOG_DIR"
        echo "Trying current directory instead..."
        LOG_DIR="."
    }
    
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    LOG_FILE="$LOG_DIR/docker_run_${TIMESTAMP}.log"
    
    # Test if we can write to the log file
    touch "$LOG_FILE" 2>/dev/null || {
        echo "❌ Cannot write to log file: $LOG_FILE"
        echo "Using current directory instead..."
        LOG_FILE="./docker_run_${TIMESTAMP}.log"
        touch "$LOG_FILE" || {
            echo "❌ Cannot create log file even in current directory"
            echo "Please check permissions and try again"
            exit 1
        }
    }
    
    echo "🚀 Running with nohup support..."
    echo "📋 Log file: $LOG_FILE"
    echo "📊 Monitor progress with: tail -f $LOG_FILE"
    echo "🔍 Check if running with: ps aux | grep docker"
    echo ""
    echo "Starting background execution..."
    
    # Re-run this script without --nohup in background
    nohup "$0" "${FILTERED_ARGS[@]}" > "$LOG_FILE" 2>&1 &
    PID=$!
    
    # Give it a moment to start
    sleep 1
    
    # Check if process started successfully
    if ps -p $PID > /dev/null 2>&1; then
        echo "✅ Background process started with PID: $PID"
        echo "📋 Log file: $LOG_FILE"
        echo ""
        echo "Commands to monitor:"
        echo "  tail -f $LOG_FILE                    # Follow log output"
        echo "  grep -E '(✅|❌|🧪|📊)' $LOG_FILE    # Show status updates"
        echo "  ps -p $PID                          # Check if still running"
        echo "  kill $PID                           # Stop the process if needed"
        echo ""
    else
        echo "❌ Failed to start background process"
        echo "Check the log file for errors: $LOG_FILE"
        exit 1
    fi
    
    exit 0
fi

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
    
    # UID/GID already exported at script start
    
    # Load environment variables from local env file  
    source "$TESTING_DIR/local_env/.env.local"
    
    # Run as root to avoid permission issues with different user IDs across systems
    # (Dockerfile has hardcoded user 502, but host systems vary widely)
    docker compose -f "$REPO_DIR/docker-compose.yml" -f "$TESTING_DIR/docker-compose.override.yml" run --rm --user root \
        -v "$TESTING_DIR:/home/ontology/workspace/testing" \
        -w "/home/ontology/workspace/testing" \
        cdm-ontologies \
        python "$script_path"
    
    # Fix permissions after run
    docker run --rm \
        -v "$TESTING_DIR:/workspace" \
        --user root \
        alpine:latest \
        sh -c "chown -R $UID:$GID /workspace/results /workspace/data /workspace/logs 2>/dev/null || true"
}

# Function to run with custom working directory
run_docker_custom() {
    local command="$1"
    local description="$2"
    
    echo ""
    echo "🚀 Running: $description"
    echo "📋 Command: $command"
    
    # UID/GID already exported at script start
    
    # Load environment variables from local env file  
    source "$TESTING_DIR/local_env/.env.local"
    
    # Run as root to avoid permission issues with different user IDs across systems
    # (Dockerfile has hardcoded user 502, but host systems vary widely)
    docker compose -f "$REPO_DIR/docker-compose.yml" -f "$TESTING_DIR/docker-compose.override.yml" run --rm --user root \
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
    
    "enhanced")
        echo "🔬 Running enhanced analysis (24 ontologies)..."
        run_docker "enhanced_order_analysis.py" "Enhanced 24-ontology analysis"
        ;;
    
    "permutations")
        echo "🧬 Running permutation tests (4 ontologies)..."
        run_docker "test_permutations_4onto.py" "4-ontology permutation tests"
        ;;
    
    "summary")
        echo "📋 Generating summary report..."
        run_docker "generate_summary.py" "Generate summary report"
        ;;
    
    "detailed")
        echo "🔬 Generating detailed comparison report..."
        run_docker "generate_detailed_report.py" "Generate detailed comparison report"
        ;;
    
    "compare")
        echo "🔍 Comparing merge results..."
        run_docker "compare_merges.py" "Compare merge results"
        ;;
    
    "analyze")
        echo "📊 Analyzing annotations..."
        run_docker "analyze_annotations.py" "Analyze term annotations"
        ;;
    
    "test-metrics")
        echo "🧪 Testing enhanced metrics functionality..."
        run_docker "test_enhanced_metrics.py" "Test enhanced metrics collector"
        ;;
    
    "test-imports")
        echo "🐍 Testing Python imports and environment..."
        run_docker "test_imports.py" "Test Python environment"
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
        
        # Step 3: Enhanced analysis (24 ontologies)
        echo ""
        echo "=" * 60
        echo "STEP 3: Enhanced analysis (24 ontologies)"
        echo "=" * 60
        run_docker "enhanced_order_analysis.py" "Enhanced 24-ontology analysis"
        
        # Step 4: Permutation tests (4 ontologies)
        echo ""
        echo "=" * 60
        echo "STEP 4: Permutation tests (4 ontologies)"
        echo "=" * 60
        run_docker "test_permutations_4onto.py" "4-ontology permutation tests"
        
        # Step 5: Generate summary report
        echo ""
        echo "=" * 60
        echo "STEP 5: Generate summary report"
        echo "=" * 60
        run_docker "generate_summary.py" "Generate summary report"
        
        echo ""
        echo "🎉 Complete testing workflow finished!"
        echo "📋 Check results/ directory for outputs"
        ;;
    
    *)
        echo "Usage: $0 [download|pseudo-base|test-orders|enhanced|permutations|summary|detailed|compare|analyze|test-metrics|shell|all] [--nohup]"
        echo ""
        echo "Commands:"
        echo "  download     - Download all 23 ontologies"
        echo "  pseudo-base  - Create pseudo-base versions of non-base ontologies"
        echo "  test-orders  - Test different merge orders (legacy)"
        echo "  enhanced     - Enhanced 24-ontology analysis with term tracking"
        echo "  permutations - Exhaustive 4-ontology permutation testing"
        echo "  summary      - Generate comprehensive summary report"
        echo "  detailed     - Generate detailed comparison report with metrics"
        echo "  compare      - Compare merge results (legacy)"
        echo "  analyze      - Analyze term annotations (legacy)"
        echo "  test-metrics - Test enhanced metrics functionality"
        echo "  shell        - Open interactive shell"
        echo "  all          - Run complete workflow (default)"
        echo ""
        echo "Options:"
        echo "  --nohup      - Run in background with nohup (survives SSH disconnection)"
        echo ""
        echo "Examples:"
        echo "  $0 all                    # Run complete workflow in foreground"
        echo "  $0 all --nohup           # Run complete workflow in background"
        echo "  $0 enhanced --nohup      # Run enhanced analysis in background"
        exit 1
        ;;
esac

echo ""
echo "✅ Task completed successfully!"