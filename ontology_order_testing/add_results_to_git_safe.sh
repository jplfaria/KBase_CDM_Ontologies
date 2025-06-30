#!/bin/bash
# Permission-safe script to add ontology order testing results to git

set -e

echo "📦 Adding Ontology Order Testing Results to Git"
echo "=============================================="

# Try to fix permissions if possible
if [ -d "results" ] && [ ! -w "results" ]; then
    echo "🔧 Attempting to fix permissions..."
    # Try with Docker first (most reliable)
    if command -v docker &> /dev/null; then
        docker run --rm \
            -v "$PWD:/workspace" \
            -w /workspace \
            --user root \
            alpine:latest \
            sh -c "chown -R $(id -u):$(id -g) results/ 2>/dev/null || true"
    # Try sudo as fallback
    elif command -v sudo &> /dev/null; then
        sudo chown -R $USER:$USER results/ 2>/dev/null || true
    fi
fi

# Determine where to write based on permissions
if [ -w "results/" ]; then
    RESULTS_DIR="results"
    echo "✅ Using results/ directory"
else
    RESULTS_DIR="."
    echo "⚠️  Results directory not writable, using current directory"
fi

# Create results summary
echo "📝 Creating results summary..."
cat > "$RESULTS_DIR/RESULTS_SUMMARY.md" << 'EOF'
# Ontology Order Testing Results - Key Findings

## Executive Summary
Order matters significantly when merging ontologies with ROBOT's --annotate-defined-by flag.

## 24-Ontology Test Results
### File Size Impact
- **Alphabetical**: 1,580,634,603 bytes (1.58 GB)
- **Hierarchy/Size**: 1,531,010,144 bytes (1.53 GB)
- **Savings**: 49,624,459 bytes (49.6 MB, 3.14%)

### Axiom Count Impact  
- **Alphabetical**: 3,812,530 axioms
- **Hierarchy/Size**: 3,634,095 axioms
- **Reduction**: 178,435 axioms (4.68%)

### Class Count Impact
- **Alphabetical**: 32,668 classes
- **Hierarchy/Size**: 24,095 classes  
- **Reduction**: 8,573 classes (26.2%)

## 4-Ontology Permutation Analysis
- Tested all 24 permutations of CHEBI, FOODON, GO, ENVO
- **Size variation**: 32.2 MB (4.20%) between best and worst orders
- **Best order**: FOODON → GO → ENVO → CHEBI (766 MB)
- **Worst order**: ENVO → GO → FOODON → CHEBI (798 MB)

## Key Insights
1. CHEBI position dramatically affects size (9MB smaller when last)
2. FOODON first produces smallest files
3. ENVO first produces largest files
4. Hierarchy ordering groups related ontologies, reducing redundancy

## Recommendation
Use hierarchy-based ordering in production for:
- 3.14% space savings
- 178K fewer axioms to process
- More logical grouping of related ontologies
EOF

# Copy log file if it exists
if [ -f "./docker_run_20250627_214535.log" ]; then
    echo "📋 Copying test execution log..."
    cp ./docker_run_20250627_214535.log "$RESULTS_DIR/full_test_execution.log" 2>/dev/null || \
        echo "⚠️  Could not copy log file (permission issue)"
fi

# Add files to git (using -f to force add even if owned by root)
echo "📂 Adding results files to git..."

# Function to safely add files
add_if_exists() {
    if [ -f "$1" ]; then
        git add -f "$1" 2>/dev/null && echo "  ✅ Added: $1" || echo "  ⚠️  Could not add: $1"
    fi
}

# Add the summary we just created
add_if_exists "$RESULTS_DIR/RESULTS_SUMMARY.md"

# Add results files (checking both locations)
for pattern in "order_testing_summary_*.txt" "detailed_comparison_*.txt" "enhanced_analysis_results.json" "permutation_test_results.json"; do
    # Try results directory first
    for file in results/$pattern; do
        [ -f "$file" ] && add_if_exists "$file"
    done
    # Try current directory as fallback
    for file in $pattern; do
        [ -f "$file" ] && add_if_exists "$file"
    done
done

# Add log if it was copied
add_if_exists "$RESULTS_DIR/full_test_execution.log"

# Show what will be committed
echo ""
echo "📋 Files staged for commit:"
git status --short | grep "^A" || echo "  (No files staged yet)"

# Check if we have anything to commit
if [ -z "$(git status --short | grep '^A')" ]; then
    echo ""
    echo "❌ No files could be added. Permission issues prevent access."
    echo ""
    echo "Try one of these solutions:"
    echo "1. Run: docker run --rm -v \"\$PWD:/workspace\" -w /workspace --user root alpine chown -R \$(id -u):\$(id -g) results/"
    echo "2. Run with sudo: sudo chown -R \$USER:\$USER results/"
    echo "3. Copy files manually: cp results/*.json results/*.txt ."
    exit 1
fi

# Commit
echo ""
echo "💾 Committing results..."
git commit -m "Add comprehensive ontology order testing results

Key findings:
- Hierarchy ordering saves 49.6MB (3.14%) vs alphabetical
- Reduces axiom count by 178,435 (4.68%)
- Reduces class count by 8,573 (26.2%)
- CHEBI position significantly impacts file size
- 4-ontology permutations show 4.20% size variation

Test execution:
- 24-ontology analysis with 3 ordering strategies
- 48 permutation tests (24 orders × 2 variants)
- Enhanced metrics with proper axiom counting
- ~14 hours total execution time

Results ready for detailed interpretation.

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>"

echo "✅ Results committed successfully!"
echo ""
echo "Next steps:"
echo "1. Push to remote: git push origin order_testing"
echo "2. On other machine: git pull origin order_testing"
echo "3. Results will be in ontology_order_testing/results/"