#!/bin/bash
# Script to add ontology order testing results to git

set -e

echo "📦 Adding Ontology Order Testing Results to Git"
echo "=============================================="

# Create results summary
echo "📝 Creating results summary..."
cat > results/RESULTS_SUMMARY.md << 'EOF'
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
    cp ./docker_run_20250627_214535.log results/full_test_execution.log
else
    echo "⚠️  Log file not found, skipping..."
fi

# Add files to git
echo "📂 Adding results files to git..."
git add -f results/RESULTS_SUMMARY.md
git add -f results/order_testing_summary_*.txt
git add -f results/detailed_comparison_*.txt  
git add -f results/enhanced_analysis_results.json
git add -f results/permutation_test_results.json

# Add log if it was copied
if [ -f "results/full_test_execution.log" ]; then
    git add -f results/full_test_execution.log
fi

# Show what will be committed
echo ""
echo "📋 Files to be committed:"
git status --short | grep "^A"

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